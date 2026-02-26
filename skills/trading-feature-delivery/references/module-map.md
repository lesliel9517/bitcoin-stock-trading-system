# Module Map

## Core Runtime Path

1. `src/data/*` publishes `MarketEvent` through `EventBus`.
2. `src/strategies/*` consume market events and publish `SignalEvent`.
3. `src/trading/execution.py` converts signals into orders.
4. `src/trading/order_manager.py` submits orders to exchange gateways.
5. `src/core/event.py` `FillEvent` updates portfolio and risk state.

## Ownership Guidelines

- Event models and contracts: `src/core/`.
- Strategy behavior: `src/strategies/`.
- Order state and exchange interaction: `src/trading/`.
- Position sizing and stop controls: `src/risk/`.
- Historical simulation: `src/backtest/`.
- CLI surface: `src/cli/commands/`.
