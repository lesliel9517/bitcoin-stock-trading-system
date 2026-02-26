"""Download sample market data for testing"""

import asyncio
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.storage import DataStorage
from src.utils.logger import setup_logger, logger


def generate_sample_data(
    symbol: str,
    start_date: datetime,
    end_date: datetime,
    initial_price: float = 50000.0
) -> pd.DataFrame:
    """生成模拟的OHLCV数据

    Args:
        symbol: 交易对符号
        start_date: 开始日期
        end_date: 结束日期
        initial_price: 初始价格

    Returns:
        OHLCV数据DataFrame
    """
    # 生成日期范围
    dates = pd.date_range(start=start_date, end=end_date, freq='1D')

    # 生成随机价格走势
    np.random.seed(42)
    returns = np.random.normal(0.001, 0.02, len(dates))  # 日收益率
    prices = initial_price * (1 + returns).cumprod()

    # 生成OHLCV数据
    data = []
    for i, date in enumerate(dates):
        price = prices[i]
        high = price * (1 + abs(np.random.normal(0, 0.01)))
        low = price * (1 - abs(np.random.normal(0, 0.01)))
        open_price = price * (1 + np.random.normal(0, 0.005))
        volume = np.random.uniform(1000, 10000)

        data.append({
            'timestamp': date,
            'open': open_price,
            'high': high,
            'low': low,
            'close': price,
            'volume': volume
        })

    df = pd.DataFrame(data)
    df.set_index('timestamp', inplace=True)

    return df


def main():
    """主函数"""
    # 设置日志
    setup_logger(log_level='INFO')

    logger.info("📊 Downloading sample market data...")

    # 创建数据存储
    storage = DataStorage()

    # 生成示例数据
    symbols = ['BTC-USD', 'ETH-USD']
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)  # 1年数据

    for symbol in symbols:
        logger.info(f"Generating data for {symbol}...")

        # 设置初始价格
        initial_price = 50000.0 if symbol == 'BTC-USD' else 3000.0

        # 生成数据
        data = generate_sample_data(symbol, start_date, end_date, initial_price)

        # 保存数据
        storage.save_ohlcv(data, symbol, 'binance', '1d')

        logger.info(f"✅ Saved {len(data)} records for {symbol}")

    logger.info("✅ Sample data download completed!")
    logger.info(f"📁 Data saved to: {storage.db_path}")


if __name__ == '__main__':
    main()
