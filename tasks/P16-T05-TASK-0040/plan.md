# Plan: TASK-0040

1. Add `store_app = typer.Typer(help="Manage the SQLite packet store.")` in `cli/main.py`
2. Add `app.add_typer(store_app, name="store")`
3. Add `store_app.command("import")` — `store_import(ctx, dir: str)`:
   - Glob `assay-*.json` from dir
   - Parse each, skip with warning on error
   - Call `import_packets(packets, db_path)` once with the batch
   - Echo count
4. Tests in `tests/test_store_import_cmd.py`:
   - imports packets from dir
   - skips malformed JSON with warning
   - duplicate import does not error (INSERT OR REPLACE)
   - empty dir reports 0 imported
