#!/usr/bin/env python3
"""Simple dashboard test"""

import asyncio
import sys
from decimal import Decimal
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / 'examples'))

from src.core.event_bus import EventBus
from src.data.feed import SimulatedDataFeed
from src.core.event import EventType
from professional_realtime import ProfessionalDashboard
from rich.console import Console
from rich.live import Live

async def main():
    console = Console()
    console.print("[cyan]Starting simple dashboard test...[/cyan]\n")

    # Create components
    event_bus = EventBus()
    dashboard = ProfessionalDashboard(max_points=100)

    # Start event bus
    await event_bus.start()
    console.print("[green]✓ Event bus started[/green]")

    # Create data feed
    data_feed = SimulatedDataFeed(event_bus, update_interval=0.5)
    symbol = "BTCUSDT"
    await data_feed.subscribe(symbol)
    data_feed.set_price(symbol, Decimal('66886'))

    # Start data feed
    await data_feed.start()
    console.print("[green]✓ Data feed started[/green]")

    # Event handler
    market_events = asyncio.Queue()

    async def handle_market_event(event):
        await market_events.put(event)

    event_bus.subscribe(EventType.MARKET, handle_market_event)
    console.print("[green]✓ Event handler subscribed[/green]\n")

    # Test receiving events
    console.print("[yellow]Waiting for events...[/yellow]")

    try:
        for i in range(5):
            event = await asyncio.wait_for(market_events.get(), timeout=2.0)
            price = float(event.price)
            dashboard.update_price(price, 0)
            console.print(f"[green]✓ Event {i+1}: price=${price:,.2f}[/green]")
    except asyncio.TimeoutError:
        console.print("[red]✗ Timeout waiting for events[/red]")

    console.print("\n[cyan]Test complete![/cyan]")

    await data_feed.stop()
    await event_bus.stop()

if __name__ == "__main__":
    asyncio.run(main())
