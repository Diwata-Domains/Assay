# Plan: TASK-0038

1. Modify `report` command in `cli/main.py`:
   - Accept `--db` option (defaults to `config.store.db`)
   - Call `list_packets(db_path)` to load packets
   - Apply `--filter` on the in-memory list (same logic as today)
   - Pass packets to existing text/json/html renderers unchanged

2. Keep `--output` option for backwards compatibility (used only by html renderer to find screenshots on disk).

3. Add tests in `tests/test_report_sqlite.py`:
   - `report` reads from SQLite db
   - `--filter outcome=fail` filters correctly
   - `--format json` and `--format html` still work
   - Empty db returns "no packets found"
