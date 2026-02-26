"""Portfolio management"""

from typing import Dict, List
from decimal import Decimal
from datetime import datetime

from .position import Position
from ..core.types import PositionSide
from ..utils.logger import logger


class Portfolio:
    """Portfolio manager

    Manages account balance, positions and P&L
    """

    def __init__(self, initial_balance: Decimal = Decimal(100000)):
        """Initialize portfolio

        Args:
            initial_balance: Initial capital
        """
        self.initial_balance = initial_balance
        self.cash = initial_balance
        self.positions: Dict[str, Position] = {}
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    def get_balance(self) -> Decimal:
        """Get cash balance"""
        return self.cash

    def get_position(self, symbol: str) -> Decimal:
        """Get position quantity

        Args:
            symbol: Trading pair symbol

        Returns:
            Position quantity (positive for long, negative for short)
        """
        if symbol in self.positions:
            return self.positions[symbol].quantity
        return Decimal(0)

    def get_position_obj(self, symbol: str) -> Position:
        """Get position object

        Args:
            symbol: Trading pair symbol

        Returns:
            Position object
        """
        if symbol not in self.positions:
            self.positions[symbol] = Position(symbol=symbol, exchange="")
        return self.positions[symbol]

    def update_position(self, symbol: str, quantity: Decimal, price: Decimal, exchange: str = ""):
        """Update position (does not manage cash - cash is managed by exchange)

        Args:
            symbol: Trading pair symbol
            quantity: Quantity change (positive for buy, negative for sell)
            price: Fill price
            exchange: Exchange
        """
        if symbol not in self.positions:
            self.positions[symbol] = Position(symbol=symbol, exchange=exchange)

        position = self.positions[symbol]

        if quantity > 0:
            # Buy - only update position, cash is managed by exchange
            position.add_position(quantity, price)
            logger.info(f"Position updated: Buy {quantity} {symbol} at {price}")
        else:
            # Sell - only update position, cash is managed by exchange
            pnl = position.reduce_position(abs(quantity), price)
            logger.info(f"Position updated: Sell {abs(quantity)} {symbol} at {price}, PnL: {pnl}")

        self.updated_at = datetime.now()

    def update_prices(self, prices: Dict[str, Decimal]):
        """Batch update position prices

        Args:
            prices: Price dictionary {symbol: price}
        """
        for symbol, price in prices.items():
            if symbol in self.positions:
                self.positions[symbol].update_price(price)

    def get_total_value(self) -> Decimal:
        """Get total asset value (cash + position market value)"""
        total = self.cash

        for position in self.positions.values():
            if position.quantity != 0:
                total += position.get_market_value()

        return total

    def get_total_pnl(self) -> Decimal:
        """Get total P&L"""
        return self.get_total_value() - self.initial_balance

    def get_total_pnl_percent(self) -> Decimal:
        """Get total P&L percentage"""
        if self.initial_balance == 0:
            return Decimal(0)
        return (self.get_total_pnl() / self.initial_balance) * 100

    def get_all_positions(self) -> List[Position]:
        """Get all positions"""
        return [p for p in self.positions.values() if p.quantity != 0]

    def get_positions_value(self) -> Decimal:
        """Get total positions market value"""
        total = Decimal(0)
        for position in self.positions.values():
            if position.quantity != 0:
                total += position.get_market_value()
        return total

    def get_cash_ratio(self) -> Decimal:
        """Get cash ratio"""
        total_value = self.get_total_value()
        if total_value == 0:
            return Decimal(0)
        return (self.cash / total_value) * 100

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "initial_balance": float(self.initial_balance),
            "cash": float(self.cash),
            "total_value": float(self.get_total_value()),
            "positions_value": float(self.get_positions_value()),
            "total_pnl": float(self.get_total_pnl()),
            "total_pnl_percent": float(self.get_total_pnl_percent()),
            "cash_ratio": float(self.get_cash_ratio()),
            "positions": [p.to_dict() for p in self.get_all_positions()],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
