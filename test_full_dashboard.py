#!/usr/bin/env python3
"""Full dashboard test matching CLI code"""

import asyncio
import sys
from decimal import Decimal
from pathlib import Path

# Add project to path (same as CLI)
sys.path.insert(0, str(Path(__file__).parent))
examples_path = Path(__file__).parent / 'examples'
sys.path.insert(0, str(examples_path))

from src.core.event_bus import EventBus
from src.trading.portfolio import Portfolio
from src.data.feed import SimulatedDataFeed
from src.strategies.examples.adaptive_strategy import AdaptiveStrategy
from src.core.event import EventType
from professional_realtime import ProfessionalDashboard
from rich.console import Console
from rich.live import Live

async def run_dashboard():
    console = Console()
    console.print("[cyan]Starting full dashboard test...[/cyan]\n")

    # Initialize components
    event_bus = EventBus()
    portfolio = Portfolio(initial_balance=Decimal(100000))
    dashboard = ProfessionalDashboard(max_points=100)

    # Initialize strategy
    strategy_config = {
        'parameters': {
            'ma_short': 10,
            'ma_long': 30,
            'volatility_window': 20,
            'trend_window': 50
        }
    }
    strategy = AdaptiveStrategy('adaptive_live', strategy_config)
    strategy.event_bus = event_bus
    strategy.start()

    # Start event bus FIRST
    await event_bus.start()
    console.print("[green]✓ Event bus started[/green]")

    # Initialize data feed
    symbol = "BTCUSDT"
    data_feed = SimulatedDataFeed(event_bus, update_interval=0.5)
    await data_feed.subscribe(symbol)
    data_feed.set_price(symbol, Decimal('66886'))
    console.print("[yellow]Using simulated data[/yellow]")

    # Start data feed AFTER event bus
    await data_feed.start()
    console.print("[green]✓ Data feed started[/green]\n")

    await asyncio.sleep(0.5)

    # Trading state
    position = Decimal(0)
    entry_price = None

    # Event handler
    market_events = asyncio.Queue()

    async def handle_market_event(event):
        await market_events.put(event)

    # Subscribe to market events
    event_bus.subscribe(EventType.MARKET, handle_market_event)
    console.print("[green]✓ Event handler subscribed[/green]\n")

    console.print("[yellow]Starting main loop (will run for 5 seconds)...[/yellow]\n")

    with Live(dashboard.render(), refresh_per_second=2, console=console) as live:
        try:
            start_time = asyncio.get_event_loop().time()
            event_count = 0

            console.print(f"[cyan]Loop started at {start_time}[/cyan]")

            while asyncio.get_event_loop().time() - start_time < 5:
                try:
                    event = await asyncio.wait_for(market_events.get(), timeout=0.1)
                    event_count += 1

                    if event_count % 5 == 0:
                        console.print(f"[dim]Processed {event_count} events...[/dim]")

                    price = float(event.price)
                    volume = float(event.volume) if event.volume else 0

                    # Update price
                    dashboard.update_price(price, volume)

                    # Update portfolio
                    portfolio.update_prices({symbol: Decimal(str(price))})

                    # Process strategy
                    signal = await strategy.on_market_data(event)

                    # Update stats
                    position_status = f"持仓 {float(position):.4f} BTC" if position > 0 else "空仓"
                    dashboard.update_stats(
                        float(portfolio.get_total_value()),
                        position_status,
                        strategy.market_regime,
                        strategy.volatility_regime
                    )

                    # Update display
                    live.update(dashboard.render())

                except asyncio.TimeoutError:
                    # No event, just update display
                    live.update(dashboard.render())

            console.print(f"\n[green]✓ Test complete! Processed {event_count} events[/green]")

        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted[/yellow]")
        finally:
            await data_feed.stop()
            await event_bus.stop()

if __name__ == "__main__":
    try:
        asyncio.run(run_dashboard())
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
