# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A real-time quantitative trading system for cryptocurrencies (Bitcoin, Ethereum) and stocks (US and A-share markets). The system supports live trading, backtesting, strategy optimization, risk management, and real-time monitoring.

**Current Implementation Status**: Core event-driven architecture is complete. Backtesting and simulation trading are fully functional. Two strategies are currently implemented: `ma_cross` (moving average crossover) and `adaptive_strategy` (dynamic parameter adjustment based on market conditions). Professional real-time dashboards with visualization are fully functional. Many CLI commands are placeholders for future development.

**Note**: The main README.md is written in Chinese. This CLAUDE.md provides English documentation for development.

## Development Commands

### Setup and Installation

```bash
# Install in development mode
pip install -e .

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

### Quick Start

#### Quick Start Scripts

Several shell scripts are provided for quick testing:

```bash
./quick_trade.sh       # 60-second simulation with fake data
./paper_trade.sh       # Paper trading with real Binance data
./live_trade.sh        # Live trading mode
./realtime_demo.sh     # Real-time dashboard demo
./simple_realtime.sh   # Simplified dashboard demo
./terminal_demo.sh     # Terminal-style dashboard demo
./adaptive_demo.sh     # Adaptive strategy demo
```

#### Run Examples Directly

```bash
# Backtesting examples
python examples/quick_backtest.py
python examples/demo_backtest.py
python examples/adaptive_backtest_demo.py

# Live trading examples
python examples/live_trading_demo.py

# Real-time dashboard examples
python examples/professional_realtime.py
python examples/simple_realtime.py
python examples/terminal_realtime.py
```

### Real-time Dashboard Visualization

The system includes professional real-time trading dashboards with rich visualization:

```bash
# Start trading with professional dashboard (default)
btc-trade trade start --strategy ma_cross --symbol BTC-USD --mode paper --dashboard

# Disable dashboard for text-only logging
btc-trade trade start --strategy ma_cross --symbol BTC-USD --mode paper --no-dashboard

# Customize dashboard MA parameters
btc-trade trade start --strategy ma_cross --symbol BTC-USD --mode paper --ma-short 10 --ma-long 30
```

**Dashboard Features**:
- Real-time candlestick charts and time-sharing charts
- Live trading metrics (price, volume, 24h high/low, amplitude)
- Position tracking and P&L visualization
- Market regime detection (trending/ranging, volatility)
- Signal and trade history with color-coded output
- Professional layout matching trading platforms like Futu (富途牛牛)

**Available Dashboard Modes**:
- `professional_realtime.py`: Full-featured dashboard with candlestick charts
- `simple_realtime.py`: Simplified dashboard for quick monitoring
- `terminal_realtime.py`: Terminal-style display for minimal resource usage

### Testing

**Note**: The test suite is not yet fully implemented. The `tests/` directory structure exists but test files need to be created.

```bash
# When tests are implemented, use:
pytest                                    # Run all tests
pytest tests/unit/test_core/             # Run specific module
pytest --cov=src --cov-report=html       # Coverage report
```

### Code Quality

```bash
# Format code
black src/ tests/

# Check code style
flake8 src/ tests/

# Type checking
mypy src/
```

## Coding Conventions

- Use Python 3.10+ with 4-space indentation and PEP 8 defaults
- `snake_case` for functions, methods, variables, and module files
- `PascalCase` for classes
- Small, single-purpose modules under the domain package that owns the behavior
- Run `black`, `flake8`, and `mypy` before commits

### CLI Commands

The main CLI entry point is `btc-trade` (defined in setup.py). **Note**: Currently `ma_cross` and `adaptive_strategy` are implemented.

**Fully Functional Commands**:

```bash
# Backtesting
btc-trade backtest start --strategy ma_cross --symbol BTC-USD --start 2024-01-01 --end 2024-12-31
btc-trade backtest start --strategy ma_cross --symbol BTC-USD --start 2024-01-01 --end 2024-12-31 --output results.csv

# Trading Modes with Dashboard Visualization
# 1. Simulation mode: Fake data with simulated execution
btc-trade trade start --strategy ma_cross --symbol BTC-USD --mode simulation --capital 100000 --duration 60 --dashboard

# 2. Paper trading mode: Real Binance data with virtual money (RECOMMENDED for testing)
btc-trade trade start --strategy ma_cross --symbol BTC-USD --mode paper --capital 100000 --dashboard

# 3. Disable dashboard for text-only output
btc-trade trade start --strategy ma_cross --symbol BTC-USD --mode paper --no-dashboard

# 4. Dashboard customization
btc-trade trade start --strategy ma_cross --symbol BTC-USD --mode paper --ma-short 10 --ma-long 30

# 5. Live trading mode: Real money (not yet implemented)
# btc-trade trade start --strategy ma_cross --symbol BTC-USD --mode live
```

**Placeholder Commands** (show "Feature coming soon"):

```bash
# Backtest management
btc-trade backtest list
btc-trade backtest report --id <backtest_id>

# Trading management
btc-trade trade stop
btc-trade trade status
btc-trade trade positions
btc-trade trade orders
```

**Planned Commands** (not yet implemented):

```bash
# Strategy Management
btc-trade strategy list
btc-trade strategy info --name ma_cross
btc-trade strategy optimize --name ma_cross --symbol BTC-USD

# Monitoring
btc-trade monitor start
btc-trade monitor dashboard
btc-trade monitor metrics

# Data Management
btc-trade data download --symbol BTC-USD --start 2024-01-01
btc-trade data list
```

## System Architecture

### Layered Architecture

The system follows a layered event-driven architecture:

```
CLI Layer (src/cli/)
    ↓
Application Layer (strategy management, backtest coordination)
    ↓
Core Engine Layer (event bus, trading engine, order management, risk management)
    ↓
Service Layer (market data, exchange gateways, portfolio, alerts)
    ↓
Infrastructure Layer (database, cache, logging, config)
```

### Event-Driven Core

The system is built around an **asynchronous event bus** (`src/core/event_bus.py`) that coordinates all components:

**Event Types** (defined in `src/core/event.py`):
- `MARKET`: Market data updates (price, volume, OHLCV)
- `SIGNAL`: Trading signals from strategies (BUY, SELL, HOLD, CLOSE)
- `ORDER`: Order lifecycle events (creation, submission, fills)
- `FILL`: Trade execution confirmations
- `RISK`: Risk management alerts and actions
- `MONITOR`: System monitoring metrics
- `SYSTEM`: System-level events

**Event Flow**:
1. Market data arrives → `MarketEvent` published to EventBus
2. Strategies subscribe to `MARKET` events → generate `SignalEvent`
3. ExecutionEngine receives signals → creates `OrderEvent`
4. RiskManager validates orders → may block or modify
5. OrderManager submits to exchange → receives `FillEvent`
6. Portfolio updates positions based on fills
7. MonitoringEngine tracks all events for metrics/alerts

### Key Components

#### TradingEngine (`src/core/engine.py`)

The main orchestrator for real-time trading. It:
- Initializes and coordinates all subsystems (EventBus, Portfolio, OrderManager, ExecutionEngine, RiskManager, Monitor)
- Manages strategy lifecycle (add, start, stop)
- Connects to exchanges and data feeds
- Provides unified start/stop/status interface

**Usage Pattern**:
```python
engine = TradingEngine(initial_capital=Decimal(100000), config={...})
engine.set_exchange(exchange_gateway)
engine.set_data_feed(data_feed)
engine.add_strategy(strategy)
await engine.start()  # or engine.run(duration=3600)
```

#### BacktestEngine (`src/backtest/engine.py`)

Simulates historical trading with:
- Commission and slippage modeling
- Equity curve tracking
- Performance metrics calculation (via PerformanceAnalyzer)
- Trade history recording

**Key Difference from TradingEngine**: BacktestEngine processes historical data synchronously in a loop, while TradingEngine handles real-time async events.

#### Strategy Base Class (`src/strategies/base.py`)

All strategies must inherit from `Strategy` and implement:
- `on_init()`: Initialize strategy state
- `async on_market_data(event: MarketEvent)`: Process real-time market data, return optional SignalEvent
- `calculate_indicators(data: pd.DataFrame)`: Compute technical indicators

**Strategy Pattern**:
- Strategies maintain data cache (`_data_cache`) for each symbol
- Use `generate_signal()` helper to create properly formatted SignalEvents
- Strategies are event subscribers - they receive MarketEvents via EventBus

**Currently Implemented Strategies**:

1. **MA Cross Strategy** (`src/strategies/examples/ma_cross.py`):
   - Simple moving average crossover
   - Configurable short/long MA periods (default: 10/30)
   - Basic trend-following approach
   - Best for trending markets

2. **Adaptive Strategy** (`src/strategies/examples/adaptive_strategy.py`):
   - Automatically adjusts parameters based on market conditions
   - Detects market regime (trending_up, trending_down, ranging)
   - Monitors volatility levels (low, normal, high)
   - Dynamic stop-loss, take-profit, and position sizing
   - Adapts MA periods based on market state
   - More sophisticated than MA Cross for varying market conditions

#### Exchange Gateways (`src/trading/exchanges/`)

Abstract interface (`base.py`) for exchange integration:
- `connect()` / `disconnect()`: Manage connections
- `place_order()`, `cancel_order()`, `get_order_status()`: Order operations
- `get_balance()`, `get_positions()`: Account queries
- `subscribe_market_data()`: Real-time data streams

Implementations for Binance, OKX, Alpaca follow this interface.

#### Risk Management (`src/risk/`)

Multi-layered risk control:
- **RiskManager** (`manager.py`): Validates orders against rules before execution
- **RiskRules** (`rules.py`): Position limits, drawdown limits, daily loss limits
- **PositionSizer** (`position_sizer.py`): Calculates safe position sizes
- **StopLoss** (`stop_loss.py`): Automatic stop-loss and take-profit

Risk checks happen **before** orders reach the exchange - RiskManager subscribes to SIGNAL events and can block/modify them.

#### Portfolio & Position Management (`src/trading/`)

- **Portfolio** (`portfolio.py`): Tracks cash, positions, and total equity
- **Position** (`position.py`): Individual position with entry price, quantity, P&L
- **OrderManager** (`order_manager.py`): Tracks order lifecycle, manages active orders
- **ExecutionEngine** (`execution.py`): Converts signals to orders, coordinates with risk manager

### Data Flow Example: Live Trading

1. **DataFeed** receives real-time price from exchange WebSocket
2. Creates `MarketEvent`, publishes to EventBus
3. **Strategy** receives event via `on_market_data()`, calculates indicators
4. Strategy generates `SignalEvent` (e.g., BUY signal), publishes to EventBus
5. **ExecutionEngine** receives signal, creates order
6. **RiskManager** validates order against rules (position limits, etc.)
7. If approved, **OrderManager** submits order to exchange
8. Exchange confirms fill → `FillEvent` published
9. **Portfolio** updates position based on fill
10. **MonitoringEngine** logs metrics, may send alerts

### Configuration

Environment variables (`.env`):
- Exchange API keys (BINANCE_API_KEY, OKX_API_KEY, ALPACA_API_KEY)
- Database URL (default: SQLite at `./data/db/trading.db`)
- Redis cache settings
- Alert channels (Telegram, Email)
- System mode: `simulation` or `live`

Configuration files in `config/`:
- Strategy parameters
- Risk management rules
- Exchange settings

## Paper Trading with Real Market Data

The system supports paper trading mode that connects to real exchanges for market data but simulates all trading operations locally:

**Implementation**:
- `BinanceDataFeed` (`src/data/binance_feed.py`): Connects to Binance WebSocket API for real-time price updates
- `BinancePaperExchange` (`src/trading/exchanges/binance_paper.py`): Simulates order execution using real market prices

**Usage**:
```bash
# Set Binance API credentials in .env (optional for public data)
BINANCE_TESTNET=false  # Set to true for testnet

# Run paper trading
btc-trade trade start --strategy ma_cross --symbol BTC-USD --mode paper --capital 100000
```

**How it works**:
1. Connects to Binance WebSocket for real-time market data
2. Strategy receives actual market prices and generates signals
3. Orders are executed locally against real prices (with simulated slippage and commission)
4. No actual orders are sent to the exchange
5. Virtual account tracks balances and positions

This is the recommended mode for testing strategies with real market conditions before risking actual capital.

## Important Patterns

### Async/Await Throughout

The system is fully asynchronous:
- EventBus runs an async event loop
- All event handlers can be async or sync (EventBus handles both)
- Exchange operations are async
- Use `await` for engine start/stop, order operations, data feeds

### Decimal for Financial Calculations

All prices, quantities, and monetary values use `Decimal` (not float) to avoid floating-point precision errors. Event classes automatically convert to Decimal in `__post_init__`.

### Event Priority

Events have a `priority` field (lower = higher priority). EventBus uses a PriorityQueue to process critical events first.

### Strategy Data Management

Strategies cache historical data per symbol. In real-time mode, they append new bars to the cache. In backtest mode, they receive the full dataset upfront.

### CLI Structure

CLI commands are organized in `src/cli/commands/`:
- Currently implemented: `backtest.py`, `trade.py`
- Commands are Click-based with rich formatting
- Main entry point: `src/cli/main.py` → `cli()` function

**Note**: Only `backtest` and `trade` command groups are currently implemented. Other command groups (strategy, monitor, data) are planned but not yet created.

## Testing Strategy

**Current Status**: Test infrastructure is planned but not yet implemented. The `tests/` directory structure exists but test files need to be created.

**Planned test organization**:
- `tests/unit/test_core/`: Event system, types, engine
- `tests/unit/test_strategies/`: Strategy logic, indicators
- `tests/unit/test_trading/`: Order management, portfolio, execution
- `tests/unit/test_risk/`: Risk rules, position sizing
- `tests/integration/`: End-to-end flows

When implementing tests, use pytest (plus pytest-asyncio for async tests) with fixtures for common setup (mock exchanges, sample data, etc.). Keep tests focused and cover new logic with unit tests, adding integration tests for cross-module workflows.

## Commit Format

Use clear, scoped commits following conventional commit style:
- `feat: add trailing stop rule`
- `fix: handle empty candle stream in binance feed`
- `refactor: simplify order validation logic`
- `test: add unit tests for risk manager`

## Adding a New Strategy

1. Create a new file in `src/strategies/examples/`
2. Inherit from `Strategy` base class
3. Implement required abstract methods:
   - `on_init()`: Initialize strategy state
   - `async on_market_data(event: MarketEvent)`: Process market data and return optional SignalEvent
   - `calculate_indicators(data: pd.DataFrame)`: Compute technical indicators
4. Define strategy parameters in `__init__` from config
5. Update CLI command handlers in `src/cli/commands/` to support the new strategy
6. Add configuration template in `config/strategies/`
7. Write tests in `tests/unit/test_strategies/`

**Reference**: See `src/strategies/examples/ma_cross.py` for a complete example.

## Example Scripts

The `examples/` directory contains ready-to-run demonstration scripts:

**Backtesting Examples**:
- `quick_backtest.py`: Fast backtest demonstration
- `demo_backtest.py`: Detailed backtest with visualization
- `adaptive_backtest_demo.py`: Adaptive strategy backtesting

**Live Trading Examples**:
- `live_trading_demo.py`: Continuous live trading simulation with momentum strategy

**Real-time Dashboard Examples**:
- `professional_realtime.py`: Professional dashboard with candlestick charts (23KB, most feature-rich)
- `simple_realtime.py`: Simplified dashboard for quick monitoring (9KB)
- `terminal_realtime.py`: Terminal-style display for minimal resource usage (11KB)
- `realtime_demo.py`: Basic real-time trading demo (7KB)

These are useful for understanding how to use the system programmatically without the CLI.

## Adding a New Exchange

1. Create a new file in `src/trading/exchanges/`
2. Inherit from `ExchangeGateway` base class
3. Implement all abstract methods (connect, place_order, etc.)
4. Handle exchange-specific API quirks and rate limits
5. Map exchange order statuses to system OrderStatus enum
6. Add exchange configuration to `.env.example`
7. Write integration tests with mock API responses

## Database Schema

The system includes a `DataStorage` class (`src/data/storage.py`) for persisting OHLCV data and backtest results. Default storage uses SQLite at `./data/db/trading.db`.

**Note**: Full database schema with SQLAlchemy models and Alembic migrations may not be fully implemented yet. Check `src/data/storage.py` for current data persistence capabilities.

## Logging

Loguru-based logging throughout:
- Logs to console and file (`./data/logs/trading.log`)
- Log levels: DEBUG, INFO, WARNING, ERROR
- Set via `--log-level` CLI flag or LOG_LEVEL env var
- Each module uses: `from ..utils.logger import logger`

### CLI Live Trading Logger

The live trading logger (`src/cli/live_logger.py`) displays real-time trading information with color-coded output, designed to match professional trading platforms like Futu (富途牛牛).

**Display Indicators** (参考富途牛牛 BTC/USD 界面):
- **Current Price**: Bold display with real-time updates
- **24h Change**: Percentage and absolute change (e.g., -3.11% ($-2,143.26))
- **24h High/Low**: Highest and lowest prices in 24 hours
- **Amplitude (振幅)**: Calculated as (24h High - 24h Low) / Open Price × 100%
- **Volume**: Trading volume with smart units (M for millions, K for thousands)
- **Market Cap**: Market capitalization with smart units (T for trillions, B for billions)
- **Position Info**: Current holdings, equity, and PnL

**Color Scheme**:
- **Green**: Positive changes, buy orders, profits
- **Red**: Negative changes, sell orders, losses
- **Yellow**: Important info (equity, signals)
- **Cyan**: Symbols, positions, market cap
- **White**: Current prices
- **Magenta**: Amplitude, signal strength
- **Blue**: Volume, strategy names
- **Dim**: Timestamps, labels

**Session Summary** (参考量化交易系统):
- Portfolio performance with initial/final capital
- Position details with entry price and unrealized PnL
- Trading statistics: signals, fills, buy/sell counts, win rate
- Recent trade history with timestamps and PnL

**Important**: Do NOT use emoji or Unicode symbols (🟢🔴🔔) in log output. Use ANSI color codes instead via the `Colors` class defined in `live_logger.py`.

## Common Gotchas

1. **EventBus must be started**: Call `await event_bus.start()` before publishing events, or they'll queue but not process
2. **Strategy data cache**: Strategies need sufficient historical data before generating signals (check `min_data_points`)
3. **Order quantity precision**: Exchanges have minimum order sizes and precision requirements - handle in exchange gateway
4. **Async context**: Don't mix sync and async code carelessly - use `asyncio.run()` or `await` properly
5. **Decimal serialization**: When saving to JSON/database, convert Decimal to float/string explicitly
6. **Exchange rate limits**: Implement rate limiting in exchange gateways to avoid API bans
7. **WebSocket reconnection**: Data feeds should handle disconnections and reconnect automatically
8. **CLI command availability**: Many CLI commands show "Feature coming soon" - check the CLI Commands section above for what's actually implemented
9. **Strategy limitation**: Currently `ma_cross` and `adaptive_strategy` are implemented - adding new strategies requires updating CLI command handlers in `src/cli/commands/`
10. **Dashboard performance**: Real-time dashboards use Rich library for rendering - may consume more CPU on slower systems, use `--no-dashboard` flag for text-only output

## Performance Considerations

- EventBus queue size is limited (default 10000) - monitor queue depth
- Strategies should be computationally efficient in `on_market_data()` (runs on every tick)
- Use pandas vectorized operations in `calculate_indicators()` instead of loops
- Cache indicator calculations when possible
- For high-frequency strategies, consider using Redis for state management

## Available Skills

This repository includes custom Claude Code skills for specialized workflows. Use the Skill tool to invoke them.

### trading-feature-delivery

**Usage**: `/trading-feature-delivery` or invoke via Skill tool

**Purpose**: Implement or modify features in this Python trading system with safe integration across data feeds, strategy signals, execution, portfolio updates, and risk controls.

**When to use**:
- Adding new functionality to the trading system
- Fixing bugs in existing modules
- Refactoring code under `src/` while preserving runtime behavior
- Modifying event flow, order execution, or risk guardrails

**Workflow**:
1. Maps the request to relevant modules using architecture notes
2. Identifies data-flow edges (signal → order → fill → portfolio → risk events)
3. Implements minimal, cohesive edits in the owning package
4. Validates behavior with targeted checks
5. Summarizes changes, commands run, and any unresolved risks

**Engineering Rules**:
- Preserves Decimal-based money math for prices, balances, and quantity
- Keeps event payload contracts compatible with `src/core/event.py`
- Adds or updates tests for behavioral changes
- Prefers small patches and explicit failure handling

**References**:
- `skills/trading-feature-delivery/references/module-map.md`: Module ownership and integration points
- `skills/trading-feature-delivery/references/verification.md`: Command-level validation

### project-code-review

**Usage**: `/project-code-review` or invoke via Skill tool

**Purpose**: Perform structured code reviews for this Python trading repository with severity-ranked findings, concrete file/line references, and test-risk analysis.

**When to use**:
- Reviewing changes in `src/`, `scripts/`, `config/`
- Auditing trading, risk, data-feed, or backtest behavior
- Checking for behavior regressions, runtime failures, and missing test coverage
- Before committing critical changes to order execution or risk management

**Workflow**:
1. Collects evidence by running available checks
2. Inspects touched modules and their direct call chain
3. Identifies findings prioritized by severity (high, medium, low)
4. Checks test adequacy for changed behavior
5. Reports findings with file:line references, impact, and fix direction

**Review Rules**:
- Prioritizes concrete defects over style-only nits
- Treats order state consistency, fill-price correctness, and stop-loss logic as high-priority
- States explicitly when no findings are found
- Focuses on issues that can lose money, hide risk events, or break order lifecycle consistency

**References**:
- `skills/project-code-review/references/review-checklist.md`: Command sequence and risk-focused hotspots

## Context Management for Long Sessions

To prevent context window overflow during extended development sessions, follow these practices:

### Automatic Context Compression

Claude Code automatically compresses prior messages as the conversation approaches context limits. This means:
- Your conversation is not limited by the context window
- Older messages are summarized to preserve space
- Recent context and critical information are retained
- You can continue working indefinitely without manual intervention

### Manual Context Management Strategies

When working on complex tasks, use these strategies to keep context focused:

**1. Use Subagents for Isolated Tasks**

Delegate independent research or exploration to subagents using the Task tool:
```python
# Good: Use subagent for codebase exploration
Task(subagent_type="Explore", prompt="Find all strategy implementations")

# Good: Use subagent for complex multi-step tasks
Task(subagent_type="general-purpose", prompt="Research and implement new indicator")
```

**2. Summarize Completed Work**

After completing major milestones, create concise summaries:
- Document key decisions in MEMORY.md (kept under 200 lines)
- Update CLAUDE.md with new patterns or conventions
- Create topic-specific memory files for detailed notes

**3. Break Large Tasks into Phases**

For ambitious projects:
- Complete one phase fully before starting the next
- Commit working code at phase boundaries
- Document phase outcomes in git commit messages
- Start fresh conversations for new phases if needed

**4. Use Memory Files Effectively**

Store persistent information in `/Users/zixuan.liu/.claude/projects/-Users-zixuan-liu-workspace-bitcoin-stock-trading-system/memory/`:
- `MEMORY.md`: High-level patterns, conventions, and key decisions (always loaded, keep concise)
- Topic files: `debugging.md`, `patterns.md`, `architecture.md` for detailed notes
- Update memories when patterns are confirmed, remove outdated ones
- Link from MEMORY.md to topic files for organization

**5. Leverage Project Documentation**

Instead of re-explaining context:
- Reference CLAUDE.md for architecture and conventions
- Point to README.md for project overview
- Use inline code comments for complex logic
- Maintain up-to-date docstrings for public APIs

**6. Periodic Context Resets**

For very long sessions (100+ messages):
- Commit all working changes
- Start a new conversation with clear objectives
- Reference previous work via git history or documentation
- Use `/init` to reload project context from CLAUDE.md

### Best Practices for Context Efficiency

**DO**:
- Keep responses concise and focused
- Use tool calls instead of verbose explanations
- Reference file paths instead of pasting large code blocks
- Delegate independent tasks to subagents
- Update documentation instead of repeating information

**DON'T**:
- Paste entire files when discussing small changes
- Repeat architectural explanations already in CLAUDE.md
- Include verbose summaries of obvious actions
- Duplicate information across messages
- Keep debugging output in context after issues are resolved

### Monitoring Context Usage

Watch for these signs of context pressure:
- Responses becoming slower
- System reminders about context compression
- Difficulty recalling earlier conversation details
- Repeated questions about previously discussed topics

When you notice these signs, consider starting a fresh conversation or using subagents for new tasks.
