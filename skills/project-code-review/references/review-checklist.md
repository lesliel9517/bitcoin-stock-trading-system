# Review Checklist

## Quick Commands

- `./.venv/bin/pytest -q`
- `./.venv/bin/flake8 src tests scripts --count`
- `./.venv/bin/mypy src`

## High-Risk Hotspots

- `src/trading/order_manager.py`: order lifecycle, active order cleanup, fill events.
- `src/trading/exchanges/*.py`: execution price, balance/position validation, ID mutation.
- `src/risk/*.py`: stop-loss/take-profit checks and risk-event emission.
- `src/backtest/engine.py`: strategy integration and signal simulation path.
- `src/core/event_bus.py`: event dispatch behavior and error handling.

## Finding Quality Bar

- Always include `path:line`.
- Explain impact in one sentence.
- Propose a direct fix direction.
- Mark missing tests when behavior changes.
