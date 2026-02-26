#!/usr/bin/env python3
"""
使用模拟数据的回测示例

不需要网络连接，使用生成的模拟数据进行回测
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal
import pandas as pd
import numpy as np

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.backtest.engine import BacktestEngine
from src.strategies.examples.ma_cross import MACrossStrategy
from src.utils.logger import setup_logger, logger


def generate_mock_data(days=365, initial_price=50000):
    """生成模拟的BTC价格数据"""

    dates = pd.date_range(start='2024-01-01', periods=days, freq='D')

    # 生成随机价格走势（带趋势）
    np.random.seed(42)
    returns = np.random.normal(0.001, 0.02, days)  # 日收益率
    prices = [initial_price]

    for ret in returns[1:]:
        new_price = prices[-1] * (1 + ret)
        prices.append(new_price)

    # 创建OHLCV数据
    df = pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
        'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
        'close': prices,
        'volume': np.random.uniform(100, 1000, days)
    })

    df.set_index('timestamp', inplace=True)
    return df


async def run_backtest():
    """运行回测示例"""

    print("=" * 60)
    print("Bitcoin Trading System - 模拟数据回测示例")
    print("=" * 60)
    print()

    # 设置日志
    setup_logger(log_level="INFO")

    # 配置参数
    symbol = "BTC/USDT"
    initial_capital = Decimal("100000")

    print(f"📊 回测配置:")
    print(f"   交易对: {symbol} (模拟数据)")
    print(f"   时间范围: 2024-01-01 至 2024-12-31")
    print(f"   初始资金: ${initial_capital:,.2f}")
    print()

    # 1. 生成模拟数据
    print("📥 生成模拟历史数据...")
    df = generate_mock_data(days=365, initial_price=50000)
    print(f"✅ 成功生成 {len(df)} 条数据")
    print(f"   价格范围: ${df['close'].min():,.2f} - ${df['close'].max():,.2f}")
    print()

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
    print(f"   短期均线: {strategy_config['parameters']['short_window']} 天")
    print(f"   长期均线: {strategy_config['parameters']['long_window']} 天")
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
        exchange="simulator"
    )

    # 5. 显示结果
    print("=" * 60)
    print("📈 回测结果")
    print("=" * 60)
    print()

    metrics = results['metrics']
    portfolio = results['portfolio']

    print("💰 收益指标:")
    print(f"   初始资金: ${float(initial_capital):,.2f}")
    print(f"   最终资金: ${portfolio['total_value']:,.2f}")
    print(f"   总收益率: {metrics.get('total_return', 0):.2%}")
    print(f"   年化收益率: {metrics.get('annual_return', 0):.2%}")
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
    if metrics.get('avg_win', 0) != 0:
        print(f"   平均盈利: {metrics.get('avg_win', 0):.2%}")
    if metrics.get('avg_loss', 0) != 0:
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
    print("💡 说明:")
    print("   - 这是使用模拟数据的演示，不需要网络连接")
    print("   - 实际使用时可以连接真实交易所获取数据")
    print("   - 可以修改策略参数（short_window, long_window）来优化策略")
    print()
    print("📚 下一步:")
    print("   - 查看 README_USAGE.md 了解如何使用真实数据")
    print("   - 查看 CLAUDE.md 了解系统架构")
    print("   - 尝试开发自己的交易策略")
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
