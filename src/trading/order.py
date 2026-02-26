"""Order model"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional
import uuid

from ..core.types import OrderSide, OrderType, OrderStatus, TimeInForce


@dataclass
class Order:
    """Order model"""
    symbol: str
    side: OrderSide
    quantity: Decimal
    order_type: OrderType = OrderType.MARKET
    price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    time_in_force: TimeInForce = TimeInForce.GTC
    exchange: str = "binance"
    strategy_id: str = ""
    order_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: Decimal = Decimal(0)
    average_price: Optional[Decimal] = None
    commission: Decimal = Decimal(0)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    error_message: Optional[str] = None

    def __post_init__(self):
        """Ensure quantity and price are Decimal type"""
        if not isinstance(self.quantity, Decimal):
            self.quantity = Decimal(str(self.quantity))
        if self.price is not None and not isinstance(self.price, Decimal):
            self.price = Decimal(str(self.price))
        if self.stop_price is not None and not isinstance(self.stop_price, Decimal):
            self.stop_price = Decimal(str(self.stop_price))
        if not isinstance(self.filled_quantity, Decimal):
            self.filled_quantity = Decimal(str(self.filled_quantity))
        if not isinstance(self.commission, Decimal):
            self.commission = Decimal(str(self.commission))

    def is_filled(self) -> bool:
        """Check if order is fully filled"""
        return self.status == OrderStatus.FILLED

    def is_active(self) -> bool:
        """Check if order is active"""
        return self.status in [OrderStatus.PENDING, OrderStatus.SUBMITTED, OrderStatus.PARTIAL_FILLED]

    def get_remaining_quantity(self) -> Decimal:
        """Get remaining unfilled quantity"""
        return self.quantity - self.filled_quantity

    def update_fill(self, quantity: Decimal, price: Decimal, commission: Decimal = Decimal(0)):
        """Update fill information

        Args:
            quantity: Filled quantity
            price: Fill price
            commission: Commission fee
        """
        self.filled_quantity += quantity
        self.commission += commission
        self.updated_at = datetime.now()

        # Calculate average fill price
        if self.average_price is None:
            self.average_price = price
        else:
            total_value = self.average_price * (self.filled_quantity - quantity) + price * quantity
            self.average_price = total_value / self.filled_quantity

        # Update status
        if self.filled_quantity >= self.quantity:
            self.status = OrderStatus.FILLED
            self.filled_at = datetime.now()
        elif self.filled_quantity > 0:
            self.status = OrderStatus.PARTIAL_FILLED

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "quantity": float(self.quantity),
            "order_type": self.order_type.value,
            "price": float(self.price) if self.price else None,
            "stop_price": float(self.stop_price) if self.stop_price else None,
            "status": self.status.value,
            "filled_quantity": float(self.filled_quantity),
            "average_price": float(self.average_price) if self.average_price else None,
            "commission": float(self.commission),
            "exchange": self.exchange,
            "strategy_id": self.strategy_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "filled_at": self.filled_at.isoformat() if self.filled_at else None,
        }
