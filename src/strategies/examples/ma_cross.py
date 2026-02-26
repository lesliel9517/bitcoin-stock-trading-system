"""Moving Average Crossover Strategy"""

from typing import Dict, Optional
import pandas as pd
from decimal import Decimal

from ..base import Strategy
from ..indicators.ma import calculate_ma_cross
from ...core.event import MarketEvent, SignalEvent
from ...core.types import SignalType
from ...utils.logger import logger


class MACrossStrategy(Strategy):
    """Moving Average Crossover Strategy

    Trading based on crossover signals between short-term and long-term moving averages:
    - Golden cross (short MA crosses above long MA): Buy signal
    - Death cross (short MA crosses below long MA): Sell signal
    """

    def __init__(self, strategy_id: str, config: Dict):
        """Initialize strategy

        Args:
            strategy_id: Strategy ID
            config: Strategy configuration
        """
        super().__init__(strategy_id, config)

        # Strategy parameters
        self.short_window = self.parameters.get('short_window', 5)
        self.long_window = self.parameters.get('long_window', 20)
        self.ma_type = self.parameters.get('ma_type', 'SMA')

        # Minimum data points required
        self.min_data_points = max(self.short_window, self.long_window) + 1

        logger.info(
            f"MA Cross Strategy initialized: "
            f"short={self.short_window}, long={self.long_window}, type={self.ma_type}"
        )

    def on_init(self):
        """Strategy initialization"""
        logger.info(f"MA Cross Strategy {self.strategy_id} initialized")

    async def on_market_data(self, event: MarketEvent) -> Optional[SignalEvent]:
        """Process market data

        Args:
            event: Market event

        Returns:
            Trading signal (if any)
        """
        if not self.is_active:
            return None

        symbol = event.symbol

        # Get historical data
        data = self.get_data(symbol)

        # Initialize empty DataFrame if None
        if data is None:
            data = pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])
            data.index.name = 'timestamp'

        # Add latest data point
        new_row = pd.DataFrame({
            'timestamp': [event.timestamp],
            'open': [float(event.open or event.price)],
            'high': [float(event.high or event.price)],
            'low': [float(event.low or event.price)],
            'close': [float(event.price)],
            'volume': [float(event.volume)]
        })
        new_row.set_index('timestamp', inplace=True)

        # Update data
        data = pd.concat([data, new_row])
        data = data[~data.index.duplicated(keep='last')]  # Remove duplicates
        self.update_data(symbol, data)

        # Check if we have enough data
        if len(data) < self.min_data_points:
            if len(data) % 5 == 0 or len(data) == 1:  # Log every 5 data points
                logger.info(f"Accumulating data for {symbol}: {len(data)}/{self.min_data_points} points")
            return None

        # Calculate indicators
        data_with_indicators = self.calculate_indicators(data)

        # Generate and publish signal
        signal = self._generate_signal(symbol, data_with_indicators)
        if signal and self.event_bus:
            await self.event_bus.publish(signal)

        return None  # Return value is not used

    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators

        Args:
            data: OHLCV data

        Returns:
            Data with indicators
        """
        return calculate_ma_cross(
            data,
            short_window=self.short_window,
            long_window=self.long_window,
            ma_type=self.ma_type
        )

    def _generate_signal(self, symbol: str, data: pd.DataFrame) -> Optional[SignalEvent]:
        """Generate trading signal

        Args:
            symbol: Trading pair symbol
            data: Data with indicators

        Returns:
            Trading signal (if any)
        """
        if len(data) < 2:
            return None

        # Get latest signal
        latest = data.iloc[-1]

        # Check for golden cross
        if latest['golden_cross']:
            logger.info(
                f"🔔 Golden cross detected for {symbol} | "
                f"MA_short={latest['ma_short']:.2f}, MA_long={latest['ma_long']:.2f}, "
                f"Price={latest['close']:.2f}"
            )
            return self.generate_signal(
                symbol=symbol,
                signal_type=SignalType.BUY,
                strength=1.0,
                metadata={
                    'ma_short': float(latest['ma_short']),
                    'ma_long': float(latest['ma_long']),
                    'price': float(latest['close']),
                    'signal_type': 'golden_cross'
                }
            )

        # Check for death cross
        if latest['death_cross']:
            logger.info(
                f"🔔 Death cross detected for {symbol} | "
                f"MA_short={latest['ma_short']:.2f}, MA_long={latest['ma_long']:.2f}, "
                f"Price={latest['close']:.2f}"
            )
            return self.generate_signal(
                symbol=symbol,
                signal_type=SignalType.SELL,
                strength=1.0,
                metadata={
                    'ma_short': float(latest['ma_short']),
                    'ma_long': float(latest['ma_long']),
                    'price': float(latest['close']),
                    'signal_type': 'death_cross'
                }
            )

        return None

    def backtest_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """Backtest mode: Generate signals in batch

        Args:
            data: OHLCV data

        Returns:
            Data with signals
        """
        data_with_indicators = self.calculate_indicators(data)

        # Generate signal column
        data_with_indicators['signal'] = 0
        data_with_indicators.loc[data_with_indicators['golden_cross'], 'signal'] = 1  # Buy
        data_with_indicators.loc[data_with_indicators['death_cross'], 'signal'] = -1  # Sell

        return data_with_indicators
