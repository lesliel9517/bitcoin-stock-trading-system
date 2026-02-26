"""Real-time market data feed from CoinGecko API

CoinGecko provides free, public cryptocurrency price data without geographic restrictions.
"""

import asyncio
import aiohttp
from typing import Dict, Optional
from datetime import datetime
from decimal import Decimal

from ..core.event import MarketEvent
from ..core.event_bus import EventBus
from ..utils.logger import logger
from .feed import DataFeed


class CoinGeckoDataFeed(DataFeed):
    """Real-time data feed from CoinGecko API

    Uses CoinGecko's free public API to fetch real cryptocurrency prices.
    No API key required, no geographic restrictions.
    """

    # Symbol mapping: our format -> CoinGecko ID
    SYMBOL_MAP = {
        'BTC-USD': 'bitcoin',
        'BTC-USDT': 'bitcoin',
        'ETH-USD': 'ethereum',
        'ETH-USDT': 'ethereum',
        'BNB-USD': 'binancecoin',
        'SOL-USD': 'solana',
        'ADA-USD': 'cardano',
        'XRP-USD': 'ripple',
        'DOT-USD': 'polkadot',
        'DOGE-USD': 'dogecoin',
    }

    def __init__(
        self,
        event_bus: EventBus,
        update_interval: float = 10.0  # CoinGecko free tier: max 10-30 calls/min
    ):
        """Initialize CoinGecko data feed

        Args:
            event_bus: Event bus for publishing market events
            update_interval: Update interval in seconds (default: 10s)
        """
        super().__init__(event_bus)
        self.update_interval = update_interval
        self.api_url = "https://api.coingecko.com/api/v3"
        self.session: Optional[aiohttp.ClientSession] = None

        logger.info(f"CoinGecko data feed initialized (update interval: {update_interval}s)")

    def _get_coingecko_id(self, symbol: str) -> Optional[str]:
        """Get CoinGecko coin ID from symbol

        Args:
            symbol: Trading symbol (e.g., 'BTC-USD')

        Returns:
            CoinGecko coin ID (e.g., 'bitcoin')
        """
        return self.SYMBOL_MAP.get(symbol.upper())

    async def start(self):
        """Start the data feed"""
        await super().start()

        # Create aiohttp session
        self.session = aiohttp.ClientSession()

        # Start price update tasks for all subscribed symbols
        for symbol in self.subscriptions.keys():
            task = asyncio.create_task(self._fetch_price_loop(symbol))
            self._tasks.append(task)

        logger.info("CoinGecko data feed started")

    async def stop(self):
        """Stop the data feed"""
        self.is_running = False

        # Close aiohttp session
        if self.session:
            await self.session.close()

        await super().stop()
        logger.info("CoinGecko data feed stopped")

    async def _fetch_price_loop(self, symbol: str):
        """Continuously fetch price for a symbol

        Args:
            symbol: Trading symbol
        """
        coin_id = self._get_coingecko_id(symbol)
        if not coin_id:
            logger.error(f"Unknown symbol: {symbol}")
            return

        while self.is_running:
            try:
                # Fetch current price
                price_data = await self._fetch_price(coin_id)

                if price_data:
                    price = Decimal(str(price_data['usd']))
                    volume_24h = Decimal(str(price_data.get('usd_24h_vol', 0)))
                    change_24h = price_data.get('usd_24h_change', 0)

                    # Publish market data
                    await self.publish_market_data(
                        symbol=symbol,
                        price=price,
                        volume=volume_24h,
                        exchange='coingecko'
                    )

                    logger.debug(f"Updated {symbol}: ${price:,.2f} (24h change: {change_24h:.2f}%)")

                # Wait before next update
                await asyncio.sleep(self.update_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error fetching price for {symbol}: {e}")
                await asyncio.sleep(self.update_interval)

    async def _fetch_price(self, coin_id: str) -> Optional[Dict]:
        """Fetch price from CoinGecko API

        Args:
            coin_id: CoinGecko coin ID (e.g., 'bitcoin')

        Returns:
            Price data dictionary
        """
        try:
            url = f"{self.api_url}/simple/price"
            params = {
                'ids': coin_id,
                'vs_currencies': 'usd',
                'include_24hr_vol': 'true',
                'include_24hr_change': 'true'
            }

            async with self.session.get(url, params=params, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get(coin_id)
                else:
                    logger.error(f"CoinGecko API error: HTTP {response.status}")
                    return None

        except asyncio.TimeoutError:
            logger.error("CoinGecko API timeout")
            return None
        except Exception as e:
            logger.error(f"Error calling CoinGecko API: {e}")
            return None

    async def get_current_price(self, symbol: str) -> Optional[Decimal]:
        """Get current price for a symbol (one-time fetch)

        Args:
            symbol: Trading symbol

        Returns:
            Current price
        """
        coin_id = self._get_coingecko_id(symbol)
        if not coin_id:
            return None

        if not self.session:
            self.session = aiohttp.ClientSession()

        price_data = await self._fetch_price(coin_id)
        if price_data:
            return Decimal(str(price_data['usd']))

        return None
