"""Execution engine for processing trading signals"""

import asyncio
from typing import Dict, Optional
from decimal import Decimal
from datetime import datetime

from .order_manager import OrderManager
from .portfolio import Portfolio
from ..core.event import SignalEvent, FillEvent, MarketEvent
from ..core.event_bus import EventBus
from ..core.types import OrderSide, SignalType
from ..utils.logger import logger


class ExecutionEngine:
    """Execution engine

    Processes trading signals and executes orders
    """

    def __init__(
        self,
        event_bus: EventBus,
        order_manager: OrderManager,
        portfolio: Portfolio,
        risk_manager=None,
        config: Dict = None
    ):
        """Initialize execution engine

        Args:
            event_bus: Event bus
            order_manager: Order manager
            portfolio: Portfolio
            risk_manager: Risk manager (optional)
            config: Configuration
        """
        self.event_bus = event_bus
        self.order_manager = order_manager
        self.portfolio = portfolio
        self.risk_manager = risk_manager
        self.config = config or {}

        # Execution parameters
        self.default_position_size = Decimal(self.config.get('default_position_size', '0.95'))
        self.min_order_value = Decimal(self.config.get('min_order_value', '10'))

        # Subscribe to signal events
        from ..core.event import EventType
        self.event_bus.subscribe(EventType.SIGNAL, self.on_signal)
        self.event_bus.subscribe(EventType.FILL, self.on_fill)
        self.event_bus.subscribe(EventType.MARKET, self.on_market_data)

        logger.info("Execution engine initialized")

    async def on_signal(self, event: SignalEvent):
        """Process trading signal

        Args:
            event: Signal event
        """
        logger.info(f"Processing signal: {event.signal_type} for {event.symbol} (strength={event.strength})")

        try:
            # Execute corresponding operation based on signal type
            if event.signal_type == SignalType.BUY.value:
                await self._execute_buy(event)
            elif event.signal_type == SignalType.SELL.value:
                await self._execute_sell(event)
            elif event.signal_type == SignalType.CLOSE.value:
                await self._execute_close(event)
            else:
                logger.warning(f"Unknown signal type: {event.signal_type}")

        except Exception as e:
            logger.error(f"Error processing signal: {e}", exc_info=True)

    async def _execute_buy(self, signal: SignalEvent):
        """Execute buy signal

        Args:
            signal: Signal event
        """
        symbol = signal.symbol

        # Check if already have position
        current_position = self.portfolio.get_position(symbol)
        if current_position > 0:
            logger.info(f"Already have position in {symbol}, skipping buy signal")
            return

        # Calculate order quantity
        quantity = self._calculate_order_quantity(symbol, signal)
        if quantity <= 0:
            logger.warning(f"Calculated quantity is zero or negative for {symbol}")
            return

        # Create order
        order = await self.order_manager.create_order(
            symbol=symbol,
            side=OrderSide.BUY,
            quantity=quantity,
            order_type="MARKET",
            strategy_id=signal.strategy_id
        )

        # Risk validation
        if self.risk_manager:
            is_valid, error_msg = await self.risk_manager.validate_order(order, self.portfolio)
            if not is_valid:
                logger.warning(f"Order rejected by risk manager: {error_msg}")
                return

        # Submit order
        await self.order_manager.submit_order(order)

    async def _execute_sell(self, signal: SignalEvent):
        """Execute sell signal

        Args:
            signal: Signal event
        """
        symbol = signal.symbol

        # Check position
        current_position = self.portfolio.get_position(symbol)
        if current_position <= 0:
            logger.info(f"No position in {symbol}, skipping sell signal")
            return

        # Sell entire position
        quantity = current_position

        # Create and submit order
        order = await self.order_manager.create_order(
            symbol=symbol,
            side=OrderSide.SELL,
            quantity=quantity,
            order_type="MARKET",
            strategy_id=signal.strategy_id
        )

        await self.order_manager.submit_order(order)

    async def _execute_close(self, signal: SignalEvent):
        """Execute close position signal

        Args:
            signal: Signal event
        """
        # Close position is same as sell
        await self._execute_sell(signal)

    def _calculate_order_quantity(self, symbol: str, signal: SignalEvent) -> Decimal:
        """Calculate order quantity

        Args:
            symbol: Trading pair symbol
            signal: Signal event

        Returns:
            Order quantity
        """
        # Get current price (from signal metadata)
        price = signal.metadata.get('price')
        if price is None:
            logger.warning(f"No price in signal metadata for {symbol}")
            return Decimal(0)

        price = Decimal(str(price))

        # Use risk manager to calculate position size
        if self.risk_manager:
            quantity = self.risk_manager.calculate_position_size(
                symbol, price, self.portfolio, signal.strength
            )
        else:
            # Fallback to default calculation method
            available_cash = self.portfolio.get_balance() * self.default_position_size
            quantity = available_cash / price
            quantity = quantity * Decimal(str(signal.strength))

        # Check minimum order value
        order_value = quantity * price
        if order_value < self.min_order_value:
            logger.warning(f"Order value {order_value} below minimum {self.min_order_value}")
            return Decimal(0)

        return quantity

    async def on_fill(self, event: FillEvent):
        """Process fill event

        Args:
            event: Fill event
        """
        logger.info(f"Processing fill: {event.side} {event.quantity} {event.symbol} @ {event.price}")

        try:
            # Update portfolio position (position only, not cash)
            if event.side == "BUY":
                self.portfolio.update_position(
                    symbol=event.symbol,
                    quantity=event.quantity,
                    price=event.price,
                    exchange=event.exchange
                )

                # Set stop loss and take profit
                if self.risk_manager:
                    self.risk_manager.on_position_opened(event.symbol, event.price)

            else:
                self.portfolio.update_position(
                    symbol=event.symbol,
                    quantity=-event.quantity,
                    price=event.price,
                    exchange=event.exchange
                )

                # Remove stop loss and take profit
                if self.risk_manager:
                    position = self.portfolio.get_position(event.symbol)
                    if position == 0:
                        self.risk_manager.on_position_closed(event.symbol)

            # Sync cash balance from exchange (exchange manages the actual cash)
            exchange_balance = await self.order_manager.exchange.get_balance()
            self.portfolio.cash = exchange_balance

            logger.info(f"Portfolio updated: balance={self.portfolio.get_balance()}, total_value={self.portfolio.get_total_value()}")

        except Exception as e:
            logger.error(f"Error processing fill: {e}", exc_info=True)

    async def on_market_data(self, event: MarketEvent):
        """Process market data and check stop loss/take profit

        Args:
            event: Market event
        """
        # Update exchange with current price so it can execute orders
        if hasattr(self.order_manager.exchange, 'update_price'):
            self.order_manager.exchange.update_price(event.symbol, event.price)

        if not self.risk_manager:
            return

        symbol = event.symbol
        current_price = event.price

        # Check if have position
        position = self.portfolio.get_position(symbol)
        if position <= 0:
            return

        # Check stop loss and take profit
        should_close, reason = await self.risk_manager.check_stop_levels(symbol, current_price)

        if should_close:
            logger.info(f"Closing position for {symbol} due to {reason}")

            # Create close position signal
            close_signal = SignalEvent(
                event_type=event.event_type,
                strategy_id="risk_manager",
                symbol=symbol,
                signal_type=SignalType.CLOSE.value,
                strength=1.0,
                metadata={'price': float(current_price), 'reason': reason},
                timestamp=datetime.now(),
                data={},
                source="execution_engine"
            )

            # Execute close position
            await self._execute_close(close_signal)
