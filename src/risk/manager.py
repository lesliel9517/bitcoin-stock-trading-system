"""Risk manager - integrates all risk management components"""

from typing import Dict, List, Optional
from decimal import Decimal
from datetime import datetime

from .rules import (
    RiskRule,
    MaxPositionSizeRule,
    MaxDrawdownRule,
    MaxDailyLossRule,
    MaxOrdersPerDayRule,
    MinOrderValueRule,
)
from .position_sizer import PositionSizer, create_position_sizer
from .stop_loss import StopLossManager
from ..trading.order import Order
from ..trading.portfolio import Portfolio
from ..core.event import RiskEvent, EventType
from ..core.event_bus import EventBus
from ..utils.logger import logger


class RiskManager:
    """Risk manager

    Integrates all risk management functions:
    - Risk rule validation
    - Position size calculation
    - Stop loss and take profit management
    """

    def __init__(self, event_bus: EventBus, config: Dict = None):
        """Initialize risk manager

        Args:
            event_bus: Event bus
            config: Configuration
        """
        self.event_bus = event_bus
        self.config = config or {}

        # Risk rules list
        self.rules: List[RiskRule] = []

        # Position sizer
        position_sizing_config = self.config.get('position_sizing', {})
        method = position_sizing_config.get('method', 'fixed')
        self.position_sizer = create_position_sizer(method, position_sizing_config)

        # Stop loss manager
        self.stop_loss_manager = StopLossManager(self.config)

        # Initialize default rules
        self._init_default_rules()

        logger.info("Risk manager initialized")

    def _init_default_rules(self):
        """Initialize default risk rules"""
        # Maximum position size rule
        if self.config.get('max_position_size'):
            self.add_rule(MaxPositionSizeRule(config=self.config))

        # Maximum drawdown rule
        if self.config.get('max_drawdown'):
            self.add_rule(MaxDrawdownRule(config=self.config))

        # Maximum daily loss rule
        if self.config.get('max_daily_loss'):
            self.add_rule(MaxDailyLossRule(config=self.config))

        # Maximum orders per day rule
        if self.config.get('max_orders_per_day'):
            self.add_rule(MaxOrdersPerDayRule(config=self.config))

        # Minimum order value rule
        if self.config.get('min_order_value'):
            self.add_rule(MinOrderValueRule(config=self.config))

    def add_rule(self, rule: RiskRule):
        """Add risk rule

        Args:
            rule: Risk rule
        """
        self.rules.append(rule)
        logger.info(f"Risk rule added: {rule.rule_id}")

    def remove_rule(self, rule_id: str):
        """Remove risk rule

        Args:
            rule_id: Rule ID
        """
        self.rules = [r for r in self.rules if r.rule_id != rule_id]
        logger.info(f"Risk rule removed: {rule_id}")

    async def validate_order(self, order: Order, portfolio: Portfolio) -> tuple[bool, Optional[str]]:
        """Validate if order meets risk requirements

        Args:
            order: Order object
            portfolio: Portfolio

        Returns:
            (Whether passed, error message)
        """
        # Execute all risk rules
        for rule in self.rules:
            if not rule.enabled:
                continue

            is_valid, error_msg = rule.validate(order, portfolio)
            if not is_valid:
                # Publish risk event
                await self._emit_risk_event(
                    risk_type=rule.rule_id,
                    severity="WARNING",
                    message=error_msg or "Risk rule validation failed",
                    action="REJECT_ORDER",
                    affected_symbol=order.symbol
                )
                return False, error_msg

        return True, None

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
            signal_strength: Signal strength

        Returns:
            Position quantity
        """
        return self.position_sizer.calculate_position_size(
            symbol, price, portfolio, signal_strength
        )

    def on_position_opened(
        self,
        symbol: str,
        entry_price: Decimal,
        stop_loss_percent: Optional[Decimal] = None,
        take_profit_percent: Optional[Decimal] = None
    ):
        """Called when position is opened

        Args:
            symbol: Trading pair symbol
            entry_price: Entry price
            stop_loss_percent: Stop loss percentage (optional)
            take_profit_percent: Take profit percentage (optional)
        """
        self.stop_loss_manager.set_stop_levels(
            symbol, entry_price, stop_loss_percent, take_profit_percent
        )

    def on_position_closed(self, symbol: str):
        """Called when position is closed

        Args:
            symbol: Trading pair symbol
        """
        self.stop_loss_manager.remove_stop_levels(symbol)

    async def check_stop_levels(self, symbol: str, current_price: Decimal) -> tuple[bool, Optional[str]]:
        """Check stop loss and take profit

        Args:
            symbol: Trading pair symbol
            current_price: Current price

        Returns:
            (Whether to close position, reason)
        """
        should_close, reason = self.stop_loss_manager.should_close_position(symbol, current_price)

        if should_close:
            # Publish risk event
            await self._emit_risk_event(
                risk_type=reason,
                severity="INFO",
                message=f"{reason.upper()} triggered for {symbol} at {current_price}",
                action="CLOSE_POSITION",
                affected_symbol=symbol
            )

        return should_close, reason

    async def _emit_risk_event(
        self,
        risk_type: str,
        severity: str,
        message: str,
        action: str,
        affected_symbol: Optional[str] = None
    ):
        """Emit risk event

        Args:
            risk_type: Risk type
            severity: Severity level
            message: Message
            action: Recommended action
            affected_symbol: Affected trading pair
        """
        event = RiskEvent(
            event_type=EventType.RISK,
            risk_type=risk_type,
            severity=severity,
            message=message,
            action=action,
            affected_symbol=affected_symbol,
            timestamp=datetime.now(),
            data={},
            source="risk_manager"
        )
        await self.event_bus.publish(event)
        logger.warning(f"Risk event: {message}")

    def get_stop_levels(self, symbol: str) -> Optional[Dict]:
        """Get stop loss and take profit levels

        Args:
            symbol: Trading pair symbol

        Returns:
            Stop loss and take profit information
        """
        return self.stop_loss_manager.get_stop_levels(symbol)

    def get_all_stop_levels(self) -> Dict[str, Dict]:
        """Get all stop loss and take profit levels

        Returns:
            All stop loss and take profit information
        """
        return self.stop_loss_manager.get_all_stop_levels()

    def get_rules_status(self) -> List[Dict]:
        """Get all rules status

        Returns:
            Rules status list
        """
        return [
            {
                'rule_id': rule.rule_id,
                'enabled': rule.enabled,
                'config': rule.config
            }
            for rule in self.rules
        ]
