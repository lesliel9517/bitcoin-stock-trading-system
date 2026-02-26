"""Stop loss and take profit management"""

from typing import Dict, Optional
from decimal import Decimal
from datetime import datetime

from ..trading.portfolio import Portfolio
from ..trading.order import Order
from ..core.types import OrderSide
from ..utils.logger import logger


class StopLossManager:
    """Stop loss and take profit manager

    Manages stop loss and take profit levels for each position
    """

    def __init__(self, config: Dict = None):
        """Initialize stop loss manager

        Args:
            config: Configuration
        """
        self.config = config or {}

        # Stop loss configuration
        self.stop_loss_enabled = self.config.get('stop_loss', {}).get('enabled', True)
        self.default_stop_loss_percent = Decimal(
            str(self.config.get('stop_loss', {}).get('default_percent', '0.02'))
        )
        self.trailing_stop_enabled = self.config.get('stop_loss', {}).get('trailing', False)

        # Take profit configuration
        self.take_profit_enabled = self.config.get('take_profit', {}).get('enabled', True)
        self.default_take_profit_percent = Decimal(
            str(self.config.get('take_profit', {}).get('default_percent', '0.05'))
        )

        # Position stop loss and take profit levels
        self.stop_levels: Dict[str, Dict] = {}  # {symbol: {stop_loss, take_profit, highest_price}}

        logger.info(
            f"Stop loss manager initialized: "
            f"stop_loss={self.stop_loss_enabled} ({self.default_stop_loss_percent:.2%}), "
            f"take_profit={self.take_profit_enabled} ({self.default_take_profit_percent:.2%}), "
            f"trailing={self.trailing_stop_enabled}"
        )

    def set_stop_levels(
        self,
        symbol: str,
        entry_price: Decimal,
        stop_loss_percent: Optional[Decimal] = None,
        take_profit_percent: Optional[Decimal] = None
    ):
        """Set stop loss and take profit levels

        Args:
            symbol: Trading pair symbol
            entry_price: Entry price
            stop_loss_percent: Stop loss percentage (optional)
            take_profit_percent: Take profit percentage (optional)
        """
        stop_loss_pct = stop_loss_percent or self.default_stop_loss_percent
        take_profit_pct = take_profit_percent or self.default_take_profit_percent

        # Calculate stop loss and take profit prices
        stop_loss_price = entry_price * (Decimal(1) - stop_loss_pct)
        take_profit_price = entry_price * (Decimal(1) + take_profit_pct)

        self.stop_levels[symbol] = {
            'entry_price': entry_price,
            'stop_loss': stop_loss_price,
            'take_profit': take_profit_price,
            'highest_price': entry_price,  # For trailing stop
            'stop_loss_percent': stop_loss_pct,
        }

        logger.info(
            f"Stop levels set for {symbol}: "
            f"entry={entry_price}, stop={stop_loss_price}, target={take_profit_price}"
        )

    def update_trailing_stop(self, symbol: str, current_price: Decimal):
        """Update trailing stop

        Args:
            symbol: Trading pair symbol
            current_price: Current price
        """
        if not self.trailing_stop_enabled:
            return

        if symbol not in self.stop_levels:
            return

        levels = self.stop_levels[symbol]

        # Update highest price
        if current_price > levels['highest_price']:
            levels['highest_price'] = current_price

            # Update stop loss price (move up)
            new_stop_loss = current_price * (Decimal(1) - levels['stop_loss_percent'])

            # Only update if new stop loss is higher than current stop loss
            if new_stop_loss > levels['stop_loss']:
                old_stop = levels['stop_loss']
                levels['stop_loss'] = new_stop_loss
                logger.info(
                    f"Trailing stop updated for {symbol}: "
                    f"{old_stop} -> {new_stop_loss} (price={current_price})"
                )

    def check_stop_loss(self, symbol: str, current_price: Decimal) -> bool:
        """Check if stop loss is triggered

        Args:
            symbol: Trading pair symbol
            current_price: Current price

        Returns:
            Whether stop loss is triggered
        """
        if not self.stop_loss_enabled:
            return False

        if symbol not in self.stop_levels:
            return False

        stop_loss_price = self.stop_levels[symbol]['stop_loss']

        if current_price <= stop_loss_price:
            logger.warning(
                f"Stop loss triggered for {symbol}: "
                f"price={current_price} <= stop={stop_loss_price}"
            )
            return True

        return False

    def check_take_profit(self, symbol: str, current_price: Decimal) -> bool:
        """Check if take profit is triggered

        Args:
            symbol: Trading pair symbol
            current_price: Current price

        Returns:
            Whether take profit is triggered
        """
        if not self.take_profit_enabled:
            return False

        if symbol not in self.stop_levels:
            return False

        take_profit_price = self.stop_levels[symbol]['take_profit']

        if current_price >= take_profit_price:
            logger.info(
                f"Take profit triggered for {symbol}: "
                f"price={current_price} >= target={take_profit_price}"
            )
            return True

        return False

    def should_close_position(self, symbol: str, current_price: Decimal) -> tuple[bool, Optional[str]]:
        """Check if position should be closed

        Args:
            symbol: Trading pair symbol
            current_price: Current price

        Returns:
            (Whether to close, reason)
        """
        # Update trailing stop
        self.update_trailing_stop(symbol, current_price)

        # Check stop loss
        if self.check_stop_loss(symbol, current_price):
            return True, "stop_loss"

        # Check take profit
        if self.check_take_profit(symbol, current_price):
            return True, "take_profit"

        return False, None

    def remove_stop_levels(self, symbol: str):
        """Remove stop loss and take profit levels

        Args:
            symbol: Trading pair symbol
        """
        if symbol in self.stop_levels:
            del self.stop_levels[symbol]
            logger.info(f"Stop levels removed for {symbol}")

    def get_stop_levels(self, symbol: str) -> Optional[Dict]:
        """Get stop loss and take profit levels

        Args:
            symbol: Trading pair symbol

        Returns:
            Stop loss and take profit information
        """
        return self.stop_levels.get(symbol)

    def get_all_stop_levels(self) -> Dict[str, Dict]:
        """Get all stop loss and take profit levels

        Returns:
            All stop loss and take profit information
        """
        return self.stop_levels.copy()
