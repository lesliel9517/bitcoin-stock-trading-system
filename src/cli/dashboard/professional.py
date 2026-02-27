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
        self.time_range = "1D"  # 1D, 5日, 日K, 周K, 月K, 年K
        self.time_ranges = ["1D", "5日", "日K", "周K", "月K", "年K"]
        self.time_range_data = {
            '1D': {'prices': deque(maxlen=120), 'timestamps': deque(maxlen=120), 'volumes': deque(maxlen=120)},
            '5日': {'prices': [], 'timestamps': [], 'volumes': []},
            '日K': {'prices': [], 'timestamps': [], 'volumes': []},
            '周K': {'prices': [], 'timestamps': [], 'volumes': []},
            '月K': {'prices': [], 'timestamps': [], 'volumes': []},
            '年K': {'prices': [], 'timestamps': [], 'volumes': []}
        }

    def create_layout(self) -> Layout:
        """创建布局：左侧图表 + 右侧信息"""
        layout = Layout()

        # 顶部标题栏 + 主体 + 底部快捷键
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body", ratio=1),
            Layout(name="footer", size=1)
        )

        # 主体：左侧图表 + 右侧信息面板
        layout["body"].split_row(
            Layout(name="left", ratio=2),
            Layout(name="right", ratio=1)
        )

        # 左侧：价格统计 + 周期Tab + 图表 + 成交量 + 日志
        layout["left"].split_column(
            Layout(name="price_stats", size=5),
            Layout(name="period_tabs", size=3),
            Layout(name="chart", ratio=2),           # 减小图表区比例
            Layout(name="volume", size=4),
            Layout(name="logs", ratio=1)
        )

        return layout

    def render_header(self) -> Panel:
        """渲染顶部标题栏：标题 + 时间"""
        text = Text()

        # 左侧：标题
        text.append("BTC-USD 实时交易", style="bold cyan")

        # 中间填充
        text.append("  " * 15)

        # 右侧：时间
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        text.append(current_time, style="dim")

        return Panel(
            Align.center(text),
            style="",  # 使用终端默认背景
            border_style="bright_black"
        )

    def render_price_stats(self) -> Panel:
        """渲染价格统计区：左侧大号价格 + 右侧市场指标"""
        table = Table.grid(padding=(0, 2))
        table.add_column(justify="left", ratio=2)  # 左侧大号价格
        table.add_column(justify="left", ratio=1)  # 右侧第一列
        table.add_column(justify="left", ratio=1)  # 右侧第二列

        # 左侧：大号当前价格 + 涨跌
        price_color = "bright_green" if self.price_change >= 0 else "bright_red"
        change_sign = "+" if self.price_change >= 0 else ""

        left_content = Text()
        left_content.append(f"${self.current_price:,.2f}\n", style=f"bold {price_color}")
        left_content.append(
            f"{change_sign}${self.price_change:,.2f}  {change_sign}{self.price_change_pct:.2f}%",
            style=f"{price_color}"
        )

        # 右侧第一列：市场指标
        col1 = Text()
        col1.append(f"最高  ${self.high_24h:,.2f}\n", style="bright_white")
        col1.append(f"今开  ${self.open_price:,.2f}\n", style="bright_white")
        col1.append(f"成交量  {self._format_volume(self.volume_24h)}\n", style="bright_cyan")
        col1.append(f"历史最高  ${self.all_time_high:,.2f}", style="bright_yellow")

        # 右侧第二列：市场指标
        col2 = Text()
        col2.append(f"最低  ${self.low_24h:,.2f}\n", style="bright_white")
        col2.append(f"昨收  ${self.prev_close:,.2f}\n", style="bright_white")

        # 24H涨跌
        change_24h_color = "bright_green" if self.price_change >= 0 else "bright_red"
        col2.append(
            f"24H涨跌  {change_sign}{self.price_change_pct:.2f}%\n",
            style=change_24h_color
        )

        # 振幅
        amplitude = self._calculate_amplitude()
        col2.append(f"振幅  {amplitude:.2f}%", style="bright_magenta")

        table.add_row(left_content, col1, col2)

        return Panel(
            table,
            style="",  # 使用终端默认背景
            border_style="bright_black",
            padding=(1, 2)
        )

    def render_period_tabs(self) -> Panel:
        """渲染周期Tab：1D/5日/日K/周K/月K/年K"""
        text = Text()

        for i, period in enumerate(self.time_ranges):
            if period == self.time_range:
                # 当前选中的周期：高亮显示
                text.append(f" {period} ", style="bold bright_yellow on bright_black")
            else:
                text.append(f" {period} ", style="dim")

            # 添加分隔符
            if i < len(self.time_ranges) - 1:
                text.append("  ", style="dim")

        return Panel(
            Align.center(text),
            style="",  # 使用终端默认背景
            border_style="dim"
        )
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

    def render_info_panel(self) -> Panel:
        """渲染右侧信息面板：账户信息 + 统计 + 历史交易"""
        table = Table.grid(padding=(0, 1))
        table.add_column(style="bright_white", justify="left")
        table.add_column(style="bold bright_white", justify="right")

        # 账户信息
        table.add_row("", "[bold bright_yellow]账户信息[/bold bright_yellow]")
        table.add_row("总资产", f"${self.equity:,.2f}")
        table.add_row("现金", f"${self.cash_balance:,.2f}")

        # 盈亏
        pnl_color = "bright_green" if self.pnl >= 0 else "bright_red"
        pnl_sign = "+" if self.pnl >= 0 else ""
        table.add_row("盈亏", f"[{pnl_color}]{pnl_sign}${self.pnl:,.2f}[/{pnl_color}]")
        table.add_row("收益率", f"[{pnl_color}]{pnl_sign}{self.pnl_pct:.2f}%[/{pnl_color}]")

        table.add_row("", "")

        # 收益统计
        table.add_row("", "[bold bright_green]收益统计[/bold bright_green]")
        table.add_row("累积盈利", f"[bright_green]+${self.total_profit:,.2f}[/bright_green]")
        table.add_row("累积亏损", f"[bright_red]-${self.total_loss:,.2f}[/bright_red]")
        net_pnl = self.total_profit - self.total_loss
        net_color = "bright_green" if net_pnl >= 0 else "bright_red"
        net_sign = "+" if net_pnl >= 0 else ""
        table.add_row("净收益", f"[{net_color}]{net_sign}${net_pnl:,.2f}[/{net_color}]")

        table.add_row("", "")

        # 持仓信息
        table.add_row("", "[bold bright_cyan]持仓信息[/bold bright_cyan]")
        pos_color = "bright_green" if "持仓" in self.position else "dim"
        table.add_row("状态", f"[{pos_color}]{self.position}[/{pos_color}]")

        table.add_row("", "")

        # 交易统计
        table.add_row("", "[bold bright_magenta]交易统计[/bold bright_magenta]")
        table.add_row("交易次数", str(self.total_trades))
        table.add_row("胜率", f"{self.win_rate:.1f}%")

        table.add_row("", "")

        # 市场状态
        table.add_row("", "[bold bright_white]市场状态[/bold bright_white]")
        table.add_row("趋势", self.market_regime)
        table.add_row("波动", self.volatility)

        table.add_row("", "")

        # 最近交易（显示最近20条）
        if len(self.trade_history) > 0:
            table.add_row("", "[bold bright_red]最近交易 (最近20条)[/bold bright_red]")
            for trade in list(self.trade_history)[-20:]:  # 显示最近20条
                if trade['type'] == 'buy':
                    qty = trade.get('quantity', 0)
                    table.add_row(
                        "[bright_blue]买入[/bright_blue]",
                        f"${trade['price']:.2f} × {qty:.4f}"
                    )
                else:
                    qty = trade.get('quantity', 0)
                    pnl = trade.get('pnl', 0)
                    pnl_color = "bright_green" if pnl > 0 else "bright_red"
                    pnl_sign = "+" if pnl >= 0 else ""
                    table.add_row(
                        f"[{pnl_color}]卖出[/{pnl_color}]",
                        f"${trade['price']:.2f} × {qty:.4f} [{pnl_color}]{pnl_sign}${pnl:.2f}[/{pnl_color}]"
                    )

        return Panel(
            table,
            title="[bold bright_green]实时数据[/bold bright_green]",
            style="",  # 使用终端默认背景
            border_style="bright_green",
            padding=(1, 1)
        )

    def render_chart(self) -> Panel:
        """渲染主图表区：价格线 + 均线"""
        # 根据当前周期选择数据源
        if self.time_range == '1D':
            # 实时数据
            prices_list = list(self.prices)[-60:]
            ma_short_list = list(self.ma_short)[-60:] if len(self.ma_short) > 0 else []
        else:
            # 历史数据
            range_data = self.time_range_data.get(self.time_range, {})
            prices_list = range_data.get('prices', [])[-60:]
            ma_short_list = []  # 历史数据暂不显示均线

        if len(prices_list) < 2:
            return Panel(
                Align.center(Text("等待数据...", style="dim")),
                title="[bright_cyan]价格走势[/bright_cyan]",
                style="",  # 使用终端默认背景
                border_style="bright_cyan"
            )

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
            chart[row][i] = "[bright_blue]●[/bright_blue]"

            # 连接线
            if i > 0:
                prev_price = prices_list[i-1]
                prev_row = int(((prev_price - min_p) / range_p) * (chart_height - 1))
                prev_row = chart_height - 1 - prev_row

                if prev_row < row:
                    for r in range(prev_row + 1, row):
                        if chart[r][i] == " ":
                            chart[r][i] = "[bright_blue]│[/bright_blue]"
                elif prev_row > row:
                    for r in range(row + 1, prev_row):
                        if chart[r][i] == " ":
                            chart[r][i] = "[bright_blue]│[/bright_blue]"

        # 绘制均线（橙色）
        if len(ma_short_list) == len(prices_list):
            for i, ma in enumerate(ma_short_list):
                if ma > 0:
                    row = int(((ma - min_p) / range_p) * (chart_height - 1))
                    row = chart_height - 1 - row
                    if 0 <= row < chart_height and chart[row][i] == " ":
                        chart[row][i] = "[yellow]·[/yellow]"

        # 标记交易点
        for trade in self.trades[-10:]:
            if 0 <= trade['index'] < len(self.prices):
                idx = trade['index'] - (len(self.prices) - len(prices_list))
                if 0 <= idx < len(prices_list):
                    price = prices_list[idx]
                    row = int(((price - min_p) / range_p) * (chart_height - 1))
                    row = chart_height - 1 - row
                    if trade['side'] == 'buy':
                        chart[row][idx] = "[bright_green]B[/bright_green]"
                    else:
                        chart[row][idx] = "[bright_red]S[/bright_red]"

        # 构建图表字符串
        lines = []
        for row_idx, row in enumerate(chart):
            if row_idx % 3 == 0:
                price_at_row = max_p - (range_p * row_idx / (chart_height - 1))
                left_label = f"${price_at_row:>8.2f} │"
            else:
                left_label = " " * 11 + "│"

            lines.append(left_label + "".join(row))

        lines.append(" " * 11 + "└" + "─" * chart_width)
        lines.append("")
        lines.append("[dim][bright_blue]●[/bright_blue]=价格  [yellow]·[/yellow]=均线  [bright_green]B[/bright_green]=买入  [bright_red]S[/bright_red]=卖出[/dim]")

        chart_text = "\n".join(lines)

        return Panel(
            chart_text,
            title="[bright_cyan]价格走势[/bright_cyan]",
            style="",  # 使用终端默认背景
            border_style="bright_cyan",
            padding=(0, 1)
        )

    def render_volume(self) -> Panel:
        """渲染成交量柱状图"""
        # 根据当前周期选择数据源
        if self.time_range == '1D':
            volumes_list = list(self.volumes)[-60:]
            prices_list = list(self.prices)[-60:]
        else:
            range_data = self.time_range_data.get(self.time_range, {})
            volumes_list = range_data.get('volumes', [])[-60:]
            prices_list = range_data.get('prices', [])[-60:]

        if len(volumes_list) < 2:
            return Panel(
                Align.center(Text("等待数据...", style="dim")),
                title="[bright_yellow]成交量[/bright_yellow]",
                style="",  # 使用终端默认背景
                border_style="bright_yellow"
            )

        max_vol = max(volumes_list) if volumes_list else 1

        chart_height = 4
        chart_width = len(volumes_list)

        lines = []
        for row in range(chart_height, 0, -1):
            line_chars = []
            threshold = (max_vol * row / chart_height)

            for i, vol in enumerate(volumes_list):
                if vol >= threshold:
                    if i > 0 and prices_list[i] >= prices_list[i-1]:
                        line_chars.append("[bright_green]█[/bright_green]")
                    else:
                        line_chars.append("[bright_red]█[/bright_red]")
                else:
                    line_chars.append(" ")

            lines.append("".join(line_chars))

        volume_text = "\n".join(lines)

        return Panel(
            volume_text,
            title="[bright_yellow]成交量[/bright_yellow]",
            style="",  # 使用终端默认背景
            border_style="bright_yellow",
            padding=(0, 1)
        )

    def render_logs(self) -> Panel:
        """渲染日志区"""
        if not self.logs:
            return Panel(
                Align.center(Text("等待系统事件...", style="dim")),
                title="[bright_yellow]实时日志[/bright_yellow]",
                style="",  # 使用终端默认背景
                border_style="bright_yellow"
            )

        lines = []
        for log in list(self.logs)[-6:]:
            timestamp = log['time']
            message = log['message']
            log_type = log['type']

            if log_type == "trade":
                color = "bright_blue" if "买入" in message else ("bright_green" if "盈利" in message else "bright_red")
            elif log_type == "signal":
                color = "bright_yellow"
            elif log_type == "market":
                color = "bright_cyan"
            elif log_type == "error":
                color = "bright_red"
            else:
                color = "white"

            lines.append(f"[{color}]{timestamp} {message}[/{color}]")

        log_text = "\n".join(lines)

        return Panel(
            log_text,
            title="[bright_yellow]实时日志[/bright_yellow]",
            style="",  # 使用终端默认背景
            border_style="bright_yellow",
            padding=(0, 1)
        )

    def render_footer(self) -> Panel:
        """渲染底部快捷键提示"""
        text = Text()
        text.append("快捷键: ", style="dim")
        text.append("Ctrl+C", style="bright_white")
        text.append("=退出  ", style="dim")
        text.append("1-6", style="bright_white")
        text.append("=切换周期  ", style="dim")
        text.append("R", style="bright_white")
        text.append("=刷新", style="dim")

        return Panel(
            Align.center(text),
            style="",  # 使用终端默认背景
            border_style="dim"
        )

    # ========== 时间周期切换方法 ==========

    def switch_time_range(self, range_key: str):
        """切换时间周期

        Args:
            range_key: 周期键（1D, 5日, 日K, 周K, 月K, 年K）
        """
        if range_key in self.time_ranges:
            old_range = self.time_range
            self.time_range = range_key
            self.add_log(f"切换周期: {old_range} → {range_key}", "info")

    async def load_historical_data(self, symbol: str, range_key: str):
        """加载历史数据

        Args:
            symbol: 交易对符号
            range_key: 周期键
        """
        try:
            import ccxt
            import os

            # 映射周期到ccxt的timeframe
            timeframe_map = {
                '1D': ('1m', 1440),      # 1天，1分钟K线，1440根
                '5日': ('5m', 1440),     # 5天，5分钟K线，1440根
                '日K': ('1h', 720),      # 30天，1小时K线，720根
                '周K': ('1d', 180),      # 180天，1天K线，180根
                '月K': ('1d', 365),      # 365天，1天K线，365根
                '年K': ('1w', 260)       # 5年，1周K线，260根
            }

            if range_key not in timeframe_map:
                return

            timeframe, limit = timeframe_map[range_key]

            # 配置代理
            proxies = {}
            http_proxy = os.getenv('HTTP_PROXY') or os.getenv('http_proxy')
            https_proxy = os.getenv('HTTPS_PROXY') or os.getenv('https_proxy')

            if http_proxy:
                proxies['http'] = http_proxy
            if https_proxy:
                proxies['https'] = https_proxy

            # 使用ccxt获取历史数据
            exchange_config = {}
            if proxies:
                exchange_config['proxies'] = proxies
                self.add_log(f"使用代理: {http_proxy or https_proxy}", "info")

            exchange = ccxt.binance(exchange_config)
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)

            # 提取数据
            prices = [candle[4] for candle in ohlcv]  # Close price
            timestamps = [candle[0] for candle in ohlcv]  # Timestamp
            volumes = [candle[5] for candle in ohlcv]  # Volume

            # 存储到time_range_data
            self.time_range_data[range_key] = {
                'prices': prices,
                'timestamps': timestamps,
                'volumes': volumes
            }

            self.add_log(f"已加载 {range_key} 历史数据 ({len(prices)} 个数据点)", "info")

        except Exception as e:
            self.add_log(f"加载历史数据失败: {str(e)}", "error")

    def render(self) -> Layout:
        """渲染完整仪表板"""
        layout = self.create_layout()

        layout["header"].update(self.render_header())
        layout["price_stats"].update(self.render_price_stats())
        layout["period_tabs"].update(self.render_period_tabs())
        layout["chart"].update(self.render_chart())
        layout["volume"].update(self.render_volume())
        layout["logs"].update(self.render_logs())
        layout["right"].update(self.render_info_panel())
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
