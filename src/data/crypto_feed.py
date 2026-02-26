"""Real-time market data feed from CryptoCompare API

Uses CryptoCompare API for real-time cryptocurrency prices.
No authentication required, works globally.
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


class CryptoDataFeed(DataFeed):
    """Real-time data feed from CryptoCompare API"""

    def __init__(
        self,
        event_bus: EventBus,
        update_interval: float = 1.0
    ):
        """Initialize crypto data feed

        Args:
            event_bus: Event bus for publishing market events
            update_interval: Update interval in seconds (default: 1.0)
        """
        super().__init__(event_bus)
        self.update_interval = update_interval
        self.session: Optional[aiohttp.ClientSession] = None

        # Symbol mapping
        self.symbol_map = {
            'BTC-USD': 'BTC',
            'ETH-USD': 'ETH',
        }

        logger.info(f"Crypto data feed initialized (update_interval={update_interval}s)")

    async def start(self):
        """Start the data feed"""
        await super().start()

        # Create HTTP session
        self.session = aiohttp.ClientSession()

        # Start polling task
        self._tasks.append(asyncio.create_task(self._poll_prices()))

        logger.info("Crypto data feed started")

    async def stop(self):
        """Stop the data feed"""
        self.is_running = False

        # Close HTTP session
        if self.session:
            await self.session.close()
            self.session = None

        await super().stop()
        logger.info("Crypto data feed stopped")

    async def _poll_prices(self):
        """Poll prices from CryptoCompare API"""
        if not self.subscriptions:
            logger.warning("No subscriptions, polling not started")
            return

        logger.info(f"Starting price polling for {len(self.subscriptions)} symbols")

        while self.is_running:
            try:
                for symbol in list(self.subscriptions.keys()):
                    crypto_symbol = self.symbol_map.get(symbol)
                    if not crypto_symbol:
                        logger.warning(f"Unknown symbol: {symbol}")
                        continue

                    # Fetch price data
                    price_data = await self._fetch_price(crypto_symbol)

                    if price_data:
                        # Publish market data
                        await self.publish_market_data(
                            symbol=symbol,
                            price=price_data['price'],
                            volume=price_data.get('volume', Decimal('0')),
                            exchange='cryptocompare',
                            high=price_data.get('high_24h'),
                            low=price_data.get('low_24h'),
                            open=price_data.get('open_24h'),
                            change_24h=price_data.get('change_24h'),
                            change_pct_24h=price_data.get('change_pct_24h'),
                            change_pct_day=price_data.get('change_pct_day'),
                            mktcap=price_data.get('mktcap'),
                        )

                await asyncio.sleep(self.update_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error polling prices: {e}", exc_info=True)
                await asyncio.sleep(self.update_interval)

    async def _fetch_price(self, crypto_symbol: str) -> Optional[Dict]:
        """Fetch price data from CryptoCompare

        Args:
            crypto_symbol: Cryptocurrency symbol (e.g., 'BTC', 'ETH')

        Returns:
            Dictionary with price and market data
        """
        try:
            # Use pricemultifull API for detailed data
            url = 'https://min-api.cryptocompare.com/data/pricemultifull'
            params = {
                'fsyms': crypto_symbol,
                'tsyms': 'USD'
            }

            async with self.session.get(url, params=params, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()

                    if 'RAW' in data and crypto_symbol in data['RAW'] and 'USD' in data['RAW'][crypto_symbol]:
                        raw = data['RAW'][crypto_symbol]['USD']

                        # Safely extract and convert values
                        result = {
                            'price': Decimal(str(raw['PRICE'])),
                        }

                        # Optional fields - only add if present and valid
                        if 'CHANGEPCT24HOUR' in raw and raw['CHANGEPCT24HOUR'] is not None:
                            result['change_pct_24h'] = Decimal(str(raw['CHANGEPCT24HOUR']))

                        if 'CHANGEPCTDAY' in raw and raw['CHANGEPCTDAY'] is not None:
                            result['change_pct_day'] = Decimal(str(raw['CHANGEPCTDAY']))

                        if 'CHANGE24HOUR' in raw and raw['CHANGE24HOUR'] is not None:
                            result['change_24h'] = Decimal(str(raw['CHANGE24HOUR']))

                        if 'HIGH24HOUR' in raw and raw['HIGH24HOUR'] is not None:
                            result['high_24h'] = Decimal(str(raw['HIGH24HOUR']))

                        if 'LOW24HOUR' in raw and raw['LOW24HOUR'] is not None:
                            result['low_24h'] = Decimal(str(raw['LOW24HOUR']))

                        if 'OPEN24HOUR' in raw and raw['OPEN24HOUR'] is not None:
                            result['open_24h'] = Decimal(str(raw['OPEN24HOUR']))

                        if 'VOLUME24HOUR' in raw and raw['VOLUME24HOUR'] is not None:
                            result['volume'] = Decimal(str(raw['VOLUME24HOUR']))

                        if 'MKTCAP' in raw and raw['MKTCAP'] is not None:
                            result['mktcap'] = Decimal(str(raw['MKTCAP']))

                        return result

        except Exception as e:
            logger.error(f"Failed to fetch price for {crypto_symbol}: {e}", exc_info=True)

        return None
