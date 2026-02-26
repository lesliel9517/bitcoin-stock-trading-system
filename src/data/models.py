"""Data models for market data"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass
class OHLCV:
    """OHLCV数据模型（开高低收量）"""
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    symbol: str
    exchange: str
    timeframe: str = "1d"

    def __post_init__(self):
        """确保价格和数量是Decimal类型"""
        if not isinstance(self.open, Decimal):
            self.open = Decimal(str(self.open))
        if not isinstance(self.high, Decimal):
            self.high = Decimal(str(self.high))
        if not isinstance(self.low, Decimal):
            self.low = Decimal(str(self.low))
        if not isinstance(self.close, Decimal):
            self.close = Decimal(str(self.close))
        if not isinstance(self.volume, Decimal):
            self.volume = Decimal(str(self.volume))


@dataclass
class Tick:
    """Tick数据模型"""
    timestamp: datetime
    symbol: str
    exchange: str
    price: Decimal
    volume: Decimal
    bid: Optional[Decimal] = None
    ask: Optional[Decimal] = None
    bid_volume: Optional[Decimal] = None
    ask_volume: Optional[Decimal] = None

    def __post_init__(self):
        """确保价格和数量是Decimal类型"""
        if not isinstance(self.price, Decimal):
            self.price = Decimal(str(self.price))
        if not isinstance(self.volume, Decimal):
            self.volume = Decimal(str(self.volume))
        if self.bid is not None and not isinstance(self.bid, Decimal):
            self.bid = Decimal(str(self.bid))
        if self.ask is not None and not isinstance(self.ask, Decimal):
            self.ask = Decimal(str(self.ask))


@dataclass
class OrderBook:
    """订单簿数据模型"""
    timestamp: datetime
    symbol: str
    exchange: str
    bids: list  # [(price, volume), ...]
    asks: list  # [(price, volume), ...]

    def get_best_bid(self) -> Optional[Decimal]:
        """获取最优买价"""
        if self.bids:
            return Decimal(str(self.bids[0][0]))
        return None

    def get_best_ask(self) -> Optional[Decimal]:
        """获取最优卖价"""
        if self.asks:
            return Decimal(str(self.asks[0][0]))
        return None

    def get_spread(self) -> Optional[Decimal]:
        """获取买卖价差"""
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()
        if best_bid and best_ask:
            return best_ask - best_bid
        return None
