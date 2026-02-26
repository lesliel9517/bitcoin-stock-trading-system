"""Binance HTTP API data feed (alternative to WebSocket for proxy environments)"""

import asyncio
import aiohttp
from typing import Dict, Optional
from datetime import datetime
from decimal import Decimal

from ..core.event import MarketEvent
from ..core.event_bus import EventBus
from ..utils.logger import logger
from .feed import DataFeed


class BinanceHttpFeed(DataFeed):
    """Real-time data feed from Binance HTTP API

    Uses REST API polling instead of WebSocket.
    Better for proxy/firewall environments where WebSocket is blocked.
    """

    def __init__(
        self,
        event_bus: EventBus,
        update_interval: float = 1.0,
        testnet: bool = False
    ):
        """Initialize Binance HTTP data feed

        Args:
            event_bus: Event bus for publishing market events
            update_interval: Polling interval in seconds (default: 1.0)
            testnet: Whether to use Binance testnet (default: False)
        """
        super().__init__(event_bus)
        self.update_interval = update_interval
        self.testnet = testnet
        self.base_url = self._get_base_url()
        self.session: Optional[aiohttp.ClientSession] = None

        logger.info(f"Binance HTTP feed initialized (testnet={testnet}, interval={update_interval}s)")

    def _get_base_url(self) -> str:
        """Get API base URL based on testnet setting"""
        if self.testnet:
            return "https://testnet.binance.vision/api/v3"
        return "https://api.binance.com/api/v3"

    def _format_symbol(self, symbol: str) -> str:
        """Format symbol for Binance API

        Args:
            symbol: Symbol like 'BTC-USD' or 'BTCUSDT'

        Returns:
            Formatted symbol like 'BTCUSDT'
        """
        # Remove separators and convert to uppercase
        symbol = symbol.replace('-', '').replace('/', '').upper()

        # Convert USD to USDT for Binance
        if symbol.endswith('USD') and not symbol.endswith('USDT'):
            symbol = symbol[:-3] + 'USDT'

        return symbol

    async def start(self):
        """Start the data feed and begin polling"""
        await super().start()

        # Create HTTP session
        self.session = aiohttp.ClientSession()

        # Start polling tasks for each subscribed symbol
        for symbol in self.subscriptions.keys():
            task = asyncio.create_task(self._poll_symbol(symbol))
            self._tasks.append(task)

        logger.info("Binance HTTP feed started")

    async def stop(self):
        """Stop the data feed and close HTTP session"""
        self.is_running = False

        # Close HTTP session
        if self.session:
            await self.session.close()

        await super().stop()
        logger.info("Binance HTTP feed stopped")

    async def _poll_symbol(self, symbol: str):
        """Poll market data for a symbol

        Args:
            symbol: Trading symbol
        """
        formatted_symbol = self._format_symbol(symbol)

        while self.is_running:
            try:
                # Fetch ticker data
                ticker_url = f"{self.base_url}/ticker/24hr"
                params = {'symbol': formatted_symbol}

                async with self.session.get(ticker_url, params=params, timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        await self._process_ticker(symbol, data)
                    else:
                        logger.warning(f"HTTP {response.status} for {symbol}")

                await asyncio.sleep(self.update_interval)

            except asyncio.CancelledError:
                break
            except asyncio.TimeoutError:
                logger.warning(f"Timeout fetching data for {symbol}")
                await asyncio.sleep(self.update_interval)
            except Exception as e:
                logger.error(f"Error polling {symbol}: {e}")
                await asyncio.sleep(self.update_interval)

    async def _process_ticker(self, symbol: str, data: Dict):
        """Process ticker data and publish market event

        Args:
            symbol: Trading symbol
            data: Ticker data from Binance API
        """
        try:
            # Extract data
            price = Decimal(data['lastPrice'])
            volume = Decimal(data['volume'])
            high = Decimal(data['highPrice'])
            low = Decimal(data['lowPrice'])
            open_price = Decimal(data['openPrice'])
            bid = Decimal(data['bidPrice']) if 'bidPrice' in data else None
            ask = Decimal(data['askPrice']) if 'askPrice' in data else None

            # Publish market event
            await self.publish_market_data(
                symbol=symbol,
                price=price,
                volume=volume,
                exchange='binance',
                high=high,
                low=low,
                open=open_price,
                close=price,
                bid=bid,
                ask=ask
            )

        except (KeyError, ValueError) as e:
            logger.error(f"Error parsing ticker data for {symbol}: {e}")
