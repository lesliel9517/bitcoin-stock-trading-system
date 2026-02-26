"""
Real-time Trading Dashboard for CLI

Professional dashboard with charts and trading info
"""

import asyncio
from datetime import datetime
from decimal import Decimal
from collections import deque
import plotext as plt
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.live import Live

from ..core.event_bus import EventBus
from ..core.event import MarketEvent, SignalEvent, EventType
from ..trading.portfolio import Portfolio
from ..strategies.base import Strategy
from ..utils.logger import logger


class RealtimeDashboard:
    """Real-time trading dashboard with visualization"""

    def __init__(self, event_bus: EventBus, portfolio: Portfolio, strategy: Strategy, max_points=100):
        self.event_bus = event_bus
        self.portfolio = portfolio
        self.strategy = strategy
        self.console = Console()
        self.max_points = max_points

        # Data buffers
        self.timestamps = deque(maxlen=max_points)
        self.prices = deque(maxlen=max_points)
        self.ma_short = deque(maxlen=max_points)
        self.ma_long = deque(maxlen=max_points)

        # OHLC for candlestick
        self.ohlc_data = deque(maxlen=50)
        self.candle_buffer = {'open': 0, 'high': 0, 'low': float('inf'), 'close': 0, 'count': 0}

        # Trading data
        self.trades = []
        self.signals = []

        # Stats
        self.current_price = 0
        self.price_change = 0
        self.price_change_pct = 0
        self.high_24h = 0
        self.low_24h = 0
        self.position = "空仓"
        self.total_trades = 0
        self.win_rate = 0
        self.market_regime = "未知"
        self.volatility = "正常"

    def create_layout(self) -> Layout:
        """Create dashboard layout"""
        layout = Layout()

        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body", ratio=1)
        )

        layout["body"].split_row(
            Layout(name="charts", ratio=3),
            Layout(name="info", ratio=1)
        )

        layout["charts"].split_column(
            Layout(name="timeshare", ratio=1),
            Layout(name="candlestick", ratio=1)
        )

        return layout

    def render_header(self) -> Panel:
        """Render header"""
        price_color = "green" if self.price_change >= 0 else "red"
        change_sign = "+" if self.price_change >= 0 else ""

        text = Text()
        text.append("BTC-USD ", style="bold cyan")
        text.append(f"${self.current_price:,.2f} ", style=f"bold {price_color}")
        text.append(f"{change_sign}{self.price_change_pct:.2f}% ", style=price_color)
        text.append(f"| H: ${self.high_24h:,.0f} ", style="dim")
        text.append(f"L: ${self.low_24h:,.0f} ", style="dim")
        text.append(f"| {datetime.now().strftime('%H:%M:%S')}", style="dim")

        return Panel(text, style="bold blue")

    def render_timeshare_chart(self) -> Panel:
        """Render time-sharing chart"""
        plt.clf()

        if len(self.prices) > 1:
            x_data = list(range(len(self.prices)))

            # Price line
            plt.plot(x_data, list(self.prices), label="价格", color="cyan", marker="dot")

            # Moving averages
            if len(self.ma_short) > 0:
                plt.plot(x_data, list(self.ma_short), label="MA短", color="magenta")
            if len(self.ma_long) > 0:
                plt.plot(x_data, list(self.ma_long), label="MA长", color="yellow")

            # Trade markers
            for trade in self.trades[-10:]:
                if 0 <= trade['index'] < len(self.prices):
                    marker = "^" if trade['side'] == 'buy' else "v"
                    color = "green" if trade['side'] == 'buy' else "red"
                    plt.scatter([trade['index']], [trade['price']], marker=marker, color=color)

            plt.title("分时图")
            plt.theme("dark")

        return Panel(plt.build(), title="[cyan]实时走势[/cyan]", border_style="cyan")

    def render_candlestick_chart(self) -> Panel:
        """Render candlestick chart"""
        plt.clf()

        if len(self.ohlc_data) > 1:
            x_data = list(range(len(self.ohlc_data)))
            highs = [d['high'] for d in self.ohlc_data]
            lows = [d['low'] for d in self.ohlc_data]
            closes = [d['close'] for d in self.ohlc_data]

            # High-low bars
            for i, (h, l) in enumerate(zip(highs, lows)):
                plt.plot([i, i], [l, h], color="white")

            # Close prices
            plt.plot(x_data, closes, marker="dot", color="cyan")

            plt.title("K线图")
            plt.theme("dark")

        return Panel(plt.build(), title="[yellow]K线走势[/yellow]", border_style="yellow")

    def render_info_panel(self) -> Panel:
        """Render info panel"""
        table = Table.grid(padding=(0, 2))
        table.add_column(style="dim", justify="left")
        table.add_column(style="bold", justify="right")

        # Account
        table.add_row("", "[bold yellow]账户信息[/bold yellow]")
        equity = float(self.portfolio.get_total_value())
        table.add_row("总资产", f"${equity:,.2f}")

        pnl = equity - float(self.portfolio.initial_balance)
        pnl_pct = (pnl / float(self.portfolio.initial_balance)) * 100
        pnl_color = "green" if pnl >= 0 else "red"
        pnl_sign = "+" if pnl >= 0 else ""
        table.add_row("盈亏", f"[{pnl_color}]{pnl_sign}${pnl:,.2f}[/{pnl_color}]")
        table.add_row("收益率", f"[{pnl_color}]{pnl_sign}{pnl_pct:.2f}%[/{pnl_color}]")

        table.add_row("", "")

        # Position
        table.add_row("", "[bold cyan]持仓信息[/bold cyan]")
        pos_color = "green" if "持仓" in self.position else "dim"
        table.add_row("状态", f"[{pos_color}]{self.position}[/{pos_color}]")

        table.add_row("", "")

        # Trading stats
        table.add_row("", "[bold magenta]交易统计[/bold magenta]")
        table.add_row("交易次数", str(self.total_trades))
        table.add_row("胜率", f"{self.win_rate:.1f}%")

        table.add_row("", "")

        # Market state
        table.add_row("", "[bold white]市场状态[/bold white]")
        table.add_row("趋势", self.market_regime)
        table.add_row("波动", self.volatility)

        table.add_row("", "")

        # Recent trades
        if len(self.trades) > 0:
            table.add_row("", "[bold red]最近交易[/bold red]")
            for trade in self.trades[-3:]:
                side_text = "买" if trade['side'] == 'buy' else "卖"
                side_color = "green" if trade['side'] == 'buy' else "red"
                table.add_row(f"[{side_color}]{side_text}[/{side_color}]", f"${trade['price']:,.0f}")

        return Panel(table, title="[bold green]实时数据[/bold green]", border_style="green")

    def update_price(self, price: float):
        """Update price data"""
        self.prices.append(price)
        self.current_price = price

        # Update 24h high/low
        if len(self.prices) > 0:
            self.high_24h = max(self.prices)
            self.low_24h = min(self.prices)

            if len(self.prices) > 1:
                first_price = self.prices[0]
                self.price_change = price - first_price
                self.price_change_pct = (self.price_change / first_price) * 100

        # Update OHLC
        if self.candle_buffer['count'] == 0:
            self.candle_buffer['open'] = price
            self.candle_buffer['high'] = price
            self.candle_buffer['low'] = price

        self.candle_buffer['high'] = max(self.candle_buffer['high'], price)
        self.candle_buffer['low'] = min(self.candle_buffer['low'], price)
        self.candle_buffer['close'] = price
        self.candle_buffer['count'] += 1

        if self.candle_buffer['count'] >= 10:
            self.ohlc_data.append({
                'open': self.candle_buffer['open'],
                'high': self.candle_buffer['high'],
                'low': self.candle_buffer['low'],
                'close': self.candle_buffer['close']
            })
            self.candle_buffer = {'open': 0, 'high': 0, 'low': float('inf'), 'close': 0, 'count': 0}

    def update_ma(self, ma_short: float, ma_long: float):
        """Update moving averages"""
        self.ma_short.append(ma_short)
        self.ma_long.append(ma_long)

    def add_trade(self, side: str, price: float):
        """Add trade"""
        self.trades.append({
            'index': len(self.prices) - 1,
            'side': side,
            'price': price
        })
        self.total_trades = len(self.trades)

        # Calculate win rate
        if len(self.trades) >= 2:
            wins = 0
            for i in range(1, len(self.trades), 2):
                if i < len(self.trades):
                    buy_price = self.trades[i-1]['price']
                    sell_price = self.trades[i]['price']
                    if sell_price > buy_price:
                        wins += 1
            self.win_rate = (wins / (len(self.trades) // 2)) * 100 if len(self.trades) >= 2 else 0

    def update_position(self, position: str):
        """Update position"""
        self.position = position

    def update_market_state(self, regime: str, volatility: str):
        """Update market state"""
        regime_map = {
            'trending_up': '上涨趋势',
            'trending_down': '下跌趋势',
            'ranging': '震荡'
        }
        self.market_regime = regime_map.get(regime, regime)

        vol_map = {
            'high': '高波动',
            'low': '低波动',
            'normal': '正常'
        }
        self.volatility = vol_map.get(volatility, volatility)

    def render(self) -> Layout:
        """Render dashboard"""
        layout = self.create_layout()

        layout["header"].update(self.render_header())
        layout["timeshare"].update(self.render_timeshare_chart())
        layout["candlestick"].update(self.render_candlestick_chart())
        layout["info"].update(self.render_info_panel())

        return layout

    async def run(self, duration: int = None):
        """Run dashboard"""
        self.console.print("\n[bold cyan]启动实时可视化仪表板...[/bold cyan]\n")

        # Subscribe to events
        async def handle_market_event(event: MarketEvent):
            price = float(event.price)
            self.update_price(price)

            # Update MA if available
            symbol = event.symbol
            if hasattr(self.strategy, '_data_cache') and symbol in self.strategy._data_cache:
                data = self.strategy._data_cache[symbol]
                if len(data) >= 30:
                    data_with_ind = self.strategy.calculate_indicators(data.copy())
                    if len(data_with_ind) > 0:
                        latest = data_with_ind.iloc[-1]
                        if 'ma_short' in latest and 'ma_long' in latest:
                            self.update_ma(float(latest['ma_short']), float(latest['ma_long']))

            # Update position
            positions = self.portfolio.get_all_positions()
            if len(positions) > 0:
                pos = positions[0]
                self.update_position(f"持仓 {float(pos.quantity):.4f} BTC")
            else:
                self.update_position("空仓")

            # Update market state
            if hasattr(self.strategy, 'market_regime'):
                self.update_market_state(self.strategy.market_regime, self.strategy.volatility_regime)

        async def handle_signal_event(event: SignalEvent):
            if event.signal_type in ['buy', 'sell']:
                # Get current price
                if len(self.prices) > 0:
                    self.add_trade(event.signal_type, self.prices[-1])

        self.event_bus.subscribe(EventType.MARKET, handle_market_event)
        self.event_bus.subscribe(EventType.SIGNAL, handle_signal_event)

        # Run with live display
        start_time = asyncio.get_event_loop().time()

        with Live(self.render(), refresh_per_second=2, console=self.console) as live:
            try:
                while True:
                    # Check duration
                    if duration:
                        elapsed = asyncio.get_event_loop().time() - start_time
                        if elapsed >= duration:
                            break

                    # Update display
                    live.update(self.render())

                    await asyncio.sleep(0.5)

            except KeyboardInterrupt:
                self.console.print("\n[yellow]停止可视化...[/yellow]")

        # Print summary
        self.print_summary()

    def print_summary(self):
        """Print final summary"""
        self.console.print("\n[bold cyan]交易总结[/bold cyan]\n")

        equity = float(self.portfolio.get_total_value())
        initial = float(self.portfolio.initial_balance)
        pnl = equity - initial
        pnl_pct = (pnl / initial) * 100

        self.console.print(f"初始资金: [yellow]${initial:,.2f}[/yellow]")
        self.console.print(f"最终资金: [yellow]${equity:,.2f}[/yellow]")

        pnl_color = "green" if pnl >= 0 else "red"
        pnl_sign = "+" if pnl >= 0 else ""
        self.console.print(f"总收益: [{pnl_color}]{pnl_sign}${pnl:,.2f} ({pnl_sign}{pnl_pct:.2f}%)[/{pnl_color}]")
        self.console.print(f"交易次数: [cyan]{self.total_trades}[/cyan]")
        self.console.print(f"胜率: [cyan]{self.win_rate:.1f}%[/cyan]\n")
