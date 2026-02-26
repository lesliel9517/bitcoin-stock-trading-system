"""Base exchange gateway interface"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from decimal import Decimal
from datetime import datetime

from ..order import Order
from ...core.types import OrderSide, OrderType, OrderStatus


class ExchangeGateway(ABC):
    """Exchange gateway base class

    Defines unified exchange interface, supports order execution, queries, etc.
    """

    def __init__(self, exchange_id: str, config: Dict):
        """Initialize exchange gateway

        Args:
            exchange_id: Exchange ID
            config: Configuration
        """
        self.exchange_id = exchange_id
        self.config = config
        self.is_connected = False

    @abstractmethod
    async def connect(self):
        """Connect to exchange"""
        pass

    @abstractmethod
    async def disconnect(self):
        """Disconnect"""
        pass

    @abstractmethod
    async def submit_order(self, order: Order) -> Order:
        """Submit order

        Args:
            order: Order object

        Returns:
            Updated order object
        """
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel order

        Args:
            order_id: Order ID

        Returns:
            Whether successfully cancelled
        """
        pass

    @abstractmethod
    async def get_order_status(self, order_id: str) -> Optional[Order]:
        """Query order status

        Args:
            order_id: Order ID

        Returns:
            Order object
        """
        pass

    @abstractmethod
    async def get_balance(self, currency: str = "USD") -> Decimal:
        """Query account balance

        Args:
            currency: Currency type

        Returns:
            Balance
        """
        pass

    @abstractmethod
    async def get_position(self, symbol: str) -> Decimal:
        """Query position

        Args:
            symbol: Trading pair symbol

        Returns:
            Position quantity
        """
        pass

    @abstractmethod
    async def get_latest_price(self, symbol: str) -> Optional[Decimal]:
        """Get latest price

        Args:
            symbol: Trading pair symbol

        Returns:
            Latest price
        """
        pass

    def validate_order(self, order: Order) -> tuple[bool, Optional[str]]:
        """Validate order parameters

        Args:
            order: Order object

        Returns:
            (is_valid, error_message)
        """
        # Basic validation
        if order.quantity <= 0:
            return False, "Order quantity must be positive"

        if order.order_type == OrderType.LIMIT and order.price is None:
            return False, "Limit order must have a price"

        if order.order_type == OrderType.STOP and order.stop_price is None:
            return False, "Stop order must have a stop price"

        return True, None
