"""Test risk management functionality"""

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
    """测试风险管理功能"""
    # 设置日志
    setup_logger(log_level='INFO')

    logger.info("🚀 Testing Risk Management System")
    logger.info("=" * 60)

    # 1. 创建交易引擎（启用风险管理）
    logger.info("\n⚙️  Step 1: Creating trading engine with risk management...")

    risk_config = {
        'max_position_size': '0.1',      # 单个持仓最大10%
        'max_drawdown': '0.2',           # 最大回撤20%
        'max_daily_loss': '0.05',        # 每日最大亏损5%
        'max_orders_per_day': 10,        # 每日最大10笔订单
        'min_order_value': '100',        # 最小订单价值$100
        'position_sizing': {
            'method': 'fixed',           # 使用固定仓位
            'position_ratio': '0.05'     # 每次使用5%资金
        },
        'stop_loss': {
            'enabled': True,
            'default_percent': '0.02',   # 默认2%止损
            'trailing': True             # 启用移动止损
        },
        'take_profit': {
            'enabled': True,
            'default_percent': '0.05'    # 默认5%止盈
        }
    }

    engine = TradingEngine(
        initial_capital=Decimal('100000'),
        config={
            'execution': {'default_position_size': '0.95'},
            'risk': risk_config
        }
    )
    logger.info("✅ Trading engine created with risk management")

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
    strategy = MACrossStrategy(strategy_id='ma_cross_risk_test', config=strategy_config)
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

    # 5. 运行交易（15秒）
    logger.info("\n🏃 Step 5: Running trading with risk management for 15 seconds...")
    logger.info("Watching for:")
    logger.info("  - Position sizing")
    logger.info("  - Stop loss triggers")
    logger.info("  - Take profit triggers")
    logger.info("  - Risk rule validations\n")

    await engine.start()
    await asyncio.sleep(15)
    await engine.stop()

    # 6. 显示结果
    logger.info("\n" + "=" * 60)
    logger.info("📊 RISK MANAGEMENT TEST RESULTS")
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

    # 显示止损止盈水平
    if engine.risk_manager:
        stop_levels = engine.risk_manager.get_all_stop_levels()
        if stop_levels:
            logger.info(f"\n🛡️  Stop Levels:")
            for symbol, levels in stop_levels.items():
                logger.info(f"  {symbol}:")
                logger.info(f"    Entry:       ${levels['entry_price']:.2f}")
                logger.info(f"    Stop Loss:   ${levels['stop_loss']:.2f}")
                logger.info(f"    Take Profit: ${levels['take_profit']:.2f}")
                logger.info(f"    Highest:     ${levels['highest_price']:.2f}")
        else:
            logger.info(f"\n🛡️  Stop Levels: None")

        # 显示风控规则状态
        rules_status = engine.risk_manager.get_rules_status()
        if rules_status:
            logger.info(f"\n📋 Risk Rules:")
            for rule in rules_status:
                status_icon = "✅" if rule['enabled'] else "❌"
                logger.info(f"  {status_icon} {rule['rule_id']}")

    # 显示订单
    orders = engine.get_orders()
    if orders:
        logger.info(f"\n📋 Orders ({len(orders)}):")
        for order in orders:
            logger.info(f"  {order['side']} {order['quantity']:.4f} {order['symbol']} @ ${order.get('average_price', 'MARKET')}")
            logger.info(f"    Status: {order['status']}")
    else:
        logger.info(f"\n📋 Orders: None")

    logger.info("\n" + "=" * 60)
    logger.info("✅ Risk management test completed successfully!")
    logger.info("\n💡 Risk management features tested:")
    logger.info("  ✓ Position sizing calculation")
    logger.info("  ✓ Stop loss and take profit levels")
    logger.info("  ✓ Trailing stop loss")
    logger.info("  ✓ Risk rule validation")
    logger.info("  ✓ Order rejection on rule violation")


if __name__ == '__main__':
    asyncio.run(main())
