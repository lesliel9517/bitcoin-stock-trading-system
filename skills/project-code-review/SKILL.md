---
name: project-code-review
description: Perform structured code reviews for this Python trading repository with severity-ranked findings, concrete file/line references, and test-risk analysis. Use when asked to "review", "audit", or "check" changes in `src/`, `scripts/`, `config/`, or architecture and reliability of trading, risk, data-feed, or backtest behavior.
---

# Project Code Review

Run a bug-first review focused on behavior regressions, runtime failures, and missing test coverage. Prioritize issues that can lose money, hide risk events, or break order lifecycle consistency.

## Workflow

1. Collect evidence:
- Run available checks from `references/review-checklist.md`.
- Inspect touched modules and their direct call chain.

2. Identify findings:
- Prioritize concrete defects over style-only nits.
- Rank by severity: `high`, `medium`, `low`.
- Require file and line for every finding.

3. Check test adequacy:
- Confirm whether tests exist for changed behavior.
- Call out missing tests for order execution, risk checks, and signal handling paths.

4. Report in this format:
- Findings first, ordered by severity.
- `path:line` reference per finding.
- Short impact and fix direction.
- Then list residual risks and testing gaps.

## Review Rules

- Do not treat lint-only issues as primary findings unless they cause runtime defects.
- Treat order state consistency, fill-price correctness, and stop-loss logic as high-priority.
- State explicitly when no findings are found.
- If checks cannot run, state what failed and why.

## References

- Use `references/review-checklist.md` for command sequence and risk-focused hotspots.
