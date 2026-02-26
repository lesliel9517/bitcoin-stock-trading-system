"""
Real-time Trading Visualization Demo

Demonstrates live trading with real-time chart updates
"""

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
import pandas as pd
import yfinance as yf
import webbrowser
import time

from src.backtest.engine import BacktestEngine
from src.strategies.examples.adaptive_strategy import AdaptiveStrategy
from src.monitor.realtime_viz import RealtimeVisualizer
from src.utils.logger import logger


async def main():
    """Run real-time trading visualization demo"""

    print("\n" + "="*80)
    print("🚀 实时交易可视化演示")
    print("="*80 + "\n")

    # 1. Download market data
    print("📊 下载市场数据...")
    symbol = "BTC-USD"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)

    ticker = yf.Ticker(symbol)
    data = ticker.history(start=start_date, end=end_date, interval="1d")

    if data.empty:
        print("❌ 数据下载失败")
        return

    data.columns = [col.lower() for col in data.columns]
    data = data[['open', 'high', 'low', 'close', 'volume']]

    print(f"✅ 已下载 {len(data)} 天数据\n")

    # 2. Initialize real-time visualizer
    print("📈 初始化实时可视化...")
    visualizer = RealtimeVisualizer()

    # Open browser
    viz_url = visualizer.get_url()
    print(f"🌐 打开浏览器: {viz_url}\n")
    webbrowser.open(viz_url)

    await asyncio.sleep(2)  # Wait for browser to open

    # 3. Initialize backtest engine
    print("⚙️  初始化交易引擎...")
    engine = BacktestEngine(
        initial_capital=Decimal(100000),
        commission=Decimal("0.001"),
        slippage=Decimal("0.0005")
    )

    # 4. Create strategy
    strategy_config = {
        'parameters': {
            'ma_short': 10,
            'ma_long': 30,
            'volatility_window': 20,
            'trend_window': 50
        }
    }
    strategy = AdaptiveStrategy('adaptive_realtime', strategy_config)
    engine.set_strategy(strategy)

    print("🔄 开始模拟实时交易...\n")
    print("提示: 图表会自动刷新，请在浏览器中查看实时更新\n")

    # 5. Simulate real-time trading
    initial_capital = float(engine.initial_capital)
    position = Decimal(0)
    entry_price = None

    for i in range(len(data)):
        row = data.iloc[i]
        timestamp = row.name if isinstance(row.name, datetime) else datetime.now()
        price = Decimal(str(row['close']))

        # Update visualizer with current price
        visualizer.update_price(timestamp, price)

        # Update portfolio prices
        engine.portfolio.update_prices({symbol: price})
        current_equity = engine.portfolio.get_total_value()

        # Update equity curve
        visualizer.update_equity(timestamp, current_equity)

        # Calculate indicators and generate signals
        temp_data = data.iloc[:i+1].copy()
        engine.strategy.update_data(symbol, temp_data)

        if len(temp_data) >= 30:
            data_with_signals = engine.strategy.calculate_indicators(temp_data)

            if len(data_with_signals) >= 2:
                current = data_with_signals.iloc[-1]
                previous = data_with_signals.iloc[-2]

                # Check for buy signal
                if (previous['ma_short'] <= previous['ma_long'] and
                    current['ma_short'] > current['ma_long'] and
                    position == 0):

                    # Buy
                    from src.core.types import OrderSide
                    quantity = engine._calculate_position_size(price)
                    if quantity > 0:
                        engine._execute_trade(symbol, OrderSide.BUY, quantity, price, timestamp, 'yfinance')
                        position = quantity
                        entry_price = price

                        visualizer.add_trade(timestamp, 'buy', price, quantity)
                        visualizer.add_signal(timestamp, 'buy', price)

                        print(f"🟢 {timestamp.strftime('%Y-%m-%d')} | 买入 @ ${price:,.2f} | 数量: {quantity:.4f}")

                # Check for sell signal
                elif (previous['ma_short'] >= previous['ma_long'] and
                      current['ma_short'] < current['ma_long'] and
                      position > 0):

                    # Sell
                    from src.core.types import OrderSide
                    engine._execute_trade(symbol, OrderSide.SELL, position, price, timestamp, 'yfinance')

                    pnl = (price - entry_price) / entry_price * 100 if entry_price else 0

                    visualizer.add_trade(timestamp, 'sell', price, position)
                    visualizer.add_signal(timestamp, 'sell', price)

                    print(f"🔴 {timestamp.strftime('%Y-%m-%d')} | 卖出 @ ${price:,.2f} | 盈亏: {pnl:.2f}%")

                    position = Decimal(0)
                    entry_price = None

        # Update statistics
        total_pnl = float(current_equity - engine.initial_capital)
        return_pct = (total_pnl / initial_capital) * 100

        stats = {
            'current_price': float(price),
            'total_equity': float(current_equity),
            'total_pnl': total_pnl,
            'return_pct': return_pct,
            'total_trades': len(engine.trades),
            'position_status': f'持仓 {float(position):.4f} BTC' if position > 0 else '空仓'
        }

        visualizer.update_stats(stats)
        visualizer.save()

        # Simulate real-time delay
        await asyncio.sleep(0.5)  # 0.5 second per data point

        # Print progress
        if (i + 1) % 10 == 0:
            print(f"📊 进度: {i+1}/{len(data)} | 当前价格: ${price:,.2f} | 账户: ${current_equity:,.2f}")

    # Close any open position
    if position > 0:
        final_price = Decimal(str(data.iloc[-1]['close']))
        final_timestamp = data.index[-1]
        from src.core.types import OrderSide
        engine._execute_trade(symbol, OrderSide.SELL, position, final_price, final_timestamp, 'yfinance')
        visualizer.add_trade(final_timestamp, 'sell', final_price, position)

    # Final update
    final_equity = engine.portfolio.get_total_value()
    final_pnl = float(final_equity - engine.initial_capital)
    final_return = (final_pnl / initial_capital) * 100

    stats = {
        'current_price': float(data.iloc[-1]['close']),
        'total_equity': float(final_equity),
        'total_pnl': final_pnl,
        'return_pct': final_return,
        'total_trades': len(engine.trades),
        'position_status': '空仓'
    }
    visualizer.update_stats(stats)
    visualizer.save()

    # Print final results
    print("\n" + "="*80)
    print("📈 交易完成")
    print("="*80 + "\n")
    print(f"💰 初始资金: ${initial_capital:,.2f}")
    print(f"💰 最终资金: ${final_equity:,.2f}")
    print(f"📊 总收益: ${final_pnl:,.2f} ({final_return:.2f}%)")
    print(f"🎯 交易次数: {len(engine.trades)}")
    print(f"\n🌐 实时图表仍在浏览器中显示")
    print(f"   {viz_url}\n")

    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
