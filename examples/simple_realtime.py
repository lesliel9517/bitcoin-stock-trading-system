"""
Simple Real-time Trading Visualization

Displays real-time trading information in terminal
"""

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
import pandas as pd
import yfinance as yf
import os
import sys

from src.backtest.engine import BacktestEngine
from src.strategies.examples.adaptive_strategy import AdaptiveStrategy
from src.core.types import OrderSide


def clear_screen():
    """Clear terminal screen"""
    os.system('clear' if os.name != 'nt' else 'cls')


def print_header():
    """Print header"""
    print("=" * 80)
    print("🚀 实时交易监控系统".center(80))
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}".center(80))
    print("=" * 80)


def print_chart(prices, trades):
    """Print simple ASCII chart"""
    if len(prices) < 2:
        return

    # Get last 50 prices
    recent_prices = prices[-50:]

    # Normalize to chart height
    min_price = min(recent_prices)
    max_price = max(recent_prices)
    price_range = max_price - min_price if max_price > min_price else 1

    chart_height = 15
    chart_width = len(recent_prices)

    print("\n📈 价格走势图:")
    print("-" * 60)

    # Draw chart
    for row in range(chart_height, -1, -1):
        line = ""
        for i, price in enumerate(recent_prices):
            normalized = int((price - min_price) / price_range * chart_height)

            # Check if there's a trade at this position
            trade_marker = ""
            for trade in trades:
                if trade['index'] == len(prices) - len(recent_prices) + i:
                    if trade['side'] == 'buy':
                        trade_marker = "🟢"
                    else:
                        trade_marker = "🔴"
                    break

            if normalized == row:
                if trade_marker:
                    line += trade_marker
                else:
                    line += "●"
            elif normalized > row:
                line += "│"
            else:
                line += " "

        # Add price label
        price_at_row = min_price + (price_range * row / chart_height)
        print(f"${price_at_row:>8,.0f} {line}")

    print("-" * 60)


def print_stats(stats):
    """Print statistics"""
    print("\n📊 实时数据:")
    print("-" * 60)

    # Current price
    print(f"当前价格: ${stats['price']:>12,.2f}")

    # Equity
    print(f"账户总值: ${stats['equity']:>12,.2f}")

    # PnL
    pnl_sign = "+" if stats['pnl'] >= 0 else ""
    pnl_color = "\033[92m" if stats['pnl'] >= 0 else "\033[91m"  # Green or Red
    reset_color = "\033[0m"
    print(f"总盈亏:   {pnl_color}{pnl_sign}${stats['pnl']:>11,.2f} ({pnl_sign}{stats['pnl_pct']:.2f}%){reset_color}")

    # Trades
    print(f"交易次数: {stats['trades']:>12}")

    # Position
    pos_color = "\033[92m" if "持仓" in stats['position'] else "\033[90m"
    print(f"持仓状态: {pos_color}{stats['position']:>12}{reset_color}")

    print("-" * 60)


def print_recent_trade(trades):
    """Print recent trade"""
    if len(trades) > 0:
        trade = trades[-1]
        side_text = "买入" if trade['side'] == 'buy' else "卖出"
        side_color = "\033[92m" if trade['side'] == 'buy' else "\033[91m"
        reset_color = "\033[0m"

        print(f"\n💼 最近交易: {side_color}{side_text}{reset_color} @ ${trade['price']:,.2f}", end="")

        if 'pnl_pct' in trade and trade['pnl_pct'] != 0:
            pnl_sign = "+" if trade['pnl_pct'] > 0 else ""
            pnl_color = "\033[92m" if trade['pnl_pct'] > 0 else "\033[91m"
            print(f" | 盈亏: {pnl_color}{pnl_sign}{trade['pnl_pct']:.2f}%{reset_color}")
        else:
            print()


async def main():
    """Run real-time trading visualization"""

    print("\n初始化系统...\n")

    # Download data
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

    print(f"✅ 已下载 {len(data)} 天数据")
    print("⏳ 开始模拟交易...\n")

    await asyncio.sleep(2)

    # Initialize engine
    engine = BacktestEngine(
        initial_capital=Decimal(100000),
        commission=Decimal("0.001"),
        slippage=Decimal("0.0005")
    )

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

    # Trading data
    prices = []
    trades = []
    position = Decimal(0)
    entry_price = None
    initial_capital = 100000

    # Run simulation
    for i in range(len(data)):
        row = data.iloc[i]
        timestamp = row.name if isinstance(row.name, datetime) else datetime.now()
        price = Decimal(str(row['close']))

        # Update portfolio
        engine.portfolio.update_prices({symbol: price})
        current_equity = engine.portfolio.get_total_value()

        # Store price
        prices.append(float(price))

        # Position status
        position_status = f"持仓 {float(position):.4f} BTC" if position > 0 else "空仓"

        # Calculate stats
        pnl = float(current_equity - engine.initial_capital)
        pnl_pct = (pnl / initial_capital) * 100

        stats = {
            'price': float(price),
            'equity': float(current_equity),
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'trades': len(trades),
            'position': position_status
        }

        # Generate signals
        temp_data = data.iloc[:i+1].copy()
        engine.strategy.update_data(symbol, temp_data)

        if len(temp_data) >= 30:
            data_with_signals = engine.strategy.calculate_indicators(temp_data)

            if len(data_with_signals) >= 2:
                current = data_with_signals.iloc[-1]
                previous = data_with_signals.iloc[-2]

                # Buy signal
                if (previous['ma_short'] <= previous['ma_long'] and
                    current['ma_short'] > current['ma_long'] and
                    position == 0):

                    quantity = engine._calculate_position_size(price)
                    if quantity > 0:
                        engine._execute_trade(symbol, OrderSide.BUY, quantity, price, timestamp, 'yfinance')
                        position = quantity
                        entry_price = price

                        trades.append({
                            'index': len(prices) - 1,
                            'side': 'buy',
                            'price': float(price),
                            'pnl_pct': 0
                        })

                # Sell signal
                elif (previous['ma_short'] >= previous['ma_long'] and
                      current['ma_short'] < current['ma_long'] and
                      position > 0):

                    pnl_pct = float((price - entry_price) / entry_price * 100) if entry_price else 0

                    engine._execute_trade(symbol, OrderSide.SELL, position, price, timestamp, 'yfinance')

                    trades.append({
                        'index': len(prices) - 1,
                        'side': 'sell',
                        'price': float(price),
                        'pnl_pct': pnl_pct
                    })

                    position = Decimal(0)
                    entry_price = None

        # Update display every iteration
        clear_screen()
        print_header()
        print_chart(prices, trades)
        print_stats(stats)
        print_recent_trade(trades)
        print(f"\n进度: {i+1}/{len(data)}")

        # Simulate real-time delay
        await asyncio.sleep(0.5)

    # Close position if needed
    if position > 0:
        final_price = Decimal(str(data.iloc[-1]['close']))
        final_timestamp = data.index[-1]
        engine._execute_trade(symbol, OrderSide.SELL, position, final_price, final_timestamp, 'yfinance')

    # Final summary
    final_equity = engine.portfolio.get_total_value()
    final_pnl = float(final_equity - engine.initial_capital)
    final_return = (final_pnl / initial_capital) * 100

    print("\n" + "=" * 80)
    print("交易完成".center(80))
    print("=" * 80)
    print(f"\n初始资金: ${initial_capital:,.2f}")
    print(f"最终资金: ${float(final_equity):,.2f}")

    pnl_sign = "+" if final_pnl >= 0 else ""
    pnl_color = "\033[92m" if final_pnl >= 0 else "\033[91m"
    reset_color = "\033[0m"
    print(f"总收益: {pnl_color}{pnl_sign}${final_pnl:,.2f} ({pnl_sign}{final_return:.2f}%){reset_color}")
    print(f"交易次数: {len(engine.trades)}\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n程序已停止")
