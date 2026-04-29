# Deliverable Spec: TASK-0038

- `assay report` reads from SQLite via `list_packets`
- `--filter key=value` applied post-query
- `--format text/json/html` unchanged
- Graceful empty result when db missing
- Tests: `tests/test_report_sqlite.py`
