"""Simulated exchange for testing"""

import asyncio
from typing import Dict, Optional
from decimal import Decimal
from datetime import datetime
import uuid

from .base import ExchangeGateway
from ..order import Order
from ...core.types import OrderStatus, OrderType
from ...utils.logger import logger


class SimulatedExchange(ExchangeGateway):
    """Simulated exchange

    For testing and simulated trading, does not connect to real exchange
    """

    def __init__(self, exchange_id: str = "simulator", config: Dict = None):
        """Initialize simulated exchange

        Args:
            exchange_id: Exchange ID
            config: Configuration
        """
        super().__init__(exchange_id, config or {})

        # Simulated account state
        self.balance = Decimal(config.get('initial_balance', '100000') if config else '100000')
        self.positions: Dict[str, Decimal] = {}
        self.orders: Dict[str, Order] = {}
        self.prices: Dict[str, Decimal] = {}

        # Simulation parameters
        self.commission_rate = Decimal(config.get('commission', '0.001') if config else '0.001')
        self.slippage_rate = Decimal(config.get('slippage', '0.0005') if config else '0.0005')
        self.latency_ms = config.get('latency_ms', 100) if config else 100

        logger.info(f"Simulated exchange initialized: balance={self.balance}")

    async def connect(self):
        """Connect to simulated exchange"""
        await asyncio.sleep(0.1)  # Simulate connection latency
        self.is_connected = True
        logger.info("Connected to simulated exchange")

    async def disconnect(self):
        """Disconnect"""
        self.is_connected = False
        logger.info("Disconnected from simulated exchange")

    async def submit_order(self, order: Order) -> Order:
        """Submit order

        Args:
            order: Order object

        Returns:
            Updated order object
        """
        if not self.is_connected:
            order.status = OrderStatus.REJECTED
            order.error_message = "Exchange not connected"
            return order

        # Validate order
        is_valid, error_msg = self.validate_order(order)
        if not is_valid:
            order.status = OrderStatus.REJECTED
            order.error_message = error_msg
            logger.warning(f"Order rejected: {error_msg}")
            return order

        # Simulate network latency
        await asyncio.sleep(self.latency_ms / 1000)

        # Get current price
        current_price = self.prices.get(order.symbol)
        if current_price is None:
            order.status = OrderStatus.REJECTED
            order.error_message = f"No price data for {order.symbol}"
            logger.warning(f"Order rejected: no price data for {order.symbol}")
            return order

        # Calculate execution price (apply slippage)
        if order.order_type == OrderType.MARKET:
            if order.side.value == "BUY":
                execution_price = current_price * (Decimal(1) + self.slippage_rate)
            else:
                execution_price = current_price * (Decimal(1) - self.slippage_rate)
        elif order.order_type == OrderType.LIMIT:
            execution_price = order.price
        else:
            order.status = OrderStatus.REJECTED
            order.error_message = f"Unsupported order type: {order.order_type}"
            return order

        # Check if balance is sufficient
        if order.side.value == "BUY":
            required_balance = order.quantity * execution_price * (Decimal(1) + self.commission_rate)
            if required_balance > self.balance:
                order.status = OrderStatus.REJECTED
                order.error_message = f"Insufficient balance: required={required_balance}, available={self.balance}"
                logger.warning(f"Order rejected: insufficient balance")
                return order

        # Check if position is sufficient (when selling)
        if order.side.value == "SELL":
            current_position = self.positions.get(order.symbol, Decimal(0))
            if current_position < order.quantity:
                order.status = OrderStatus.REJECTED
                order.error_message = f"Insufficient position: required={order.quantity}, available={current_position}"
                logger.warning(f"Order rejected: insufficient position")
                return order

        # Execute order
        order.status = OrderStatus.FILLED
        order.filled_quantity = order.quantity
        order.average_price = execution_price
        order.filled_at = datetime.now()

        # Calculate commission
        commission = order.quantity * execution_price * self.commission_rate
        order.commission = commission

        # Update account state
        if order.side.value == "BUY":
            cost = order.quantity * execution_price + commission
            self.balance -= cost
            self.positions[order.symbol] = self.positions.get(order.symbol, Decimal(0)) + order.quantity
            logger.info(f"Buy order filled: {order.quantity} {order.symbol} @ {execution_price}, cost={cost}")
        else:
            proceeds = order.quantity * execution_price - commission
            self.balance += proceeds
            self.positions[order.symbol] = self.positions.get(order.symbol, Decimal(0)) - order.quantity
            logger.info(f"Sell order filled: {order.quantity} {order.symbol} @ {execution_price}, proceeds={proceeds}")

        # Save order
        self.orders[order.order_id] = order

        return order

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel order

        Args:
            order_id: Order ID

        Returns:
            Whether successfully cancelled
        """
        if order_id in self.orders:
            order = self.orders[order_id]
            if order.status in [OrderStatus.PENDING, OrderStatus.SUBMITTED]:
                order.status = OrderStatus.CANCELLED
                order.updated_at = datetime.now()
                logger.info(f"Order cancelled: {order_id}")
                return True
        return False

    async def get_order_status(self, order_id: str) -> Optional[Order]:
        """Query order status

        Args:
            order_id: Order ID

        Returns:
            Order object
        """
        return self.orders.get(order_id)

    async def get_balance(self, currency: str = "USD") -> Decimal:
        """Query account balance

        Args:
            currency: Currency type

        Returns:
            Balance
        """
        return self.balance

    async def get_position(self, symbol: str) -> Decimal:
        """Query position

        Args:
            symbol: Trading pair symbol

        Returns:
            Position quantity
        """
        return self.positions.get(symbol, Decimal(0))

    async def get_latest_price(self, symbol: str) -> Optional[Decimal]:
        """Get latest price

        Args:
            symbol: Trading pair symbol

        Returns:
            Latest price
        """
        return self.prices.get(symbol)

    def update_price(self, symbol: str, price: Decimal):
        """Update price (for simulation)

        Args:
            symbol: Trading pair symbol
            price: Price
        """
        self.prices[symbol] = price

    def get_all_orders(self) -> list[Order]:
        """Get all orders

        Returns:
            Order list
        """
        return list(self.orders.values())

    def reset(self):
        """Reset simulated exchange state"""
        initial_balance = Decimal(self.config.get('initial_balance', '100000'))
        self.balance = initial_balance
        self.positions.clear()
        self.orders.clear()
        self.prices.clear()
        logger.info("Simulated exchange reset")
