#!/usr/bin/env python3
"""
Continuous Live Trading Demo with Active Momentum Strategy

Uses a simple momentum strategy that trades frequently based on price changes.
Press Ctrl+C to gracefully exit.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
from decimal import Decimal
import signal
import random

# Add project path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.engine import TradingEngine
from src.strategies.base import Strategy
from src.data.feed import DataFeed
from src.trading.exchanges.simulator import SimulatedExchange
from src.utils.logger import setup_logger, logger
from src.core.event import MarketEvent, SignalEvent
from src.core.types import SignalType


class MomentumStrategy(Strategy):
    """Simple momentum strategy that trades on price changes"""

    def __init__(self, strategy_id: str, config: dict):
        super().__init__(strategy_id, config)
        self.last_price = None
        self.position_open = False
        self.buy_threshold = Decimal('0.015')  # 1.5% price increase triggers buy
        self.sell_threshold = Decimal('0.015')  # 1.5% price decrease triggers sell
        self.event_bus = None  # Will be set by engine

    def set_event_bus(self, event_bus):
        """Set the event bus for publishing signals"""
        self.event_bus = event_bus

    def on_init(self):
        logger.info(f"Momentum strategy {self.strategy_id} initialized")

    async def on_market_data(self, event: MarketEvent):
        if not self.is_active:
            return None

        current_price = event.price

        if self.last_price is None:
            self.last_price = current_price
            return None

        # Calculate price change percentage
        price_change = (current_price - self.last_price) / self.last_price

        signal = None

        # Buy signal: price increased significantly and no position
        if price_change > self.buy_threshold and not self.position_open:
            print(f"      BUY SIGNAL: Price up {price_change*100:.2f}% (${self.last_price:.0f} -> ${current_price:.0f})")
            signal = self.generate_signal(
                symbol=event.symbol,
                signal_type=SignalType.BUY,
                strength=1.0,
                metadata={'price': float(current_price)}  # Include current price
            )
            self.position_open = True

            # Publish signal to event bus
            if self.event_bus and signal:
                await self.event_bus.publish(signal)

        # Sell signal: price decreased significantly and have position
        elif price_change < -self.sell_threshold and self.position_open:
            print(f"      SELL SIGNAL: Price down {price_change*100:.2f}% (${self.last_price:.0f} -> ${current_price:.0f})")
            signal = self.generate_signal(
                symbol=event.symbol,
                signal_type=SignalType.SELL,
                strength=1.0,
                metadata={'price': float(current_price)}  # Include current price
            )
            self.position_open = False

            # Publish signal to event bus
            if self.event_bus and signal:
                await self.event_bus.publish(signal)

        self.last_price = current_price
        return signal

    def calculate_indicators(self, data):
        return data

    def backtest_signals(self, data):
        return data


class VolatileDataFeed(DataFeed):
    """Volatile data feed that generates trending price movements"""

    def __init__(self, event_bus, update_interval=1.0):
        super().__init__(event_bus)
        self.update_interval = update_interval
        self.prices = {}
        self.trend_direction = 1
        self.trend_counter = 0
        self.trend_duration = random.randint(5, 10)

    def set_price(self, symbol: str, price: Decimal):
        self.prices[symbol] = price

    async def start(self):
        await super().start()
        for symbol in self.subscriptions.keys():
            task = asyncio.create_task(self._generate_volatile_data(symbol))
            self._tasks.append(task)
        logger.info("Volatile data feed started")

    async def _generate_volatile_data(self, symbol: str):
        if symbol not in self.prices:
            self.prices[symbol] = Decimal('50000')

        while self.is_running:
            try:
                current_price = self.prices[symbol]

                # Change trend direction periodically
                self.trend_counter += 1
                if self.trend_counter >= self.trend_duration:
                    self.trend_direction *= -1
                    self.trend_counter = 0
                    self.trend_duration = random.randint(5, 10)
                    direction = 'UPWARD' if self.trend_direction > 0 else 'DOWNWARD'
                    print(f"      Market trend: {direction}")

                # Generate trending price movement (2-3% per update)
                trend_change = Decimal(str(random.uniform(0.02, 0.03))) * self.trend_direction
                noise = Decimal(str(random.uniform(-0.005, 0.005)))
                total_change = trend_change + noise

                new_price = current_price * (Decimal('1') + total_change)
                self.prices[symbol] = new_price

                volume = Decimal(str(random.uniform(100, 1000)))

                await self.publish_market_data(
                    symbol=symbol,
                    price=new_price,
                    volume=volume,
                    exchange="simulator",
                    bid=new_price * Decimal('0.999'),
                    ask=new_price * Decimal('1.001'),
                    open=current_price,
                    high=max(current_price, new_price) * Decimal('1.001'),
                    low=min(current_price, new_price) * Decimal('0.999'),
                    close=new_price
                )

                await asyncio.sleep(self.update_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error generating data for {symbol}: {e}")
                await asyncio.sleep(self.update_interval)


class LiveTradingDemo:
    """Continuous live trading demonstration"""

    def __init__(self):
        self.engine = None
        self.is_running = False

    async def start(self):
        print("=" * 70)
        print("Bitcoin Trading System - Active Momentum Trading")
        print("=" * 70)
        print()

        setup_logger(log_level="INFO")

        symbol = "BTC/USDT"
        initial_capital = Decimal("100000")

        print("TRADING CONFIGURATION:")
        print(f"  Symbol:          {symbol}")
        print(f"  Initial Capital: ${initial_capital:,.2f}")
        print(f"  Strategy:        Momentum (trades on 1.5%+ price moves)")
        print(f"  Mode:            Simulation with volatile prices")
        print()

        print("[1/3] Initializing trading engine...")
        self.engine = TradingEngine(initial_capital=initial_capital, config={})

        print("[2/3] Connecting to simulated exchange...")
        exchange = SimulatedExchange(
            exchange_id="simulator",
            config={'initial_balance': str(initial_capital)}
        )
        self.engine.set_exchange(exchange)

        print("[3/3] Starting volatile data feed...")
        data_feed = VolatileDataFeed(self.engine.event_bus, update_interval=1.0)
        data_feed.set_price(symbol, Decimal('50000'))
        await data_feed.subscribe(symbol)
        self.engine.set_data_feed(data_feed)

        strategy = MomentumStrategy(
            strategy_id="momentum_live",
            config={'symbols': [symbol], 'timeframe': '1m', 'parameters': {}}
        )
        strategy.set_event_bus(self.engine.event_bus)  # Set event bus for signal publishing
        self.engine.add_strategy(strategy)

        print("System ready.")
        print()
        print("=" * 70)
        print("TRADING SYSTEM STARTED")
        print("=" * 70)
        print()
        print("INFO:")
        print("  - Momentum strategy trades on 1.5%+ price movements")
        print("  - Trades should start within 5-10 seconds")
        print("  - Price updates every 1 second")
        print("  - Press Ctrl+C to exit")
        print()
        print("-" * 70)
        print()

        self.is_running = True
        await self.engine.start()
        await self._monitor_loop()

    async def _monitor_loop(self):
        last_report_time = datetime.now()
        report_interval = 10

        try:
            while self.is_running:
                await asyncio.sleep(1)

                now = datetime.now()
                if (now - last_report_time).seconds >= report_interval:
                    self._print_status()
                    last_report_time = now

        except asyncio.CancelledError:
            logger.info("Monitor loop cancelled")

    def _print_status(self):
        status = self.engine.get_status()
        portfolio = self.engine.get_portfolio()

        print(f"[{datetime.now().strftime('%H:%M:%S')}] TRADING STATUS:")
        print(f"  Total Value:     ${portfolio.get_total_value():,.2f}")
        print(f"  Available Cash:  ${portfolio.cash:,.2f}")
        print(f"  Position Value:  ${portfolio.get_positions_value():,.2f}")
        print(f"  Active Orders:   {status['active_orders']}")

        positions = portfolio.get_all_positions()
        if positions:
            print(f"  Current Positions:")
            for position in positions:
                pnl = position.unrealized_pnl
                total_cost = position.quantity * position.avg_price
                pnl_pct = (pnl / total_cost * 100) if total_cost > 0 else 0
                print(f"    {position.symbol}: {position.quantity:.4f} | "
                      f"Avg Price: ${position.avg_price:.2f} | "
                      f"P&L: ${pnl:.2f} ({pnl_pct:+.2f}%)")
        else:
            print(f"  Current Positions: None")

        print("-" * 70)
        print()

    async def stop(self):
        print()
        print("=" * 70)
        print("STOPPING TRADING SYSTEM...")
        print("=" * 70)
        print()

        self.is_running = False

        if self.engine:
            await self.engine.stop()

        self._print_final_stats()

    def _print_final_stats(self):
        if not self.engine:
            print("System not fully initialized")
            return

        portfolio = self.engine.get_portfolio()
        orders = self.engine.get_orders()

        print()
        print("=" * 70)
        print("TRADING SUMMARY")
        print("=" * 70)
        print()

        print("FINAL ACCOUNT:")
        print(f"  Total Assets:    ${portfolio.get_total_value():,.2f}")
        print(f"  Cash:            ${portfolio.cash:,.2f}")
        print(f"  Position Value:  ${portfolio.get_positions_value():,.2f}")
        print()

        print("TRADING STATISTICS:")
        print(f"  Total Orders:    {len(orders)}")

        filled_orders = [o for o in orders if o.get('status') == 'FILLED']
        print(f"  Filled Orders:   {len(filled_orders)}")

        buy_orders = [o for o in filled_orders if o.get('side') == 'BUY']
        sell_orders = [o for o in filled_orders if o.get('side') == 'SELL']
        print(f"  Buy Orders:      {len(buy_orders)}")
        print(f"  Sell Orders:     {len(sell_orders)}")
        print()

        if filled_orders:
            print("RECENT TRADES:")
            for order in filled_orders[-5:]:
                timestamp = order.get('timestamp', 'N/A')
                if isinstance(timestamp, datetime):
                    timestamp = timestamp.strftime('%H:%M:%S')
                side = order.get('side', 'N/A')
                symbol = order.get('symbol', 'N/A')
                quantity = order.get('quantity', 0)
                price = order.get('price')
                if price:
                    print(f"  [{timestamp}] {side:4s} {quantity:.4f} {symbol} @ ${price:.2f}")
                else:
                    print(f"  [{timestamp}] {side:4s} {quantity:.4f} {symbol}")
            print()

        print("=" * 70)
        print("TRADING SYSTEM SAFELY EXITED")
        print("=" * 70)


async def main():
    demo = LiveTradingDemo()

    def signal_handler(sig, frame):
        print("\n\nReceived exit signal...")
        asyncio.create_task(demo.stop())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        await demo.start()
    except KeyboardInterrupt:
        await demo.stop()
    except Exception as e:
        print(f"\n\nERROR: {e}")
        import traceback
        traceback.print_exc()
        if demo.engine:
            await demo.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nGoodbye!")
