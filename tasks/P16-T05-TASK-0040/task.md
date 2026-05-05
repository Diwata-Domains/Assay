# Task: assay store import --dir

## Metadata
- **ID:** TASK-0040
- **Status:** done
- **Phase:** P16-T05
- **Backlog:** P16-T05 — assay store import --dir: import existing assay JSON files
- **Packet Path:** tasks/P16-T05-TASK-0040/
- **Dependencies:** TASK-0036
- **Primary Adapter:** none
- **Secondary Adapters:** none

## Objective
Add `assay store import --dir <path>` subcommand that reads all `assay-*.json` files from the given directory and imports them into the SQLite store via `import_packets`.

## Why This Task Exists
Phase 16 goal: users who accumulated data in the old file-based format can migrate to the store without manual work.

## Scope
- New `store_app` sub-typer added to the CLI
- `store import --dir <path>` subcommand
- Uses `import_packets` from `assay.store.db`
- Prints count of imported packets
- Skips unparseable files with a warning

## Constraints
- Must not duplicate existing rows (import_packets uses INSERT OR REPLACE)
- `store` subcommand must be reachable as `assay store import`

## Escalation Conditions
- None anticipated
