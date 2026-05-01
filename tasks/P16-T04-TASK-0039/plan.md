# Plan: TASK-0039

1. Add `--export` option (Optional[str]) to `report` command in `cli/main.py`
2. After the filter step, if `--export` is set: write `json.dumps(packets, indent=2)` to the given path and echo confirmation
3. Continue into the normal `--format` rendering (export is orthogonal to format)
4. Tests in `tests/test_report_export.py`:
   - `--export` writes valid JSON file
   - `--export` respects `--filter`
   - `--export` with `--format text` still renders text table
   - `--export` with no packets writes empty array
