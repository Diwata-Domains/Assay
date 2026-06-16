# Task: GitHub Actions CI (pytest + ruff + mypy + vitest)

## Metadata
- **ID:** TASK-0019
- **Status:** done
- **Phase:** Phase 10 — Distribution + CI
- **Backlog:** P10-T02
- **Packet Path:** tasks/P10-T02-TASK-0019/
- **Dependencies:** Phase 9 complete
- **Primary Adapter:** none
- **Secondary Adapters:** none

## Objective
Create `.github/workflows/ci.yml` to run the full test and lint suite on every push and pull request. Matrix Python 3.11 and 3.12. Separate job for TypeScript SDK vitest.

## Why This Task Exists
Prevents regressions from reaching main. Phase 10 exit criterion: CI is green on main.

## Scope
- `python` job: `pip install -e ".[dev]"` → ruff → mypy → pytest
- `sdk` job: `npm ci` + `npm test` (vitest) in `sdk/` directory
- Triggers: all branches, all PRs

## Constraints
- Must use `pip install -e ".[dev]"` — the `[dev]` optional group contains pytest, ruff, mypy
- SDK job must only run vitest, not build (build is for release only)

## Escalation Conditions
- None
