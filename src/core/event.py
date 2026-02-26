"""Event system for the trading system"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from decimal import Decimal


class EventType(Enum):
    """Event type enumeration"""
    MARKET = "market"           # Market data
    SIGNAL = "signal"           # Trading signals
    ORDER = "order"             # Order events
    FILL = "fill"               # Fill events
    RISK = "risk"               # Risk events
    MONITOR = "monitor"         # Monitoring events
    SYSTEM = "system"           # System events


@dataclass
class Event:
    """Base event class"""
    event_type: EventType
    timestamp: datetime
    data: Dict[str, Any]
    source: str
    priority: int = 0

    def __lt__(self, other):
        """Support priority queue"""
        if not isinstance(other, Event):
            return NotImplemented
        return self.priority < other.priority

    def __post_init__(self):
        """Ensure timestamp is a datetime object"""
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp)


@dataclass
class MarketEvent(Event):
    """Market event"""
    symbol: str = ""
    exchange: str = ""
    price: Decimal = Decimal(0)
    volume: Decimal = Decimal(0)
    bid: Optional[Decimal] = None
    ask: Optional[Decimal] = None
    high: Optional[Decimal] = None
    low: Optional[Decimal] = None
    open: Optional[Decimal] = None
    close: Optional[Decimal] = None

    def __post_init__(self):
        super().__post_init__()
        self.event_type = EventType.MARKET

        # Ensure prices are Decimal type
        if not isinstance(self.price, Decimal):
            self.price = Decimal(str(self.price))
        if not isinstance(self.volume, Decimal):
            self.volume = Decimal(str(self.volume))
        if self.bid is not None and not isinstance(self.bid, Decimal):
            self.bid = Decimal(str(self.bid))
        if self.ask is not None and not isinstance(self.ask, Decimal):
            self.ask = Decimal(str(self.ask))


@dataclass
class SignalEvent(Event):
    """Signal event"""
    strategy_id: str = ""
    symbol: str = ""
    signal_type: str = "HOLD"  # BUY, SELL, HOLD, CLOSE
    strength: float = 0.0      # Signal strength 0-1
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        super().__post_init__()
        self.event_type = EventType.SIGNAL
        if self.metadata is None:
            self.metadata = {}


@dataclass
class OrderEvent(Event):
    """Order event"""
    order_id: str = ""
    symbol: str = ""
    order_type: str = "MARKET"   # MARKET, LIMIT, STOP
    side: str = "BUY"            # BUY, SELL
    quantity: Decimal = Decimal(0)
    price: Optional[Decimal] = None
    status: str = "PENDING"
    exchange: str = ""
    strategy_id: str = ""

    def __post_init__(self):
        super().__post_init__()
        self.event_type = EventType.ORDER

        # Ensure quantity is Decimal type
        if not isinstance(self.quantity, Decimal):
            self.quantity = Decimal(str(self.quantity))
        if self.price is not None and not isinstance(self.price, Decimal):
            self.price = Decimal(str(self.price))


@dataclass
class FillEvent(Event):
    """Fill event"""
    order_id: str = ""
    symbol: str = ""
    side: str = "BUY"
    quantity: Decimal = Decimal(0)
    price: Decimal = Decimal(0)
    commission: Decimal = Decimal(0)
    exchange: str = ""
    fill_id: str = ""

    def __post_init__(self):
        super().__post_init__()
        self.event_type = EventType.FILL

        # Ensure price and quantity are Decimal type
        if not isinstance(self.quantity, Decimal):
            self.quantity = Decimal(str(self.quantity))
        if not isinstance(self.price, Decimal):
            self.price = Decimal(str(self.price))
        if not isinstance(self.commission, Decimal):
            self.commission = Decimal(str(self.commission))


@dataclass
class RiskEvent(Event):
    """Risk event"""
    risk_type: str = ""          # POSITION_LIMIT, DRAWDOWN, LOSS_LIMIT
    severity: str = "INFO"       # INFO, WARNING, CRITICAL
    message: str = ""
    action: str = "ALERT"        # ALERT, REDUCE_POSITION, STOP_TRADING
    affected_symbol: Optional[str] = None

    def __post_init__(self):
        super().__post_init__()
        self.event_type = EventType.RISK


@dataclass
class MonitorEvent(Event):
    """Monitoring event"""
    metric_name: str = ""
    metric_value: Any = None
    metric_type: str = "INFO"    # INFO, WARNING, ERROR
    description: str = ""

    def __post_init__(self):
        super().__post_init__()
        self.event_type = EventType.MONITOR


@dataclass
class SystemEvent(Event):
    """System event"""
    event_name: str = ""
    message: str = ""
    level: str = "INFO"          # INFO, WARNING, ERROR

    def __post_init__(self):
        super().__post_init__()
        self.event_type = EventType.SYSTEM
