#!/usr/bin/env python3
"""
快速回测示例脚本

演示如何使用系统进行策略回测
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.backtest.engine import BacktestEngine
from src.strategies.examples.ma_cross import MACrossStrategy
from src.data.providers.binance import BinanceDataProvider
from src.data.storage import DataStorage
from src.utils.logger import setup_logger, logger


async def run_backtest():
    """运行回测示例"""

    print("=" * 60)
    print("Bitcoin & Stock Trading System - 回测示例")
    print("=" * 60)
    print()

    # 设置日志
    setup_logger(log_level="INFO")

    # 配置参数
    symbol = "BTC/USDT"
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2024, 12, 31)
    initial_capital = Decimal("100000")

    print(f"📊 回测配置:")
    print(f"   交易对: {symbol}")
    print(f"   时间范围: {start_date.date()} 至 {end_date.date()}")
    print(f"   初始资金: ${initial_capital:,.2f}")
    print()

    # 1. 获取历史数据
    print("📥 正在获取历史数据...")
    data_provider = BinanceDataProvider(testnet=True)

    try:
        # 从Binance获取数据
        df = await data_provider.get_historical_data(
            symbol=symbol,
            start=start_date,
            end=end_date,
            timeframe="1d"
        )

        if df.empty:
            print("❌ 未获取到数据，请检查网络连接或交易对符号")
            return

        print(f"✅ 成功获取 {len(df)} 条数据")
        print()

        # 保存数据到本地（可选）
        storage = DataStorage()
        storage.save_ohlcv(df, symbol, "binance", "1d")
        print("💾 数据已保存到本地数据库")
        print()

    except Exception as e:
        print(f"❌ 获取数据失败: {e}")
        print("💡 提示: 如果网络连接失败，可以使用本地已保存的数据")

        # 尝试从本地加载
        storage = DataStorage()
        df = storage.load_ohlcv(symbol, "binance", "1d", start_date, end_date)

        if df.empty:
            print("❌ 本地也没有数据，请先下载数据")
            return

        print(f"✅ 从本地加载了 {len(df)} 条数据")
        print()

    finally:
        await data_provider.close()

    # 2. 创建策略
    print("🎯 创建均线交叉策略...")
    strategy_config = {
        'symbols': [symbol],
        'timeframe': '1d',
        'parameters': {
            'short_window': 5,
            'long_window': 20,
            'ma_type': 'SMA'
        }
    }

    strategy = MACrossStrategy(
        strategy_id="ma_cross_backtest",
        config=strategy_config
    )
    print("✅ 策略创建成功")
    print()

    # 3. 创建回测引擎
    print("🚀 启动回测引擎...")
    backtest_engine = BacktestEngine(
        initial_capital=initial_capital,
        commission=Decimal("0.001"),  # 0.1% 手续费
        slippage=Decimal("0.0005")    # 0.05% 滑点
    )

    backtest_engine.set_strategy(strategy)

    # 4. 运行回测
    print("⏳ 正在运行回测...")
    print()

    results = await backtest_engine.run(
        data=df,
        symbol=symbol,
        exchange="binance"
    )

    # 5. 显示结果
    print("=" * 60)
    print("📈 回测结果")
    print("=" * 60)
    print()

    metrics = results['metrics']

    print("💰 收益指标:")
    print(f"   总收益率: {metrics.get('total_return', 0):.2%}")
    print(f"   年化收益率: {metrics.get('annual_return', 0):.2%}")
    print(f"   最终资金: ${results['portfolio']['total_value']:,.2f}")
    print()

    print("📊 风险指标:")
    print(f"   夏普比率: {metrics.get('sharpe_ratio', 0):.2f}")
    print(f"   最大回撤: {metrics.get('max_drawdown', 0):.2%}")
    print(f"   波动率: {metrics.get('volatility', 0):.2%}")
    print()

    print("🎲 交易统计:")
    print(f"   总交易次数: {metrics.get('total_trades', 0)}")
    print(f"   胜率: {metrics.get('win_rate', 0):.2%}")
    print(f"   盈亏比: {metrics.get('profit_factor', 0):.2f}")
    print(f"   平均盈利: {metrics.get('avg_win', 0):.2%}")
    print(f"   平均亏损: {metrics.get('avg_loss', 0):.2%}")
    print()

    # 6. 显示交易记录
    trades = results['trades']
    if trades:
        print("📝 最近5笔交易:")
        print("-" * 60)
        for trade in trades[-5:]:
            timestamp = trade['timestamp'].strftime('%Y-%m-%d')
            side = trade['side']
            price = trade['price']
            quantity = trade['quantity']
            value = trade['portfolio_value']
            print(f"   {timestamp} | {side:4s} | ${price:,.2f} | {quantity:.4f} | 总值: ${value:,.2f}")
        print()

    print("=" * 60)
    print("✅ 回测完成！")
    print("=" * 60)
    print()
    print("💡 提示:")
    print("   - 可以修改策略参数（short_window, long_window）来优化策略")
    print("   - 可以尝试不同的交易对和时间范围")
    print("   - 查看 README_USAGE.md 了解更多使用方法")
    print()


if __name__ == "__main__":
    try:
        asyncio.run(run_backtest())
    except KeyboardInterrupt:
        print("\n\n⚠️  回测已中断")
    except Exception as e:
        print(f"\n\n❌ 回测失败: {e}")
        import traceback
        traceback.print_exc()
