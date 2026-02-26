"""Position management"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

from ..core.types import PositionSide


@dataclass
class Position:
    """Position model"""
    symbol: str
    exchange: str
    side: PositionSide = PositionSide.FLAT
    quantity: Decimal = Decimal(0)
    average_price: Decimal = Decimal(0)
    current_price: Decimal = Decimal(0)
    unrealized_pnl: Decimal = Decimal(0)
    realized_pnl: Decimal = Decimal(0)
    opened_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        """Ensure quantity and price are Decimal type"""
        if not isinstance(self.quantity, Decimal):
            self.quantity = Decimal(str(self.quantity))
        if not isinstance(self.average_price, Decimal):
            self.average_price = Decimal(str(self.average_price))
        if not isinstance(self.current_price, Decimal):
            self.current_price = Decimal(str(self.current_price))
        if not isinstance(self.unrealized_pnl, Decimal):
            self.unrealized_pnl = Decimal(str(self.unrealized_pnl))
        if not isinstance(self.realized_pnl, Decimal):
            self.realized_pnl = Decimal(str(self.realized_pnl))

    def update_price(self, price: Decimal):
        """Update current price and calculate unrealized P&L

        Args:
            price: Current price
        """
        self.current_price = price
        self.updated_at = datetime.now()

        if self.quantity != 0:
            if self.side == PositionSide.LONG:
                self.unrealized_pnl = (price - self.average_price) * self.quantity
            elif self.side == PositionSide.SHORT:
                self.unrealized_pnl = (self.average_price - price) * self.quantity

    def add_position(self, quantity: Decimal, price: Decimal):
        """Add to position

        Args:
            quantity: Quantity to add
            price: Fill price
        """
        if self.quantity == 0:
            # New position
            self.quantity = quantity
            self.average_price = price
            self.side = PositionSide.LONG if quantity > 0 else PositionSide.SHORT
            self.opened_at = datetime.now()
        else:
            # Add to existing position
            total_cost = self.average_price * self.quantity + price * quantity
            self.quantity += quantity
            if self.quantity != 0:
                self.average_price = total_cost / self.quantity

        self.updated_at = datetime.now()

    def reduce_position(self, quantity: Decimal, price: Decimal) -> Decimal:
        """Reduce position

        Args:
            quantity: Quantity to reduce
            price: Fill price

        Returns:
            Realized P&L
        """
        if quantity > abs(self.quantity):
            quantity = abs(self.quantity)

        # Calculate realized P&L
        if self.side == PositionSide.LONG:
            pnl = (price - self.average_price) * quantity
        else:
            pnl = (self.average_price - price) * quantity

        self.realized_pnl += pnl
        self.quantity -= quantity

        # If position is closed
        if self.quantity == 0:
            self.side = PositionSide.FLAT
            self.average_price = Decimal(0)

        self.updated_at = datetime.now()
        return pnl

    def get_market_value(self) -> Decimal:
        """Get position market value"""
        return abs(self.quantity) * self.current_price

    def get_total_pnl(self) -> Decimal:
        """Get total P&L (realized + unrealized)"""
        return self.realized_pnl + self.unrealized_pnl

    def get_pnl_percent(self) -> Decimal:
        """Get P&L percentage"""
        if self.average_price == 0 or self.quantity == 0:
            return Decimal(0)

        cost = self.average_price * abs(self.quantity)
        if cost == 0:
            return Decimal(0)

        return (self.get_total_pnl() / cost) * 100

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "symbol": self.symbol,
            "exchange": self.exchange,
            "side": self.side.value,
            "quantity": float(self.quantity),
            "average_price": float(self.average_price),
            "current_price": float(self.current_price),
            "market_value": float(self.get_market_value()),
            "unrealized_pnl": float(self.unrealized_pnl),
            "realized_pnl": float(self.realized_pnl),
            "total_pnl": float(self.get_total_pnl()),
            "pnl_percent": float(self.get_pnl_percent()),
            "opened_at": self.opened_at.isoformat() if self.opened_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
