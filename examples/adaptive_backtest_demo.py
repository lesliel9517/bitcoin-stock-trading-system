"""
Adaptive Strategy Backtest Demo

Demonstrates:
1. Dynamic adaptive trading strategy
2. Trade record serialization to database
3. Beautiful interactive visualization with K-line charts
"""

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
import pandas as pd
import yfinance as yf

from src.backtest.engine import BacktestEngine
from src.strategies.examples.adaptive_strategy import AdaptiveStrategy
from src.data.storage import DataStorage
from src.utils.logger import logger


async def main():
    """Run adaptive strategy backtest demo"""

    print("\n" + "="*80)
    print("🚀 Adaptive Trading Strategy Backtest Demo")
    print("="*80 + "\n")

    # 1. Download market data
    print("📊 Downloading BTC-USD market data...")
    symbol = "BTC-USD"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)  # 6 months

    ticker = yf.Ticker(symbol)
    data = ticker.history(start=start_date, end=end_date, interval="1d")

    if data.empty:
        print("❌ Failed to download data")
        return

    # Rename columns to match our format
    data.columns = [col.lower() for col in data.columns]
    data = data[['open', 'high', 'low', 'close', 'volume']]

    print(f"✅ Downloaded {len(data)} days of data")
    print(f"   Period: {data.index[0].date()} to {data.index[-1].date()}")
    print(f"   Price range: ${data['close'].min():.2f} - ${data['close'].max():.2f}\n")

    # 2. Initialize backtest engine with storage
    print("⚙️  Initializing backtest engine...")
    storage = DataStorage()
    engine = BacktestEngine(
        initial_capital=Decimal(100000),
        commission=Decimal("0.001"),  # 0.1%
        slippage=Decimal("0.0005"),   # 0.05%
        storage=storage
    )

    # 3. Create adaptive strategy
    print("🧠 Creating adaptive strategy...")
    strategy_config = {
        'parameters': {
            'ma_short': 10,
            'ma_long': 30,
            'volatility_window': 20,
            'trend_window': 50
        }
    }
    strategy = AdaptiveStrategy('adaptive_btc', strategy_config)
    engine.set_strategy(strategy)

    print("   Strategy features:")
    print("   • Dynamic MA period adjustment based on trend")
    print("   • Adaptive stop-loss/take-profit based on volatility")
    print("   • Market regime detection (trending/ranging)")
    print("   • Position sizing based on market conditions\n")

    # 4. Run backtest
    print("🔄 Running backtest...")
    results = await engine.run(data, symbol=symbol, exchange="yfinance")

    # 5. Display results
    print("\n" + "="*80)
    print("📈 BACKTEST RESULTS")
    print("="*80 + "\n")

    metrics = results['metrics']
    portfolio = results['portfolio']

    print(f"Session ID: {results['session_id']}\n")

    print("💰 Portfolio Performance:")
    print(f"   Initial Capital:  ${portfolio['initial_balance']:,.2f}")
    print(f"   Final Capital:    ${portfolio['total_value']:,.2f}")
    print(f"   Total Return:     {metrics.get('total_return', 0):.2f}%")
    print(f"   Total P&L:        ${portfolio['total_pnl']:,.2f}\n")

    print("📊 Risk Metrics:")
    print(f"   Sharpe Ratio:     {metrics.get('sharpe_ratio', 0):.2f}")
    print(f"   Max Drawdown:     {metrics.get('max_drawdown', 0):.2f}%")
    print(f"   Volatility:       {metrics.get('volatility', 0):.2f}%\n")

    print("🎯 Trading Statistics:")
    print(f"   Total Trades:     {len(results['trades'])}")
    print(f"   Win Rate:         {metrics.get('win_rate', 0):.2f}%")
    print(f"   Profit Factor:    {metrics.get('profit_factor', 0):.2f}")
    print(f"   Avg Trade:        {metrics.get('avg_trade_pnl', 0):.2f}%\n")

    # 6. Show trade history
    if results['trades']:
        print("📝 Recent Trades (last 5):")
        trades_df = pd.DataFrame(results['trades'])
        recent_trades = trades_df.tail(5)

        for _, trade in recent_trades.iterrows():
            side_emoji = "🟢" if trade['side'] == 'buy' else "🔴"
            print(f"   {side_emoji} {trade['timestamp'].strftime('%Y-%m-%d')} | "
                  f"{trade['side'].upper():4s} | "
                  f"${trade['price']:,.2f} | "
                  f"Qty: {trade['quantity']:.4f}")
        print()

    # 7. Database storage info
    print("💾 Data Storage:")
    print(f"   ✅ Trades saved to database")
    print(f"   ✅ Equity curve saved to database")
    print(f"   ✅ Session metadata saved\n")

    # 8. Visualization
    if results.get('report_path'):
        print("📊 Visualization:")
        print(f"   ✅ Interactive report generated")
        print(f"   📁 Location: {results['report_path']}")
        print(f"   🌐 Open in browser to view:\n")
        print(f"      file://{results['report_path']}\n")

    # 9. Export options
    print("💾 Export Options:")
    session_id = results['session_id']

    # Export trades to CSV
    trades_csv = f"./data/exports/trades_{session_id}.csv"
    storage.export_trades_csv(session_id, trades_csv)
    print(f"   ✅ Trades exported: {trades_csv}")

    # Export equity curve to CSV
    equity_csv = f"./data/exports/equity_{session_id}.csv"
    storage.export_equity_csv(session_id, equity_csv)
    print(f"   ✅ Equity curve exported: {equity_csv}\n")

    # 10. Show recent sessions
    print("📚 Recent Backtest Sessions:")
    sessions = storage.get_backtest_sessions(limit=5)
    if not sessions.empty:
        for _, session in sessions.iterrows():
            print(f"   • {session['strategy']:15s} | "
                  f"{session['symbol']:10s} | "
                  f"Return: {session['total_return']:6.2f}% | "
                  f"{session['created_at'].strftime('%Y-%m-%d %H:%M')}")

    print("\n" + "="*80)
    print("✅ Demo completed successfully!")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
