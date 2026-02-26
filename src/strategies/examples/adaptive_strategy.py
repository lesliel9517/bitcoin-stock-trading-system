"""Adaptive dynamic trading strategy"""

from typing import Dict, Optional
from decimal import Decimal
import pandas as pd
import numpy as np

from ..base import Strategy
from ...core.event import MarketEvent, SignalEvent
from ...core.types import SignalType
from ...utils.logger import logger


class AdaptiveStrategy(Strategy):
    """Adaptive trading strategy with dynamic parameter adjustment

    Automatically adjusts parameters based on market conditions:
    - Detects market regime (trending/ranging, high/low volatility)
    - Adjusts MA periods, stop-loss, and position sizing dynamically
    - Implements adaptive risk management
    """

    def __init__(self, strategy_id: str, config: Dict):
        """Initialize adaptive strategy

        Args:
            strategy_id: Strategy ID
            config: Strategy configuration
        """
        super().__init__(strategy_id, config)

        # Base parameters (will be adjusted dynamically)
        self.base_ma_short = self.parameters.get('ma_short', 10)
        self.base_ma_long = self.parameters.get('ma_long', 30)
        self.volatility_window = self.parameters.get('volatility_window', 20)
        self.trend_window = self.parameters.get('trend_window', 50)

        # Dynamic parameters (updated based on market state)
        self.current_ma_short = self.base_ma_short
        self.current_ma_long = self.base_ma_long
        self.current_stop_loss = Decimal("0.02")  # 2% default
        self.current_take_profit = Decimal("0.04")  # 4% default
        self.current_position_size = Decimal("0.95")  # 95% default

        # Market state tracking
        self.market_regime = "unknown"  # trending_up, trending_down, ranging
        self.volatility_regime = "normal"  # low, normal, high
        self.trend_strength = 0.0

        # Position tracking
        self.entry_price = None
        self.position_active = False

        logger.info(f"Adaptive strategy initialized: {self.strategy_id}")

    def on_init(self):
        """Initialize strategy state"""
        logger.info(f"Adaptive strategy {self.strategy_id} started")

    async def on_market_data(self, event: MarketEvent) -> Optional[SignalEvent]:
        """Process market data and generate signals

        Args:
            event: Market data event

        Returns:
            Signal event if conditions are met
        """
        symbol = event.symbol

        # Update data cache
        if symbol not in self._data_cache:
            self._data_cache[symbol] = pd.DataFrame()

        new_row = pd.DataFrame([{
            'timestamp': event.timestamp,
            'open': float(event.open or event.price),
            'high': float(event.high or event.price),
            'low': float(event.low or event.price),
            'close': float(event.price),
            'volume': float(event.volume)
        }])
        new_row.set_index('timestamp', inplace=True)

        self._data_cache[symbol] = pd.concat([self._data_cache[symbol], new_row])

        # Need enough data for analysis
        if len(self._data_cache[symbol]) < max(self.trend_window, self.volatility_window):
            return None

        # Analyze market state and adjust parameters
        self._analyze_market_state(symbol)

        # Calculate indicators with dynamic parameters
        data = self.calculate_indicators(self._data_cache[symbol].copy())

        if len(data) < 2:
            return None

        # Get current and previous values
        current = data.iloc[-1]
        previous = data.iloc[-2]

        current_price = Decimal(str(current['close']))

        # Check stop-loss and take-profit if position is active
        if self.position_active and self.entry_price:
            pnl_pct = (current_price - self.entry_price) / self.entry_price

            # Stop-loss hit
            if pnl_pct <= -self.current_stop_loss:
                logger.info(f"Stop-loss triggered: {pnl_pct:.2%}")
                self.position_active = False
                self.entry_price = None
                return self.generate_signal(
                    symbol=symbol,
                    signal_type=SignalType.SELL,
                    strength=1.0,
                    metadata={
                        'price': float(current_price),
                        'reason': f"Stop-loss: {pnl_pct:.2%}",
                        'pnl_pct': float(pnl_pct)
                    }
                )

            # Take-profit hit
            if pnl_pct >= self.current_take_profit:
                logger.info(f"Take-profit triggered: {pnl_pct:.2%}")
                self.position_active = False
                self.entry_price = None
                return self.generate_signal(
                    symbol=symbol,
                    signal_type=SignalType.SELL,
                    strength=1.0,
                    metadata={
                        'price': float(current_price),
                        'reason': f"Take-profit: {pnl_pct:.2%}",
                        'pnl_pct': float(pnl_pct)
                    }
                )

        # Generate trading signals based on MA crossover with filters
        ma_short_curr = current['ma_short']
        ma_long_curr = current['ma_long']
        ma_short_prev = previous['ma_short']
        ma_long_prev = previous['ma_long']
        current_close = current['close']

        # Additional filters
        rsi = current.get('rsi', 50)

        # Buy signal: short MA crosses above long MA
        if (ma_short_prev <= ma_long_prev and ma_short_curr > ma_long_curr and
            not self.position_active):

            # Filter 1: Price should be above long MA (uptrend confirmation)
            price_above_ma = current_close > ma_long_curr

            # Filter 2: RSI should not be overbought (avoid buying at peaks)
            rsi_ok = 30 < rsi < 70

            # Filter 3: MA spread should be reasonable (avoid late entries)
            ma_spread = (ma_short_curr - ma_long_curr) / ma_long_curr
            spread_ok = ma_spread < 0.02  # Less than 2% spread

            # Only buy if all filters pass
            if (price_above_ma and rsi_ok and spread_ok and
                self.market_regime in ['trending_up', 'ranging'] and
                self.volatility_regime != 'high'):

                self.position_active = True
                self.entry_price = current_price

                logger.info(
                    f"Buy signal: MA cross | Price: {current_close:.2f} | MA_long: {ma_long_curr:.2f} | "
                    f"RSI: {rsi:.1f} | Spread: {ma_spread:.2%} | Regime: {self.market_regime}"
                )

                return self.generate_signal(
                    symbol=symbol,
                    signal_type=SignalType.BUY,
                    strength=1.0,
                    metadata={
                        'price': float(current_price),
                        'reason': f"MA cross up | {self.market_regime} | RSI:{rsi:.1f}",
                        'market_regime': self.market_regime,
                        'volatility_regime': self.volatility_regime,
                        'rsi': float(rsi),
                        'stop_loss': float(self.current_stop_loss),
                        'take_profit': float(self.current_take_profit)
                    }
                )

        # Sell signal: short MA crosses below long MA
        elif (ma_short_prev >= ma_long_prev and ma_short_curr < ma_long_curr and
              self.position_active):

            self.position_active = False
            self.entry_price = None

            logger.info(
                f"Sell signal: MA cross down | Price: {current_close:.2f} | "
                f"RSI: {rsi:.1f} | Regime: {self.market_regime}"
            )

            return self.generate_signal(
                symbol=symbol,
                signal_type=SignalType.SELL,
                strength=1.0,
                metadata={
                    'price': float(current_price),
                    'reason': f"MA cross down | {self.market_regime}",
                    'market_regime': self.market_regime,
                    'rsi': float(rsi)
                }
            )

        return None

    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators with dynamic parameters

        Args:
            data: OHLCV data

        Returns:
            Data with indicators
        """
        # Calculate moving averages with current dynamic parameters
        data['ma_short'] = data['close'].rolling(window=self.current_ma_short).mean()
        data['ma_long'] = data['close'].rolling(window=self.current_ma_long).mean()

        # Calculate ATR for volatility
        high_low = data['high'] - data['low']
        high_close = np.abs(data['high'] - data['close'].shift())
        low_close = np.abs(data['low'] - data['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        data['atr'] = true_range.rolling(window=14).mean()

        # Calculate RSI
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        data['rsi'] = 100 - (100 / (1 + rs))

        return data

    def _analyze_market_state(self, symbol: str):
        """Analyze market state and adjust parameters dynamically

        Args:
            symbol: Trading symbol
        """
        data = self._data_cache[symbol].copy()

        if len(data) < self.trend_window:
            return

        # 1. Detect volatility regime
        returns = data['close'].pct_change().dropna()
        recent_vol = returns.tail(self.volatility_window).std()
        historical_vol = returns.std()

        if recent_vol > historical_vol * 1.5:
            self.volatility_regime = "high"
            # In high volatility: widen stops, reduce position size
            self.current_stop_loss = Decimal("0.03")  # 3%
            self.current_take_profit = Decimal("0.06")  # 6%
            self.current_position_size = Decimal("0.70")  # 70%
        elif recent_vol < historical_vol * 0.7:
            self.volatility_regime = "low"
            # In low volatility: tighter stops, larger position
            self.current_stop_loss = Decimal("0.015")  # 1.5%
            self.current_take_profit = Decimal("0.03")  # 3%
            self.current_position_size = Decimal("0.95")  # 95%
        else:
            self.volatility_regime = "normal"
            self.current_stop_loss = Decimal("0.02")  # 2%
            self.current_take_profit = Decimal("0.04")  # 4%
            self.current_position_size = Decimal("0.85")  # 85%

        # 2. Detect trend regime
        recent_data = data.tail(self.trend_window)
        sma_trend = recent_data['close'].rolling(window=20).mean()

        # Calculate trend strength using linear regression
        x = np.arange(len(sma_trend))
        y = sma_trend.values
        valid_idx = ~np.isnan(y)

        if valid_idx.sum() > 10:
            slope, _ = np.polyfit(x[valid_idx], y[valid_idx], 1)
            self.trend_strength = slope / y[valid_idx].mean() * 100  # Normalize

            if self.trend_strength > 0.5:
                self.market_regime = "trending_up"
                # In uptrend: use faster MAs to catch momentum
                self.current_ma_short = max(5, self.base_ma_short - 3)
                self.current_ma_long = max(15, self.base_ma_long - 10)
            elif self.trend_strength < -0.5:
                self.market_regime = "trending_down"
                # In downtrend: use slower MAs to avoid false signals
                self.current_ma_short = self.base_ma_short + 5
                self.current_ma_long = self.base_ma_long + 10
            else:
                self.market_regime = "ranging"
                # In ranging market: use base parameters
                self.current_ma_short = self.base_ma_short
                self.current_ma_long = self.base_ma_long

        logger.debug(
            f"Market state: {self.market_regime} | Volatility: {self.volatility_regime} | "
            f"Trend: {self.trend_strength:.2f} | MA: {self.current_ma_short}/{self.current_ma_long} | "
            f"Stop: {self.current_stop_loss:.2%} | Size: {self.current_position_size:.2%}"
        )

    def backtest_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """Generate signals for backtesting

        Args:
            data: Historical OHLCV data

        Returns:
            Data with signals
        """
        data = self.calculate_indicators(data.copy())

        signals = []
        position_active = False
        entry_price = None

        for i in range(1, len(data)):
            signal = 0

            # Update market state periodically
            if i % 10 == 0:  # Update every 10 bars
                temp_data = data.iloc[:i+1].copy()
                self._data_cache['backtest'] = temp_data
                self._analyze_market_state('backtest')

            current = data.iloc[i]
            previous = data.iloc[i-1]

            current_price = current['close']

            # Check stop-loss and take-profit
            if position_active and entry_price:
                pnl_pct = (current_price - entry_price) / entry_price

                if pnl_pct <= -float(self.current_stop_loss) or pnl_pct >= float(self.current_take_profit):
                    signal = -1
                    position_active = False
                    entry_price = None

            # MA crossover signals with filters
            if not position_active:
                if (previous['ma_short'] <= previous['ma_long'] and
                    current['ma_short'] > current['ma_long']):

                    # Apply same filters as real-time
                    rsi = current.get('rsi', 50)
                    price_above_ma = current['close'] > current['ma_long']
                    rsi_ok = 30 < rsi < 70
                    ma_spread = (current['ma_short'] - current['ma_long']) / current['ma_long']
                    spread_ok = ma_spread < 0.02

                    # Only buy if all filters pass
                    if (price_above_ma and rsi_ok and spread_ok and
                        self.market_regime in ['trending_up', 'ranging'] and
                        self.volatility_regime != 'high'):
                        signal = 1
                        position_active = True
                        entry_price = current_price

            elif position_active:
                if (previous['ma_short'] >= previous['ma_long'] and
                    current['ma_short'] < current['ma_long']):
                    signal = -1
                    position_active = False
                    entry_price = None

            signals.append(signal)

        data['signal'] = [0] + signals

        return data
