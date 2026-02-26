"""Binance data provider"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Callable
import pandas as pd
import ccxt.async_support as ccxt

from .base import DataProvider
from ...utils.logger import logger


class BinanceDataProvider(DataProvider):
    """Binance数据提供者

    提供Binance交易所的历史和实时数据
    """

    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None, testnet: bool = False):
        """初始化Binance数据提供者

        Args:
            api_key: API密钥（可选，公开数据不需要）
            api_secret: API密钥（可选）
            testnet: 是否使用测试网
        """
        super().__init__("binance")

        config = {}
        if api_key and api_secret:
            config['apiKey'] = api_key
            config['secret'] = api_secret

        if testnet:
            config['urls'] = {
                'api': {
                    'public': 'https://testnet.binance.vision/api',
                    'private': 'https://testnet.binance.vision/api',
                }
            }

        self.exchange = ccxt.binance(config)
        self.ws_connections = {}

        logger.info(f"Binance data provider initialized (testnet={testnet})")

    async def get_historical_data(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        timeframe: str = "1d"
    ) -> pd.DataFrame:
        """获取历史OHLCV数据

        Args:
            symbol: 交易对符号（如 BTC/USDT）
            start: 开始时间
            end: 结束时间
            timeframe: 时间周期（1m, 5m, 15m, 1h, 4h, 1d等）

        Returns:
            包含OHLCV数据的DataFrame
        """
        try:
            # 标准化交易对符号
            symbol = self.normalize_symbol(symbol)

            # 转换时间为毫秒时间戳
            since = int(start.timestamp() * 1000)
            end_ts = int(end.timestamp() * 1000)

            all_ohlcv = []

            # 分批获取数据（Binance限制每次最多1000条）
            while since < end_ts:
                ohlcv = await self.exchange.fetch_ohlcv(
                    symbol,
                    timeframe=timeframe,
                    since=since,
                    limit=1000
                )

                if not ohlcv:
                    break

                all_ohlcv.extend(ohlcv)

                # 更新起始时间为最后一条数据的时间
                since = ohlcv[-1][0] + 1

                # 避免触发速率限制
                await asyncio.sleep(0.1)

            # 转换为DataFrame
            if not all_ohlcv:
                logger.warning(f"No data found for {symbol}")
                return pd.DataFrame()

            df = pd.DataFrame(
                all_ohlcv,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )

            # 转换时间戳
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)

            # 过滤到指定的结束时间
            df = df[df.index <= end]

            logger.info(f"Fetched {len(df)} records for {symbol} from Binance")
            return df

        except Exception as e:
            logger.error(f"Error fetching historical data from Binance: {e}")
            raise

    async def get_latest_price(self, symbol: str) -> Optional[float]:
        """获取最新价格

        Args:
            symbol: 交易对符号

        Returns:
            最新价格
        """
        try:
            symbol = self.normalize_symbol(symbol)
            ticker = await self.exchange.fetch_ticker(symbol)
            return ticker['last']
        except Exception as e:
            logger.error(f"Error fetching latest price from Binance: {e}")
            return None

    async def subscribe_market_data(self, symbol: str, callback: Callable):
        """订阅实时行情数据

        Args:
            symbol: 交易对符号
            callback: 数据回调函数
        """
        try:
            symbol = self.normalize_symbol(symbol)

            # 使用CCXT的watch方法订阅WebSocket
            async def watch_ticker():
                while True:
                    try:
                        ticker = await self.exchange.watch_ticker(symbol)
                        await callback(ticker)
                    except Exception as e:
                        logger.error(f"Error in WebSocket for {symbol}: {e}")
                        await asyncio.sleep(5)  # 重连延迟

            task = asyncio.create_task(watch_ticker())
            self.ws_connections[symbol] = task

            logger.info(f"Subscribed to {symbol} on Binance")

        except Exception as e:
            logger.error(f"Error subscribing to market data: {e}")
            raise

    async def unsubscribe_market_data(self, symbol: str):
        """取消订阅实时行情数据

        Args:
            symbol: 交易对符号
        """
        symbol = self.normalize_symbol(symbol)

        if symbol in self.ws_connections:
            task = self.ws_connections[symbol]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            del self.ws_connections[symbol]
            logger.info(f"Unsubscribed from {symbol} on Binance")

    def normalize_symbol(self, symbol: str) -> str:
        """标准化交易对符号

        Args:
            symbol: 交易对符号

        Returns:
            标准化后的符号（如 BTC/USDT）
        """
        symbol = symbol.upper()

        # 转换常见格式
        if '-' in symbol:
            # BTC-USD -> BTC/USD
            symbol = symbol.replace('-', '/')
        elif '/' not in symbol and len(symbol) > 3:
            # BTCUSDT -> BTC/USDT
            if symbol.endswith('USDT'):
                symbol = symbol[:-4] + '/USDT'
            elif symbol.endswith('USD'):
                symbol = symbol[:-3] + '/USD'
            elif symbol.endswith('BTC'):
                symbol = symbol[:-3] + '/BTC'

        return symbol

    async def close(self):
        """关闭连接"""
        # 取消所有WebSocket连接
        for symbol in list(self.ws_connections.keys()):
            await self.unsubscribe_market_data(symbol)

        # 关闭交易所连接
        await self.exchange.close()
        logger.info("Binance data provider closed")
