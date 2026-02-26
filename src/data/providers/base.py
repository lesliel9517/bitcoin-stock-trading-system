"""Base data provider interface"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional
import pandas as pd

from ..models import OHLCV, Tick


class DataProvider(ABC):
    """数据提供者基类

    定义统一的数据接口，支持历史数据和实时数据获取
    """

    def __init__(self, name: str):
        """初始化数据提供者

        Args:
            name: 提供者名称
        """
        self.name = name

    @abstractmethod
    async def get_historical_data(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        timeframe: str = "1d"
    ) -> pd.DataFrame:
        """获取历史OHLCV数据

        Args:
            symbol: 交易对符号
            start: 开始时间
            end: 结束时间
            timeframe: 时间周期（1m, 5m, 1h, 1d等）

        Returns:
            包含OHLCV数据的DataFrame
        """
        pass

    @abstractmethod
    async def get_latest_price(self, symbol: str) -> Optional[float]:
        """获取最新价格

        Args:
            symbol: 交易对符号

        Returns:
            最新价格
        """
        pass

    @abstractmethod
    async def subscribe_market_data(self, symbol: str, callback):
        """订阅实时行情数据

        Args:
            symbol: 交易对符号
            callback: 数据回调函数
        """
        pass

    @abstractmethod
    async def unsubscribe_market_data(self, symbol: str):
        """取消订阅实时行情数据

        Args:
            symbol: 交易对符号
        """
        pass

    def validate_symbol(self, symbol: str) -> bool:
        """验证交易对符号是否有效

        Args:
            symbol: 交易对符号

        Returns:
            是否有效
        """
        # 默认实现，子类可以覆盖
        return bool(symbol)

    def normalize_symbol(self, symbol: str) -> str:
        """标准化交易对符号

        Args:
            symbol: 交易对符号

        Returns:
            标准化后的符号
        """
        # 默认实现，子类可以覆盖
        return symbol.upper()
