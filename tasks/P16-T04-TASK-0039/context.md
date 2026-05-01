# Context: TASK-0039

`assay report` now reads from SQLite. This task adds `--export <path>` to dump the (filtered) packet list to a JSON file, providing backwards compatibility for users who relied on the old on-disk JSON files.
