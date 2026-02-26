#!/usr/bin/env python3
"""Test without Live rendering"""

import asyncio
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.core.event_bus import EventBus
from src.trading.portfolio import Portfolio
from src.data.feed import SimulatedDataFeed
from src.strategies.examples.adaptive_strategy import AdaptiveStrategy
from src.core.event import EventType

async def run_test():
    print("Starting test without Live rendering...\n")

    # Initialize components
    event_bus = EventBus()
    portfolio = Portfolio(initial_balance=Decimal(100000))

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
    print("✓ Event bus started")

    # Initialize data feed
    symbol = "BTCUSDT"
    data_feed = SimulatedDataFeed(event_bus, update_interval=0.5)
    await data_feed.subscribe(symbol)
    data_feed.set_price(symbol, Decimal('66886'))

    # Start data feed
    await data_feed.start()
    print("✓ Data feed started\n")

    await asyncio.sleep(0.5)

    # Event handler
    market_events = asyncio.Queue()

    async def handle_market_event(event):
        await market_events.put(event)

    event_bus.subscribe(EventType.MARKET, handle_market_event)
    print("✓ Event handler subscribed\n")

    print("Starting main loop (will run for 5 seconds)...\n")

    try:
        start_time = asyncio.get_event_loop().time()
        event_count = 0

        while asyncio.get_event_loop().time() - start_time < 5:
            try:
                event = await asyncio.wait_for(market_events.get(), timeout=0.1)
                event_count += 1

                price = float(event.price)

                if event_count % 2 == 0:
                    print(f"Event {event_count}: price=${price:,.2f}")

                # Update portfolio
                portfolio.update_prices({symbol: Decimal(str(price))})

                # Process strategy
                signal = await strategy.on_market_data(event)

                if signal:
                    print(f"  → Signal: {signal.signal_type}")

            except asyncio.TimeoutError:
                pass

        print(f"\n✓ Test complete! Processed {event_count} events")
        print(f"Final portfolio value: ${float(portfolio.get_total_value()):,.2f}")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await data_feed.stop()
        await event_bus.stop()

if __name__ == "__main__":
    asyncio.run(run_test())
