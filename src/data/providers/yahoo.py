"""Yahoo Finance data provider"""

import asyncio
from datetime import datetime
from typing import Optional, Callable
import pandas as pd

from .base import DataProvider
from ...utils.logger import logger


class YahooFinanceProvider(DataProvider):
    """Yahoo Finance数据提供者

    提供美股和其他市场的历史数据
    注意：Yahoo Finance不提供实时WebSocket，实时数据通过轮询实现
    """

    def __init__(self):
        """初始化Yahoo Finance数据提供者"""
        super().__init__("yahoo")
        self.polling_tasks = {}
        logger.info("Yahoo Finance data provider initialized")

    async def get_historical_data(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        timeframe: str = "1d"
    ) -> pd.DataFrame:
        """获取历史OHLCV数据

        Args:
            symbol: 股票代码（如 AAPL, TSLA）
            start: 开始时间
            end: 结束时间
            timeframe: 时间周期（1d, 1wk, 1mo）

        Returns:
            包含OHLCV数据的DataFrame
        """
        try:
            import yfinance as yf

            # 标准化交易对符号
            symbol = self.normalize_symbol(symbol)

            # 转换时间周期格式
            interval_map = {
                '1m': '1m',
                '5m': '5m',
                '15m': '15m',
                '1h': '1h',
                '1d': '1d',
                '1wk': '1wk',
                '1mo': '1mo'
            }
            interval = interval_map.get(timeframe, '1d')

            # 获取数据
            ticker = yf.Ticker(symbol)
            df = await asyncio.to_thread(
                ticker.history,
                start=start,
                end=end,
                interval=interval
            )

            if df.empty:
                logger.warning(f"No data found for {symbol}")
                return pd.DataFrame()

            # 标准化列名
            df.columns = [col.lower() for col in df.columns]
            df = df.rename(columns={'date': 'timestamp'})

            # 确保有timestamp索引
            if 'timestamp' not in df.columns and df.index.name != 'timestamp':
                df.index.name = 'timestamp'

            # 只保留OHLCV列
            columns_to_keep = ['open', 'high', 'low', 'close', 'volume']
            df = df[[col for col in columns_to_keep if col in df.columns]]

            logger.info(f"Fetched {len(df)} records for {symbol} from Yahoo Finance")
            return df

        except ImportError:
            logger.error("yfinance package not installed. Install with: pip install yfinance")
            raise
        except Exception as e:
            logger.error(f"Error fetching historical data from Yahoo Finance: {e}")
            raise

    async def get_latest_price(self, symbol: str) -> Optional[float]:
        """获取最新价格

        Args:
            symbol: 股票代码

        Returns:
            最新价格
        """
        try:
            import yfinance as yf

            symbol = self.normalize_symbol(symbol)
            ticker = yf.Ticker(symbol)

            # 获取最新数据
            data = await asyncio.to_thread(ticker.history, period='1d')

            if not data.empty:
                return float(data['Close'].iloc[-1])

            return None

        except Exception as e:
            logger.error(f"Error fetching latest price from Yahoo Finance: {e}")
            return None

    async def subscribe_market_data(self, symbol: str, callback: Callable):
        """订阅实时行情数据（通过轮询实现）

        Args:
            symbol: 股票代码
            callback: 数据回调函数
        """
        try:
            symbol = self.normalize_symbol(symbol)

            async def poll_data():
                """轮询获取数据"""
                while True:
                    try:
                        price = await self.get_latest_price(symbol)
                        if price:
                            # 构造ticker数据
                            ticker_data = {
                                'symbol': symbol,
                                'last': price,
                                'timestamp': datetime.now()
                            }
                            await callback(ticker_data)

                        # 每60秒更新一次（避免过于频繁）
                        await asyncio.sleep(60)

                    except Exception as e:
                        logger.error(f"Error polling data for {symbol}: {e}")
                        await asyncio.sleep(60)

            task = asyncio.create_task(poll_data())
            self.polling_tasks[symbol] = task

            logger.info(f"Started polling for {symbol} on Yahoo Finance")

        except Exception as e:
            logger.error(f"Error subscribing to market data: {e}")
            raise

    async def unsubscribe_market_data(self, symbol: str):
        """取消订阅实时行情数据

        Args:
            symbol: 股票代码
        """
        symbol = self.normalize_symbol(symbol)

        if symbol in self.polling_tasks:
            task = self.polling_tasks[symbol]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            del self.polling_tasks[symbol]
            logger.info(f"Stopped polling for {symbol} on Yahoo Finance")

    def normalize_symbol(self, symbol: str) -> str:
        """标准化股票代码

        Args:
            symbol: 股票代码

        Returns:
            标准化后的代码
        """
        # Yahoo Finance使用大写股票代码
        return symbol.upper()

    async def close(self):
        """关闭连接"""
        # 取消所有轮询任务
        for symbol in list(self.polling_tasks.keys()):
            await self.unsubscribe_market_data(symbol)

        logger.info("Yahoo Finance data provider closed")
