# Plan: TASK-0045

1. `formatter/formatter.py`: add `verification_id: str | None = None` param to both `format_packet` and `format_sdk_packet`; use it instead of `str(uuid4())` when provided

2. `cli/main.py` `run` command: add `--verification-id` Option; pass to `format_packet(bundle, task_id=..., verification_id=...)`

3. `ingest/app.py`: in `ingest` handler, check `payload.metadata.get("verification_id")` and pass to `format_sdk_packet(..., verification_id=...)`

4. Tests: `tests/test_verification_id_passthrough.py`
   - CLI `--verification-id` sets packet verification_id
   - Omitting flag generates UUID (backwards compat)
   - Ingest metadata verification_id passthrough
