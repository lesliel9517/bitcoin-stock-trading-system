"""Risk management rules engine"""

from abc import ABC, abstractmethod
from typing import Dict, Optional
from decimal import Decimal
from datetime import datetime

from ..trading.order import Order
from ..trading.portfolio import Portfolio
from ..utils.logger import logger


class RiskRule(ABC):
    """Risk rule base class"""

    def __init__(self, rule_id: str, config: Dict = None):
        """Initialize risk rule

        Args:
            rule_id: Rule ID
            config: Rule configuration
        """
        self.rule_id = rule_id
        self.config = config or {}
        self.enabled = self.config.get('enabled', True)

    @abstractmethod
    def validate(self, order: Order, portfolio: Portfolio) -> tuple[bool, Optional[str]]:
        """Validate if order complies with risk rule

        Args:
            order: Order object
            portfolio: Portfolio

        Returns:
            (Whether passed, error message)
        """
        pass

    def enable(self):
        """Enable rule"""
        self.enabled = True

    def disable(self):
        """Disable rule"""
        self.enabled = False


class MaxPositionSizeRule(RiskRule):
    """Maximum position size rule

    Limits the maximum proportion of total assets for a single position
    """

    def __init__(self, rule_id: str = "max_position_size", config: Dict = None):
        super().__init__(rule_id, config)
        self.max_position_size = Decimal(str(self.config.get('max_position_size', '0.1')))

    def validate(self, order: Order, portfolio: Portfolio) -> tuple[bool, Optional[str]]:
        """Validate order"""
        if not self.enabled:
            return True, None

        # Only check buy orders
        if order.side.value != "BUY":
            return True, None

        # Calculate order value
        order_value = order.quantity * (order.price or Decimal(0))

        # Get current position value
        current_position = portfolio.get_position(order.symbol)
        current_price = order.price or Decimal(0)
        current_position_value = abs(current_position) * current_price

        # Calculate new position value
        new_position_value = current_position_value + order_value

        # Get total assets
        total_value = portfolio.get_total_value()

        if total_value == 0:
            return False, "Total portfolio value is zero"

        # Calculate position ratio
        position_ratio = new_position_value / total_value

        if position_ratio > self.max_position_size:
            return False, f"Position size {position_ratio:.2%} exceeds limit {self.max_position_size:.2%}"

        return True, None


class MaxDrawdownRule(RiskRule):
    """Maximum drawdown rule

    Stops trading when drawdown exceeds threshold
    """

    def __init__(self, rule_id: str = "max_drawdown", config: Dict = None):
        super().__init__(rule_id, config)
        self.max_drawdown = Decimal(str(self.config.get('max_drawdown', '0.2')))
        self.peak_value = Decimal(0)

    def validate(self, order: Order, portfolio: Portfolio) -> tuple[bool, Optional[str]]:
        """Validate order"""
        if not self.enabled:
            return True, None

        current_value = portfolio.get_total_value()

        # Update peak value
        if current_value > self.peak_value:
            self.peak_value = current_value

        if self.peak_value == 0:
            return True, None

        # Calculate drawdown
        drawdown = (self.peak_value - current_value) / self.peak_value

        if drawdown > self.max_drawdown:
            return False, f"Drawdown {drawdown:.2%} exceeds limit {self.max_drawdown:.2%}"

        return True, None


class MaxDailyLossRule(RiskRule):
    """Maximum daily loss rule

    Limits maximum daily loss
    """

    def __init__(self, rule_id: str = "max_daily_loss", config: Dict = None):
        super().__init__(rule_id, config)
        self.max_daily_loss = Decimal(str(self.config.get('max_daily_loss', '0.05')))
        self.daily_start_value = Decimal(0)
        self.current_date = None

    def validate(self, order: Order, portfolio: Portfolio) -> tuple[bool, Optional[str]]:
        """Validate order"""
        if not self.enabled:
            return True, None

        today = datetime.now().date()

        # If it's a new day, reset starting value
        if self.current_date != today:
            self.current_date = today
            self.daily_start_value = portfolio.get_total_value()

        if self.daily_start_value == 0:
            return True, None

        current_value = portfolio.get_total_value()
        daily_loss = (self.daily_start_value - current_value) / self.daily_start_value

        if daily_loss > self.max_daily_loss:
            return False, f"Daily loss {daily_loss:.2%} exceeds limit {self.max_daily_loss:.2%}"

        return True, None


class MaxOrdersPerDayRule(RiskRule):
    """Maximum orders per day rule

    Limits maximum number of orders per day
    """

    def __init__(self, rule_id: str = "max_orders_per_day", config: Dict = None):
        super().__init__(rule_id, config)
        self.max_orders = self.config.get('max_orders_per_day', 100)
        self.daily_orders = 0
        self.current_date = None

    def validate(self, order: Order, portfolio: Portfolio) -> tuple[bool, Optional[str]]:
        """Validate order"""
        if not self.enabled:
            return True, None

        today = datetime.now().date()

        # If it's a new day, reset counter
        if self.current_date != today:
            self.current_date = today
            self.daily_orders = 0

        if self.daily_orders >= self.max_orders:
            return False, f"Daily order count {self.daily_orders} exceeds limit {self.max_orders}"

        # Increment counter
        self.daily_orders += 1

        return True, None


class MinOrderValueRule(RiskRule):
    """Minimum order value rule

    Ensures order value is not below minimum
    """

    def __init__(self, rule_id: str = "min_order_value", config: Dict = None):
        super().__init__(rule_id, config)
        self.min_order_value = Decimal(str(self.config.get('min_order_value', '10')))

    def validate(self, order: Order, portfolio: Portfolio) -> tuple[bool, Optional[str]]:
        """Validate order"""
        if not self.enabled:
            return True, None

        # Calculate order value
        order_value = order.quantity * (order.price or Decimal(0))

        if order_value < self.min_order_value:
            return False, f"Order value {order_value} below minimum {self.min_order_value}"

        return True, None
