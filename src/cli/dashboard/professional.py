"""
Professional Real-time Trading Dashboard

A rich terminal UI for monitoring live trading with candlestick charts,
real-time metrics, and trade history.
"""

from datetime import datetime
from collections import deque
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


class ProfessionalDashboard:
    """Professional real-time trading dashboard"""

    def __init__(self, max_points=100):
        self.console = Console()
        self.max_points = max_points

        # Data buffers for chart (real-time, per second)
        self.timestamps = deque(maxlen=max_points)
        self.prices = deque(maxlen=max_points)  # Real-time prices (per second)
        self.volumes = deque(maxlen=max_points)
        self.ma_short = deque(maxlen=max_points)
        self.ma_long = deque(maxlen=max_points)

        # OHLC data for candlestick
        self.ohlc_data = deque(maxlen=50)

        # Trading data
        self.trades = []
        self.signals = []

        # Real-time logs (all events)
        self.logs = deque(maxlen=50)  # Keep last 50 log entries

        # Additional market data
        self.open_price = 0  # Today's opening price
        self.prev_close = 0  # Yesterday's close
        self.all_time_high = 0  # Historical highest price
        self.current_time = ""  # Trading time display

        # Stats
        self.current_price = 0
        self.price_change = 0
        self.price_change_pct = 0
        self.high_24h = 0
        self.low_24h = 0
        self.volume_24h = 0
        self.equity = 100000
        self.pnl = 0
        self.pnl_pct = 0
        self.cash_balance = 100000
        self.position = "空仓"
        self.total_trades = 0
        self.win_rate = 0

        # Profit/Loss tracking
        self.total_profit = 0  # 累积盈利
        self.total_loss = 0    # 累积亏损
        self.trade_history = deque(maxlen=20)  # 保留最近20条交易记录

        # Daily baseline price (for calculating daily change)
        self.price_24h_start = 0  # Today's opening price at 00:00
        self.last_reset_date = None  # Track when we last reset the baseline

        # Market state
        self.market_regime = "未知"
        self.volatility = "正常"

        # Time range selection
        self.time_range = "live"  # live, day, week, month, year
        self.time_range_data = {
            'live': {'prices': deque(maxlen=120), 'timestamps': deque(maxlen=120)},
            'day': {'prices': [], 'timestamps': []},
            'week': {'prices': [], 'timestamps': []},
            'month': {'prices': [], 'timestamps': []},
            'year': {'prices': [], 'timestamps': []}
        }

        # Today's opening price (for calculating daily change)
        self.today_open_price = 0

    def create_layout(self) -> Layout:
        """Create dashboard layout"""
        layout = Layout()

        layout.split_column(
            Layout(name="body", ratio=1)
        )

        layout["body"].split_row(
            Layout(name="left", ratio=2),
            Layout(name="right", ratio=1)
        )

        # Left side: chart + trade log
        layout["left"].split_column(
            Layout(name="chart", ratio=2),
            Layout(name="trade_log", ratio=3)
        )

        return layout

    def render_header(self) -> Panel:
        """Render header with key metrics and time range selector"""
        # Price with color
        price_color = "green" if self.price_change >= 0 else "red"
        change_sign = "+" if self.price_change >= 0 else ""

        text = Text()
        text.append("BTC-USD ", style="bold cyan")
        text.append(f"${self.current_price:,.2f} ", style=f"bold {price_color}")
        text.append(f"{change_sign}{self.price_change_pct:.2f}% ", style=price_color)
        text.append(f"| H: ${self.high_24h:,.0f} ", style="dim")
        text.append(f"L: ${self.low_24h:,.0f} ", style="dim")

        # Time range selector
        text.append(" | ", style="dim")
        time_ranges = ["live", "day", "week", "month", "year"]
        for tr in time_ranges:
            if tr == self.time_range:
                text.append(f"[{tr.upper()}]", style="bold yellow")
            else:
                text.append(f" {tr} ", style="dim")

        text.append(f" | {datetime.now().strftime('%H:%M:%S')}", style="dim")

        return Panel(text, style="bold blue")

    def render_combined_chart(self) -> Panel:
        """Render smooth line chart with connected dots (Futu-style)"""
        current_price = self.current_price
        price_change_24h = self.price_change
        price_change_pct_24h = self.price_change_pct
        change_sign = "+" if price_change_24h >= 0 else ""
        trend_color = "green" if price_change_24h >= 0 else "red"

        header_display = f"[bold white]${current_price:,.2f}[/bold white]  [{trend_color}]{change_sign}${price_change_24h:,.2f} ({change_sign}{price_change_pct_24h:.2f}%)[/{trend_color}]"

        # Get data
        if self.time_range == "live":
            prices_list = list(self.prices)[-60:]  # Last 60 seconds
        else:
            range_data = self.time_range_data.get(self.time_range, {})
            prices_list = range_data.get('prices', [])[-20:]

        if len(prices_list) < 2:
            return Panel(
                f"{header_display}\n\n等待数据...",
                title="[cyan]价格[/cyan]",
                border_style="cyan",
                padding=(1, 2)
            )

        # Calculate chart dimensions
        min_p = min(prices_list)
        max_p = max(prices_list)
        range_p = max_p - min_p if max_p > min_p else 1

        chart_height = 12
        chart_width = len(prices_list)

        # Create empty chart grid
        chart = [[" " for _ in range(chart_width)] for _ in range(chart_height)]

        # Plot points and connect with lines
        for i, price in enumerate(prices_list):
            # Calculate row position
            row = int(((price - min_p) / range_p) * (chart_height - 1))
            row = chart_height - 1 - row  # Flip vertically

            # Check if this is a trade point
            trade_at_index = None
            for trade in self.trades:
                if trade['index'] == len(self.prices) - len(prices_list) + i:
                    trade_at_index = trade
                    break

            # Determine color and marker
            if trade_at_index:
                # Trade markers: B for buy, S for sell
                if trade_at_index['side'] == 'buy':
                    chart[row][i] = "[bold blue]B[/bold blue]"
                else:
                    if trade_at_index.get('entry_price'):
                        if trade_at_index['price'] > trade_at_index['entry_price']:
                            chart[row][i] = "[bold green]S[/bold green]"
                        else:
                            chart[row][i] = "[bold red]S[/bold red]"
                    else:
                        chart[row][i] = "[bold red]S[/bold red]"
            else:
                # Regular price point - small dot
                if i > 0 and price > prices_list[i-1]:
                    color = "green"
                elif i > 0 and price < prices_list[i-1]:
                    color = "red"
                else:
                    color = "white"
                chart[row][i] = f"[{color}]·[/{color}]"

            # Connect to previous point with line
            if i > 0:
                prev_price = prices_list[i-1]
                prev_row = int(((prev_price - min_p) / range_p) * (chart_height - 1))
                prev_row = chart_height - 1 - prev_row

                # Determine line color
                if price > prices_list[i-1]:
                    line_color = "green"
                elif price < prices_list[i-1]:
                    line_color = "red"
                else:
                    line_color = "white"

                # Draw connecting line
                if prev_row < row:  # Going down
                    for r in range(prev_row + 1, row):
                        if chart[r][i] == " ":
                            chart[r][i] = f"[{line_color}]│[/{line_color}]"
                elif prev_row > row:  # Going up
                    for r in range(row + 1, prev_row):
                        if chart[r][i] == " ":
                            chart[r][i] = f"[{line_color}]│[/{line_color}]"

        # Build chart string with price labels and change percentage (only show highest and lowest)
        lines = []
        # Use price_24h_start as baseline (today's opening price at 00:00)
        baseline_price = self.price_24h_start if self.price_24h_start > 0 else self.current_price

        for row_idx, row in enumerate(chart):
            # Only show price labels with percentage for highest and lowest
            if row_idx == 0:
                # Highest price
                change_pct = ((max_p - baseline_price) / baseline_price * 100) if baseline_price > 0 else 0
                change_sign = "+" if change_pct >= 0 else ""
                label = f"${max_p:>8.2f} {change_sign}{change_pct:>5.2f}% │"
            elif row_idx == chart_height - 1:
                # Lowest price
                change_pct = ((min_p - baseline_price) / baseline_price * 100) if baseline_price > 0 else 0
                change_sign = "+" if change_pct >= 0 else ""
                label = f"${min_p:>8.2f} {change_sign}{change_pct:>5.2f}% │"
            else:
                # No label for middle rows
                label = " " * 22 + "│"

            lines.append(label + "".join(row))

        # Add baseline
        lines.append(" " * 22 + "└" + "─" * chart_width)

        # Add legend
        lines.append("")
        lines.append("[dim][blue]B[/blue]=买入  [green]S[/green]=卖出盈利  [red]S[/red]=卖出亏损[/dim]")

        chart_text = "\n".join(lines)

        return Panel(
            f"{header_display}\n\n{chart_text}",
            title="[cyan]价格走势[/cyan]",
            border_style="cyan",
            padding=(0, 1)
        )

    def add_log(self, message: str, log_type: str = "info"):
        """Add a log entry

        Args:
            message: Log message
            log_type: Type of log (info, trade, signal, market, error)
        """
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.logs.append({
            'time': timestamp,
            'message': message,
            'type': log_type
        })

    def render_trade_log(self) -> Panel:
        """Render scrolling real-time log (all events)"""
        if not self.logs:
            return Panel("等待系统事件...", title="[yellow]实时日志[/yellow]", border_style="yellow")

        lines = []
        for log in list(self.logs)[-15:]:  # Last 15 log entries
            timestamp = log['time']
            message = log['message']
            log_type = log['type']

            # Color based on log type
            if log_type == "trade":
                color = "blue" if "买入" in message else ("green" if "盈利" in message else "red")
            elif log_type == "signal":
                color = "yellow"
            elif log_type == "market":
                color = "cyan"
            elif log_type == "error":
                color = "red"
            else:
                color = "white"

            lines.append(f"[{color}]{timestamp} {message}[/{color}]")

        log_text = "\n".join(lines)
        return Panel(log_text, title="[yellow]实时日志[/yellow]", border_style="yellow")

    def render_timeshare_chart(self) -> Panel:
        """Render time-sharing chart (simple ASCII representation)"""
        if len(self.prices) < 2:
            return Panel("等待数据...", title="[cyan]分时[/cyan]", border_style="cyan")

        # Create simple ASCII chart
        prices_list = list(self.prices)
        min_price = min(prices_list)
        max_price = max(prices_list)
        price_range = max_price - min_price if max_price > min_price else 1

        lines = []
        height = 10

        # Create chart lines
        for row in range(height, -1, -1):
            line_chars = []
            threshold = min_price + (price_range * row / height)

            for price in prices_list[-50:]:  # Last 50 points
                if price >= threshold:
                    line_chars.append("█")
                else:
                    line_chars.append(" ")

            lines.append("".join(line_chars))

        # Add trade markers info
        if self.trades:
            recent_trades = [t for t in self.trades[-5:] if 0 <= t['index'] < len(self.prices)]
            if recent_trades:
                lines.append("")
                lines.append(f"最近交易: {len(recent_trades)}笔")

        chart_text = "\n".join(lines)
        return Panel(chart_text, title="[cyan]分时[/cyan]", border_style="cyan")

    def render_candlestick_chart(self) -> Panel:
        """Render candlestick chart (simple representation)"""
        if len(self.ohlc_data) < 2:
            return Panel("等待K线数据...", title="[yellow]K线[/yellow]", border_style="yellow")

        # Simple OHLC representation
        lines = []
        for candle in list(self.ohlc_data)[-20:]:  # Last 20 candles
            o, h, l, c = candle['open'], candle['high'], candle['low'], candle['close']

            # Determine color
            if c >= o:
                color = "green"
                body = "▲"
            else:
                color = "red"
                body = "▼"

            lines.append(f"[{color}]{body}[/{color}] H:{h:.0f} L:{l:.0f}")

        chart_text = "\n".join(lines[-10:])  # Show last 10
        return Panel(chart_text, title="[yellow]K线[/yellow]", border_style="yellow")

    def render_info_panel(self) -> Panel:
        """Render right-side info panel"""
        table = Table.grid(padding=(0, 2))
        table.add_column(style="dim", justify="left")
        table.add_column(style="bold", justify="left")

        # Account info
        table.add_row("", "[bold yellow]账户信息[/bold yellow]")
        table.add_row("总资产", f"${self.equity:,.2f}")
        table.add_row("现金", f"${self.cash_balance:,.2f}")

        # P&L (based on initial capital)
        pnl_color = "green" if self.pnl >= 0 else "red"
        pnl_sign = "+" if self.pnl >= 0 else ""
        table.add_row("盈亏", f"[{pnl_color}]{pnl_sign}${self.pnl:,.2f}[/{pnl_color}]")
        table.add_row("收益率", f"[{pnl_color}]{pnl_sign}{self.pnl_pct:.2f}%[/{pnl_color}]")

        table.add_row("", "")

        # Profit/Loss breakdown
        table.add_row("", "[bold green]收益统计[/bold green]")
        table.add_row("累积盈利", f"[green]+${self.total_profit:,.2f}[/green]")
        table.add_row("累积亏损", f"[red]-${self.total_loss:,.2f}[/red]")
        net_pnl = self.total_profit - self.total_loss
        net_color = "green" if net_pnl >= 0 else "red"
        net_sign = "+" if net_pnl >= 0 else ""
        table.add_row("净收益", f"[{net_color}]{net_sign}${net_pnl:,.2f}[/{net_color}]")

        table.add_row("", "")

        # Position info
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

        # Recent trades with PnL
        if len(self.trade_history) > 0:
            table.add_row("", "[bold red]最近交易[/bold red]")
            for trade in list(self.trade_history)[-3:]:  # Convert deque to list for slicing
                if trade['type'] == 'buy':
                    qty = trade.get('quantity', 0)
                    table.add_row(
                        "[blue]买入[/blue]",
                        f"${trade['price']:.2f} × {qty:.4f}"
                    )
                else:
                    qty = trade.get('quantity', 0)
                    pnl = trade.get('pnl', 0)
                    pnl_color = "green" if pnl > 0 else "red"
                    pnl_sign = "+" if pnl >= 0 else ""
                    table.add_row(
                        f"[{pnl_color}]卖出[/{pnl_color}]",
                        f"${trade['price']:.2f} × {qty:.4f} [{pnl_color}]{pnl_sign}${pnl:.2f}[/{pnl_color}]"
                    )

        return Panel(table, title="[bold green]实时数据[/bold green]", border_style="green")

    def update_price(self, price: float, volume: float = 0):
        """Update price data - real-time per second"""
        now = datetime.now()
        old_price = self.current_price
        self.current_price = price

        # Check if we need to reset daily baseline (at 00:00)
        current_date = now.date()
        if self.last_reset_date is None or self.last_reset_date != current_date:
            # New day - reset baseline to current price
            self.price_24h_start = price
            self.last_reset_date = current_date
            self.add_log(f"新的一天开始，基准价格: ${price:.2f}", "info")

        # Add to chart data (per second)
        self.timestamps.append(now)
        self.prices.append(price)
        self.volumes.append(volume)

        # Calculate change from daily baseline
        if self.price_24h_start > 0:
            self.price_change = price - self.price_24h_start
            self.price_change_pct = (self.price_change / self.price_24h_start) * 100
        else:
            # First price of the day
            self.price_24h_start = price
            self.price_change = 0
            self.price_change_pct = 0

        # Update 24h high/low
        if self.high_24h == 0:
            self.high_24h = price
            self.low_24h = price
        else:
            self.high_24h = max(self.high_24h, price)
            self.low_24h = min(self.low_24h, price)

        # Log significant price changes (>0.5%)
        if old_price > 0:
            change_pct = abs((price - old_price) / old_price) * 100
            if change_pct > 0.5:
                direction = "上涨" if price > old_price else "下跌"
                change_amount = price - old_price
                sign = "+" if change_amount >= 0 else ""
                self.add_log(f"价格{direction} {sign}${change_amount:.2f} ({sign}{change_pct:.2f}%) → ${price:.2f}", "market")

    def update_ohlc(self, open_p: float, high: float, low: float, close: float):
        """Update OHLC data for candlestick"""
        self.ohlc_data.append({
            'open': open_p,
            'high': high,
            'low': low,
            'close': close
        })

    def update_ma(self, ma_short: float, ma_long: float):
        """Update moving averages"""
        self.ma_short.append(ma_short)
        self.ma_long.append(ma_long)

    def add_trade(self, side: str, price: float, entry_price: float = None, quantity: float = 0):
        """Add trade and track P&L"""
        self.trades.append({
            'index': len(self.prices) - 1,
            'side': side,
            'price': price,
            'entry_price': entry_price,
            'time': datetime.now()
        })

        # Track detailed trade history with P&L
        if side == 'buy':
            self.trade_history.append({
                'type': 'buy',
                'price': price,
                'quantity': quantity,
                'time': datetime.now()
            })
            self.add_log(f"✓ 买入成功 @ ${price:,.2f}", "trade")
        else:
            pnl = 0
            if entry_price and quantity > 0:
                pnl = (price - entry_price) * quantity
                pnl_pct = (pnl / (entry_price * quantity)) * 100
                sign = "+" if pnl >= 0 else ""
                status = "盈利" if pnl > 0 else "亏损"

                # Update cumulative profit/loss
                if pnl > 0:
                    self.total_profit += pnl
                else:
                    self.total_loss += abs(pnl)

                self.add_log(f"✓ 卖出成功 @ ${price:,.2f} ({sign}${pnl:,.2f}, {sign}{pnl_pct:.2f}% {status})", "trade")
            else:
                self.add_log(f"✓ 卖出成功 @ ${price:,.2f}", "trade")

            self.trade_history.append({
                'type': 'sell',
                'price': price,
                'quantity': quantity,
                'pnl': pnl,
                'time': datetime.now()
            })

        self.total_trades = len([t for t in self.trade_history if t['type'] == 'sell'])

        # Calculate win rate
        sell_trades = [t for t in self.trade_history if t['type'] == 'sell']
        if len(sell_trades) > 0:
            wins = sum(1 for t in sell_trades if t.get('pnl', 0) > 0)
            self.win_rate = (wins / len(sell_trades)) * 100

    def update_stats(self, equity: float, cash: float, position: str, market_regime: str = "", volatility: str = ""):
        """Update statistics"""
        old_regime = self.market_regime
        old_volatility = self.volatility

        self.equity = equity
        self.cash_balance = cash
        initial_capital = 100000
        self.pnl = equity - initial_capital
        self.pnl_pct = (self.pnl / initial_capital) * 100
        self.position = position

        if market_regime:
            regime_map = {
                'trending_up': '上涨趋势',
                'trending_down': '下跌趋势',
                'ranging': '震荡'
            }
            new_regime = regime_map.get(market_regime, market_regime)
            if new_regime != old_regime and old_regime != "未知":
                current_price = self.current_price if self.current_price > 0 else 0
                self.add_log(f"市场状态变化: {new_regime} (当前价格: ${current_price:,.2f})", "market")
            self.market_regime = new_regime

        if volatility:
            vol_map = {
                'high': '高波动',
                'low': '低波动',
                'normal': '正常'
            }
            new_volatility = vol_map.get(volatility, volatility)
            if new_volatility != old_volatility and old_volatility != "正常":
                current_price = self.current_price if self.current_price > 0 else 0
                self.add_log(f"波动率变化: {new_volatility} (当前价格: ${current_price:,.2f})", "market")
            self.volatility = new_volatility

    async def fetch_historical_data(self, symbol: str, time_range: str):
        """Fetch historical data for different time ranges"""
        try:
            import ccxt
            exchange = ccxt.binance()

            # Define timeframe and limit based on time range
            timeframe_map = {
                'day': ('1h', 24),      # 24 hours, 1 hour per candle
                'week': ('1d', 7),      # 7 days, 1 day per candle
                'month': ('1d', 20),    # 20 days (limit to 20 points)
                'year': ('1w', 20)      # 20 weeks (limit to 20 points)
            }

            if time_range not in timeframe_map:
                return

            timeframe, limit = timeframe_map[time_range]

            # Fetch OHLCV data
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)

            # Extract closing prices
            prices = [candle[4] for candle in ohlcv]  # Close price
            timestamps = [candle[0] for candle in ohlcv]  # Timestamp

            # Store in time_range_data
            self.time_range_data[time_range] = {
                'prices': prices,
                'timestamps': timestamps
            }

            self.add_log(f"已加载 {time_range} 历史数据 ({len(prices)} 个数据点)", "info")

        except Exception as e:
            self.add_log(f"加载历史数据失败: {str(e)}", "error")
        """Switch time range display"""
        if range_key in ['live', 'day', 'week', 'month', 'year']:
            self.time_range = range_key
            self.add_log(f"切换到 {range_key} 视图", "info")

    def render(self) -> Layout:
        """Render complete dashboard"""
        layout = self.create_layout()

        layout["chart"].update(self.render_combined_chart())
        layout["trade_log"].update(self.render_trade_log())
        layout["right"].update(self.render_info_panel())

        return layout


