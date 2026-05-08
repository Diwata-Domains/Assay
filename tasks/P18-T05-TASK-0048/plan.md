# Plan: TASK-0048

1. `tests/test_verify_e2e.py`:
   a. Generate packet via `format_packet(bundle, task_id="TASK-0041", verification_id="VERIFY-0041-001")`
   b. Write packet JSON to tmp_path
   c. Assert packet passes grain's `_validate_ingest_payload` rules (inline validation, no import from grain)
   d. Submit via CLI `assay submit --packet <path>` with grain output_path configured
   e. Verify submitted packet has correct verification_id
   f. Insert packet into SQLite; call `GET /status/VERIFY-0041-001`; assert complete

2. Also test: packet generated without `--verification-id` fails the VERIFY format check (UUID-shaped vid is not VERIFY-format) — confirms the warning in _do_submit is warranted
