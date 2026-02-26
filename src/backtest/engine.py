"""Backtest engine"""

import asyncio
from typing import Dict, List, Optional
from datetime import datetime
from decimal import Decimal
import pandas as pd
import uuid

from ..core.event_bus import EventBus
from ..core.event import MarketEvent
from ..strategies.base import Strategy
from ..trading.portfolio import Portfolio
from ..trading.order import Order
from ..core.types import OrderSide, OrderType, OrderStatus
from ..utils.logger import logger
from .performance import PerformanceAnalyzer
from ..data.storage import DataStorage
from .visualizer import BacktestVisualizer


class BacktestEngine:
    """Backtest engine

    Simulates historical trading and evaluates strategy performance
    """

    def __init__(
        self,
        initial_capital: Decimal = Decimal(100000),
        commission: Decimal = Decimal("0.001"),
        slippage: Decimal = Decimal("0.0005"),
        storage: Optional[DataStorage] = None
    ):
        """Initialize backtest engine

        Args:
            initial_capital: Initial capital
            commission: Commission rate
            slippage: Slippage rate
            storage: Data storage instance
        """
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage

        self.portfolio = Portfolio(initial_balance=initial_capital)
        self.strategy: Optional[Strategy] = None
        self.analyzer = PerformanceAnalyzer()
        self.storage = storage or DataStorage()
        self.visualizer = BacktestVisualizer()

        # Backtest data
        self.trades: List[Dict] = []
        self.equity_curve: List[Dict] = []
        self.session_id = str(uuid.uuid4())

        logger.info(
            f"Backtest engine initialized: "
            f"capital={initial_capital}, commission={commission}, slippage={slippage}, session={self.session_id}"
        )

    def set_strategy(self, strategy: Strategy):
        """Set strategy

        Args:
            strategy: Strategy instance
        """
        self.strategy = strategy
        self.strategy.start()
        logger.info(f"Strategy set: {strategy.strategy_id}")

    async def run(
        self,
        data: pd.DataFrame,
        symbol: str,
        exchange: str = "binance"
    ) -> Dict:
        """Run backtest

        Args:
            data: Historical OHLCV data
            symbol: Trading pair symbol
            exchange: Exchange

        Returns:
            Backtest results
        """
        if self.strategy is None:
            raise ValueError("Strategy not set")

        logger.info(f"Starting backtest for {symbol} with {len(data)} data points")

        # Initialize strategy data
        self.strategy.update_data(symbol, data.copy())

        # Calculate indicators and generate signals
        data_with_signals = self.strategy.backtest_signals(data)

        # Simulate trading
        position = Decimal(0)  # Current position

        for i in range(len(data_with_signals)):
            row = data_with_signals.iloc[i]
            timestamp = row.name if isinstance(row.name, datetime) else datetime.now()
            price = Decimal(str(row['close']))
            signal = row.get('signal', 0)

            # Update position prices
            self.portfolio.update_prices({symbol: price})

            # Record equity curve
            self.equity_curve.append({
                'timestamp': timestamp,
                'equity': float(self.portfolio.get_total_value()),
                'cash': float(self.portfolio.cash),
                'position_value': float(self.portfolio.get_positions_value()),
                'price': float(price)
            })

            # Process signals
            if signal == 1 and position == 0:
                # Buy signal and no position
                quantity = self._calculate_position_size(price)
                if quantity > 0:
                    self._execute_trade(symbol, OrderSide.BUY, quantity, price, timestamp, exchange)
                    position = quantity

            elif signal == -1 and position > 0:
                # Sell signal and has position
                self._execute_trade(symbol, OrderSide.SELL, position, price, timestamp, exchange)
                position = Decimal(0)

        # Close position if still holding at the end
        if position > 0:
            final_price = Decimal(str(data_with_signals.iloc[-1]['close']))
            final_timestamp = data_with_signals.index[-1]
            self._execute_trade(symbol, OrderSide.SELL, position, final_price, final_timestamp, exchange)

        # Calculate performance metrics
        metrics = self._calculate_metrics()

        logger.info(f"Backtest completed: {len(self.trades)} trades, final equity: {self.portfolio.get_total_value()}")

        # Save to database
        self._save_results(data_with_signals, symbol, metrics)

        # Generate visualization
        report_path = self._generate_report(data_with_signals, metrics)

        return {
            'session_id': self.session_id,
            'data': data_with_signals,
            'trades': self.trades,
            'equity_curve': pd.DataFrame(self.equity_curve),
            'metrics': metrics,
            'portfolio': self.portfolio.to_dict(),
            'report_path': report_path
        }

    def _calculate_position_size(self, price: Decimal) -> Decimal:
        """Calculate position size

        Args:
            price: Current price

        Returns:
            Quantity that can be bought
        """
        # Use 95% of available cash
        available_cash = self.portfolio.cash * Decimal("0.95")
        quantity = available_cash / price

        # Consider commission
        quantity = quantity / (Decimal(1) + self.commission)

        return quantity

    def _execute_trade(
        self,
        symbol: str,
        side: OrderSide,
        quantity: Decimal,
        price: Decimal,
        timestamp: datetime,
        exchange: str
    ):
        """Execute trade

        Args:
            symbol: Trading pair symbol
            side: Buy or sell direction
            quantity: Quantity
            price: Price
            timestamp: Timestamp
            exchange: Exchange
        """
        # Apply slippage
        if side == OrderSide.BUY:
            execution_price = price * (Decimal(1) + self.slippage)
        else:
            execution_price = price * (Decimal(1) - self.slippage)

        # Calculate commission
        commission = quantity * execution_price * self.commission

        # Update position
        if side == OrderSide.BUY:
            self.portfolio.update_position(symbol, quantity, execution_price, exchange)
            self.portfolio.cash -= commission
        else:
            self.portfolio.update_position(symbol, -quantity, execution_price, exchange)
            self.portfolio.cash -= commission

        # Record trade
        trade = {
            'timestamp': timestamp,
            'symbol': symbol,
            'side': side.value,
            'quantity': float(quantity),
            'price': float(execution_price),
            'commission': float(commission),
            'portfolio_value': float(self.portfolio.get_total_value())
        }
        self.trades.append(trade)

        logger.debug(f"Trade executed: {side.value} {quantity} {symbol} @ {execution_price}")

    def _calculate_metrics(self) -> Dict:
        """Calculate performance metrics

        Returns:
            Performance metrics dictionary
        """
        if not self.equity_curve:
            return {}

        equity_df = pd.DataFrame(self.equity_curve)
        equity_df.set_index('timestamp', inplace=True)

        return self.analyzer.calculate_metrics(
            equity_curve=equity_df['equity'],
            trades=self.trades,
            initial_capital=float(self.initial_capital)
        )

    def _save_results(self, data: pd.DataFrame, symbol: str, metrics: Dict):
        """Save backtest results to database

        Args:
            data: Market data with signals
            symbol: Trading symbol
            metrics: Performance metrics
        """
        try:
            # Save trades
            self.storage.save_trades(
                self.trades,
                self.session_id,
                self.strategy.strategy_id if self.strategy else "unknown"
            )

            # Save equity curve
            self.storage.save_equity_curve(self.equity_curve, self.session_id)

            # Save session metadata
            session_data = {
                'id': self.session_id,
                'strategy': self.strategy.strategy_id if self.strategy else "unknown",
                'symbol': symbol,
                'start_date': data.index[0].isoformat() if len(data) > 0 else datetime.now().isoformat(),
                'end_date': data.index[-1].isoformat() if len(data) > 0 else datetime.now().isoformat(),
                'initial_capital': float(self.initial_capital),
                'final_capital': float(self.portfolio.get_total_value()),
                'total_return': metrics.get('total_return', 0),
                'total_trades': len(self.trades),
                'win_rate': metrics.get('win_rate', 0),
                'sharpe_ratio': metrics.get('sharpe_ratio', 0),
                'max_drawdown': metrics.get('max_drawdown', 0),
                'config': {
                    'commission': float(self.commission),
                    'slippage': float(self.slippage)
                }
            }
            self.storage.save_backtest_session(session_data)

            logger.info(f"Backtest results saved to database: session={self.session_id}")
        except Exception as e:
            logger.error(f"Failed to save backtest results: {e}")

    def _generate_report(self, data: pd.DataFrame, metrics: Dict) -> str:
        """Generate visualization report

        Args:
            data: Market data with signals
            metrics: Performance metrics

        Returns:
            Path to generated report
        """
        try:
            equity_df = pd.DataFrame(self.equity_curve)
            report_path = f"./data/reports/backtest_{self.session_id}.html"

            self.visualizer.create_report(
                data=data,
                trades=self.trades,
                equity_curve=equity_df,
                metrics=metrics,
                output_path=report_path
            )

            return report_path
        except Exception as e:
            logger.error(f"Failed to generate visualization report: {e}")
            return ""
