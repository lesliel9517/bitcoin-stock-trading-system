"""Quick start example"""

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.backtest.engine import BacktestEngine
from src.strategies.examples.ma_cross import MACrossStrategy
from src.data.storage import DataStorage
from src.utils.logger import setup_logger, logger


async def main():
    """快速开始示例"""
    # 设置日志
    setup_logger(log_level='INFO')

    logger.info("🚀 Bitcoin & Stock Trading System - Quick Start")
    logger.info("=" * 60)

    # 1. 加载数据
    logger.info("\n📊 Step 1: Loading market data...")
    storage = DataStorage()

    symbol = 'BTC-USD'
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)

    data = storage.load_ohlcv(
        symbol=symbol,
        exchange='binance',
        timeframe='1d',
        start=start_date,
        end=end_date
    )

    if data.empty:
        logger.error("❌ No data found. Please run: python scripts/download_data.py")
        return

    logger.info(f"✅ Loaded {len(data)} data points for {symbol}")

    # 2. 创建策略
    logger.info("\n⚙️  Step 2: Creating MA Cross strategy...")
    strategy_config = {
        'symbols': [symbol],
        'timeframe': '1d',
        'parameters': {
            'short_window': 5,
            'long_window': 20,
            'ma_type': 'SMA'
        }
    }

    strategy = MACrossStrategy(strategy_id='ma_cross_demo', config=strategy_config)
    logger.info("✅ Strategy created")

    # 3. 创建回测引擎
    logger.info("\n🔧 Step 3: Setting up backtest engine...")
    engine = BacktestEngine(
        initial_capital=Decimal('100000'),
        commission=Decimal('0.001'),
        slippage=Decimal('0.0005')
    )
    engine.set_strategy(strategy)
    logger.info("✅ Backtest engine ready")

    # 4. 运行回测
    logger.info("\n🏃 Step 4: Running backtest...")
    results = await engine.run(data, symbol, exchange='binance')

    # 5. 显示结果
    metrics = results['metrics']

    logger.info("\n" + "=" * 60)
    logger.info("📈 BACKTEST RESULTS")
    logger.info("=" * 60)

    logger.info(f"\n💵 Capital:")
    logger.info(f"  Initial: ${metrics['initial_capital']:,.2f}")
    logger.info(f"  Final:   ${metrics['final_equity']:,.2f}")
    logger.info(f"  Return:  {metrics['total_return_pct']:.2f}%")
    logger.info(f"  Annual:  {metrics['annual_return_pct']:.2f}%")

    logger.info(f"\n📊 Performance:")
    logger.info(f"  Max Drawdown:  {metrics['max_drawdown_pct']:.2f}%")
    logger.info(f"  Sharpe Ratio:  {metrics['sharpe_ratio']:.2f}")
    logger.info(f"  Sortino Ratio: {metrics['sortino_ratio']:.2f}")

    logger.info(f"\n🎯 Trading:")
    logger.info(f"  Total Trades:   {metrics['total_trades']}")
    logger.info(f"  Winning Trades: {metrics['winning_trades']}")
    logger.info(f"  Losing Trades:  {metrics['losing_trades']}")
    logger.info(f"  Win Rate:       {metrics['win_rate']:.2f}%")
    logger.info(f"  Profit Factor:  {metrics['profit_factor']:.2f}")

    logger.info("\n" + "=" * 60)
    logger.info("✅ Backtest completed successfully!")
    logger.info("\n💡 Next steps:")
    logger.info("  - Try different strategy parameters")
    logger.info("  - Test with other symbols (ETH-USD)")
    logger.info("  - Implement your own strategy")
    logger.info("  - Use CLI: btc-trade backtest start --help")


if __name__ == '__main__':
    asyncio.run(main())
