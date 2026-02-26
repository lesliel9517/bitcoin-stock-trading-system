"""Base strategy class"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, List
import pandas as pd
from datetime import datetime

from ..core.event import MarketEvent, SignalEvent
from ..core.types import SignalType
from ..utils.logger import logger


class Strategy(ABC):
    """Strategy base class

    All trading strategies must inherit from this class and implement abstract methods
    """

    def __init__(self, strategy_id: str, config: Dict):
        """Initialize strategy

        Args:
            strategy_id: Unique strategy identifier
            config: Strategy configuration
        """
        self.strategy_id = strategy_id
        self.config = config
        self.is_active = False
        self.symbols: List[str] = config.get('symbols', [])
        self.timeframe: str = config.get('timeframe', '1h')
        self.parameters: Dict = config.get('parameters', {})

        # Data cache
        self._data_cache: Dict[str, pd.DataFrame] = {}

        # Event bus (will be set by engine)
        self.event_bus = None

        logger.info(f"Strategy {strategy_id} initialized with config: {config}")

    @abstractmethod
    def on_init(self):
        """Strategy initialization callback

        Called before strategy starts, used to initialize strategy state
        """
        pass

    @abstractmethod
    async def on_market_data(self, event: MarketEvent) -> Optional[SignalEvent]:
        """Process market data

        Args:
            event: Market event

        Returns:
            Trading signal event (if any)
        """
        pass

    @abstractmethod
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators

        Args:
            data: OHLCV data

        Returns:
            Data with indicators
        """
        pass

    def generate_signal(
        self,
        symbol: str,
        signal_type: SignalType,
        strength: float = 1.0,
        metadata: Optional[Dict] = None
    ) -> SignalEvent:
        """Generate trading signal

        Args:
            symbol: Trading pair symbol
            signal_type: Signal type
            strength: Signal strength (0-1)
            metadata: Additional metadata

        Returns:
            Signal event
        """
        from ..core.event import EventType

        return SignalEvent(
            event_type=EventType.SIGNAL,
            strategy_id=self.strategy_id,
            symbol=symbol,
            signal_type=signal_type.value,
            strength=strength,
            metadata=metadata or {},
            timestamp=datetime.now(),
            data={},
            source=self.strategy_id
        )

    def update_data(self, symbol: str, data: pd.DataFrame):
        """Update data cache

        Args:
            symbol: Trading pair symbol
            data: OHLCV data
        """
        self._data_cache[symbol] = data

    def get_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Get cached data

        Args:
            symbol: Trading pair symbol

        Returns:
            OHLCV data
        """
        return self._data_cache.get(symbol)

    def start(self):
        """Start strategy"""
        self.is_active = True
        logger.info(f"Strategy {self.strategy_id} started")

    def stop(self):
        """Stop strategy"""
        self.is_active = False
        logger.info(f"Strategy {self.strategy_id} stopped")

    def get_parameters(self) -> Dict:
        """Get strategy parameters

        Returns:
            Parameter dictionary
        """
        return self.parameters

    def set_parameters(self, parameters: Dict):
        """Set strategy parameters

        Args:
            parameters: Parameter dictionary
        """
        self.parameters.update(parameters)
        logger.info(f"Strategy {self.strategy_id} parameters updated: {parameters}")
