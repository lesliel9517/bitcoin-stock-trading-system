"""
Simplified Real-time Dashboard

Works in any environment including background tasks
"""

import asyncio
from datetime import datetime
from decimal import Decimal
from collections import deque
import os
import sys
import re
import logging

from ..core.event_bus import EventBus
from ..core.event import MarketEvent, SignalEvent, EventType
from ..trading.portfolio import Portfolio
from ..strategies.base import Strategy


class LogCapture(logging.Handler):
    """Capture logging output for display"""

    def __init__(self, dashboard):
        super().__init__()
        self.dashboard = dashboard

    def emit(self, record):
        try:
            msg = self.format(record)
            # Filter out some noisy logs
            if 'INFO' in msg and any(x in msg for x in ['Accumulating data', 'update_price']):
                return

            level = record.levelname
            # Map log levels to dashboard levels
            level_map = {
                'INFO': 'INFO',
                'WARNING': 'SIGNAL',
                'ERROR': 'ERROR',
                'DEBUG': 'INFO'
            }
            self.dashboard.add_log(msg, level_map.get(level, 'INFO'))
        except:
            pass


class SimplifiedDashboard:
    """Simplified real-time dashboard that works everywhere"""

    def __init__(self, event_bus: EventBus, portfolio: Portfolio, strategy: Strategy, max_points=50):
        self.event_bus = event_bus
        self.portfolio = portfolio
        self.strategy = strategy
        self.max_points = max_points

        # Data buffers
        self.prices = deque(maxlen=max_points)
        self.ma_short = deque(maxlen=max_points)
        self.ma_long = deque(maxlen=max_points)
        self.trades = []

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

        # Logs buffer for right panel
        self.logs = deque(maxlen=25)  # Keep last 25 log entries

        # Setup log capture
        self._setup_log_capture()

    def _setup_log_capture(self):
        """Setup logging capture"""
        from ..utils.logger import logger

        # Add custom handler to capture logs
        handler = LogCapture(self)
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(name)s - %(message)s')
        handler.setFormatter(formatter)

        # Get the loguru logger's handlers
        # Note: This is a simplified approach
        self.add_log("系统启动", "INFO")

    def clear_screen(self):
        """Clear terminal screen"""
        os.system('clear' if os.name != 'nt' else 'cls')

    def draw_chart(self):
        """Draw ASCII price chart"""
        if len(self.prices) < 2:
            return

        chart_height = 12
        chart_width = min(len(self.prices), 60)
        recent_prices = list(self.prices)[-chart_width:]

        min_price = min(recent_prices)
        max_price = max(recent_prices)
        price_range = max_price - min_price if max_price > min_price else 1

        print("\n" + "="*80)
        print("📈 价格走势图".center(80))
        print("="*80)

        # Draw chart
        for row in range(chart_height, -1, -1):
            line = ""
            for i, price in enumerate(recent_prices):
                normalized = int((price - min_price) / price_range * chart_height)

                # Check for trades
                trade_marker = ""
                for trade in self.trades[-10:]:
                    if trade['index'] == len(self.prices) - chart_width + i:
                        trade_marker = "🟢" if trade['side'] == 'buy' else "🔴"
                        break

                if normalized == row:
                    line += trade_marker if trade_marker else "●"
                elif normalized > row:
                    line += "│"
                else:
                    line += " "

            # Price label
            price_at_row = min_price + (price_range * row / chart_height)
            print(f"${price_at_row:>8,.0f} {line}")

        print("-" * 80)

    def draw_ma_chart(self):
        """Draw moving average chart"""
        if len(self.ma_short) < 2 or len(self.ma_long) < 2:
            return

        chart_height = 8
        chart_width = min(len(self.ma_short), 60)

        recent_short = list(self.ma_short)[-chart_width:]
        recent_long = list(self.ma_long)[-chart_width:]

        all_values = recent_short + recent_long
        min_val = min(all_values)
        max_val = max(all_values)
        val_range = max_val - min_val if max_val > min_val else 1

        print("\n📊 移动平均线")
        print("-" * 80)

        for row in range(chart_height, -1, -1):
            line = ""
            for i in range(chart_width):
                short_norm = int((recent_short[i] - min_val) / val_range * chart_height)
                long_norm = int((recent_long[i] - min_val) / val_range * chart_height)

                if short_norm == row and long_norm == row:
                    line += "X"
                elif short_norm == row:
                    line += "S"
                elif long_norm == row:
                    line += "L"
                elif short_norm > row or long_norm > row:
                    line += "│"
                else:
                    line += " "

            val_at_row = min_val + (val_range * row / chart_height)
            print(f"${val_at_row:>8,.0f} {line}")

        print("-" * 80)
        print("S = MA短线  L = MA长线  X = 交叉点")

    def draw_stats(self):
        """Draw statistics panel"""
        equity = float(self.portfolio.get_total_value())
        initial = float(self.portfolio.initial_balance)
        pnl = equity - initial
        pnl_pct = (pnl / initial) * 100

        # Color codes
        green = "\033[92m"
        red = "\033[91m"
        yellow = "\033[93m"
        cyan = "\033[96m"
        reset = "\033[0m"

        print("\n" + "="*80)
        print("💰 实时数据".center(80))
        print("="*80)

        # Price info
        price_color = green if self.price_change >= 0 else red
        change_sign = "+" if self.price_change >= 0 else ""
        print(f"\n当前价格: {price_color}${self.current_price:,.2f}{reset} "
              f"({price_color}{change_sign}{self.price_change_pct:.2f}%{reset})")
        print(f"24H 高: ${self.high_24h:,.0f}  |  24H 低: ${self.low_24h:,.0f}")

        # Account info
        print(f"\n账户总值: {yellow}${equity:,.2f}{reset}")
        pnl_color = green if pnl >= 0 else red
        pnl_sign = "+" if pnl >= 0 else ""
        print(f"总盈亏: {pnl_color}{pnl_sign}${pnl:,.2f} ({pnl_sign}{pnl_pct:.2f}%){reset}")

        # Position
        pos_color = green if "持仓" in self.position else "\033[90m"
        print(f"持仓状态: {pos_color}{self.position}{reset}")

        # Trading stats
        print(f"\n交易次数: {cyan}{self.total_trades}{reset}")
        print(f"胜率: {cyan}{self.win_rate:.1f}%{reset}")

        # Market state
        print(f"\n市场趋势: {self.market_regime}")
        print(f"波动率: {self.volatility}")

        # Recent trades
        if len(self.trades) > 0:
            print(f"\n最近交易:")
            for trade in self.trades[-3:]:
                side_text = "买入" if trade['side'] == 'buy' else "卖出"
                side_color = green if trade['side'] == 'buy' else red
                time_str = trade['time'].strftime('%H:%M:%S')
                print(f"  {side_color}{side_text}{reset} @ ${trade['price']:,.2f} ({time_str})")

        print("\n" + "="*80)

    def render(self):
        """Render complete dashboard with left charts and right logs"""
        self.clear_screen()

        # Header
        print("\n" + "="*120)
        print("🚀 实时交易监控系统".center(120))
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}".center(120))
        print("="*120)

        # Two-column layout: Left (charts) | Right (logs)
        self.draw_two_column_layout()

        # Footer
        print("\n" + "="*120)
        print(f"按 Ctrl+C 停止交易".center(120))
        print("="*120 + "\n")

        # Flush output
        sys.stdout.flush()

    def update_price(self, price: float):
        """Update price data"""
        self.prices.append(price)
        self.current_price = price

        if len(self.prices) > 0:
            self.high_24h = max(self.prices)
            self.low_24h = min(self.prices)

            if len(self.prices) > 1:
                first_price = self.prices[0]
                self.price_change = price - first_price
                self.price_change_pct = (self.price_change / first_price) * 100

    def update_ma(self, ma_short: float, ma_long: float):
        """Update moving averages"""
        self.ma_short.append(ma_short)
        self.ma_long.append(ma_long)

    def add_trade(self, side: str, price: float):
        """Add trade"""
        self.trades.append({
            'index': len(self.prices) - 1,
            'side': side,
            'price': price,
            'time': datetime.now()
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

    async def run(self, duration: int = None):
        """Run dashboard"""
        print("\n启动简化实时仪表板...\n")

        # Subscribe to events
        async def handle_market_event(event: MarketEvent):
            price = float(event.price)
            self.update_price(price)

            # Update portfolio prices (CRITICAL for correct valuation)
            self.portfolio.update_prices({event.symbol: Decimal(str(price))})

            # Log price update (less frequent to avoid spam)
            if len(self.prices) % 10 == 0:  # Log every 10 price updates
                self.add_log(f"价格: ${price:,.2f}", "INFO")

            # Update MA
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
                new_position = f"持仓 {float(pos.quantity):.4f} BTC"
                if new_position != self.position:
                    self.position = new_position
                    self.add_log(f"持仓: {float(pos.quantity):.4f} BTC @ ${float(pos.average_price):,.2f}", "INFO")
            else:
                if self.position != "空仓":
                    self.position = "空仓"
                    self.add_log("持仓已清空", "INFO")

            # Update market state
            if hasattr(self.strategy, 'market_regime'):
                self.update_market_state(self.strategy.market_regime, self.strategy.volatility_regime)

        async def handle_signal_event(event: SignalEvent):
            if event.signal_type in ['buy', 'sell']:
                if len(self.prices) > 0:
                    price = self.prices[-1]

                    # Log signal with more details
                    signal_type = event.signal_type.upper()
                    self.add_log(f"🔔 {signal_type} 信号 @ ${price:,.2f}", "SIGNAL")

        self.event_bus.subscribe(EventType.MARKET, handle_market_event)
        self.event_bus.subscribe(EventType.SIGNAL, handle_signal_event)

        # Subscribe to fill events for trade logging
        async def handle_fill_event(event):
            if hasattr(event, 'side') and hasattr(event, 'price') and hasattr(event, 'quantity'):
                side_text = "买入" if event.side == "BUY" else "卖出"
                price = float(event.price)

                # Add to trades list for chart marking
                self.trades.append({
                    'index': len(self.prices) - 1,
                    'side': 'buy' if event.side == "BUY" else 'sell',
                    'price': price,
                    'time': datetime.now()
                })

                # Update trade count and win rate
                self.total_trades = len(self.trades)
                if len(self.trades) >= 2:
                    wins = 0
                    for i in range(1, len(self.trades), 2):
                        if i < len(self.trades):
                            buy_price = self.trades[i-1]['price']
                            sell_price = self.trades[i]['price']
                            if sell_price > buy_price:
                                wins += 1
                    self.win_rate = (wins / (len(self.trades) // 2)) * 100 if len(self.trades) >= 2 else 0

                # Log trade
                self.add_log(f"✓ {side_text} {float(event.quantity):.4f} @ ${price:,.2f}", "TRADE")

        from ..core.event import EventType as ET
        self.event_bus.subscribe(ET.FILL, handle_fill_event)

        self.add_log("交易引擎已启动", "INFO")

        # Run with periodic refresh
        start_time = asyncio.get_event_loop().time()
        last_render = 0

        try:
            while True:
                current_time = asyncio.get_event_loop().time()

                # Check duration
                if duration:
                    elapsed = current_time - start_time
                    if elapsed >= duration:
                        break

                # Render every 1 second
                if current_time - last_render >= 1.0:
                    self.render()
                    last_render = current_time

                await asyncio.sleep(0.1)

        except KeyboardInterrupt:
            print("\n\n停止可视化...")

        # Print summary
        self.print_summary()

    def add_log(self, message: str, level: str = "INFO"):
        """Add log entry

        Args:
            message: Log message
            level: Log level (INFO, TRADE, SIGNAL, ERROR)
        """
        timestamp = datetime.now().strftime('%H:%M:%S')

        # Color codes
        colors = {
            'INFO': '\033[90m',    # Gray/Dim
            'TRADE': '\033[92m',   # Green
            'SIGNAL': '\033[93m',  # Yellow
            'ERROR': '\033[91m',   # Red
            'BUY': '\033[92m',     # Green
            'SELL': '\033[91m'     # Red
        }

        color = colors.get(level, '\033[0m')
        reset = '\033[0m'

        # Format like logging: timestamp level message
        log_entry = f"{color}[{timestamp}] {level:6s} {message}{reset}"
        self.logs.append(log_entry)

    def _strip_ansi(self, text: str) -> str:
        """Strip ANSI color codes from text"""
        return re.sub(r'\033\[[0-9;]+m', '', text)

    def draw_two_column_layout(self):
        """Draw two-column layout: charts on left, logs on right"""
        left_width = 68
        right_width = 50

        # Generate content
        left_lines = self._generate_chart_lines(left_width)
        right_lines = self._generate_log_lines(right_width)

        # Combine both columns
        max_lines = max(len(left_lines), len(right_lines))

        print("─" * 120)

        for i in range(max_lines):
            left_line = left_lines[i] if i < len(left_lines) else ""
            right_line = right_lines[i] if i < len(right_lines) else ""

            # Calculate padding for left column (accounting for ANSI codes)
            plain_left = self._strip_ansi(left_line)
            padding_needed = left_width - len(plain_left)

            if padding_needed > 0:
                left_line += " " * padding_needed

            print(f"{left_line} │ {right_line}")

        print("─" * 120)

    def _generate_chart_lines(self, width: int) -> list:
        """Generate chart content as list of lines"""
        lines = []

        # Price info
        price_color = "\033[92m" if self.price_change >= 0 else "\033[91m"
        change_sign = "+" if self.price_change >= 0 else ""
        reset = "\033[0m"

        lines.append(f"价格: {price_color}${self.current_price:,.2f}{reset} ({price_color}{change_sign}{self.price_change_pct:.2f}%{reset})")
        lines.append(f"24H: ${self.high_24h:,.0f} / ${self.low_24h:,.0f}")
        lines.append("")

        # Price chart with line connection
        if len(self.prices) >= 2:
            chart_height = 10
            chart_width = min(len(self.prices), width - 2)
            recent_prices = list(self.prices)[-chart_width:]

            min_price = min(recent_prices)
            max_price = max(recent_prices)
            price_range = max_price - min_price if max_price > min_price else 1

            # Build chart matrix
            chart = [[' ' for _ in range(chart_width)] for _ in range(chart_height + 1)]

            # Plot prices
            for i, price in enumerate(recent_prices):
                row = int((price - min_price) / price_range * chart_height)
                chart[chart_height - row][i] = '●'

                # Connect with lines
                if i > 0:
                    prev_row = int((recent_prices[i-1] - min_price) / price_range * chart_height)
                    curr_row = row

                    # Draw vertical line between points
                    start = min(prev_row, curr_row)
                    end = max(prev_row, curr_row)
                    for r in range(start, end + 1):
                        if chart[chart_height - r][i] == ' ':
                            chart[chart_height - r][i] = '│'

                # Mark trades with B/S
                for trade in self.trades[-10:]:
                    if trade['index'] == len(self.prices) - chart_width + i:
                        chart[chart_height - row][i] = "B" if trade['side'] == 'buy' else "S"

            # Output chart
            for row in chart:
                lines.append(''.join(row))

        lines.append("")

        # Account info - sync with portfolio
        equity = float(self.portfolio.get_total_value())
        initial = float(self.portfolio.initial_balance)
        pnl = equity - initial
        pnl_pct = (pnl / initial) * 100 if initial > 0 else 0

        lines.append("账户")
        lines.append(f"总资产: ${equity:,.2f}")

        pnl_color = "\033[92m" if pnl >= 0 else "\033[91m"
        pnl_sign = "+" if pnl >= 0 else ""
        lines.append(f"盈亏: {pnl_color}{pnl_sign}${pnl:,.2f} ({pnl_sign}{pnl_pct:.2f}%){reset}")

        pos_color = "\033[92m" if "持仓" in self.position else "\033[90m"
        lines.append(f"持仓: {pos_color}{self.position}{reset}")
        lines.append("")

        # Trading stats - sync with actual trades
        lines.append("统计")
        lines.append(f"交易: {self.total_trades}")
        lines.append(f"胜率: {self.win_rate:.1f}%")
        lines.append(f"市场: {self.market_regime}")

        return lines

    def _generate_log_lines(self, width: int) -> list:
        """Generate log content as list of lines"""
        lines = []

        lines.append("系统日志")
        lines.append("─" * (width - 2))

        if len(self.logs) == 0:
            lines.append("等待系统事件...")
        else:
            # Show logs (newest at bottom, like terminal)
            for log in self.logs:
                # Truncate if too long (accounting for ANSI codes)
                plain_log = self._strip_ansi(log)

                if len(plain_log) > width - 2:
                    # Find where to cut (preserve ANSI codes)
                    lines.append(log[:width-5] + "...")
                else:
                    lines.append(log)

        return lines

    def print_summary(self):
        """Print final summary"""
        print("\n" + "="*120)
        print("交易总结".center(120))
        print("="*120)

        equity = float(self.portfolio.get_total_value())
        initial = float(self.portfolio.initial_balance)
        pnl = equity - initial
        pnl_pct = (pnl / initial) * 100

        print(f"\n初始资金: ${initial:,.2f}")
        print(f"最终资金: ${equity:,.2f}")

        pnl_color = "\033[92m" if pnl >= 0 else "\033[91m"
        pnl_sign = "+" if pnl >= 0 else ""
        reset = "\033[0m"
        print(f"总收益: {pnl_color}{pnl_sign}${pnl:,.2f} ({pnl_sign}{pnl_pct:.2f}%){reset}")
        print(f"交易次数: {self.total_trades}")
        print(f"胜率: {self.win_rate:.1f}%\n")
