# Verification

## Baseline Commands

- `./.venv/bin/pytest -q`
- `./.venv/bin/flake8 src tests scripts --count`
- `./.venv/bin/mypy src`

## Targeted Checks

- For execution/order changes:
  - Run scenario scripts in `scripts/test_realtime_trading.py`.
- For risk changes:
  - Run `scripts/test_risk_management.py`.
- For backtest changes:
  - Run `examples/quick_backtest.py`.

## Evidence Format

- Include exact commands executed.
- Include pass/fail and key error lines.
- Mention what was not run and why.
