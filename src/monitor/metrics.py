"""Performance metrics collector"""

from typing import Dict, List, Optional
from decimal import Decimal
from datetime import datetime, timedelta
from collections import deque
import numpy as np

from ..trading.portfolio import Portfolio
from ..trading.order import Order
from ..utils.logger import logger


class MetricsCollector:
    """Performance metrics collector

    Collects and calculates various performance metrics for the trading system
    """

    def __init__(self, window_size: int = 100):
        """Initialize metrics collector

        Args:
            window_size: Sliding window size
        """
        self.window_size = window_size

        # Equity curve
        self.equity_history: deque = deque(maxlen=window_size)

        # Trade records
        self.trades: List[Dict] = []
        self.recent_trades: deque = deque(maxlen=window_size)

        # Order statistics
        self.total_orders = 0
        self.filled_orders = 0
        self.rejected_orders = 0
        self.cancelled_orders = 0

        # P&L statistics
        self.total_pnl = Decimal(0)
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_commission = Decimal(0)

        # Time statistics
        self.start_time = datetime.now()
        self.last_update_time = datetime.now()

        logger.info("Metrics collector initialized")

    def record_equity(self, equity: Decimal, timestamp: datetime = None):
        """Record equity

        Args:
            equity: Current equity
            timestamp: Timestamp
        """
        if timestamp is None:
            timestamp = datetime.now()

        self.equity_history.append({
            'timestamp': timestamp,
            'equity': float(equity)
        })
        self.last_update_time = timestamp

    def record_trade(self, trade: Dict):
        """Record trade

        Args:
            trade: Trade information
        """
        self.trades.append(trade)
        self.recent_trades.append(trade)

        # Update statistics
        pnl = trade.get('pnl', 0)
        if pnl > 0:
            self.winning_trades += 1
        elif pnl < 0:
            self.losing_trades += 1

        self.total_pnl += Decimal(str(pnl))
        self.total_commission += Decimal(str(trade.get('commission', 0)))

    def record_order(self, order: Order):
        """Record order

        Args:
            order: Order object
        """
        self.total_orders += 1

        from ..core.types import OrderStatus
        if order.status == OrderStatus.FILLED:
            self.filled_orders += 1
        elif order.status == OrderStatus.REJECTED:
            self.rejected_orders += 1
        elif order.status == OrderStatus.CANCELLED:
            self.cancelled_orders += 1

    def get_current_metrics(self, portfolio: Portfolio) -> Dict:
        """Get current metrics

        Args:
            portfolio: Portfolio

        Returns:
            Metrics dictionary
        """
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'uptime_seconds': (datetime.now() - self.start_time).total_seconds(),

            # Account metrics
            'total_value': float(portfolio.get_total_value()),
            'cash': float(portfolio.get_balance()),
            'positions_value': float(portfolio.get_positions_value()),
            'total_pnl': float(self.total_pnl),
            'total_pnl_percent': float(portfolio.get_total_pnl_percent()),

            # Trading metrics
            'total_trades': len(self.trades),
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': self._calculate_win_rate(),
            'total_commission': float(self.total_commission),

            # Order metrics
            'total_orders': self.total_orders,
            'filled_orders': self.filled_orders,
            'rejected_orders': self.rejected_orders,
            'cancelled_orders': self.cancelled_orders,
            'fill_rate': self._calculate_fill_rate(),

            # Performance metrics
            'sharpe_ratio': self._calculate_sharpe_ratio(),
            'max_drawdown': self._calculate_max_drawdown(),
            'profit_factor': self._calculate_profit_factor(),
        }

        return metrics

    def _calculate_win_rate(self) -> float:
        """Calculate win rate"""
        total = self.winning_trades + self.losing_trades
        if total == 0:
            return 0.0
        return (self.winning_trades / total) * 100

    def _calculate_fill_rate(self) -> float:
        """Calculate fill rate"""
        if self.total_orders == 0:
            return 0.0
        return (self.filled_orders / self.total_orders) * 100

    def _calculate_sharpe_ratio(self, risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio"""
        if len(self.equity_history) < 2:
            return 0.0

        # Calculate return series
        equities = [e['equity'] for e in self.equity_history]
        returns = np.diff(equities) / equities[:-1]

        if len(returns) == 0 or np.std(returns) == 0:
            return 0.0

        # Annualize
        mean_return = np.mean(returns) * 252
        std_return = np.std(returns) * np.sqrt(252)

        sharpe = (mean_return - risk_free_rate) / std_return
        return float(sharpe)

    def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown"""
        if len(self.equity_history) < 2:
            return 0.0

        equities = [e['equity'] for e in self.equity_history]
        peak = equities[0]
        max_dd = 0.0

        for equity in equities:
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd

        return float(max_dd * 100)  # Return as percentage

    def _calculate_profit_factor(self) -> float:
        """Calculate profit factor"""
        if not self.trades:
            return 0.0

        total_profit = sum(t.get('pnl', 0) for t in self.trades if t.get('pnl', 0) > 0)
        total_loss = abs(sum(t.get('pnl', 0) for t in self.trades if t.get('pnl', 0) < 0))

        if total_loss == 0:
            return 0.0 if total_profit == 0 else float('inf')

        return total_profit / total_loss

    def get_recent_performance(self, minutes: int = 60) -> Dict:
        """Get recent performance

        Args:
            minutes: Time window (minutes)

        Returns:
            Performance metrics
        """
        cutoff_time = datetime.now() - timedelta(minutes=minutes)

        # Filter recent trades
        recent_trades = [t for t in self.trades if t.get('timestamp', datetime.min) > cutoff_time]

        if not recent_trades:
            return {
                'period_minutes': minutes,
                'trades_count': 0,
                'pnl': 0.0,
                'win_rate': 0.0,
            }

        winning = sum(1 for t in recent_trades if t.get('pnl', 0) > 0)
        total = len(recent_trades)
        total_pnl = sum(t.get('pnl', 0) for t in recent_trades)

        return {
            'period_minutes': minutes,
            'trades_count': total,
            'pnl': total_pnl,
            'win_rate': (winning / total * 100) if total > 0 else 0.0,
        }

    def reset(self):
        """Reset all metrics"""
        self.equity_history.clear()
        self.trades.clear()
        self.recent_trades.clear()
        self.total_orders = 0
        self.filled_orders = 0
        self.rejected_orders = 0
        self.cancelled_orders = 0
        self.total_pnl = Decimal(0)
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_commission = Decimal(0)
        self.start_time = datetime.now()
        logger.info("Metrics collector reset")
