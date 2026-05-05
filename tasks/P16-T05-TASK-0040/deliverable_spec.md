# Deliverable Spec: TASK-0040

- `assay store import --dir <path>` subcommand
- Reads `assay-*.json` files, upserts into SQLite
- Skips malformed files with warning
- Reports count: `imported: N packet(s)`
- Tests: `tests/test_store_import_cmd.py`
