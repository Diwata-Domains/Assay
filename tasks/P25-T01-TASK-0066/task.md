# Task: `assay check` command + `[checks]` config block in assay.toml

## Metadata
- **ID:** TASK-0066
- **Status:** done
- **Phase:** Phase 25 — Functional + Integration Checks
- **Backlog:** P25-T01
- **Packet Path:** tasks/P25-T01-TASK-0066/
- **Dependencies:** Phase 22 close
- **Primary Adapter:** code

## Objective
Add a `[checks]` config block to assay.toml and a new `assay check` CLI command that runs all named checks and prints a pass/fail table. Each check has an `id`, `type` (http | header | auth | functional), `target` URL, and type-specific assertion fields. Results are written to the SQLite store and printed as a table. A `--check <id>` flag runs a single named check. Exit 1 if any assertion fails.

## Why This Task Exists
Phase 25 elevates Assay from a screenshot tool into a genuine verifier. This task is the entry point — the config schema and CLI command that all subsequent assertion engine tasks (T02–T04) plug into.

## Scope
- Add `[checks]` TOML array-of-tables to `AssayConfig` in `config.py`
- Define `CheckConfig` dataclass: `id`, `type`, `target`, plus optional assertion fields (populated by later tasks)
- Add `assay check` command to CLI: loads config, iterates checks, dispatches by type, prints table, exits 1 on any failure
- Add `--check <id>` flag to run a single named check
- Write check results to SQLite store (new `check_results` table or reuse packet store)
- Tests: config parsing, CLI dispatch, table output, exit codes

## Deliverable
`src/assay/checks/` module with `check_config.py` and `runner.py`; `assay check` wired in CLI; `[checks]` parseable from `assay.toml`; tests passing.

## Constraints
- `assay check` must be composable with `assay run` — they share the SQLite store
- Check result schema must be stable enough for T05 (dashboard) to consume without migration
- Exit codes: 0 = all pass, 1 = any failure, 2 = config error
