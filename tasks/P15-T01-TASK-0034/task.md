# Task: assay run --watch: re-run on file/path change

## Metadata
- **ID:** TASK-0034
- **Status:** done
- **Phase:** Phase 15 — Watch Mode
- **Backlog:** P15-T01
- **Packet Path:** tasks/P15-T01-TASK-0034/
- **Dependencies:** TASK-0006 (runner), TASK-0032 (report)
- **Primary Adapter:** code_adapter
- **Secondary Adapters:** none

## Objective
Add a `--watch` flag to `assay run` that polls for file changes in the current directory and re-runs the test suite automatically when a change is detected. Debounce is 500ms — re-run fires 500ms after the last observed change.

## Why This Task Exists
Speeds up the inner dev loop: instead of manually re-triggering `assay run` after each edit, the watcher keeps the suite running and reports results immediately on save.

## Scope
- `src/assay/watch/` — new module:
  - `__init__.py`
  - `poller.py` — `poll_for_changes(paths, interval_ms)` using `os.stat()` mtime tracking; no external deps
- `src/assay/cli/main.py` — add `--watch` boolean flag and `--watch-path` (default `.`) to `run` command; when `--watch` is set, enter the watch loop after the initial run
- Watch loop: initial run → poll → on change, debounce 500ms → re-run → repeat; Ctrl+C exits cleanly
- `tests/test_watch_poller.py` — unit tests for the poller: detects changed mtime, ignores unchanged, handles missing files gracefully
- `tests/test_watch_cli.py` — CLI integration: `--watch` runs once then loops; Ctrl+C (KeyboardInterrupt) exits 0

## Constraints
- No external dependencies — polling via stdlib `os.stat()`
- Default watch path is `.` (current directory); recursive
- Debounce: 500ms after last detected change before re-running
- Ctrl+C must exit cleanly (exit 0)
- Existing `assay run` behavior without `--watch` must not change
- Ruff + mypy must pass

## Escalation Conditions
- If Docker runner startup time makes watch mode impractical, flag for operator review before implementing run throttling
