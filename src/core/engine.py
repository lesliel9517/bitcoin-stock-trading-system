"""Real-time trading engine"""

import asyncio
from typing import Dict, List, Optional
from decimal import Decimal
from datetime import datetime

from ..core.event_bus import EventBus
from ..core.event import MarketEvent, SignalEvent
from ..strategies.base import Strategy
from ..trading.portfolio import Portfolio
from ..trading.order_manager import OrderManager
from ..trading.execution import ExecutionEngine
from ..trading.exchanges.base import ExchangeGateway
from ..data.feed import DataFeed
from ..utils.logger import logger


class TradingEngine:
    """Real-time trading engine

    Integrates all modules to implement complete real-time trading workflow
    """

    def __init__(
        self,
        initial_capital: Decimal = Decimal(100000),
        config: Dict = None
    ):
        """Initialize trading engine

        Args:
            initial_capital: Initial capital
            config: Configuration information
        """
        self.config = config or {}
        self.is_running = False

        # Create event bus
        self.event_bus = EventBus()

        # Create portfolio
        self.portfolio = Portfolio(initial_balance=initial_capital)

        # Exchange and order manager (set later)
        self.exchange: Optional[ExchangeGateway] = None
        self.order_manager: Optional[OrderManager] = None
        self.execution_engine: Optional[ExecutionEngine] = None
        self.risk_manager = None
        self.monitor: Optional = None

        # Data feed
        self.data_feed: Optional[DataFeed] = None

        # Strategy list
        self.strategies: List[Strategy] = []

        # Create monitoring engine
        monitor_config = self.config.get('monitor', {})
        if monitor_config.get('enabled', True):
            from ..monitor.monitor import MonitoringEngine
            self.monitor = MonitoringEngine(self.event_bus, self.portfolio, monitor_config)
            logger.info("Monitoring engine enabled")

        logger.info(f"Trading engine initialized with capital: {initial_capital}")

    def set_exchange(self, exchange: ExchangeGateway):
        """Set exchange

        Args:
            exchange: Exchange gateway
        """
        self.exchange = exchange
        self.order_manager = OrderManager(self.event_bus, exchange)

        # Create risk manager
        risk_config = self.config.get('risk', {})
        if risk_config:
            from ..risk.manager import RiskManager
            self.risk_manager = RiskManager(self.event_bus, risk_config)
            logger.info("Risk manager enabled")

        self.execution_engine = ExecutionEngine(
            self.event_bus,
            self.order_manager,
            self.portfolio,
            self.risk_manager,
            self.config.get('execution', {})
        )
        logger.info(f"Exchange set: {exchange.exchange_id}")

    def set_data_feed(self, data_feed: DataFeed):
        """Set data feed

        Args:
            data_feed: Data feed manager
        """
        self.data_feed = data_feed
        logger.info("Data feed set")

    def add_strategy(self, strategy: Strategy):
        """Add strategy

        Args:
            strategy: Strategy instance
        """
        from ..core.event import EventType

        self.strategies.append(strategy)

        # Set event bus reference for strategy
        strategy.event_bus = self.event_bus

        # Subscribe to market events
        self.event_bus.subscribe(EventType.MARKET, strategy.on_market_data)

        logger.info(f"Strategy added: {strategy.strategy_id}")

    async def start(self):
        """Start trading engine"""
        if self.is_running:
            logger.warning("Trading engine is already running")
            return

        if not self.exchange:
            raise ValueError("Exchange not set")

        if not self.data_feed:
            raise ValueError("Data feed not set")

        if not self.strategies:
            raise ValueError("No strategies added")

        logger.info("Starting trading engine...")

        # Connect to exchange
        await self.exchange.connect()

        # Start event bus
        await self.event_bus.start()

        # Start data feed
        await self.data_feed.start()

        # Start all strategies
        for strategy in self.strategies:
            strategy.start()

        self.is_running = True
        logger.info("Trading engine started successfully")

    async def stop(self):
        """Stop trading engine"""
        if not self.is_running:
            return

        logger.info("Stopping trading engine...")

        # Stop all strategies
        for strategy in self.strategies:
            strategy.stop()

        # Cancel all active orders
        if self.order_manager:
            await self.order_manager.cancel_all_orders()

        # Stop data feed
        if self.data_feed:
            await self.data_feed.stop()

        # Stop event bus
        await self.event_bus.stop()

        # Disconnect from exchange
        if self.exchange:
            await self.exchange.disconnect()

        self.is_running = False
        logger.info("Trading engine stopped")

    async def run(self, duration: Optional[float] = None):
        """Run trading engine

        Args:
            duration: Run duration in seconds, None means run indefinitely
        """
        await self.start()

        try:
            if duration:
                logger.info(f"Running for {duration} seconds...")
                await asyncio.sleep(duration)
            else:
                logger.info("Running indefinitely (press Ctrl+C to stop)...")
                while self.is_running:
                    await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        finally:
            await self.stop()

    def get_status(self) -> Dict:
        """Get engine status

        Returns:
            Status information dictionary
        """
        return {
            'is_running': self.is_running,
            'portfolio': self.portfolio.to_dict(),
            'strategies': [
                {
                    'id': s.strategy_id,
                    'active': s.is_active,
                    'symbols': s.symbols
                }
                for s in self.strategies
            ],
            'active_orders': len(self.order_manager.get_active_orders()) if self.order_manager else 0,
            'exchange': self.exchange.exchange_id if self.exchange else None,
        }

    def get_portfolio(self) -> Portfolio:
        """Get portfolio

        Returns:
            Portfolio object
        """
        return self.portfolio

    def get_orders(self, symbol: Optional[str] = None) -> List:
        """Get order list

        Args:
            symbol: Trading pair symbol (optional)

        Returns:
            Order list
        """
        if not self.order_manager:
            return []

        orders = self.order_manager.get_all_orders(symbol)
        return [order.to_dict() for order in orders]
