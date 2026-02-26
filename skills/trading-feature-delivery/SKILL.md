---
name: trading-feature-delivery
description: Implement or modify features in this Python trading system with safe integration across data feeds, strategy signals, execution, portfolio updates, and risk controls. Use when adding functionality, fixing bugs, or refactoring modules under `src/` while preserving runtime behavior and testability.
---

# Trading Feature Delivery

Deliver repository-consistent changes with explicit verification. Focus on correctness in order execution, event flow, and risk guardrails before style cleanup.

## Workflow

1. Map the request to modules:
- Use architecture notes in `references/module-map.md`.
- Identify data-flow edges (signal -> order -> fill -> portfolio -> risk events).

2. Implement minimal, cohesive edits:
- Keep logic in owning package (`src/trading`, `src/risk`, `src/data`, etc.).
- Avoid broad refactors unless required by the task.

3. Validate behavior:
- Run targeted checks from `references/verification.md`.
- Prefer reproducer-first verification for bug fixes.

4. Finalize with clear output:
- Summarize what changed and why.
- List commands run and outcomes.
- State any unresolved risks.

## Engineering Rules

- Preserve Decimal-based money math for prices, balances, and quantity.
- Keep event payload contracts compatible with `src/core/event.py`.
- Add or update tests for behavioral changes; do not leave silent regressions.
- Prefer small patches and explicit failure handling over implicit assumptions.

## References

- Use `references/module-map.md` for ownership and integration points.
- Use `references/verification.md` for command-level validation.
