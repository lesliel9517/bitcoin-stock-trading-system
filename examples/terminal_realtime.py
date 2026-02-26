"""
Real-time Terminal Visualization

Live trading dashboard with real-time charts in terminal
"""

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
import pandas as pd
import yfinance as yf
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.console import Console
import plotext as plt

from src.backtest.engine import BacktestEngine
from src.strategies.examples.adaptive_strategy import AdaptiveStrategy
from src.core.types import OrderSide
from src.utils.logger import logger


class RealtimeDashboard:
    """Real-time trading dashboard"""

    def __init__(self):
        self.console = Console()
        self.prices = []
        self.timestamps = []
        self.equity_values = []
        self.trades = []
        self.current_stats = {
            'price': 0,
            'equity': 100000,
            'pnl': 0,
            'pnl_pct': 0,
            'trades': 0,
            'position': '空仓'
        }

    def create_layout(self) -> Layout:
        """Create dashboard layout"""
        layout = Layout()

        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=3)
        )

        layout["main"].split_row(
            Layout(name="chart", ratio=2),
            Layout(name="stats", ratio=1)
        )

        return layout

    def render_header(self) -> Panel:
        """Render header"""
        text = Text()
        text.append("🚀 实时交易监控系统", style="bold cyan")
        text.append(" | ", style="white")
        text.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), style="dim")

        return Panel(text, style="bold blue")

    def render_chart(self) -> Panel:
        """Render price chart"""
        plt.clf()

        if len(self.prices) > 0:
            # Plot price line
            x_data = list(range(len(self.prices)))
            plt.plot(x_data, self.prices, label="价格", color="cyan")

            # Mark trades
            for trade in self.trades:
                idx = trade['index']
                if idx < len(self.prices):
                    if trade['side'] == 'buy':
                        plt.scatter([idx], [trade['price']], marker="^", color="green", label="买入")
                    else:
                        plt.scatter([idx], [trade['price']], marker="v", color="red", label="卖出")

            plt.title("价格走势图")
            plt.xlabel("时间")
            plt.ylabel("价格 (USD)")
            plt.theme("dark")

        chart_str = plt.build()
        return Panel(chart_str, title="[bold cyan]分时图", border_style="cyan")

    def render_stats(self) -> Panel:
        """Render statistics"""
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("指标", style="dim")
        table.add_column("数值", style="bold")

        stats = self.current_stats

        # Current price
        price_style = "white"
        table.add_row("当前价格", f"${stats['price']:,.2f}", style=price_style)

        # Equity
        table.add_row("账户总值", f"${stats['equity']:,.2f}", style="yellow")

        # PnL
        pnl_style = "green" if stats['pnl'] >= 0 else "red"
        pnl_sign = "+" if stats['pnl'] >= 0 else ""
        table.add_row(
            "总盈亏",
            f"{pnl_sign}${stats['pnl']:,.2f} ({pnl_sign}{stats['pnl_pct']:.2f}%)",
            style=pnl_style
        )

        # Trades
        table.add_row("交易次数", str(stats['trades']), style="cyan")

        # Position
        pos_style = "green" if "持仓" in stats['position'] else "dim"
        table.add_row("持仓状态", stats['position'], style=pos_style)

        return Panel(table, title="[bold yellow]实时数据", border_style="yellow")

    def render_footer(self) -> Panel:
        """Render footer"""
        if len(self.trades) > 0:
            last_trade = self.trades[-1]
            side_text = "买入" if last_trade['side'] == 'buy' else "卖出"
            side_style = "green" if last_trade['side'] == 'buy' else "red"

            text = Text()
            text.append("最近交易: ", style="dim")
            text.append(side_text, style=f"bold {side_style}")
            text.append(f" @ ${last_trade['price']:,.2f}", style="white")

            if 'pnl_pct' in last_trade and last_trade['pnl_pct'] != 0:
                pnl_style = "green" if last_trade['pnl_pct'] > 0 else "red"
                pnl_sign = "+" if last_trade['pnl_pct'] > 0 else ""
                text.append(f" | 盈亏: {pnl_sign}{last_trade['pnl_pct']:.2f}%", style=pnl_style)
        else:
            text = Text("等待交易信号...", style="dim")

        return Panel(text, style="dim")

    def update_data(self, price: float, equity: float, position: str):
        """Update data"""
        self.prices.append(price)
        self.timestamps.append(datetime.now())
        self.equity_values.append(equity)

        # Keep last 100 points
        if len(self.prices) > 100:
            self.prices = self.prices[-100:]
            self.timestamps = self.timestamps[-100:]
            self.equity_values = self.equity_values[-100:]

        # Update stats
        initial_capital = 100000
        pnl = equity - initial_capital
        pnl_pct = (pnl / initial_capital) * 100

        self.current_stats = {
            'price': price,
            'equity': equity,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'trades': len(self.trades),
            'position': position
        }

    def add_trade(self, side: str, price: float, pnl_pct: float = 0):
        """Add trade"""
        self.trades.append({
            'index': len(self.prices) - 1,
            'side': side,
            'price': price,
            'pnl_pct': pnl_pct
        })

    def render(self) -> Layout:
        """Render dashboard"""
        layout = self.create_layout()

        layout["header"].update(self.render_header())
        layout["chart"].update(self.render_chart())
        layout["stats"].update(self.render_stats())
        layout["footer"].update(self.render_footer())

        return layout


async def main():
    """Run real-time trading with terminal visualization"""

    console = Console()

    console.print("\n[bold cyan]🚀 实时交易可视化系统[/bold cyan]\n")
    console.print("[dim]正在初始化...[/dim]\n")

    # Download data
    symbol = "BTC-USD"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)

    ticker = yf.Ticker(symbol)
    data = ticker.history(start=start_date, end=end_date, interval="1d")

    if data.empty:
        console.print("[red]数据下载失败[/red]")
        return

    data.columns = [col.lower() for col in data.columns]
    data = data[['open', 'high', 'low', 'close', 'volume']]

    console.print(f"[green]✓[/green] 已下载 {len(data)} 天数据\n")

    # Initialize engine
    engine = BacktestEngine(
        initial_capital=Decimal(100000),
        commission=Decimal("0.001"),
        slippage=Decimal("0.0005")
    )

    strategy_config = {
        'parameters': {
            'ma_short': 10,
            'ma_long': 30,
            'volatility_window': 20,
            'trend_window': 50
        }
    }
    strategy = AdaptiveStrategy('adaptive_realtime', strategy_config)
    engine.set_strategy(strategy)

    # Create dashboard
    dashboard = RealtimeDashboard()

    # Trading simulation
    position = Decimal(0)
    entry_price = None

    with Live(dashboard.render(), refresh_per_second=4, console=console) as live:
        for i in range(len(data)):
            row = data.iloc[i]
            timestamp = row.name if isinstance(row.name, datetime) else datetime.now()
            price = Decimal(str(row['close']))

            # Update portfolio
            engine.portfolio.update_prices({symbol: price})
            current_equity = engine.portfolio.get_total_value()

            # Position status
            position_status = f"持仓 {float(position):.4f} BTC" if position > 0 else "空仓"

            # Update dashboard
            dashboard.update_data(
                float(price),
                float(current_equity),
                position_status
            )

            # Generate signals
            temp_data = data.iloc[:i+1].copy()
            engine.strategy.update_data(symbol, temp_data)

            if len(temp_data) >= 30:
                data_with_signals = engine.strategy.calculate_indicators(temp_data)

                if len(data_with_signals) >= 2:
                    current = data_with_signals.iloc[-1]
                    previous = data_with_signals.iloc[-2]

                    # Buy signal
                    if (previous['ma_short'] <= previous['ma_long'] and
                        current['ma_short'] > current['ma_long'] and
                        position == 0):

                        quantity = engine._calculate_position_size(price)
                        if quantity > 0:
                            engine._execute_trade(symbol, OrderSide.BUY, quantity, price, timestamp, 'yfinance')
                            position = quantity
                            entry_price = price

                            dashboard.add_trade('buy', float(price))

                    # Sell signal
                    elif (previous['ma_short'] >= previous['ma_long'] and
                          current['ma_short'] < current['ma_long'] and
                          position > 0):

                        pnl_pct = float((price - entry_price) / entry_price * 100) if entry_price else 0

                        engine._execute_trade(symbol, OrderSide.SELL, position, price, timestamp, 'yfinance')

                        dashboard.add_trade('sell', float(price), pnl_pct)

                        position = Decimal(0)
                        entry_price = None

            # Update display
            live.update(dashboard.render())

            # Simulate real-time delay
            await asyncio.sleep(0.3)

    # Close position if needed
    if position > 0:
        final_price = Decimal(str(data.iloc[-1]['close']))
        final_timestamp = data.index[-1]
        engine._execute_trade(symbol, OrderSide.SELL, position, final_price, final_timestamp, 'yfinance')

    # Final summary
    final_equity = engine.portfolio.get_total_value()
    final_pnl = float(final_equity - engine.initial_capital)
    final_return = (final_pnl / 100000) * 100

    console.print("\n[bold cyan]交易完成[/bold cyan]\n")
    console.print(f"初始资金: [yellow]${100000:,.2f}[/yellow]")
    console.print(f"最终资金: [yellow]${float(final_equity):,.2f}[/yellow]")

    pnl_style = "green" if final_pnl >= 0 else "red"
    pnl_sign = "+" if final_pnl >= 0 else ""
    console.print(f"总收益: [{pnl_style}]{pnl_sign}${final_pnl:,.2f} ({pnl_sign}{final_return:.2f}%)[/{pnl_style}]")
    console.print(f"交易次数: [cyan]{len(engine.trades)}[/cyan]\n")


if __name__ == "__main__":
    asyncio.run(main())
