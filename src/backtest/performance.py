"""Performance analysis"""

from typing import Dict, List
import pandas as pd
import numpy as np
from decimal import Decimal


class PerformanceAnalyzer:
    """Performance analyzer

    Calculates various trading performance metrics
    """

    def calculate_metrics(
        self,
        equity_curve: pd.Series,
        trades: List[Dict],
        initial_capital: float,
        risk_free_rate: float = 0.02
    ) -> Dict:
        """Calculate performance metrics

        Args:
            equity_curve: Equity curve
            trades: Trade records
            initial_capital: Initial capital
            risk_free_rate: Risk-free rate (annualized)

        Returns:
            Performance metrics dictionary
        """
        if len(equity_curve) == 0:
            return {}

        # Basic metrics
        final_equity = equity_curve.iloc[-1]
        total_return = (final_equity - initial_capital) / initial_capital
        total_return_pct = total_return * 100

        # Calculate annualized return
        days = (equity_curve.index[-1] - equity_curve.index[0]).days
        years = days / 365.25
        annual_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0
        annual_return_pct = annual_return * 100

        # Calculate maximum drawdown
        max_drawdown, max_drawdown_pct = self._calculate_max_drawdown(equity_curve)

        # Calculate Sharpe ratio
        sharpe_ratio = self._calculate_sharpe_ratio(equity_curve, initial_capital, risk_free_rate)

        # Calculate Sortino ratio
        sortino_ratio = self._calculate_sortino_ratio(equity_curve, initial_capital, risk_free_rate)

        # Trade statistics
        trade_stats = self._calculate_trade_stats(trades)

        # Win rate
        win_rate = trade_stats['win_rate']

        # Profit factor
        profit_factor = trade_stats['profit_factor']

        return {
            'initial_capital': initial_capital,
            'final_equity': final_equity,
            'total_return': total_return,
            'total_return_pct': total_return_pct,
            'annual_return': annual_return,
            'annual_return_pct': annual_return_pct,
            'max_drawdown': max_drawdown,
            'max_drawdown_pct': max_drawdown_pct,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'total_trades': trade_stats['total_trades'],
            'winning_trades': trade_stats['winning_trades'],
            'losing_trades': trade_stats['losing_trades'],
            'avg_win': trade_stats['avg_win'],
            'avg_loss': trade_stats['avg_loss'],
            'largest_win': trade_stats['largest_win'],
            'largest_loss': trade_stats['largest_loss'],
            'trading_days': days,
        }

    def _calculate_max_drawdown(self, equity_curve: pd.Series) -> tuple:
        """Calculate maximum drawdown

        Args:
            equity_curve: Equity curve

        Returns:
            (Maximum drawdown amount, Maximum drawdown percentage)
        """
        cummax = equity_curve.cummax()
        drawdown = equity_curve - cummax
        max_drawdown = drawdown.min()
        max_drawdown_pct = (max_drawdown / cummax[drawdown.idxmin()]) * 100 if len(drawdown) > 0 else 0

        return float(max_drawdown), float(max_drawdown_pct)

    def _calculate_sharpe_ratio(
        self,
        equity_curve: pd.Series,
        initial_capital: float,
        risk_free_rate: float
    ) -> float:
        """Calculate Sharpe ratio

        Args:
            equity_curve: Equity curve
            initial_capital: Initial capital
            risk_free_rate: Risk-free rate

        Returns:
            Sharpe ratio
        """
        returns = equity_curve.pct_change().dropna()

        if len(returns) == 0 or returns.std() == 0:
            return 0.0

        # Annualize
        annual_return = returns.mean() * 252  # Assume 252 trading days
        annual_std = returns.std() * np.sqrt(252)

        sharpe = (annual_return - risk_free_rate) / annual_std

        return float(sharpe)

    def _calculate_sortino_ratio(
        self,
        equity_curve: pd.Series,
        initial_capital: float,
        risk_free_rate: float
    ) -> float:
        """Calculate Sortino ratio (only considers downside volatility)

        Args:
            equity_curve: Equity curve
            initial_capital: Initial capital
            risk_free_rate: Risk-free rate

        Returns:
            Sortino ratio
        """
        returns = equity_curve.pct_change().dropna()

        if len(returns) == 0:
            return 0.0

        # Only consider negative returns
        downside_returns = returns[returns < 0]

        if len(downside_returns) == 0 or downside_returns.std() == 0:
            return 0.0

        # Annualize
        annual_return = returns.mean() * 252
        downside_std = downside_returns.std() * np.sqrt(252)

        sortino = (annual_return - risk_free_rate) / downside_std

        return float(sortino)

    def _calculate_trade_stats(self, trades: List[Dict]) -> Dict:
        """Calculate trade statistics

        Args:
            trades: Trade records

        Returns:
            Trade statistics dictionary
        """
        if len(trades) < 2:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'largest_win': 0.0,
                'largest_loss': 0.0,
            }

        # Pair buy and sell trades
        pnls = []
        buy_price = None

        for trade in trades:
            if trade['side'] == 'BUY':
                buy_price = trade['price']
            elif trade['side'] == 'SELL' and buy_price is not None:
                pnl = (trade['price'] - buy_price) * trade['quantity'] - trade['commission']
                pnls.append(pnl)
                buy_price = None

        if len(pnls) == 0:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'largest_win': 0.0,
                'largest_loss': 0.0,
            }

        winning_trades = [p for p in pnls if p > 0]
        losing_trades = [p for p in pnls if p < 0]

        total_trades = len(pnls)
        num_winning = len(winning_trades)
        num_losing = len(losing_trades)

        win_rate = (num_winning / total_trades * 100) if total_trades > 0 else 0

        total_profit = sum(winning_trades) if winning_trades else 0
        total_loss = abs(sum(losing_trades)) if losing_trades else 0
        profit_factor = (total_profit / total_loss) if total_loss > 0 else 0

        avg_win = (sum(winning_trades) / num_winning) if num_winning > 0 else 0
        avg_loss = (sum(losing_trades) / num_losing) if num_losing > 0 else 0

        largest_win = max(winning_trades) if winning_trades else 0
        largest_loss = min(losing_trades) if losing_trades else 0

        return {
            'total_trades': total_trades,
            'winning_trades': num_winning,
            'losing_trades': num_losing,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'largest_win': largest_win,
            'largest_loss': largest_loss,
        }
