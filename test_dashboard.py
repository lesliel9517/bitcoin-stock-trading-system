#!/usr/bin/env python3
"""Test dashboard with simulated data"""

import asyncio
from decimal import Decimal
from src.core.event_bus import EventBus
from src.data.feed import SimulatedDataFeed

async def test():
    print("Testing SimulatedDataFeed...")

    # Create event bus
    event_bus = EventBus()

    # Create data feed
    data_feed = SimulatedDataFeed(event_bus, update_interval=0.5)
    symbol = "BTCUSDT"

    # Subscribe
    await data_feed.subscribe(symbol)
    data_feed.set_price(symbol, Decimal('66886'))

    print(f"Starting data feed for {symbol}...")
    await data_feed.start()

    print("Starting event bus...")
    await event_bus.start()

    print("Waiting for events...")

    # Wait for some events
    for i in range(10):
        await asyncio.sleep(1)

        if not event_bus.queue.empty():
            event = await event_bus.queue.get()
            print(f"✓ Received event {i+1}: price={event.price}, volume={event.volume}")
        else:
            print(f"✗ No event yet ({i+1}/10)")

    print("\nStopping...")
    await data_feed.stop()
    await event_bus.stop()
    print("Done!")

if __name__ == "__main__":
    asyncio.run(test())
