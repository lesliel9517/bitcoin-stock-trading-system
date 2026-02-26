"""Real-time market data feed from Binance WebSocket API"""

import asyncio
import json
from typing import Dict, Optional
from datetime import datetime
from decimal import Decimal
import websockets

from ..core.event import MarketEvent
from ..core.event_bus import EventBus
from ..utils.logger import logger
from .feed import DataFeed


class BinanceDataFeed(DataFeed):
    """Real-time data feed from Binance WebSocket

    Connects to Binance WebSocket API to receive live market data.
    Uses real market prices for paper trading.
    """

    def __init__(
        self,
        event_bus: EventBus,
        testnet: bool = False
    ):
        """Initialize Binance data feed

        Args:
            event_bus: Event bus for publishing market events
            testnet: Whether to use Binance testnet (default: False)
        """
        super().__init__(event_bus)
        self.testnet = testnet
        self.ws_url = self._get_ws_url()
        self.websocket = None
        self._ws_task = None

        logger.info(f"Binance data feed initialized (testnet={testnet})")

    def _get_ws_url(self) -> str:
        """Get WebSocket URL based on testnet setting"""
        if self.testnet:
            return "wss://testnet.binance.vision/ws"
        # Use data-stream.binance.vision which has better connectivity
        return "wss://data-stream.binance.vision/ws"

    def _format_symbol(self, symbol: str) -> str:
        """Format symbol for Binance WebSocket

        Args:
            symbol: Symbol like 'BTC-USD' or 'BTC/USDT'

        Returns:
            Formatted symbol like 'btcusdt'
        """
        # Remove separators and convert to lowercase
        symbol = symbol.replace('-', '').replace('/', '').lower()

        # Convert USD to USDT for Binance
        if symbol.endswith('usd'):
            symbol = symbol[:-3] + 'usdt'

        return symbol

    async def subscribe(self, symbol: str, callback: Optional[callable] = None):
        """Subscribe to market data for a symbol

        Args:
            symbol: Trading symbol (e.g., 'BTC-USD', 'ETH-USD')
            callback: Optional callback function for market events
        """
        await super().subscribe(symbol, callback)

        # If already running, restart WebSocket with new subscriptions
        if self.is_running:
            await self._restart_websocket()

    async def start(self):
        """Start the data feed and connect to Binance WebSocket"""
        await super().start()
        self._ws_task = asyncio.create_task(self._run_websocket())
        logger.info("Binance data feed started")

    async def stop(self):
        """Stop the data feed and close WebSocket connection"""
        self.is_running = False

        if self.websocket:
            await self.websocket.close()

        if self._ws_task:
            self._ws_task.cancel()
            try:
                await self._ws_task
            except asyncio.CancelledError:
                pass

        await super().stop()
        logger.info("Binance data feed stopped")

    async def _restart_websocket(self):
        """Restart WebSocket connection with updated subscriptions"""
        if self.websocket:
            await self.websocket.close()

        if self._ws_task:
            self._ws_task.cancel()
            try:
                await self._ws_task
            except asyncio.CancelledError:
                pass

        self._ws_task = asyncio.create_task(self._run_websocket())

    async def _run_websocket(self):
        """Run WebSocket connection and handle incoming messages"""
        if not self.subscriptions:
            logger.warning("No subscriptions, WebSocket not started")
            return

        # Build stream names for all subscribed symbols
        streams = []
        for symbol in self.subscriptions.keys():
            formatted_symbol = self._format_symbol(symbol)
            # Subscribe to trade stream for real-time price updates
            streams.append(f"{formatted_symbol}@trade")
            # Subscribe to ticker stream for 24h statistics
            streams.append(f"{formatted_symbol}@ticker")

        # Combine streams
        stream_names = "/".join(streams)
        ws_url = f"{self.ws_url}/{stream_names}"

        logger.info(f"Connecting to Binance WebSocket: {ws_url}")
        logger.info(f"Connection timeout: 10 seconds")

        retry_count = 0
        max_retries = 5

        while self.is_running and retry_count < max_retries:
            try:
                logger.info(f"Attempting connection (try {retry_count + 1}/{max_retries})...")
                # Add connection timeout
                async with websockets.connect(
                    ws_url,
                    ping_interval=20,
                    ping_timeout=10,
                    close_timeout=10,
                    open_timeout=10
                ) as websocket:
                    self.websocket = websocket
                    retry_count = 0  # Reset retry count on successful connection
                    logger.info("Connected to Binance WebSocket")

                    while self.is_running:
                        try:
                            message = await asyncio.wait_for(
                                websocket.recv(),
                                timeout=30.0
                            )
                            await self._handle_message(message)

                        except asyncio.TimeoutError:
                            # Send ping to keep connection alive
                            await websocket.ping()

            except websockets.exceptions.WebSocketException as e:
                retry_count += 1
                logger.error(f"WebSocket error (attempt {retry_count}/{max_retries}): {e}")
                if retry_count < max_retries and self.is_running:
                    await asyncio.sleep(min(retry_count * 2, 30))  # Exponential backoff

            except asyncio.CancelledError:
                break

            except Exception as e:
                logger.error(f"Unexpected error in WebSocket: {e}")
                retry_count += 1
                if retry_count < max_retries and self.is_running:
                    await asyncio.sleep(min(retry_count * 2, 30))

        if retry_count >= max_retries:
            logger.error("Max retries reached, stopping WebSocket")
            self.is_running = False

    async def _handle_message(self, message: str):
        """Handle incoming WebSocket message

        Args:
            message: JSON message from Binance WebSocket
        """
        try:
            data = json.loads(message)

            # Handle trade stream
            if 'e' in data and data['e'] == 'trade':
                await self._handle_trade(data)

            # Handle ticker stream
            elif 'e' in data and data['e'] == '24hrTicker':
                await self._handle_ticker(data)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse WebSocket message: {e}")
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")

    async def _handle_trade(self, data: Dict):
        """Handle trade stream data

        Args:
            data: Trade data from Binance
        """
        try:
            # Extract symbol and convert back to standard format
            symbol_raw = data['s']  # e.g., 'BTCUSDT'
            symbol = self._reverse_format_symbol(symbol_raw)

            # Extract trade data
            price = Decimal(data['p'])
            quantity = Decimal(data['q'])

            # Publish market event
            await self.publish_market_data(
                symbol=symbol,
                price=price,
                volume=quantity,
                exchange='binance'
            )

        except (KeyError, ValueError) as e:
            logger.error(f"Error parsing trade data: {e}")

    async def _handle_ticker(self, data: Dict):
        """Handle 24hr ticker stream data

        Args:
            data: Ticker data from Binance
        """
        try:
            # Extract symbol
            symbol_raw = data['s']
            symbol = self._reverse_format_symbol(symbol_raw)

            # Extract ticker data
            price = Decimal(data['c'])  # Current price
            volume = Decimal(data['v'])  # 24h volume
            high = Decimal(data['h'])   # 24h high
            low = Decimal(data['l'])    # 24h low
            open_price = Decimal(data['o'])  # 24h open

            # Bid/ask prices
            bid = Decimal(data['b']) if 'b' in data else None
            ask = Decimal(data['a']) if 'a' in data else None

            # Publish market event with full data
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
            logger.error(f"Error parsing ticker data: {e}")

    def _reverse_format_symbol(self, binance_symbol: str) -> str:
        """Convert Binance symbol back to standard format

        Args:
            binance_symbol: Binance symbol like 'BTCUSDT'

        Returns:
            Standard symbol like 'BTC-USD'
        """
        # Convert USDT back to USD
        if binance_symbol.endswith('USDT'):
            base = binance_symbol[:-4]
            return f"{base}-USD"

        # For other pairs, try to split intelligently
        # This is a simple heuristic - may need refinement
        if len(binance_symbol) >= 6:
            return f"{binance_symbol[:3]}-{binance_symbol[3:]}"

        return binance_symbol
