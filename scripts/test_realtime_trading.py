"""Test real-time trading functionality"""

import asyncio
from datetime import datetime
from decimal import Decimal
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.engine import TradingEngine
from src.strategies.examples.ma_cross import MACrossStrategy
from src.trading.exchanges.simulator import SimulatedExchange
from src.data.feed import SimulatedDataFeed
from src.utils.logger import setup_logger, logger


async def main():
    """测试实时交易功能"""
    # 设置日志
    setup_logger(log_level='INFO')

    logger.info("🚀 Testing Real-Time Trading System")
    logger.info("=" * 60)

    # 1. 创建交易引擎
    logger.info("\n⚙️  Step 1: Creating trading engine...")
    engine = TradingEngine(
        initial_capital=Decimal('100000'),
        config={'execution': {'default_position_size': '0.95'}}
    )
    logger.info("✅ Trading engine created")

    # 2. 创建策略
    logger.info("\n📊 Step 2: Creating MA Cross strategy...")
    strategy_config = {
        'symbols': ['BTC-USD'],
        'timeframe': '1h',
        'parameters': {
            'short_window': 5,
            'long_window': 20,
            'ma_type': 'SMA'
        }
    }
    strategy = MACrossStrategy(strategy_id='ma_cross_test', config=strategy_config)
    engine.add_strategy(strategy)
    logger.info("✅ Strategy added")

    # 3. 设置模拟交易所
    logger.info("\n🏦 Step 3: Setting up simulated exchange...")
    exchange = SimulatedExchange(
        exchange_id='simulator',
        config={
            'initial_balance': '100000',
            'commission': '0.001',
            'slippage': '0.0005'
        }
    )
    engine.set_exchange(exchange)
    logger.info("✅ Exchange configured")

    # 4. 设置数据流
    logger.info("\n📡 Step 4: Setting up data feed...")
    data_feed = SimulatedDataFeed(engine.event_bus, update_interval=0.5)
    await data_feed.subscribe('BTC-USD')
    data_feed.set_price('BTC-USD', Decimal('50000'))
    engine.set_data_feed(data_feed)
    logger.info("✅ Data feed configured")

    # 5. 运行交易（10秒）
    logger.info("\n🏃 Step 5: Running trading for 10 seconds...")
    logger.info("Watching for trading signals...\n")

    await engine.start()
    await asyncio.sleep(10)
    await engine.stop()

    # 6. 显示结果
    logger.info("\n" + "=" * 60)
    logger.info("📊 TRADING SESSION RESULTS")
    logger.info("=" * 60)

    status = engine.get_status()
    portfolio = status['portfolio']

    logger.info(f"\n💵 Portfolio:")
    logger.info(f"  Initial: $100,000.00")
    logger.info(f"  Final:   ${portfolio['total_value']:,.2f}")
    logger.info(f"  Return:  {portfolio['total_pnl_percent']:.2f}%")
    logger.info(f"  Cash:    ${portfolio['cash']:,.2f}")

    if portfolio['positions']:
        logger.info(f"\n📈 Positions:")
        for pos in portfolio['positions']:
            logger.info(f"  {pos['symbol']}: {pos['quantity']:.4f} @ ${pos['average_price']:.2f}")
            logger.info(f"    PnL: ${pos['total_pnl']:.2f} ({pos['pnl_percent']:.2f}%)")
    else:
        logger.info(f"\n📈 Positions: None")

    # 显示订单
    orders = engine.get_orders()
    if orders:
        logger.info(f"\n📋 Orders ({len(orders)}):")
        for order in orders:
            logger.info(f"  {order['side']} {order['quantity']:.4f} {order['symbol']} @ ${order['price'] or 'MARKET'}")
            logger.info(f"    Status: {order['status']}")
    else:
        logger.info(f"\n📋 Orders: None")

    logger.info("\n" + "=" * 60)
    logger.info("✅ Real-time trading test completed successfully!")


if __name__ == '__main__':
    asyncio.run(main())
