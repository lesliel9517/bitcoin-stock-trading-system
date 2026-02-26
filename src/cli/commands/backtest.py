"""CLI commands for backtesting"""

import click
import asyncio
from datetime import datetime
from decimal import Decimal
import pandas as pd
from pathlib import Path

from ...backtest.engine import BacktestEngine
from ...strategies.examples.ma_cross import MACrossStrategy
from ...utils.config import load_config
from ...utils.logger import logger
from ...data.storage import DataStorage


@click.group()
def backtest():
    """Backtest related commands"""
    pass


@backtest.command()
@click.option('--strategy', required=True, help='Strategy name (e.g., ma_cross)')
@click.option('--symbol', required=True, help='Trading pair symbol (e.g., BTC-USD)')
@click.option('--start', required=True, help='Start date (YYYY-MM-DD)')
@click.option('--end', required=True, help='End date (YYYY-MM-DD)')
@click.option('--timeframe', default='1d', help='Timeframe (default: 1d)')
@click.option('--capital', default=100000, type=float, help='Initial capital (default: 100000)')
@click.option('--commission', default=0.001, type=float, help='Commission rate (default: 0.001)')
@click.option('--output', help='Output file path')
def start(strategy, symbol, start, end, timeframe, capital, commission, output):
    """Start backtest"""
    click.echo(f"Starting backtest for {symbol} with {strategy} strategy")
    click.echo(f"Period: {start} to {end}")
    click.echo(f"Initial capital: ${capital:,.2f}")

    try:
        # Parse dates
        start_date = datetime.strptime(start, '%Y-%m-%d')
        end_date = datetime.strptime(end, '%Y-%m-%d')

        # Load strategy configuration
        strategy_config = load_config(f'strategies/{strategy}')

        # Create backtest engine
        engine = BacktestEngine(
            initial_capital=Decimal(str(capital)),
            commission=Decimal(str(commission))
        )

        # Create strategy instance
        if strategy == 'ma_cross':
            strategy_obj = MACrossStrategy(strategy_id=strategy, config=strategy_config)
        else:
            click.echo(f"ERROR: Unknown strategy: {strategy}", err=True)
            return

        engine.set_strategy(strategy_obj)

        # Load historical data
        click.echo(f"Loading historical data...")
        storage = DataStorage()
        data = storage.load_ohlcv(
            symbol=symbol,
            exchange='binance',
            timeframe=timeframe,
            start=start_date,
            end=end_date
        )

        if data.empty:
            click.echo(f"ERROR: No data found for {symbol}. Please download data first.", err=True)
            click.echo(f"Tip: Use 'btc-trade data download --symbol {symbol}' to download data")
            return

        click.echo(f"Loaded {len(data)} data points")

        # Run backtest
        click.echo(f"Running backtest...")
        results = asyncio.run(engine.run(data, symbol, exchange='binance'))

        # Display results
        metrics = results['metrics']
        click.echo("\n" + "="*60)
        click.echo("BACKTEST RESULTS")
        click.echo("="*60)

        click.echo(f"\nCapital:")
        click.echo(f"  Initial: ${metrics['initial_capital']:,.2f}")
        click.echo(f"  Final:   ${metrics['final_equity']:,.2f}")
        click.echo(f"  Return:  {metrics['total_return_pct']:.2f}%")
        click.echo(f"  Annual:  {metrics['annual_return_pct']:.2f}%")

        click.echo(f"\nPerformance:")
        click.echo(f"  Max Drawdown:  {metrics['max_drawdown_pct']:.2f}%")
        click.echo(f"  Sharpe Ratio:  {metrics['sharpe_ratio']:.2f}")
        click.echo(f"  Sortino Ratio: {metrics['sortino_ratio']:.2f}")

        click.echo(f"\nTrading:")
        click.echo(f"  Total Trades:   {metrics['total_trades']}")
        click.echo(f"  Winning Trades: {metrics['winning_trades']}")
        click.echo(f"  Losing Trades:  {metrics['losing_trades']}")
        click.echo(f"  Win Rate:       {metrics['win_rate']:.2f}%")
        click.echo(f"  Profit Factor:  {metrics['profit_factor']:.2f}")

        # Save results
        if output:
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Save as CSV
            results['equity_curve'].to_csv(output_path)
            click.echo(f"\nResults saved to: {output_path}")

        click.echo("\n" + "="*60)

    except Exception as e:
        click.echo(f"ERROR: {e}", err=True)
        logger.error(f"Backtest failed: {e}", exc_info=True)


@backtest.command()
def list():
    """List all backtest results"""
    click.echo("Backtest Results:")
    click.echo("(Feature coming soon)")


@backtest.command()
@click.option('--id', required=True, help='Backtest ID')
def report(id):
    """View backtest report"""
    click.echo(f"Backtest Report for ID: {id}")
    click.echo("(Feature coming soon)")
