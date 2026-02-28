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
        self.volume_24h_accumulated = 0  # 累积的24h成交量
        self.open_price = 0
        self.prev_close = 0

        # Historical extremes
        self.all_time_high = 0  # 历史最高价
        self.all_time_low = float('inf')  # 历史最低价
        self.week_52_high = 0  # 52周最高（从交易所获取）
        self.week_52_low = 0  # 52周最低（从交易所获取）

        # 52-week extremes
        self.week_52_high = 0
        self.week_52_low = float('inf')
        self.week_52_prices = deque(maxlen=52*7*24*60)  # 52周的分钟数据

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

        # Strategy info
        self.strategy_name = "adaptive_strategy"  # 当前策略名称
        self.available_strategies = ["ma_cross", "adaptive_strategy"]  # 可用策略列表

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
            Layout(name="price_stats", size=11),     # 增加到11行以显示所有统计字段（含历史最低）
            Layout(name="period_tabs", size=3),
            Layout(name="chart", ratio=1),
            Layout(name="volume", size=3),
            Layout(name="logs", ratio=1)
        )

        return layout

    def render_header(self) -> Panel:
        """渲染顶部标题栏：标题 + 策略 + 时间"""
        text = Text()

        # 左侧：标题
        text.append("BTC-USD 实时交易", style="bold cyan")

        # 中间：当前策略
        text.append("  |  ", style="dim")
        strategy_display = {
            "ma_cross": "均线交叉",
            "adaptive_strategy": "自适应策略"
        }
        text.append(f"策略: {strategy_display.get(self.strategy_name, self.strategy_name)}",
                   style="bold bright_yellow")

        # 右侧：时间
        text.append("  " * 10)
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        text.append(current_time, style="dim")

        return Panel(
            Align.center(text),
            style="",  # 使用终端默认背景
            border_style="bright_black"
        )

    def render_price_stats(self) -> Panel:
        """渲染价格统计区：顶部大号价格 + 下方两列统计字段"""
        # 大号当前价格
        price_color = "bright_green" if self.price_change >= 0 else "bright_red"
        change_sign = "+" if self.price_change >= 0 else ""

        price_text = Text()
        price_text.append(f"${self.current_price:,.2f}  ", style=f"bold {price_color}")
        price_text.append(
            f"{change_sign}${self.price_change:,.2f} ({change_sign}{self.price_change_pct:.2f}%)",
            style=f"{price_color}"
        )

        # 两列统计字段
        stats_table = Table.grid(padding=(0, 3))
        stats_table.add_column(justify="left")  # 第一列
        stats_table.add_column(justify="left")  # 第二列

        # 第一列：24H最高、今开、成交量、历史最高、52周最高
        col1 = Text()
        col1.append(f"24H最高  ${self.high_24h:,.2f}\n", style="bright_white")
        col1.append(f"今开  ${self.open_price:,.2f}\n", style="bright_white")
        col1.append(f"成交量  {self._format_volume(self.volume_24h)}\n", style="bright_cyan")
        col1.append(f"历史最高  ${self.all_time_high:,.2f}\n", style="bright_yellow")
        col1.append(f"52周最高  ${self.week_52_high:,.2f}", style="bright_magenta")

        # 第二列：24H最低、昨收、24H涨跌、历史最低、52周最低
        col2 = Text()
        col2.append(f"24H最低  ${self.low_24h:,.2f}\n", style="bright_white")
        col2.append(f"昨收  ${self.prev_close:,.2f}\n", style="bright_white")

        change_24h_color = "bright_green" if self.price_change >= 0 else "bright_red"
        col2.append(
            f"24H涨跌  {change_sign}{self.price_change_pct:.2f}%\n",
            style=change_24h_color
        )

        all_time_low_display = f"${self.all_time_low:,.2f}" if self.all_time_low < float('inf') else "$0.00"
        col2.append(f"历史最低  {all_time_low_display}\n", style="bright_yellow")
        col2.append(f"52周最低  ${self.week_52_low:,.2f}", style="bright_magenta")

        stats_table.add_row(col1, col2)

        # 组合：价格在上，统计字段在下
        from rich.console import Group

        content = Group(
            price_text,
            Text(""),  # 空行
            stats_table
        )

        return Panel(
            content,
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
        """渲染主图表区：价格线 + 均线 + 当前价虚线 + 双刻度"""
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

        # 绘制当前价虚线（白色虚线）
        if self.current_price > 0 and min_p <= self.current_price <= max_p:
            current_row = int(((self.current_price - min_p) / range_p) * (chart_height - 1))
            current_row = chart_height - 1 - current_row
            if 0 <= current_row < chart_height:
                for i in range(chart_width):
                    if chart[current_row][i] == " ":
                        # 虚线效果：每隔一个字符绘制
                        if i % 2 == 0:
                            chart[current_row][i] = "[dim white]─[/dim white]"

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

        # 构建图表字符串（左侧价格刻度 + 右侧涨跌幅刻度）
        lines = []
        base_price = self.open_price if self.open_price > 0 else self.price_24h_start
        if base_price == 0:
            base_price = min_p

        for row_idx, row in enumerate(chart):
            # 左侧价格刻度
            if row_idx % 3 == 0:
                price_at_row = max_p - (range_p * row_idx / (chart_height - 1))
                left_label = f"${price_at_row:>8.2f} │"
            else:
                left_label = " " * 11 + "│"

            # 右侧涨跌幅刻度
            if row_idx % 3 == 0:
                price_at_row = max_p - (range_p * row_idx / (chart_height - 1))
                change_pct = ((price_at_row - base_price) / base_price) * 100 if base_price > 0 else 0
                sign = "+" if change_pct >= 0 else ""
                color = "bright_green" if change_pct >= 0 else "bright_red"
                right_label = f"│ [{color}]{sign}{change_pct:>6.2f}%[/{color}]"
            else:
                right_label = "│"

            lines.append(left_label + "".join(row) + right_label)

        # 底部横线
        lines.append(" " * 11 + "└" + "─" * chart_width + "┘")
        lines.append("")
        lines.append("[dim][bright_blue]●[/bright_blue]=价格  [yellow]·[/yellow]=均线  [dim white]─[/dim white]=当前价  [bright_green]B[/bright_green]=买入  [bright_red]S[/bright_red]=卖出[/dim]")

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
        text.append("S", style="bright_white")
        text.append("=切换策略  ", style="dim")
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

    def switch_strategy(self):
        """切换策略"""
        current_index = self.available_strategies.index(self.strategy_name)
        next_index = (current_index + 1) % len(self.available_strategies)
        old_strategy = self.strategy_name
        self.strategy_name = self.available_strategies[next_index]

        strategy_display = {
            "ma_cross": "均线交叉",
            "adaptive_strategy": "自适应策略"
        }
        self.add_log(
            f"切换策略: {strategy_display.get(old_strategy, old_strategy)} → {strategy_display.get(self.strategy_name, self.strategy_name)}",
            "info"
        )
        return self.strategy_name

    async def load_historical_data(self, symbol: str, range_key: str):
        """加载历史数据

        Args:
            symbol: 交易对符号
            range_key: 周期键
        """
        try:
            import ccxt.async_support as ccxt
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

            # 配置代理和超时
            exchange_config = {
                'enableRateLimit': True,
                'timeout': 30000,  # 30秒超时
            }

            # 检查代理配置
            http_proxy = os.getenv('HTTP_PROXY') or os.getenv('http_proxy')
            https_proxy = os.getenv('HTTPS_PROXY') or os.getenv('https_proxy')

            if http_proxy or https_proxy:
                proxy_url = https_proxy or http_proxy
                exchange_config['proxies'] = {
                    'http': proxy_url,
                    'https': proxy_url,
                }
                exchange_config['aiohttp_proxy'] = proxy_url
                self.add_log(f"使用代理加载历史数据", "info")
            else:
                self.add_log(f"警告: 未配置代理，可能无法访问Binance API", "error")
                self.add_log(f"请设置环境变量 HTTP_PROXY 或 HTTPS_PROXY", "error")
                return

            # 格式化symbol为Binance格式
            binance_symbol = symbol.replace('-', '').replace('/', '')
            if binance_symbol.endswith('USD'):
                binance_symbol = binance_symbol[:-3] + 'USDT'

            self.add_log(f"正在加载 {range_key} 历史数据...", "info")

            # 使用ccxt异步获取历史数据
            exchange = ccxt.binance(exchange_config)
            try:
                ohlcv = await exchange.fetch_ohlcv(binance_symbol, timeframe, limit=limit)

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

                self.add_log(f"✓ 已加载 {range_key} 历史数据 ({len(prices)} 个数据点)", "info")

            finally:
                await exchange.close()

        except ImportError:
            self.add_log(f"缺少ccxt库，无法加载历史数据", "error")
            self.add_log(f"请运行: pip install ccxt", "error")
        except Exception as e:
            error_msg = str(e)
            if '451' in error_msg or 'restricted location' in error_msg.lower():
                self.add_log(f"Binance API地区限制，无法加载历史数据", "error")
                self.add_log(f"请配置代理或使用实时数据(1D)", "error")
            elif 'proxy' in error_msg.lower() or 'connection' in error_msg.lower():
                self.add_log(f"网络连接失败，请检查代理配置", "error")
            else:
                self.add_log(f"加载历史数据失败: {error_msg[:100]}", "error")

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

        return layout

    # ========== 数据更新方法 ==========

    def update_price(self, price: float, volume_24h: float = 0, high_24h: float = None, low_24h: float = None,
                     open_price: float = None, tick_volume: float = 0, week_52_high: float = None, week_52_low: float = None):
        """更新价格数据

        Args:
            price: 当前价格
            volume_24h: 24小时总成交量（来自交易所ticker）
            high_24h: 24小时最高价（来自交易所）
            low_24h: 24小时最低价（来自交易所）
            open_price: 24h开盘价（来自交易所，近似昨收）
            tick_volume: 单个tick的成交量（用于图表）
            week_52_high: 52周最高价（来自交易所）
            week_52_low: 52周最低价（来自交易所）
        """
        now = datetime.now()
        old_price = self.current_price
        self.current_price = price

        # 检查是否需要重置每日基准
        current_date = now.date()
        if self.last_reset_date is None or self.last_reset_date != current_date:
            self.price_24h_start = price
            self.last_reset_date = current_date
            self.add_log(f"新的一天开始，基准价格: ${price:.2f}", "info")

        # 添加到图表数据（使用tick_volume用于图表显示）
        self.timestamps.append(now)
        self.prices.append(price)
        self.volumes.append(tick_volume if tick_volume > 0 else volume_24h / 1000)  # 图表用

        # 更新24h统计数据（优先使用交易所提供的数据）
        if volume_24h > 0:
            self.volume_24h = volume_24h

        if high_24h is not None and high_24h > 0:
            self.high_24h = high_24h
        elif self.high_24h == 0:
            self.high_24h = price
        else:
            self.high_24h = max(self.high_24h, price)

        if low_24h is not None and low_24h > 0:
            self.low_24h = low_24h
        elif self.low_24h == 0:
            self.low_24h = price
        else:
            self.low_24h = min(self.low_24h, price)

        if open_price is not None and open_price > 0:
            self.open_price = open_price
            # 使用24h开盘价作为昨收的近似值
            if self.prev_close == 0:
                self.prev_close = open_price
        elif self.open_price == 0:
            self.open_price = price

        # 计算涨跌（使用开盘价）
        base_price = self.open_price if self.open_price > 0 else self.price_24h_start
        if base_price > 0:
            self.price_change = price - base_price
            self.price_change_pct = (self.price_change / base_price) * 100
        else:
            self.price_24h_start = price
            self.price_change = 0
            self.price_change_pct = 0

        # 更新历史最高和最低
        if price > self.all_time_high:
            self.all_time_high = price
        if price < self.all_time_low:
            self.all_time_low = price

        # 更新52周最高和最低（如果交易所提供）
        if week_52_high is not None and week_52_high > 0:
            self.week_52_high = week_52_high
        if week_52_low is not None and week_52_low > 0:
            self.week_52_low = week_52_low

        # 更新52周数据
        self.week_52_prices.append(price)
        if len(self.week_52_prices) > 0:
            self.week_52_high = max(self.week_52_prices)
            self.week_52_low = min(self.week_52_prices)

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
