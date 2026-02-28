"""CLI commands for trading"""

import click
import asyncio
from decimal import Decimal
from pathlib import Path
import json
import os

# CRITICAL: Disable loguru's default handler IMMEDIATELY on module import
# This prevents ANY console output in dashboard mode
from loguru import logger as _loguru_logger
_loguru_logger.remove()  # Remove default stderr handler

from ...core.engine import TradingEngine
from ...strategies.examples.ma_cross import MACrossStrategy
from ...trading.exchanges.simulator import SimulatedExchange
from ...trading.exchanges.binance_paper import BinancePaperExchange
from ...data.feed import SimulatedDataFeed
from ...data.crypto_feed import CryptoDataFeed
from ...utils.config import load_config
from ...utils.logger import logger
from ..live_logger import LiveTradeLogger, Colors


@click.group()
def trade():
    """Trading related commands"""
    pass


@trade.command()
@click.option('--strategy', default='ma_cross', help='Strategy name (default: ma_cross)')
@click.option('--symbol', default='BTCUSDT', help='Trading symbol (default: BTCUSDT)')
@click.option('--mode', default='paper', type=click.Choice(['simulation', 'paper', 'live']), help='Trading mode (default: paper with real data)')
@click.option('--capital', default=100000, type=float, help='Initial capital (default: 100000)')
@click.option('--duration', type=int, help='Run duration in seconds (leave empty for continuous)')
@click.option('--update-interval', default=1.0, type=float, help='Data update interval in seconds (default: 1.0, only for simulation mode)')
@click.option('--initial-price', type=float, help='Initial price for simulation mode (e.g., 66886 for current BTC price)')
@click.option('--dashboard/--no-dashboard', default=True, help='Enable professional real-time dashboard (default: enabled)')
@click.option('--time-range', default='live', type=click.Choice(['live', 'day', 'week', 'month', 'year']), help='Time range: live (real-time), day (24h), week (7d), month (30d), year (365d)')
@click.option('--ma-short', default=10, type=int, help='Short MA period for dashboard (default: 10)')
@click.option('--ma-long', default=30, type=int, help='Long MA period for dashboard (default: 30)')
@click.pass_context
def start(ctx, strategy, symbol, mode, capital, duration, update_interval, initial_price, dashboard, time_range, ma_short, ma_long):
    """Start real-time trading with optional dashboard visualization"""

    # Setup logging based on mode
    if dashboard and mode in ['simulation', 'paper']:
        # Dashboard mode: only log to file
        from pathlib import Path
        from loguru import logger as loguru_logger

        log_dir = Path("./data/logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        loguru_logger.add(
            log_dir / "trading.log",
            level="INFO",
            rotation="100 MB",
            retention="30 days",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
        )
    else:
        # Normal mode: setup console logging
        from ...utils.logger import setup_logger
        log_level = ctx.obj.get('log_level', 'INFO') if ctx.obj else 'INFO'
        log_file = Path('./data/logs/trading.log')
        setup_logger(log_level=log_level, log_file=str(log_file))

    try:
        if dashboard and mode in ['simulation', 'paper']:
            # Use professional dashboard - all logs will be shown in dashboard
            _run_with_professional_dashboard(symbol, capital, ma_short, ma_long, mode, initial_price, update_interval, time_range)
        else:
            # Use original trading engine logic for live mode or no-dashboard
            # Show startup info only when dashboard is disabled
            click.echo(f"Starting {mode} trading with {strategy} strategy")
            click.echo(f"Initial capital: ${capital:,.2f}")
            click.echo(f"Symbol: {symbol}")
            _run_with_trading_engine(strategy, symbol, mode, capital, duration, update_interval, initial_price, dashboard)

    except KeyboardInterrupt:
        pass  # 静默退出，不打印任何信息
    except Exception as e:
        # Log full traceback to file
        import traceback
        from pathlib import Path
        from datetime import datetime

        error_log = Path("./data/logs/error.log")
        error_log.parent.mkdir(parents=True, exist_ok=True)

        with open(error_log, 'a') as f:
            f.write(f"\n\n{'='*80}\n")
            f.write(f"Error at {datetime.now()}\n")
            f.write(f"{'='*80}\n")
            traceback.print_exc(file=f)

        click.echo(f"\n错误: {e}")
        click.echo(f"完整错误已记录到: {error_log}")
        logger.error(f"Trading failed: {e}", exc_info=True)


async def fetch_52_week_data(symbol: str):
    """从Binance获取52周最高/最低数据

    Args:
        symbol: 交易对符号（如BTC-USD）

    Returns:
        tuple: (52周最高, 52周最低)
    """
    try:
        import ccxt.async_support as ccxt
        import os

        # 配置代理
        exchange_config = {
            'enableRateLimit': True,
            'timeout': 30000,
        }

        http_proxy = os.getenv('HTTP_PROXY') or os.getenv('http_proxy')
        https_proxy = os.getenv('HTTPS_PROXY') or os.getenv('https_proxy')

        if http_proxy or https_proxy:
            proxy_url = https_proxy or http_proxy
            exchange_config['proxies'] = {
                'http': proxy_url,
                'https': proxy_url,
            }
            exchange_config['aiohttp_proxy'] = proxy_url

        # 格式化symbol为Binance格式
        binance_symbol = symbol.replace('-', '').replace('/', '')
        if binance_symbol.endswith('USD'):
            binance_symbol = binance_symbol[:-3] + 'USDT'

        # 使用ccxt获取过去365天的日K线数据
        exchange = ccxt.binance(exchange_config)

        try:
            # 获取365天的日K线（52周 ≈ 364天）
            ohlcv = await exchange.fetch_ohlcv(binance_symbol, '1d', limit=365)

            if ohlcv and len(ohlcv) > 0:
                # 计算52周最高/最低
                week_52_high = max(candle[2] for candle in ohlcv)  # High price
                week_52_low = min(candle[3] for candle in ohlcv)   # Low price

                return week_52_high, week_52_low
            else:
                return 0, 0

        finally:
            await exchange.close()

    except Exception as e:
        # 如果获取失败，返回0（不影响主程序运行）
        return 0, 0


def _run_with_professional_dashboard(symbol, capital, ma_short, ma_long, mode, initial_price, update_interval, time_range='live'):
    """Run trading with professional dashboard - silent mode, all output in dashboard"""

    # CRITICAL: Disable ALL console logging BEFORE any imports
    import logging
    import sys
    from pathlib import Path
    from datetime import datetime
    import traceback
    import uuid

    # Disable standard logging to console
    logging.getLogger().handlers = []
    logging.getLogger().setLevel(logging.CRITICAL)

    # Disable loguru console output
    from loguru import logger as loguru_logger
    loguru_logger.remove()  # Remove all handlers

    # Only log to file, not console
    log_dir = Path("./data/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    loguru_logger.add(
        log_dir / "trading.log",
        level="INFO",
        rotation="100 MB",
        retention="30 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
    )

    import asyncio
    from decimal import Decimal
    from ...core.event_bus import EventBus
    from ...trading.portfolio import Portfolio
    from ...strategies.examples.adaptive_strategy import AdaptiveStrategy
    from ...core.event import EventType
    from ..dashboard import ProfessionalDashboard
    from ...data.storage import DataStorage
    from rich.console import Console
    from rich.live import Live

    # Initialize database storage
    storage = DataStorage()
    session_id = str(uuid.uuid4())

    async def run_dashboard():
        console = Console()

        # Initialize components
        event_bus = EventBus()
        portfolio = Portfolio(initial_balance=Decimal(str(capital)))
        dashboard = ProfessionalDashboard(max_points=100)

        # Add startup logs to dashboard (NO console output)
        mode_text = {
            'simulation': '模拟交易 (虚拟数据)',
            'paper': '纸上交易 (真实数据, 虚拟资金)',
            'live': '实盘交易 (真实资金)'
        }
        dashboard.add_log(f"启动 {mode_text.get(mode, mode)} 模式", "info")
        dashboard.add_log(f"初始资金: ${capital:,.2f}", "info")
        dashboard.add_log(f"交易标的: {symbol}", "info")
        dashboard.add_log(f"策略参数: MA短期={ma_short}, MA长期={ma_long}", "info")

        # Initialize strategy
        strategy_config = {
            'parameters': {
                'ma_short': ma_short,
                'ma_long': ma_long,
                'volatility_window': 20,
                'trend_window': 50
            }
        }
        strategy = AdaptiveStrategy('adaptive_live', strategy_config)
        strategy.event_bus = event_bus
        strategy.start()

        # Start event bus FIRST
        await event_bus.start()

        # Initialize data feed based on mode
        if mode == 'simulation':
            from ...data.feed import SimulatedDataFeed
            data_feed = SimulatedDataFeed(event_bus, update_interval=update_interval or 0.5)
            await data_feed.subscribe(symbol)
            data_feed.set_price(symbol, Decimal(str(initial_price or 66886)))
            dashboard.add_log("使用模拟数据 (无需网络)", "info")
        elif mode == 'paper':
            from ...data.binance_feed import BinanceDataFeed
            data_feed = BinanceDataFeed(event_bus)
            await data_feed.subscribe(symbol)
            dashboard.add_log("正在连接 Binance 获取实时数据...", "info")

        # Start data feed
        await data_feed.start()

        if mode == 'paper':
            dashboard.add_log("✓ 已连接 Binance，接收实时数据", "info")

        # Initialize dashboard with data
        dashboard.update_price(
            price=float(initial_price or 66886),
            volume_24h=0,
            tick_volume=100.0
        )
        dashboard.update_stats(float(capital), float(capital), "空仓", "unknown", "normal")

        # 获取52周最高/最低数据
        dashboard.add_log("正在获取52周历史数据...", "info")
        week_52_high, week_52_low = await fetch_52_week_data(symbol)
        if week_52_high > 0 and week_52_low > 0:
            dashboard.week_52_high = week_52_high
            dashboard.week_52_low = week_52_low
            dashboard.add_log(f"✓ 52周最高: ${week_52_high:,.2f}, 最低: ${week_52_low:,.2f}", "info")
        else:
            dashboard.add_log("⚠ 无法获取52周数据（可能需要配置代理）", "error")

        await asyncio.sleep(0.5)

        # Trading state
        position = Decimal(0)
        entry_price = None
        candle_data = {'open': 0, 'high': 0, 'low': float('inf'), 'close': 0, 'count': 0}

        # Event handler
        market_events = asyncio.Queue()

        async def handle_market_event(event):
            await market_events.put(event)

        event_bus.subscribe(EventType.MARKET, handle_market_event)

        dashboard.add_log("启动交易系统...", "info")

        # 键盘输入队列
        keyboard_input = asyncio.Queue()

        # 键盘监听任务
        async def keyboard_listener():
            """监听键盘输入（非阻塞）"""
            import sys
            import termios
            import tty

            # 保存原始终端设置
            old_settings = termios.tcgetattr(sys.stdin)

            try:
                # 设置为非阻塞模式
                tty.setcbreak(sys.stdin.fileno())

                while True:
                    # 检查是否有输入
                    import select
                    if select.select([sys.stdin], [], [], 0.1)[0]:
                        char = sys.stdin.read(1)
                        await keyboard_input.put(char)
                    await asyncio.sleep(0.05)
            finally:
                # 恢复终端设置
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

        # 启动键盘监听任务
        keyboard_task = asyncio.create_task(keyboard_listener())

        with Live(dashboard.render(), refresh_per_second=4, console=console) as live:
            try:
                while True:
                    try:
                        # 处理键盘输入
                        try:
                            key = keyboard_input.get_nowait()
                            # 处理周期切换快捷键
                            if key == '1':
                                dashboard.switch_time_range('1D')
                            elif key == '2':
                                dashboard.switch_time_range('5日')
                                await dashboard.load_historical_data(symbol, '5日')
                            elif key == '3':
                                dashboard.switch_time_range('日K')
                                await dashboard.load_historical_data(symbol, '日K')
                            elif key == '4':
                                dashboard.switch_time_range('周K')
                                await dashboard.load_historical_data(symbol, '周K')
                            elif key == '5':
                                dashboard.switch_time_range('月K')
                                await dashboard.load_historical_data(symbol, '月K')
                            elif key == '6':
                                dashboard.switch_time_range('年K')
                                await dashboard.load_historical_data(symbol, '年K')
                            elif key.lower() == 's':
                                # 切换策略
                                new_strategy_name = dashboard.switch_strategy()

                                # 创建新策略实例
                                if new_strategy_name == 'ma_cross':
                                    from ...strategies.examples.ma_cross import MACrossStrategy
                                    new_strategy = MACrossStrategy('ma_cross_live', {
                                        'parameters': {
                                            'ma_short': ma_short,
                                            'ma_long': ma_long
                                        }
                                    })
                                else:  # adaptive_strategy
                                    new_strategy = AdaptiveStrategy('adaptive_live', {
                                        'parameters': {
                                            'ma_short': ma_short,
                                            'ma_long': ma_long,
                                            'volatility_window': 20,
                                            'trend_window': 50
                                        }
                                    })

                                # 替换策略
                                strategy.stop()
                                strategy = new_strategy
                                strategy.event_bus = event_bus
                                strategy.start()

                                dashboard.add_log(f"✓ 策略已切换", "info")
                        except asyncio.QueueEmpty:
                            pass

                        event = await asyncio.wait_for(market_events.get(), timeout=0.1)

                        price = float(event.price)
                        tick_volume = float(event.volume) if event.volume else 0

                        # Binance sends two types of events:
                        # 1. Trade events: only price and quantity (frequent)
                        # 2. Ticker events: full 24h statistics (less frequent but complete)
                        # We should use ticker data when available, otherwise just update price

                        if event.high is not None and event.low is not None and event.open is not None:
                            # This is a ticker event with full 24h statistics
                            dashboard.update_price(
                                price,
                                volume_24h=tick_volume,  # 24h total volume
                                high_24h=float(event.high),
                                low_24h=float(event.low),
                                open_price=float(event.open),
                                tick_volume=tick_volume
                            )
                        else:
                            # This is a trade event, only update price and tick volume
                            dashboard.update_price(
                                price,
                                volume_24h=0,  # Don't override 24h volume
                                tick_volume=tick_volume
                            )

                        # Aggregate OHLC
                        if candle_data['count'] == 0:
                            candle_data['open'] = price
                            candle_data['high'] = price
                            candle_data['low'] = price

                        candle_data['high'] = max(candle_data['high'], price)
                        candle_data['low'] = min(candle_data['low'], price)
                        candle_data['close'] = price
                        candle_data['count'] += 1

                        if candle_data['count'] >= 10:
                            dashboard.update_ohlc(
                                candle_data['open'],
                                candle_data['high'],
                                candle_data['low'],
                                candle_data['close']
                            )
                            candle_data = {'open': 0, 'high': 0, 'low': float('inf'), 'close': 0, 'count': 0}

                        # Update portfolio
                        portfolio.update_prices({symbol: Decimal(str(price))})

                        # Process strategy
                        signal = await strategy.on_market_data(event)

                        # Update MA
                        if symbol in strategy._data_cache:
                            data = strategy._data_cache[symbol]
                            if len(data) >= 30:
                                data_with_ind = strategy.calculate_indicators(data.copy())
                                if len(data_with_ind) > 0:
                                    latest = data_with_ind.iloc[-1]
                                    if 'ma_short' in latest and 'ma_long' in latest:
                                        dashboard.update_ma(
                                            float(latest['ma_short']),
                                            float(latest['ma_long'])
                                        )

                        # Handle signals - check signal type string
                        if signal:
                            signal_type = signal.signal_type.lower() if hasattr(signal.signal_type, 'lower') else str(signal.signal_type).lower()
                            dashboard.add_log(f"收到 {signal_type.upper()} 信号 @ ${price:,.2f}", "signal")

                            if signal_type == 'buy' and position == 0:
                                quantity = (portfolio.cash * Decimal("0.95")) / Decimal(str(price))
                                cost = quantity * Decimal(str(price))

                                portfolio.update_position(symbol, quantity, Decimal(str(price)))
                                portfolio.cash -= cost
                                position = quantity
                                entry_price = Decimal(str(price))

                                # Save trade to database
                                storage.save_trades([{
                                    'timestamp': datetime.now(),
                                    'symbol': symbol,
                                    'side': 'BUY',
                                    'quantity': float(quantity),
                                    'price': float(price),
                                    'commission': 0.0,
                                    'portfolio_value': float(portfolio.get_total_value())
                                }], session_id, 'adaptive')

                                dashboard.add_log(f"✓ 执行买入: {float(quantity):.6f} BTC @ ${price:,.2f}", "trade")
                                dashboard.add_trade('buy', price, quantity=float(quantity))

                            elif signal_type == 'sell' and position > 0:
                                sell_value = position * Decimal(str(price))

                                dashboard.add_log(f"✓ 执行卖出: {float(position):.6f} BTC @ ${price:,.2f}", "trade")
                                portfolio.update_position(symbol, -position, Decimal(str(price)))
                                portfolio.cash += sell_value

                                # Save trade to database
                                storage.save_trades([{
                                    'timestamp': datetime.now(),
                                    'symbol': symbol,
                                    'side': 'SELL',
                                    'quantity': float(position),
                                    'price': float(price),
                                    'commission': 0.0,
                                    'portfolio_value': float(portfolio.get_total_value())
                                }], session_id, 'adaptive')

                                dashboard.add_trade('sell', price, float(entry_price) if entry_price else None, float(position))
                                position = Decimal(0)
                                entry_price = None
                            else:
                                # Log why signal was not executed
                                if signal_type == 'buy' and position > 0:
                                    dashboard.add_log(f"忽略买入信号 (已有持仓)", "info")
                                elif signal_type == 'sell' and position == 0:
                                    dashboard.add_log(f"忽略卖出信号 (无持仓)", "info")

                        # Update stats
                        position_status = f"持仓 {float(position):.4f} BTC" if position > 0 else "空仓"
                        dashboard.update_stats(
                            float(portfolio.get_total_value()),
                            float(portfolio.cash),
                            position_status,
                            strategy.market_regime,
                            strategy.volatility_regime
                        )

                        # Update display
                        live.update(dashboard.render())

                    except asyncio.TimeoutError:
                        live.update(dashboard.render())

            except KeyboardInterrupt:
                pass  # Silent exit
            finally:
                # 取消键盘监听任务
                keyboard_task.cancel()
                try:
                    await keyboard_task
                except asyncio.CancelledError:
                    pass
                await data_feed.stop()
                await event_bus.stop()

    asyncio.run(run_dashboard())


def _run_with_trading_engine(strategy, symbol, mode, capital, duration, update_interval, initial_price, visualize):
    """Run trading with original trading engine (for paper/live modes or no-dashboard)"""
    import asyncio
    from decimal import Decimal
    from ...core.engine import TradingEngine
    from ...strategies.examples.ma_cross import MACrossStrategy
    from ...trading.exchanges.simulator import SimulatedExchange
    from ...trading.exchanges.binance_paper import BinancePaperExchange
    from ...data.feed import SimulatedDataFeed
    from ...data.crypto_feed import CryptoDataFeed
    from ...utils.config import load_config
    from ..live_logger import LiveTradeLogger

    # Load strategy configuration
    strategy_config = load_config(f'strategies/{strategy}')
    strategy_config['symbols'] = [symbol]

    # Create trading engine
    engine = TradingEngine(
        initial_capital=Decimal(str(capital)),
        config={
            'execution': {'default_position_size': '0.95'},
            'monitor': {'enabled': False}
        }
    )

    # Create strategy instance
    if strategy == 'ma_cross':
        strategy_obj = MACrossStrategy(strategy_id=strategy, config=strategy_config)
    else:
        click.echo(f"ERROR: Unknown strategy: {strategy}", err=True)
        return

    engine.add_strategy(strategy_obj)

    # Setup exchange and data feed based on mode
    if mode == 'simulation':
        exchange = SimulatedExchange(
            exchange_id='simulator',
            config={
                'initial_balance': str(capital),
                'commission': '0.001',
                'slippage': '0.0005'
            }
        )
        engine.set_exchange(exchange)

        data_feed = SimulatedDataFeed(engine.event_bus, update_interval=update_interval)
        asyncio.run(data_feed.subscribe(symbol))

        if initial_price:
            data_feed.set_price(symbol, Decimal(str(initial_price)))
        else:
            data_feed.set_price(symbol, Decimal('50000'))

        engine.set_data_feed(data_feed)

    elif mode == 'paper':
        click.echo("\nConnecting to CryptoCompare API for real market data...")

        exchange = BinancePaperExchange(
            exchange_id='paper',
            config={
                'initial_balance': str(capital),
                'commission': '0.001',
                'slippage': '0.0005'
            }
        )

        asyncio.run(exchange.connect())
        engine.set_exchange(exchange)

        data_feed = CryptoDataFeed(engine.event_bus, update_interval=1.0)
        asyncio.run(data_feed.subscribe(symbol))

        async def update_exchange_price(event):
            exchange.update_price(event.symbol, event.price)

        asyncio.run(data_feed.subscribe(symbol, update_exchange_price))
        engine.set_data_feed(data_feed)

        click.echo(f"✓ Connected to CryptoCompare API")
        click.echo(f"✓ Using REAL {symbol} spot prices with virtual money")

    elif mode == 'live':
        click.echo("ERROR: Live trading not yet implemented", err=True)
        click.echo("Use --mode paper for paper trading with real market data")
        return

    # Create live logger
    live_logger = LiveTradeLogger(engine.event_bus, engine.portfolio)

    # Run trading engine
    async def run_with_logger():
        await live_logger.start()
        await engine.run(duration=duration)
        await live_logger.stop()
        return live_logger

    click.echo("\nStarting trading engine...")
    click.echo("Press Ctrl+C to stop\n")

    live_logger = asyncio.run(run_with_logger())
    live_logger.print_summary()


@trade.command()
def stop():
    """Stop trading"""
    click.echo("Stopping trading...")
    click.echo("(Feature coming soon)")


@trade.command()
def status():
    """View trading status"""
    click.echo("Trading Status:")
    click.echo("(Feature coming soon)")


@trade.command()
def positions():
    """View current positions"""
    click.echo("Current Positions:")
    click.echo("(Feature coming soon)")


@trade.command()
def orders():
    """View orders"""
    click.echo("Orders:")
    click.echo("(Feature coming soon)")
    """Start real-time trading"""
    click.echo(f"Starting {mode} trading with {strategy} strategy")
    click.echo(f"Initial capital: ${capital:,.2f}")
    click.echo(f"Symbol: {symbol}")

    if dashboard:
        click.echo("Dashboard: ENABLED (professional real-time dashboard)")
    else:
        click.echo("Dashboard: DISABLED (text-only logging)")

    if mode == 'simulation':
        click.echo(f"Update interval: {update_interval}s")
        if initial_price:
            click.echo(f"Initial price: ${initial_price:,.2f}")
    elif mode == 'paper':
        click.echo("Mode: Paper trading (real market data, virtual money)")
    elif mode == 'live':
        click.echo("Mode: LIVE TRADING (real money at risk!)")

    try:
        # Load strategy configuration
        strategy_config = load_config(f'strategies/{strategy}')
        strategy_config['symbols'] = [symbol]

        # Create trading engine
        engine = TradingEngine(
            initial_capital=Decimal(str(capital)),
            config={
                'execution': {'default_position_size': '0.95'},
                'monitor': {'enabled': False}  # Disable default monitoring, use custom logger
            }
        )

        # Create strategy instance
        if strategy == 'ma_cross':
            strategy_obj = MACrossStrategy(strategy_id=strategy, config=strategy_config)
        else:
            click.echo(f"ERROR: Unknown strategy: {strategy}", err=True)
            return

        engine.add_strategy(strategy_obj)

        # Setup exchange and data feed based on mode
        if mode == 'simulation':
            # Simulation mode: fake data, fake execution
            exchange = SimulatedExchange(
                exchange_id='simulator',
                config={
                    'initial_balance': str(capital),
                    'commission': '0.001',
                    'slippage': '0.0005'
                }
            )
            engine.set_exchange(exchange)

            # Setup simulated data feed
            data_feed = SimulatedDataFeed(engine.event_bus, update_interval=update_interval)
            asyncio.run(data_feed.subscribe(symbol))

            # Set initial price (use provided price or default to 50000)
            if initial_price:
                data_feed.set_price(symbol, Decimal(str(initial_price)))
            else:
                data_feed.set_price(symbol, Decimal('50000'))

            engine.set_data_feed(data_feed)

        elif mode == 'paper':
            # Paper trading mode: real data, simulated execution
            click.echo("\nConnecting to CryptoCompare API for real market data...")

            # Setup paper trading exchange
            exchange = BinancePaperExchange(
                exchange_id='paper',
                config={
                    'initial_balance': str(capital),
                    'commission': '0.001',
                    'slippage': '0.0005'
                }
            )

            # Connect to exchange (no-op for paper trading)
            asyncio.run(exchange.connect())
            engine.set_exchange(exchange)

            # Setup real crypto data feed (CryptoCompare + Blockchain.info)
            data_feed = CryptoDataFeed(engine.event_bus, update_interval=1.0)

            # Subscribe to market data
            asyncio.run(data_feed.subscribe(symbol))

            # Setup price update callback to feed exchange
            async def update_exchange_price(event):
                """Update exchange with latest price from market data"""
                exchange.update_price(event.symbol, event.price)

            # Subscribe exchange to price updates
            asyncio.run(data_feed.subscribe(symbol, update_exchange_price))

            engine.set_data_feed(data_feed)

            click.echo(f"✓ Connected to CryptoCompare API")
            click.echo(f"✓ Using REAL {symbol} spot prices with virtual money")
            click.echo(f"✓ Price updates every 1 second")

        elif mode == 'live':
            click.echo("ERROR: Live trading not yet implemented", err=True)
            click.echo("Use --mode paper for paper trading with real market data")
            return

        # Use visualization or live logger
        if visualize:
            # Import simplified dashboard (works in any environment)
            from ...monitor.simplified_dashboard import SimplifiedDashboard

            dashboard = SimplifiedDashboard(engine.event_bus, engine.portfolio, strategy_obj)

            click.echo("\nStarting trading engine with real-time visualization...")
            click.echo("Press Ctrl+C to stop\n")

            # Run engine and dashboard together
            async def run_with_dashboard():
                # Start dashboard in background
                dashboard_task = asyncio.create_task(dashboard.run(duration=duration))

                # Start engine
                engine_task = asyncio.create_task(engine.run(duration=duration))

                # Wait for both
                await asyncio.gather(dashboard_task, engine_task)

            asyncio.run(run_with_dashboard())

        else:
            # Create live logger
            live_logger = LiveTradeLogger(engine.event_bus, engine.portfolio)

            # Run trading engine
            async def run_with_logger():
                await live_logger.start()
                await engine.run(duration=duration)
                await live_logger.stop()
                return live_logger

            click.echo("\nStarting trading engine...")
            click.echo("Press Ctrl+C to stop\n")

            live_logger = asyncio.run(run_with_logger())

            # Display final summary
            live_logger.print_summary()

    except KeyboardInterrupt:
        click.echo("\n\nTrading interrupted by user")
        if 'live_logger' in locals():
            live_logger.print_summary()
    except Exception as e:
        click.echo(f"\nERROR: {e}", err=True)
        logger.error(f"Trading failed: {e}", exc_info=True)


@trade.command()
def stop():
    """Stop trading"""
    click.echo("Stopping trading...")
    click.echo("(Feature coming soon)")


@trade.command()
def status():
    """View trading status"""
    click.echo("Trading Status:")
    click.echo("(Feature coming soon)")


@trade.command()
def positions():
    """View current positions"""
    click.echo("Current Positions:")
    click.echo("(Feature coming soon)")


@trade.command()
def orders():
    """View orders"""
    click.echo("Orders:")
    click.echo("(Feature coming soon)")


@trade.command()
@click.option('--symbol', default='BTCUSDT', help='Trading symbol (default: BTCUSDT)')
@click.option('--capital', default=100000, type=float, help='Initial capital (default: 100000)')
@click.option('--ma-short', default=10, type=int, help='Short MA period (default: 10)')
@click.option('--ma-long', default=30, type=int, help='Long MA period (default: 30)')
@click.option('--mode', default='live', type=click.Choice(['live', 'simulation']), help='Data mode: live (Binance) or simulation (fake data)')
def dashboard(symbol, capital, ma_short, ma_long, mode):
    """Start professional real-time trading dashboard"""

    if mode == 'simulation':
        click.echo("Starting professional dashboard with SIMULATED data...")
        click.echo(f"Symbol: {symbol} (simulated)")
    else:
        click.echo("Starting professional dashboard with Binance live data...")
        click.echo(f"Symbol: {symbol}")

    click.echo(f"Initial capital: ${capital:,.2f}")
    click.echo(f"Strategy: MA Cross (Short={ma_short}, Long={ma_long})")
    click.echo()

    try:
        import asyncio
        from decimal import Decimal
        from ...core.event_bus import EventBus
        from ...trading.portfolio import Portfolio
        from ...strategies.examples.adaptive_strategy import AdaptiveStrategy

        # Import dashboard from official module
        from ..dashboard import ProfessionalDashboard
        from rich.console import Console
        from rich.live import Live

        async def run_dashboard():
            console = Console()

            # Initialize components
            event_bus = EventBus()
            portfolio = Portfolio(initial_balance=Decimal(str(capital)))
            dashboard = ProfessionalDashboard(max_points=100)

            # Initialize strategy
            strategy_config = {
                'parameters': {
                    'ma_short': ma_short,
                    'ma_long': ma_long,
                    'volatility_window': 20,
                    'trend_window': 50
                }
            }
            strategy = AdaptiveStrategy('adaptive_live', strategy_config)
            strategy.event_bus = event_bus
            strategy.start()

            # Start event bus FIRST
            await event_bus.start()

            # Initialize data feed based on mode
            if mode == 'simulation':
                from ...data.feed import SimulatedDataFeed
                data_feed = SimulatedDataFeed(event_bus, update_interval=0.5)
                await data_feed.subscribe(symbol)
                data_feed.set_price(symbol, Decimal('66886'))  # Current BTC price
                console.print("[yellow]Using simulated data (no network required)[/yellow]\n")
            else:
                from ...data.binance_feed import BinanceDataFeed
                data_feed = BinanceDataFeed(event_bus)
                await data_feed.subscribe(symbol)
                console.print("[green]Connecting to Binance...[/green]")

            # Start data feed AFTER event bus
            await data_feed.start()

            if mode == 'live':
                console.print("[green]Connected! Receiving live data[/green]\n")

            await asyncio.sleep(0.5)

            # Trading state
            position = Decimal(0)
            entry_price = None

            # Data aggregation for OHLC
            candle_data = {'open': 0, 'high': 0, 'low': float('inf'), 'close': 0, 'count': 0}

            # Event handler
            from ...core.event import MarketEvent, EventType
            market_events = asyncio.Queue()

            async def handle_market_event(event):
                """Handle market events"""
                await market_events.put(event)

            # Subscribe to market events
            event_bus.subscribe(EventType.MARKET, handle_market_event)

            # Initialize dashboard with some data so it's not empty on first render
            dashboard.update_price(
                price=66886.0,
                volume_24h=0,
                tick_volume=100.0
            )
            dashboard.update_stats(float(portfolio.get_total_value()), float(portfolio.cash), "空仓", "unknown", "normal")

            # Give a moment for initial events to queue
            await asyncio.sleep(1)

            console.print("[green]Starting dashboard (press Ctrl+C to stop)...[/green]\n")

            with Live(dashboard.render(), refresh_per_second=4, console=console) as live:
                try:
                    while True:

                        # Get market events with timeout
                        try:
                            event = await asyncio.wait_for(market_events.get(), timeout=0.1)

                            if isinstance(event, MarketEvent):
                                price = float(event.price)
                                tick_volume = float(event.volume) if event.volume else 0

                                # Binance sends two types of events:
                                # 1. Trade events: only price and quantity (frequent)
                                # 2. Ticker events: full 24h statistics (less frequent but complete)
                                if event.high is not None and event.low is not None and event.open is not None:
                                    # This is a ticker event with full 24h statistics
                                    dashboard.update_price(
                                        price,
                                        volume_24h=tick_volume,
                                        high_24h=float(event.high),
                                        low_24h=float(event.low),
                                        open_price=float(event.open),
                                        tick_volume=tick_volume
                                    )
                                else:
                                    # This is a trade event, only update price
                                    dashboard.update_price(
                                        price,
                                        volume_24h=0,
                                        tick_volume=tick_volume
                                    )

                                # Aggregate OHLC data (every 10 ticks)
                                if candle_data['count'] == 0:
                                    candle_data['open'] = price
                                    candle_data['high'] = price
                                    candle_data['low'] = price

                                candle_data['high'] = max(candle_data['high'], price)
                                candle_data['low'] = min(candle_data['low'], price)
                                candle_data['close'] = price
                                candle_data['count'] += 1

                                if candle_data['count'] >= 10:
                                    dashboard.update_ohlc(
                                        candle_data['open'],
                                        candle_data['high'],
                                        candle_data['low'],
                                        candle_data['close']
                                    )
                                    candle_data = {'open': 0, 'high': 0, 'low': float('inf'), 'close': 0, 'count': 0}

                                # Update portfolio
                                portfolio.update_prices({symbol: Decimal(str(price))})

                                # Process strategy
                                signal = await strategy.on_market_data(event)

                                # Update MA if available
                                if symbol in strategy._data_cache:
                                    data = strategy._data_cache[symbol]
                                    if len(data) >= 30:
                                        data_with_ind = strategy.calculate_indicators(data.copy())
                                        if len(data_with_ind) > 0:
                                            latest = data_with_ind.iloc[-1]
                                            if 'ma_short' in latest and 'ma_long' in latest:
                                                dashboard.update_ma(
                                                    float(latest['ma_short']),
                                                    float(latest['ma_long'])
                                                )

                                # Handle signals
                                if signal:
                                    if signal.signal_type == 'buy' and position == 0:
                                        # Buy
                                        quantity = (portfolio.cash * Decimal("0.95")) / Decimal(str(price))
                                        cost = quantity * Decimal(str(price))

                                        portfolio.update_position(symbol, quantity, Decimal(str(price)))
                                        portfolio.cash -= cost
                                        position = quantity
                                        entry_price = Decimal(str(price))

                                        dashboard.add_trade('buy', price, quantity=float(quantity))

                                    elif signal.signal_type == 'sell' and position > 0:
                                        # Sell
                                        sell_value = position * Decimal(str(price))

                                        portfolio.update_position(symbol, -position, Decimal(str(price)))
                                        portfolio.cash += sell_value

                                        # Pass entry price for PnL color calculation
                                        dashboard.add_trade('sell', price, float(entry_price) if entry_price else None, float(position))
                                        position = Decimal(0)
                                        entry_price = None

                                # Update stats
                                position_status = f"持仓 {float(position):.4f} BTC" if position > 0 else "空仓"
                                dashboard.update_stats(
                                    float(portfolio.get_total_value()),
                                    float(portfolio.cash),
                                    position_status,
                                    strategy.market_regime,
                                    strategy.volatility_regime
                                )

                                # Update display
                                live.update(dashboard.render())

                        except asyncio.TimeoutError:
                            # No event, just update display
                            live.update(dashboard.render())

                except KeyboardInterrupt:
                    console.print("\n[yellow]停止交易系统...[/yellow]")
                finally:
                    await data_feed.stop()
                    await event_bus.stop()

        asyncio.run(run_dashboard())

    except KeyboardInterrupt:
        click.echo("\n\nDashboard stopped by user")
    except Exception as e:
        click.echo(f"\nERROR: {e}", err=True)
        logger.error(f"Dashboard failed: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
