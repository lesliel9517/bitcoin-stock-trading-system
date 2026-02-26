#!/usr/bin/env python3
"""Complete dashboard test - run this in your terminal"""

import asyncio
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / 'examples'))

from src.core.event_bus import EventBus
from src.trading.portfolio import Portfolio
from src.data.feed import SimulatedDataFeed
from src.strategies.examples.adaptive_strategy import AdaptiveStrategy
from src.core.event import EventType
from professional_realtime import ProfessionalDashboard
from rich.console import Console
from rich.live import Live

async def main():
    console = Console()
    console.print("[bold cyan]Complete Dashboard Test[/bold cyan]\n")

    # Initialize
    event_bus = EventBus()
    portfolio = Portfolio(initial_balance=Decimal(100000))
    dashboard = ProfessionalDashboard(max_points=100)

    # Strategy
    strategy_config = {
        'parameters': {'ma_short': 10, 'ma_long': 30, 'volatility_window': 20, 'trend_window': 50}
    }
    strategy = AdaptiveStrategy('test', strategy_config)
    strategy.event_bus = event_bus
    strategy.start()

    # Start event bus
    await event_bus.start()

    # Data feed
    symbol = "BTCUSDT"
    data_feed = SimulatedDataFeed(event_bus, update_interval=0.3)
    await data_feed.subscribe(symbol)
    data_feed.set_price(symbol, Decimal('66886'))
    await data_feed.start()

    # Event handler
    market_events = asyncio.Queue()
    async def handle_event(e):
        await market_events.put(e)
    event_bus.subscribe(EventType.MARKET, handle_event)

    # Initialize dashboard with data
    dashboard.update_price(66886.0, 100.0)
    dashboard.update_stats(100000.0, "空仓", "unknown", "normal")

    await asyncio.sleep(0.5)

    console.print("[green]Starting dashboard (Ctrl+C to stop)...[/green]\n")

    position = Decimal(0)
    entry_price = None

    with Live(dashboard.render(), refresh_per_second=4, console=console) as live:
        try:
            event_count = 0
            while True:
                try:
                    event = await asyncio.wait_for(market_events.get(), timeout=0.1)
                    event_count += 1

                    price = float(event.price)
                    dashboard.update_price(price, float(event.volume or 0))

                    portfolio.update_prices({symbol: Decimal(str(price))})
                    signal = await strategy.on_market_data(event)

                    # Handle signals
                    if signal and signal.signal_type == 'buy' and position == 0:
                        quantity = (portfolio.cash * Decimal("0.95")) / Decimal(str(price))
                        portfolio.update_position(symbol, quantity, Decimal(str(price)))
                        position = quantity
                        entry_price = Decimal(str(price))
                        dashboard.add_trade('buy', price)

                    elif signal and signal.signal_type == 'sell' and position > 0:
                        portfolio.update_position(symbol, -position, Decimal(str(price)))
                        dashboard.add_trade('sell', price, float(entry_price) if entry_price else None)
                        position = Decimal(0)
                        entry_price = None

                    # Update MA
                    if symbol in strategy._data_cache:
                        data = strategy._data_cache[symbol]
                        if len(data) >= 30:
                            data_with_ind = strategy.calculate_indicators(data.copy())
                            if len(data_with_ind) > 0:
                                latest = data_with_ind.iloc[-1]
                                if 'ma_short' in latest and 'ma_long' in latest:
                                    dashboard.update_ma(float(latest['ma_short']), float(latest['ma_long']))

                    # Update stats
                    pos_status = f"持仓 {float(position):.4f} BTC" if position > 0 else "空仓"
                    dashboard.update_stats(
                        float(portfolio.get_total_value()),
                        pos_status,
                        strategy.market_regime,
                        strategy.volatility_regime
                    )

                    live.update(dashboard.render())

                except asyncio.TimeoutError:
                    live.update(dashboard.render())

        except KeyboardInterrupt:
            console.print("\n[yellow]Stopped[/yellow]")
        finally:
            await data_feed.stop()
            await event_bus.stop()
            console.print(f"\n[green]Processed {event_count} events[/green]")

if __name__ == "__main__":
    asyncio.run(main())
