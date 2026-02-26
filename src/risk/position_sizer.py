"""Position sizing calculator"""

from abc import ABC, abstractmethod
from typing import Dict
from decimal import Decimal
import math

from ..trading.portfolio import Portfolio
from ..utils.logger import logger


class PositionSizer(ABC):
    """Position sizer base class"""

    def __init__(self, config: Dict = None):
        """Initialize position sizer

        Args:
            config: Configuration
        """
        self.config = config or {}

    @abstractmethod
    def calculate_position_size(
        self,
        symbol: str,
        price: Decimal,
        portfolio: Portfolio,
        signal_strength: float = 1.0
    ) -> Decimal:
        """Calculate position size

        Args:
            symbol: Trading pair symbol
            price: Current price
            portfolio: Portfolio
            signal_strength: Signal strength (0-1)

        Returns:
            Position quantity
        """
        pass


class FixedPositionSizer(PositionSizer):
    """Fixed position sizer

    Uses a fixed proportion of capital for trading
    """

    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.position_ratio = Decimal(str(self.config.get('position_ratio', '0.1')))

    def calculate_position_size(
        self,
        symbol: str,
        price: Decimal,
        portfolio: Portfolio,
        signal_strength: float = 1.0
    ) -> Decimal:
        """Calculate position size"""
        # Get available cash
        available_cash = portfolio.get_balance()

        # Calculate position value
        position_value = available_cash * self.position_ratio

        # Consider signal strength
        position_value = position_value * Decimal(str(signal_strength))

        # Calculate quantity
        if price == 0:
            return Decimal(0)

        quantity = position_value / price

        logger.debug(f"Fixed position size: {quantity} {symbol} @ {price}")
        return quantity


class PercentRiskPositionSizer(PositionSizer):
    """Percent risk position sizer

    Calculates position size based on account risk percentage
    """

    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.risk_per_trade = Decimal(str(self.config.get('risk_per_trade', '0.02')))
        self.stop_loss_percent = Decimal(str(self.config.get('stop_loss_percent', '0.02')))

    def calculate_position_size(
        self,
        symbol: str,
        price: Decimal,
        portfolio: Portfolio,
        signal_strength: float = 1.0
    ) -> Decimal:
        """Calculate position size"""
        # Get total account value
        total_value = portfolio.get_total_value()

        # Calculate risk amount
        risk_amount = total_value * self.risk_per_trade

        # Consider signal strength
        risk_amount = risk_amount * Decimal(str(signal_strength))

        # Calculate position based on stop loss percentage
        if self.stop_loss_percent == 0 or price == 0:
            return Decimal(0)

        quantity = risk_amount / (price * self.stop_loss_percent)

        logger.debug(f"Percent risk position size: {quantity} {symbol} @ {price}")
        return quantity


class KellyPositionSizer(PositionSizer):
    """Kelly criterion position sizer

    Uses Kelly formula to calculate optimal position size
    """

    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.win_rate = Decimal(str(self.config.get('win_rate', '0.55')))
        self.win_loss_ratio = Decimal(str(self.config.get('win_loss_ratio', '1.5')))
        self.kelly_fraction = Decimal(str(self.config.get('kelly_fraction', '0.25')))  # Use fractional Kelly

    def calculate_position_size(
        self,
        symbol: str,
        price: Decimal,
        portfolio: Portfolio,
        signal_strength: float = 1.0
    ) -> Decimal:
        """Calculate position size"""
        # Kelly formula: f = (p * b - q) / b
        # p = win rate, q = 1 - p, b = win/loss ratio
        p = self.win_rate
        q = Decimal(1) - p
        b = self.win_loss_ratio

        # Calculate Kelly percentage
        kelly_percent = (p * b - q) / b

        # Ensure non-negative
        if kelly_percent < 0:
            kelly_percent = Decimal(0)

        # Use fractional Kelly (reduce risk)
        kelly_percent = kelly_percent * self.kelly_fraction

        # Limit maximum position
        kelly_percent = min(kelly_percent, Decimal('0.25'))

        # Get available cash
        available_cash = portfolio.get_balance()

        # Calculate position value
        position_value = available_cash * kelly_percent

        # Consider signal strength
        position_value = position_value * Decimal(str(signal_strength))

        # Calculate quantity
        if price == 0:
            return Decimal(0)

        quantity = position_value / price

        logger.debug(f"Kelly position size: {quantity} {symbol} @ {price} (kelly={kelly_percent:.2%})")
        return quantity


class VolatilityPositionSizer(PositionSizer):
    """Volatility position sizer

    Adjusts position size based on asset volatility
    """

    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.target_volatility = Decimal(str(self.config.get('target_volatility', '0.02')))
        self.base_position_ratio = Decimal(str(self.config.get('base_position_ratio', '0.1')))

    def calculate_position_size(
        self,
        symbol: str,
        price: Decimal,
        portfolio: Portfolio,
        signal_strength: float = 1.0,
        asset_volatility: Decimal = None
    ) -> Decimal:
        """Calculate position size

        Args:
            symbol: Trading pair symbol
            price: Current price
            portfolio: Portfolio
            signal_strength: Signal strength
            asset_volatility: Asset volatility (if provided)

        Returns:
            Position quantity
        """
        # If no volatility provided, use base position
        if asset_volatility is None or asset_volatility == 0:
            asset_volatility = self.target_volatility

        # Adjust position based on volatility
        volatility_adjustment = self.target_volatility / asset_volatility

        # Limit adjustment range
        volatility_adjustment = max(Decimal('0.5'), min(volatility_adjustment, Decimal('2.0')))

        # Get available cash
        available_cash = portfolio.get_balance()

        # Calculate position value
        position_value = available_cash * self.base_position_ratio * volatility_adjustment

        # Consider signal strength
        position_value = position_value * Decimal(str(signal_strength))

        # Calculate quantity
        if price == 0:
            return Decimal(0)

        quantity = position_value / price

        logger.debug(f"Volatility position size: {quantity} {symbol} @ {price} (vol_adj={volatility_adjustment:.2f})")
        return quantity


def create_position_sizer(method: str, config: Dict = None) -> PositionSizer:
    """Create position sizer

    Args:
        method: Calculation method (fixed, percent_risk, kelly, volatility)
        config: Configuration

    Returns:
        Position sizer instance
    """
    sizers = {
        'fixed': FixedPositionSizer,
        'percent_risk': PercentRiskPositionSizer,
        'kelly': KellyPositionSizer,
        'volatility': VolatilityPositionSizer,
    }

    sizer_class = sizers.get(method.lower())
    if sizer_class is None:
        logger.warning(f"Unknown position sizing method: {method}, using fixed")
        sizer_class = FixedPositionSizer

    return sizer_class(config)
