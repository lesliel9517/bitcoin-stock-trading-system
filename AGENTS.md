# Repository Guidelines

## Project Structure & Module Organization
Core code lives in `src/`, organized by domain:
- `src/core`: event bus, types, and engine primitives.
- `src/data`: market feeds, providers, and storage models.
- `src/strategies`: strategy base classes, indicators, and examples.
- `src/trading`, `src/risk`, `src/backtest`, `src/monitor`, `src/cli`: execution, controls, simulation, observability, and CLI commands.

Configuration is in `config/` (system, exchange, risk, and strategy YAML files). Runtime artifacts are under `data/` (`data/db/`, `data/logs/`). Examples and helper scripts are in `examples/` and `scripts/`.

## Build, Test, and Development Commands
- `python -m venv venv && source venv/bin/activate`: create and activate local environment.
- `pip install -r requirements.txt`: install dependencies.
- `pip install -e .`: install editable package and expose `btc-trade` CLI.
- `pytest`: run all tests.
- `pytest --cov=src --cov-report=html`: generate coverage report.
- `black src/ tests/`: format code.
- `flake8 src/ tests/`: lint style issues.
- `mypy src/`: run static type checks.
- `btc-trade --help`: inspect CLI entry points.

## Coding Style & Naming Conventions
Use Python 3.10+ with 4-space indentation and PEP 8 defaults. Prefer:
- `snake_case` for functions, methods, variables, and module files.
- `PascalCase` for classes.
- Small, single-purpose modules under the domain package that owns the behavior.

Run `black`, `flake8`, and `mypy` before opening a PR.

## Testing Guidelines
Use `pytest` (plus `pytest-asyncio` where needed). Place tests under `tests/unit/` or `tests/integration/`, and name files `test_*.py`. Keep new logic covered with focused unit tests and add integration tests for cross-module workflows (for example, strategy -> order -> risk checks).

## Commit & Pull Request Guidelines
Local Git history is not available in this workspace snapshot, so use clear, scoped commits:
- `feat: add trailing stop rule`
- `fix: handle empty candle stream in binance feed`

PRs should include:
- what changed and why,
- affected modules (e.g., `src/risk/manager.py`),
- test evidence (`pytest` output or coverage delta),
- config or env changes (`.env`, `config/*.yaml`), if any.

## Security & Configuration Tips
Never commit secrets. Keep credentials only in `.env` (seed from `.env.example`). Use simulation mode first (`btc-trade trade start ... --mode simulation`) before any live execution.
