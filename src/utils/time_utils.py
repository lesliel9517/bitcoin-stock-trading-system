"""Time utilities"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Union
import pandas as pd


def now() -> datetime:
    """Get current UTC time"""
    return datetime.now(timezone.utc)


def now_timestamp() -> int:
    """Get current UTC timestamp (milliseconds)"""
    return int(now().timestamp() * 1000)


def to_datetime(value: Union[str, int, float, datetime]) -> datetime:
    """Convert to datetime object

    Args:
        value: Time value (string, timestamp, or datetime object)

    Returns:
        datetime object
    """
    if isinstance(value, datetime):
        # Ensure timezone info exists
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    elif isinstance(value, (int, float)):
        # Timestamp (seconds or milliseconds)
        if value > 1e10:  # Millisecond timestamp
            value = value / 1000
        return datetime.fromtimestamp(value, tz=timezone.utc)
    elif isinstance(value, str):
        # ISO format string
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    else:
        raise ValueError(f"Cannot convert {type(value)} to datetime")


def to_timestamp(dt: datetime, milliseconds: bool = True) -> int:
    """Convert datetime to timestamp

    Args:
        dt: datetime object
        milliseconds: Whether to return millisecond timestamp

    Returns:
        Timestamp
    """
    timestamp = dt.timestamp()
    if milliseconds:
        return int(timestamp * 1000)
    return int(timestamp)


def format_datetime(dt: datetime, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format datetime

    Args:
        dt: datetime object
        fmt: Format string

    Returns:
        Formatted string
    """
    return dt.strftime(fmt)


def parse_timeframe(timeframe: str) -> timedelta:
    """Parse timeframe string

    Args:
        timeframe: Timeframe (e.g., "1m", "5m", "1h", "1d")

    Returns:
        timedelta object
    """
    unit = timeframe[-1]
    value = int(timeframe[:-1])

    if unit == 'm':
        return timedelta(minutes=value)
    elif unit == 'h':
        return timedelta(hours=value)
    elif unit == 'd':
        return timedelta(days=value)
    elif unit == 'w':
        return timedelta(weeks=value)
    else:
        raise ValueError(f"Unknown timeframe unit: {unit}")


def get_trading_days(start: datetime, end: datetime, exchange: str = "NYSE") -> int:
    """Calculate number of trading days

    Args:
        start: Start date
        end: End date
        exchange: Exchange (NYSE, NASDAQ, SSE, etc.)

    Returns:
        Number of trading days
    """
    # Simplified implementation: exclude weekends
    days = (end - start).days
    weeks = days // 7
    remaining_days = days % 7

    # Calculate weekdays in remaining days
    weekday_start = start.weekday()
    weekend_days = 0

    for i in range(remaining_days):
        if (weekday_start + i) % 7 in [5, 6]:  # Saturday, Sunday
            weekend_days += 1

    trading_days = days - (weeks * 2) - weekend_days
    return max(0, trading_days)


def align_to_timeframe(dt: datetime, timeframe: str) -> datetime:
    """Align time to timeframe

    Args:
        dt: datetime object
        timeframe: Timeframe (e.g., "1m", "5m", "1h", "1d")

    Returns:
        Aligned datetime
    """
    unit = timeframe[-1]
    value = int(timeframe[:-1])

    if unit == 'm':
        # Align to minute
        minute = (dt.minute // value) * value
        return dt.replace(minute=minute, second=0, microsecond=0)
    elif unit == 'h':
        # Align to hour
        hour = (dt.hour // value) * value
        return dt.replace(hour=hour, minute=0, second=0, microsecond=0)
    elif unit == 'd':
        # Align to day
        return dt.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        return dt


def is_market_open(dt: datetime, exchange: str = "NYSE") -> bool:
    """Check if market is open

    Args:
        dt: datetime object
        exchange: Exchange

    Returns:
        Whether market is open
    """
    # Simplified implementation: check if it's a weekday
    # In production, should consider specific trading hours and holidays

    if exchange in ["NYSE", "NASDAQ"]:
        # US stocks: Monday to Friday 9:30-16:00 ET
        if dt.weekday() >= 5:  # Weekend
            return False
        # Simplified here, should convert to ET timezone and check specific time
        return True
    elif exchange in ["SSE", "SZSE"]:
        # A-shares: Monday to Friday 9:30-11:30, 13:00-15:00
        if dt.weekday() >= 5:  # Weekend
            return False
        return True
    elif exchange in ["BINANCE", "OKX"]:
        # Cryptocurrency: 24/7
        return True
    else:
        return True


def get_next_trading_day(dt: datetime, exchange: str = "NYSE") -> datetime:
    """Get next trading day

    Args:
        dt: datetime object
        exchange: Exchange

    Returns:
        Next trading day
    """
    if exchange in ["BINANCE", "OKX"]:
        # Cryptocurrency market 24/7, return next day
        return dt + timedelta(days=1)

    # Other markets: skip weekends
    next_day = dt + timedelta(days=1)
    while next_day.weekday() >= 5:  # Weekend
        next_day += timedelta(days=1)

    return next_day
