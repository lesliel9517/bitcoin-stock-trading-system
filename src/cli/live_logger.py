"""Live trading logger for CLI"""

import asyncio
from datetime import datetime
from decimal import Decimal
from typing import Dict, Optional, List
from collections import deque

from ..core.event import MarketEvent, SignalEvent, OrderEvent, FillEvent, EventType
from ..core.event_bus import EventBus
from ..trading.portfolio import Portfolio


# ANSI color codes
class Colors:
    """ANSI color codes for terminal output"""
    RESET = '\033[0m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    DIM = '\033[2m'


class LiveTradeLogger:
    """Real-time trading log display"""

    def __init__(self, event_bus: EventBus, portfolio: Portfolio):
        self.event_bus = event_bus
        self.portfolio = portfolio
        self.is_running = False

        # Trade records
        self.recent_trades = deque(maxlen=20)
        self.current_prices: Dict[str, Decimal] = {}

        # Statistics
        self.total_signals = 0
        self.total_fills = 0
        self.buy_count = 0
        self.sell_count = 0

        # Subscribe to events
        self.event_bus.subscribe(EventType.MARKET, self.on_market_event)
        self.event_bus.subscribe(EventType.SIGNAL, self.on_signal_event)
        self.event_bus.subscribe(EventType.FILL, self.on_fill_event)

    async def start(self):
        """Start real-time logging"""
        self.is_running = True
        print("\n" + f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}{'LIVE TRADING SESSION':^80}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.RESET}")
        print(f"{Colors.YELLOW}Initial Capital: {Colors.BOLD}${float(self.portfolio.initial_balance):,.2f}{Colors.RESET}")
        print(f"{Colors.DIM}Session Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.RESET}\n")

    async def stop(self):
        """Stop real-time logging"""
        self.is_running = False

    async def on_market_event(self, event: MarketEvent):
        """Handle market data events"""
        if not self.is_running:
            return

        # Update prices
        self.current_prices[event.symbol] = event.price
        self.portfolio.update_prices(self.current_prices)

        # Calculate profit and loss
        total_value = self.portfolio.get_total_value()
        total_pnl = self.portfolio.get_total_pnl()
        pnl_percent = self.portfolio.get_total_pnl_percent()
        position = self.portfolio.get_position(event.symbol)

        # Format timestamp
        ts = event.timestamp.strftime('%H:%M:%S')

        # Format PnL with sign
        pnl_sign = "+" if total_pnl >= 0 else ""

        # Extract extended market data
        change_pct_24h = event.data.get('change_pct_24h')
        change_24h = event.data.get('change_24h')
        high_24h = event.high
        low_24h = event.low
        open_24h = event.open
        volume_24h = event.volume
        mktcap = event.data.get('mktcap')

        # Calculate amplitude (振幅)
        amplitude = None
        if high_24h and low_24h and open_24h and open_24h > 0:
            amplitude = ((high_24h - low_24h) / open_24h) * 100

        # Build rich status line (参考富途牛牛布局)
        status_parts = []

        # Time and Symbol
        status_parts.append(f"{Colors.DIM}[{ts}]{Colors.RESET}")
        status_parts.append(f"{Colors.BOLD}{Colors.WHITE}{event.symbol}{Colors.RESET}")

        # Current Price (大字显示效果)
        status_parts.append(f"{Colors.BOLD}${float(event.price):,.2f}{Colors.RESET}")

        # 24h Change (涨跌额和涨跌幅)
        if change_pct_24h is not None:
            change_sign = "+" if change_pct_24h >= 0 else ""
            change_color = Colors.GREEN if change_pct_24h >= 0 else Colors.RED
            change_display = f"{change_sign}{float(change_pct_24h):.2f}%"

            # Add absolute change if available
            if change_24h is not None:
                change_display += f" ({change_sign}${float(change_24h):,.2f})"

            status_parts.append(f"{change_color}{change_display}{Colors.RESET}")

        # 24h High/Low (最高/最低)
        if high_24h and low_24h:
            status_parts.append(f"{Colors.DIM}H:{Colors.RESET}${float(high_24h):,.2f}")
            status_parts.append(f"{Colors.DIM}L:{Colors.RESET}${float(low_24h):,.2f}")

        # Amplitude (振幅)
        if amplitude is not None:
            status_parts.append(f"{Colors.MAGENTA}Amp:{float(amplitude):.2f}%{Colors.RESET}")

        # Volume (成交量)
        if volume_24h and volume_24h > 0:
            if volume_24h >= 1_000_000:
                vol_display = f"{float(volume_24h)/1_000_000:.2f}M"
            elif volume_24h >= 1000:
                vol_display = f"{float(volume_24h)/1000:.1f}K"
            else:
                vol_display = f"{float(volume_24h):.1f}"
            status_parts.append(f"{Colors.BLUE}Vol:{vol_display}{Colors.RESET}")

        # Market Cap (市值)
        if mktcap and mktcap > 0:
            if mktcap >= 1_000_000_000_000:  # Trillion
                mktcap_display = f"${float(mktcap) / 1_000_000_000_000:.2f}T"
            else:  # Billion
                mktcap_display = f"${float(mktcap) / 1_000_000_000:.1f}B"
            status_parts.append(f"{Colors.CYAN}MCap:{mktcap_display}{Colors.RESET}")

        # Separator
        status_parts.append(f"{Colors.DIM}|{Colors.RESET}")

        # Portfolio Info (持仓信息)
        if position > 0:
            status_parts.append(f"{Colors.CYAN}Pos:{float(position):.4f}{Colors.RESET}")

        status_parts.append(f"{Colors.YELLOW}Equity:${float(total_value):,.2f}{Colors.RESET}")

        # PnL with color
        pnl_color = Colors.GREEN if total_pnl >= 0 else Colors.RED
        status_parts.append(f"{pnl_color}PnL:{pnl_sign}${float(total_pnl):,.2f}({pnl_sign}{float(pnl_percent):.2f}%){Colors.RESET}")

        status = " ".join(status_parts)
        print(status)

    async def on_signal_event(self, event: SignalEvent):
        """Handle signal events"""
        if not self.is_running:
            return

        self.total_signals += 1
        ts = event.timestamp.strftime('%H:%M:%S')
        price = event.metadata.get('price', 'N/A')

        # Rich signal display with colors
        print()
        print(f"{Colors.BOLD}{Colors.YELLOW}{'=' * 80}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.YELLOW}[{ts}] TRADING SIGNAL: {event.signal_type}{Colors.RESET}")
        print(f"{Colors.CYAN}   Symbol: {event.symbol}{Colors.RESET}")
        print(f"{Colors.WHITE}   Price: ${price}{Colors.RESET}")
        print(f"{Colors.MAGENTA}   Strength: {event.strength:.2f}{Colors.RESET}")
        print(f"{Colors.BLUE}   Strategy: {event.strategy_id}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.YELLOW}{'=' * 80}{Colors.RESET}")

    async def on_fill_event(self, event: FillEvent):
        """Handle fill events"""
        if not self.is_running:
            return

        self.total_fills += 1
        if event.side == "BUY":
            self.buy_count += 1
            action_color = Colors.GREEN
            action = "BOUGHT"
        else:
            self.sell_count += 1
            action_color = Colors.RED
            action = "SOLD"

        ts = event.timestamp.strftime('%H:%M:%S')
        fill_value = event.quantity * event.price

        # Get position PnL
        position_obj = self.portfolio.get_position_obj(event.symbol)
        position_pnl = position_obj.unrealized_pnl if position_obj else Decimal('0')
        pnl_sign = "+" if position_pnl >= 0 else ""

        # Get current position
        current_position = self.portfolio.get_position(event.symbol)

        # Rich fill display with colors
        print()
        print(f"{Colors.BOLD}{action_color}{'=' * 80}{Colors.RESET}")
        print(f"{Colors.BOLD}{action_color}[{ts}] ORDER FILLED: {action}{Colors.RESET}")
        print(f"{Colors.CYAN}   Symbol: {event.symbol}{Colors.RESET}")
        print(f"{Colors.WHITE}   Quantity: {float(event.quantity):.4f}{Colors.RESET}")
        print(f"{Colors.WHITE}   Price: ${float(event.price):,.2f}{Colors.RESET}")
        print(f"{Colors.YELLOW}   Total Value: ${float(fill_value):,.2f}{Colors.RESET}")
        print(f"{Colors.DIM}   Commission: ${float(event.commission):,.4f}{Colors.RESET}")
        print(f"{Colors.CYAN}   Current Position: {float(current_position):.4f}{Colors.RESET}")
        pnl_display_color = Colors.GREEN if position_pnl >= 0 else Colors.RED
        print(f"{pnl_display_color}   Position PnL: {pnl_sign}${float(position_pnl):,.2f}{Colors.RESET}")
        print(f"{Colors.YELLOW}   Portfolio Value: ${float(self.portfolio.get_total_value()):,.2f}{Colors.RESET}")
        print(f"{Colors.BOLD}{action_color}{'=' * 80}{Colors.RESET}")

        # Record trade
        self.recent_trades.append({
            'timestamp': ts,
            'side': event.side,
            'symbol': event.symbol,
            'quantity': float(event.quantity),
            'price': float(event.price),
            'pnl': float(position_pnl)
        })

    def print_summary(self):
        """Print trading summary (参考量化交易系统)"""
        print("\n\n" + f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}{'SESSION SUMMARY':^80}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.RESET}")

        # Portfolio Performance
        total_value = self.portfolio.get_total_value()
        total_pnl = self.portfolio.get_total_pnl()
        pnl_percent = self.portfolio.get_total_pnl_percent()
        pnl_sign = "+" if total_pnl >= 0 else ""
        pnl_color = Colors.GREEN if total_pnl >= 0 else Colors.RED

        print(f"\n{Colors.BOLD}{Colors.YELLOW}Portfolio Performance:{Colors.RESET}")
        print(f"  {Colors.DIM}Initial Capital:{Colors.RESET}  ${float(self.portfolio.initial_balance):>15,.2f}")
        print(f"  {Colors.DIM}Final Equity:{Colors.RESET}    ${float(total_value):>15,.2f}")
        print(f"  {Colors.DIM}Available Cash:{Colors.RESET}  ${float(self.portfolio.cash):>15,.2f}")
        print(f"  {pnl_color}Total PnL:{Colors.RESET}       {pnl_sign}${float(total_pnl):>14,.2f} ({pnl_sign}{float(pnl_percent):.2f}%)")

        # Positions
        positions = self.portfolio.get_all_positions()
        if positions:
            print(f"\n{Colors.BOLD}{Colors.YELLOW}Current Positions:{Colors.RESET}")
            for pos in positions:
                pnl = pos.unrealized_pnl
                pnl_pct = pos.get_pnl_percent()
                pnl_sign = "+" if pnl >= 0 else ""
                pos_pnl_color = Colors.GREEN if pnl >= 0 else Colors.RED

                print(f"  {Colors.CYAN}{pos.symbol}{Colors.RESET}")
                print(f"    {Colors.DIM}Quantity:{Colors.RESET}     {float(pos.quantity):>10.4f}")
                print(f"    {Colors.DIM}Avg Price:{Colors.RESET}    ${float(pos.average_price):>10,.2f}")
                print(f"    {Colors.DIM}Current Price:{Colors.RESET} ${float(pos.current_price):>10,.2f}")
                print(f"    {pos_pnl_color}Position PnL:{Colors.RESET}  {pnl_sign}${float(pnl):>9,.2f} ({pnl_sign}{float(pnl_pct):.2f}%)")

        # Trading Statistics
        print(f"\n{Colors.BOLD}{Colors.YELLOW}Trading Statistics:{Colors.RESET}")
        print(f"  {Colors.DIM}Total Signals:{Colors.RESET}   {self.total_signals:>5}")
        print(f"  {Colors.DIM}Total Fills:{Colors.RESET}     {self.total_fills:>5}")
        print(f"  {Colors.GREEN}Buy Orders:{Colors.RESET}      {self.buy_count:>5}")
        print(f"  {Colors.RED}Sell Orders:{Colors.RESET}     {self.sell_count:>5}")

        # Win rate calculation
        if self.total_fills > 0:
            # Calculate win rate from recent trades
            winning_trades = sum(1 for t in self.recent_trades if t['pnl'] > 0)
            losing_trades = sum(1 for t in self.recent_trades if t['pnl'] < 0)
            total_closed = winning_trades + losing_trades

            if total_closed > 0:
                win_rate = (winning_trades / total_closed) * 100
                win_rate_color = Colors.GREEN if win_rate >= 50 else Colors.RED
                print(f"  {win_rate_color}Win Rate:{Colors.RESET}       {win_rate:>5.1f}% ({winning_trades}W/{losing_trades}L)")

        # Recent trades
        if self.recent_trades:
            print(f"\n{Colors.BOLD}{Colors.YELLOW}Recent Trades:{Colors.RESET}")
            for trade in list(self.recent_trades)[-10:]:
                pnl_sign = "+" if trade['pnl'] >= 0 else ""
                trade_pnl_color = Colors.GREEN if trade['pnl'] >= 0 else Colors.RED
                side_color = Colors.GREEN if trade['side'] == 'BUY' else Colors.RED

                print(f"  {Colors.DIM}[{trade['timestamp']}]{Colors.RESET} "
                      f"{side_color}{trade['side']:4s}{Colors.RESET} "
                      f"{trade['quantity']:>8.4f} {trade['symbol']} @ "
                      f"${trade['price']:>10,.2f} | "
                      f"{trade_pnl_color}PnL {pnl_sign}${trade['pnl']:>8,.2f}{Colors.RESET}")

        print("\n" + f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.RESET}")
