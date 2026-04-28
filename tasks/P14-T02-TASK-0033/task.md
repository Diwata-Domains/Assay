# Task: assay report --format html --open: auto-open report in default browser

## Metadata
- **ID:** TASK-0033
- **Status:** done
- **Phase:** Phase 14 — HTML Report
- **Backlog:** P14-T02
- **Packet Path:** tasks/P14-T02-TASK-0033/
- **Dependencies:** TASK-0032
- **Primary Adapter:** code_adapter
- **Secondary Adapters:** none

## Objective
Add an `--open` flag to `assay report` that, when combined with `--format html`, automatically opens the generated HTML report in the system default browser after writing it to disk.

## Why This Task Exists
The HTML report is more useful when it opens immediately after generation — one command from run to review.

## Scope
- `src/assay/cli/main.py` — add `--open` boolean flag to the `report` command
- When `--format html --open` is used: after writing `assay-report.html`, call `webbrowser.open(path)` using Python's stdlib `webbrowser` module
- When `--open` is used without `--format html`: print a warning (`--open is only supported with --format html`) and continue without error
- `tests/test_report_open.py` — unit test: confirm `webbrowser.open` is called with the correct path when `--open` is set; mock the call so no browser actually opens in tests

## Constraints
- Use Python stdlib `webbrowser` — no third-party library
- `--open` with non-HTML formats must not error — warn and no-op
- Ruff + mypy must pass after implementation

## Escalation Conditions
- None anticipated
