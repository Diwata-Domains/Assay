# Context: TASK-0038

`assay report` currently scans `assay-*.json` files from an output directory. Now that `assay run` and `/ingest` write to SQLite (TASK-0037), the report command should read from the store instead.

The `list_packets` function in `src/assay/store/db.py` already supports `outcome` and `task_id` filters and returns `list[dict[str, object]]` — compatible with the existing rendering pipeline.
