"""
Professional Real-time Trading Dashboard - Futu Style

深色主题纵向行情面板，参考富途牛牛设计
"""

from datetime import datetime
from collections import deque
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align


class ProfessionalDashboard:
    """Professional real-time trading dashboard - Futu style"""

    def __init__(self, max_points=100):
        self.console = Console()
        self.max_points = max_points

        # Data buffers
        self.timestamps = deque(maxlen=max_points)
        self.prices = deque(maxlen=max_points)
        self.volumes = deque(maxlen=max_points)
        self.ma_short = deque(maxlen=max_points)
        self.ma_long = deque(maxlen=max_points)

        # OHLC data
        self.ohlc_data = deque(maxlen=50)

        # Trading data
        self.trades = []
        self.signals = []
        self.logs = deque(maxlen=50)

        # Market data
        self.current_price = 0
        self.price_change = 0
        self.price_change_pct = 0
        self.high_24h = 0
        self.low_24h = 0
        self.volume_24h = 0
        self.open_price = 0
        self.prev_close = 0
        self.all_time_high = 0

        # Portfolio data
        self.equity = 100000
        self.pnl = 0
        self.pnl_pct = 0
        self.cash_balance = 100000
        self.position = "空仓"
        self.total_trades = 0
        self.win_rate = 0
        self.total_profit = 0
        self.total_loss = 0
        self.trade_history = deque(maxlen=20)

        # Daily baseline
        self.price_24h_start = 0
        self.last_reset_date = None

        # Market state
        self.market_regime = "未知"
        self.volatility = "正常"

        # Time range
        self.time_range = "1D"  # 1D, 5D, 日K, 周K, 月K, 年K
        self.time_ranges = ["1D", "5日", "日K", "周K", "月K", "年K"]

    def create_layout(self) -> Layout:
        """创建纵向布局"""
        layout = Layout()

        # 纵向分割：顶部标题栏 + 主体内容 + 底部操作栏
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body", ratio=1),
            Layout(name="footer", size=3)
        )

        # 主体内容纵向分割
        layout["body"].split_column(
            Layout(name="price_stats", size=8),      # 价格统计区
            Layout(name="period_tabs", size=3),      # 周期Tab
            Layout(name="chart", ratio=3),           # 主图表区
            Layout(name="volume", size=6),           # 成交量柱
            Layout(name="indicators", size=3),       # 技术指标
            Layout(name="logs", ratio=1)             # 日志区
        )

        return layout

    def render_header(self) -> Panel:
        """渲染顶部标题栏：返回 + 标题 + 搜索/收藏 + 时间"""
        text = Text()

        # 左侧：返回按钮 + 标题
        text.append("← ", style="dim")
        text.append("BTC 比特币", style="bold cyan")
        text.append("▼", style="dim")

        # 中间填充
        text.append("  " * 10)

        # 右侧：搜索/收藏图标
        text.append("🔍 ", style="dim")
        text.append("★", style="yellow")

        # 第二行：交易时间
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        time_text = Text(f"\n{current_time}", style="dim", justify="center")

        combined = Text()
        combined.append(text)
        combined.append(time_text)

        return Panel(
            Align.center(combined),
            style="on #1a1a1a",
            border_style="dim"
        )

    def render_price_stats(self) -> Panel:
        """渲染价格统计区：左侧大号价格 + 右侧统计字段"""
        # 创建表格布局
        table = Table.grid(padding=(0, 2))
        table.add_column(justify="left", ratio=2)   # 左侧价格区
        table.add_column(justify="left", ratio=1)   # 右侧第一列
        table.add_column(justify="left", ratio=1)   # 右侧第二列

        # 左侧：大号当前价格
        price_color = "green" if self.price_change >= 0 else "red"
        change_sign = "+" if self.price_change >= 0 else ""

        left_content = Text()
        left_content.append(f"${self.current_price:,.2f}\n", style=f"bold {price_color} on #1a1a1a")
        left_content.append(
            f"{change_sign}${self.price_change:,.2f}  {change_sign}{self.price_change_pct:.2f}%",
            style=f"{price_color}"
        )

        # 右侧第一列：统计字段
        col1 = Text()
        col1.append(f"最高  ${self.high_24h:,.2f}\n", style="dim")
        col1.append(f"今开  ${self.open_price:,.2f}\n", style="dim")
        col1.append(f"成交量  {self._format_volume(self.volume_24h)}\n", style="dim")
        col1.append(f"历史最高  ${self.all_time_high:,.2f}", style="dim")

        # 右侧第二列：统计字段
        col2 = Text()
        col2.append(f"最低  ${self.low_24h:,.2f}\n", style="dim")
        col2.append(f"昨收  ${self.prev_close:,.2f}\n", style="dim")

        # 24H涨跌
        change_24h_color = "green" if self.price_change >= 0 else "red"
        col2.append(
            f"24H涨跌  {change_sign}{self.price_change_pct:.2f}%\n",
            style=change_24h_color
        )
        col2.append(f"振幅  {self._calculate_amplitude():.2f}%", style="magenta")

        table.add_row(left_content, col1, col2)

        return Panel(
            table,
            style="on #1a1a1a",
            border_style="dim",
            padding=(1, 2)
        )

    def render_period_tabs(self) -> Panel:
        """渲染周期Tab：1D/5日/日K/周K等"""
        text = Text()

        for i, period in enumerate(self.time_ranges):
            if period == self.time_range:
                # 当前选中的周期：高亮显示
                text.append(f" {period} ", style="bold yellow on #333333")
            else:
                text.append(f" {period} ", style="dim")

            # 添加分隔符
            if i < len(self.time_ranges) - 1:
                text.append(" ", style="dim")

        return Panel(
            Align.center(text),
            style="on #1a1a1a",
            border_style="dim"
        )

    def render_chart(self) -> Panel:
        """渲染主图表区：蓝色价格线 + 橙色均线 + 刻度"""
        if len(self.prices) < 2:
            return Panel(
                Align.center(Text("等待数据...", style="dim")),
                title="[cyan]价格走势[/cyan]",
                style="on #1a1a1a",
                border_style="cyan"
            )

        # 获取数据
        prices_list = list(self.prices)[-60:]
        ma_short_list = list(self.ma_short)[-60:] if len(self.ma_short) > 0 else []
        ma_long_list = list(self.ma_long)[-60:] if len(self.ma_long) > 0 else []

        min_p = min(prices_list)
        max_p = max(prices_list)
        range_p = max_p - min_p if max_p > min_p else 1

        chart_height = 15
        chart_width = len(prices_list)

        # 创建图表矩阵
        chart = [[" " for _ in range(chart_width)] for _ in range(chart_height)]

        # 绘制价格线（蓝色）
        for i, price in enumerate(prices_list):
            row = int(((price - min_p) / range_p) * (chart_height - 1))
            row = chart_height - 1 - row
            chart[row][i] = "[blue]●[/blue]"

            # 连接线
            if i > 0:
                prev_price = prices_list[i-1]
                prev_row = int(((prev_price - min_p) / range_p) * (chart_height - 1))
                prev_row = chart_height - 1 - prev_row

                if prev_row < row:
                    for r in range(prev_row + 1, row):
                        if chart[r][i] == " ":
                            chart[r][i] = "[blue]│[/blue]"
                elif prev_row > row:
                    for r in range(row + 1, prev_row):
                        if chart[r][i] == " ":
                            chart[r][i] = "[blue]│[/blue]"

        # 绘制均线（橙色）
        if len(ma_short_list) == len(prices_list):
            for i, ma in enumerate(ma_short_list):
                if ma > 0:
                    row = int(((ma - min_p) / range_p) * (chart_height - 1))
                    row = chart_height - 1 - row
                    if 0 <= row < chart_height and chart[row][i] == " ":
                        chart[row][i] = "[yellow]·[/yellow]"

        # 构建图表字符串，添加左侧价格刻度和右侧涨跌幅刻度
        lines = []
        baseline_price = self.price_24h_start if self.price_24h_start > 0 else self.current_price

        for row_idx, row in enumerate(chart):
            # 左侧价格刻度（每3行显示一次）
            if row_idx % 3 == 0:
                price_at_row = max_p - (range_p * row_idx / (chart_height - 1))
                left_label = f"${price_at_row:>8.2f} │"
            else:
                left_label = " " * 11 + "│"

            # 右侧涨跌幅刻度（每3行显示一次）
            if row_idx % 3 == 0:
                price_at_row = max_p - (range_p * row_idx / (chart_height - 1))
                change_pct = ((price_at_row - baseline_price) / baseline_price * 100) if baseline_price > 0 else 0
                change_sign = "+" if change_pct >= 0 else ""
                right_label = f"│ {change_sign}{change_pct:>5.2f}%"
            else:
                right_label = "│"

            lines.append(left_label + "".join(row) + right_label)

        # 添加底部基线
        lines.append(" " * 11 + "└" + "─" * chart_width + "┘")

        # 添加图例
        lines.append("")
        lines.append("[dim][blue]●[/blue]=价格线  [yellow]·[/yellow]=均线[/dim]")

        chart_text = "\n".join(lines)

        return Panel(
            chart_text,
            title="[cyan]价格走势[/cyan]",
            style="on #1a1a1a",
            border_style="cyan",
            padding=(0, 1)
        )

    def render_volume(self) -> Panel:
        """渲染成交量柱状图：红绿柱"""
        if len(self.volumes) < 2:
            return Panel(
                Align.center(Text("等待数据...", style="dim")),
                title="[yellow]成交量[/yellow]",
                style="on #1a1a1a",
                border_style="yellow"
            )

        volumes_list = list(self.volumes)[-60:]
        prices_list = list(self.prices)[-60:]

        max_vol = max(volumes_list) if volumes_list else 1

        # 创建柱状图（高度5行）
        chart_height = 5
        chart_width = len(volumes_list)

        lines = []
        for row in range(chart_height, 0, -1):
            line_chars = []
            threshold = (max_vol * row / chart_height)

            for i, vol in enumerate(volumes_list):
                if vol >= threshold:
                    # 根据价格涨跌决定颜色
                    if i > 0 and prices_list[i] >= prices_list[i-1]:
                        line_chars.append("[green]█[/green]")
                    else:
                        line_chars.append("[red]█[/red]")
                else:
                    line_chars.append(" ")

            lines.append("".join(line_chars))

        volume_text = "\n".join(lines)

        return Panel(
            volume_text,
            title="[yellow]成交量[/yellow]",
            style="on #1a1a1a",
            border_style="yellow",
            padding=(0, 1)
        )

    def render_indicators(self) -> Panel:
        """渲染技术指标行：KDJ等数值"""
        text = Text()

        # 示例技术指标
        text.append("MA(5): ", style="dim")
        text.append(f"{self.ma_short[-1] if len(self.ma_short) > 0 else 0:.2f}", style="yellow")
        text.append("  ", style="dim")

        text.append("MA(10): ", style="dim")
        text.append(f"{self.ma_long[-1] if len(self.ma_long) > 0 else 0:.2f}", style="yellow")
        text.append("  ", style="dim")

        text.append("KDJ: ", style="dim")
        text.append("K:50.2 D:48.5 J:53.6", style="cyan")

        return Panel(
            Align.center(text),
            style="on #1a1a1a",
            border_style="dim"
        )

    def render_logs(self) -> Panel:
        """渲染日志区"""
        if not self.logs:
            return Panel(
                Align.center(Text("等待系统事件...", style="dim")),
                title="[yellow]实时日志[/yellow]",
                style="on #1a1a1a",
                border_style="yellow"
            )

        lines = []
        for log in list(self.logs)[-8:]:
            timestamp = log['time']
            message = log['message']
            log_type = log['type']

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

        return Panel(
            log_text,
            title="[yellow]实时日志[/yellow]",
            style="on #1a1a1a",
            border_style="yellow",
            padding=(0, 1)
        )

    def render_footer(self) -> Panel:
        """渲染底部操作栏：交易按钮 + 功能图标"""
        text = Text()

        # 左侧：橙色交易按钮
        text.append(" [ ", style="dim")
        text.append("交易", style="bold yellow on #ff6600")
        text.append(" ] ", style="dim")

        # 中间填充
        text.append("  " * 5)

        # 右侧：功能图标
        text.append("📊 ", style="dim")
        text.append("📈 ", style="dim")
        text.append("⚙️ ", style="dim")
        text.append("ℹ️", style="dim")

        return Panel(
            Align.center(text),
            style="on #1a1a1a",
            border_style="dim"
        )

    def render(self) -> Layout:
        """渲染完整仪表板"""
        layout = self.create_layout()

        layout["header"].update(self.render_header())
        layout["price_stats"].update(self.render_price_stats())
        layout["period_tabs"].update(self.render_period_tabs())
        layout["chart"].update(self.render_chart())
        layout["volume"].update(self.render_volume())
        layout["indicators"].update(self.render_indicators())
        layout["logs"].update(self.render_logs())
        layout["footer"].update(self.render_footer())

        return layout

    # ========== 数据更新方法 ==========

    def update_price(self, price: float, volume: float = 0):
        """更新价格数据"""
        now = datetime.now()
        old_price = self.current_price
        self.current_price = price

        # 检查是否需要重置每日基准
        current_date = now.date()
        if self.last_reset_date is None or self.last_reset_date != current_date:
            self.price_24h_start = price
            self.last_reset_date = current_date
            self.add_log(f"新的一天开始，基准价格: ${price:.2f}", "info")

        # 添加到图表数据
        self.timestamps.append(now)
        self.prices.append(price)
        self.volumes.append(volume)

        # 计算涨跌
        if self.price_24h_start > 0:
            self.price_change = price - self.price_24h_start
            self.price_change_pct = (self.price_change / self.price_24h_start) * 100
        else:
            self.price_24h_start = price
            self.price_change = 0
            self.price_change_pct = 0

        # 更新24h高低
        if self.high_24h == 0:
            self.high_24h = price
            self.low_24h = price
        else:
            self.high_24h = max(self.high_24h, price)
            self.low_24h = min(self.low_24h, price)

        # 更新历史最高
        if price > self.all_time_high:
            self.all_time_high = price

        # 记录显著价格变化
        if old_price > 0:
            change_pct = abs((price - old_price) / old_price) * 100
            if change_pct > 0.5:
                direction = "上涨" if price > old_price else "下跌"
                change_amount = price - old_price
                sign = "+" if change_amount >= 0 else ""
                self.add_log(
                    f"价格{direction} {sign}${change_amount:.2f} ({sign}{change_pct:.2f}%) → ${price:.2f}",
                    "market"
                )

    def update_ohlc(self, open_p: float, high: float, low: float, close: float):
        """更新OHLC数据"""
        self.ohlc_data.append({
            'open': open_p,
            'high': high,
            'low': low,
            'close': close
        })

        # 更新今开价
        if self.open_price == 0:
            self.open_price = open_p

    def update_ma(self, ma_short: float, ma_long: float):
        """更新移动平均线"""
        self.ma_short.append(ma_short)
        self.ma_long.append(ma_long)

    def add_trade(self, side: str, price: float, entry_price: float = None, quantity: float = 0):
        """添加交易记录"""
        self.trades.append({
            'index': len(self.prices) - 1,
            'side': side,
            'price': price,
            'entry_price': entry_price,
            'time': datetime.now()
        })

        # 记录详细交易历史
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

                if pnl > 0:
                    self.total_profit += pnl
                else:
                    self.total_loss += abs(pnl)

                self.add_log(
                    f"✓ 卖出成功 @ ${price:,.2f} ({sign}${pnl:,.2f}, {sign}{pnl_pct:.2f}% {status})",
                    "trade"
                )
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

        # 计算胜率
        sell_trades = [t for t in self.trade_history if t['type'] == 'sell']
        if len(sell_trades) > 0:
            wins = sum(1 for t in sell_trades if t.get('pnl', 0) > 0)
            self.win_rate = (wins / len(sell_trades)) * 100

    def update_stats(self, equity: float, cash: float, position: str, market_regime: str = "", volatility: str = ""):
        """更新统计数据"""
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
                self.add_log(f"市场状态变化: {new_regime}", "market")
            self.market_regime = new_regime

        if volatility:
            vol_map = {
                'high': '高波动',
                'low': '低波动',
                'normal': '正常'
            }
            new_volatility = vol_map.get(volatility, volatility)
            if new_volatility != old_volatility and old_volatility != "正常":
                self.add_log(f"波动率变化: {new_volatility}", "market")
            self.volatility = new_volatility

    def add_log(self, message: str, log_type: str = "info"):
        """添加日志条目"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.logs.append({
            'time': timestamp,
            'message': message,
            'type': log_type
        })

    # ========== 辅助方法 ==========

    def _format_volume(self, volume: float) -> str:
        """格式化成交量"""
        if volume >= 1_000_000_000:
            return f"{volume / 1_000_000_000:.2f}B"
        elif volume >= 1_000_000:
            return f"{volume / 1_000_000:.2f}M"
        elif volume >= 1_000:
            return f"{volume / 1_000:.2f}K"
        else:
            return f"{volume:.2f}"

    def _calculate_amplitude(self) -> float:
        """计算振幅"""
        if self.open_price > 0 and self.high_24h > 0 and self.low_24h > 0:
            return ((self.high_24h - self.low_24h) / self.open_price) * 100
        return 0.0
