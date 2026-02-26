"""Real-time data feed with realistic price simulation"""

import asyncio
from typing import Dict, List, Optional, Callable
from datetime import datetime
from decimal import Decimal
import random
import math

from ..core.event import MarketEvent
from ..core.event_bus import EventBus
from ..core.types import OrderSide
from ..utils.logger import logger


class DataFeed:
    """Real-time data feed manager"""

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.subscriptions: Dict[str, List[Callable]] = {}
        self.is_running = False
        self._tasks: List[asyncio.Task] = []

        logger.info("Data feed initialized")

    async def subscribe(self, symbol: str, callback: Optional[Callable] = None):
        """Subscribe to market data"""
        if symbol not in self.subscriptions:
            self.subscriptions[symbol] = []

        if callback:
            self.subscriptions[symbol].append(callback)

        logger.info(f"Subscribed to {symbol}")

    async def unsubscribe(self, symbol: str, callback: Optional[Callable] = None):
        """Unsubscribe from market data"""
        if symbol in self.subscriptions:
            if callback and callback in self.subscriptions[symbol]:
                self.subscriptions[symbol].remove(callback)
            elif not callback:
                del self.subscriptions[symbol]

        logger.info(f"Unsubscribed from {symbol}")

    async def publish_market_data(
        self,
        symbol: str,
        price: Decimal,
        volume: Decimal,
        exchange: str = "simulator",
        **kwargs
    ):
        """Publish market data"""
        from ..core.event import EventType

        # Extract standard OHLC data
        event_data = {
            'bid': kwargs.get('bid'),
            'ask': kwargs.get('ask'),
            'high': kwargs.get('high'),
            'low': kwargs.get('low'),
            'open': kwargs.get('open'),
            'close': kwargs.get('close'),
        }

        # Store extended market data in the data field
        extended_data = {}
        for key in ['change_24h', 'change_pct_24h', 'change_day', 'change_pct_day',
                    'high_day', 'low_day', 'open_day', 'mktcap']:
            if key in kwargs:
                extended_data[key] = kwargs[key]

        event = MarketEvent(
            event_type=EventType.MARKET,
            symbol=symbol,
            exchange=exchange,
            price=price,
            volume=volume,
            bid=event_data['bid'],
            ask=event_data['ask'],
            high=event_data['high'],
            low=event_data['low'],
            open=event_data['open'],
            close=event_data['close'],
            timestamp=datetime.now(),
            data=extended_data,  # Store extended data here
            source="data_feed"
        )

        await self.event_bus.publish(event)

        if symbol in self.subscriptions:
            for callback in self.subscriptions[symbol]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event)
                    else:
                        callback(event)
                except Exception as e:
                    logger.error(f"Error in callback for {symbol}: {e}")

    async def start(self):
        """Start data feed"""
        self.is_running = True
        logger.info("Data feed started")

    async def stop(self):
        """Stop data feed"""
        self.is_running = False

        for task in self._tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        self._tasks.clear()
        logger.info("Data feed stopped")

    def get_subscriptions(self) -> List[str]:
        """Get all subscribed symbols"""
        return list(self.subscriptions.keys())


class SimulatedDataFeed(DataFeed):
    """Simulated data feed - generates realistic prices using Geometric Brownian Motion"""

    def __init__(
        self,
        event_bus: EventBus,
        update_interval: float = 1.0,
        volatility: float = 0.02,  # Annualized volatility 20%
        drift: float = 0.0  # Drift rate (trend)
    ):
        super().__init__(event_bus)
        self.update_interval = update_interval
        self.prices: Dict[str, Decimal] = {}

        # Geometric Brownian Motion parameters
        self.volatility = volatility
        self.drift = drift

        # Price history (for calculating technical indicators)
        self.price_history: Dict[str, List[Decimal]] = {}

    def set_price(self, symbol: str, price: Decimal):
        """Set initial price"""
        self.prices[symbol] = price
        if symbol not in self.price_history:
            self.price_history[symbol] = []

    async def start(self):
        """Start simulated data feed"""
        await super().start()

        for symbol in self.subscriptions.keys():
            task = asyncio.create_task(self._generate_realistic_data(symbol))
            self._tasks.append(task)

        logger.info("Simulated data feed started with realistic price model")

    async def _generate_realistic_data(self, symbol: str):
        """Generate realistic prices using Geometric Brownian Motion

        Formula: dS = μ*S*dt + σ*S*dW
        Where:
        - S: Current price
        - μ: Drift rate (trend)
        - σ: Volatility
        - dW: Wiener process (random walk)
        - dt: Time step
        """
        # Initial price
        if symbol not in self.prices:
            self.prices[symbol] = Decimal('50000')

        # Time step (annualized)
        dt = self.update_interval / (365 * 24 * 3600)  # Convert to years

        while self.is_running:
            try:
                current_price = self.prices[symbol]

                # Geometric Brownian Motion
                # dW ~ N(0, dt)
                random_shock = random.gauss(0, math.sqrt(dt))

                # Price change percentage
                drift_component = self.drift * dt
                diffusion_component = self.volatility * random_shock
                price_change_pct = drift_component + diffusion_component

                # Calculate new price
                new_price = current_price * (Decimal('1') + Decimal(str(price_change_pct)))

                # Ensure price doesn't become negative or too small
                if new_price < Decimal('0.01'):
                    new_price = Decimal('0.01')

                self.prices[symbol] = new_price

                # Record price history
                if symbol not in self.price_history:
                    self.price_history[symbol] = []
                self.price_history[symbol].append(new_price)

                # Keep only the most recent 1000 price points
                if len(self.price_history[symbol]) > 1000:
                    self.price_history[symbol].pop(0)

                # Generate realistic bid-ask spread (about 0.1%)
                spread = new_price * Decimal('0.001')
                bid = new_price - spread / 2
                ask = new_price + spread / 2

                # Generate volume (based on price volatility)
                volume_base = 50
                volume_volatility = abs(float(price_change_pct)) * 1000
                volume = Decimal(str(random.uniform(
                    volume_base * 0.5,
                    volume_base * 1.5 + volume_volatility
                )))

                # Publish market data
                await self.publish_market_data(
                    symbol=symbol,
                    price=new_price,
                    volume=volume,
                    exchange="simulator",
                    bid=bid,
                    ask=ask
                )

                await asyncio.sleep(self.update_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error generating data for {symbol}: {e}")
                await asyncio.sleep(self.update_interval)
