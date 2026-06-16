# Plan: TASK-0047

1. In `_do_submit` in `cli/main.py`:
   - After reading the packet JSON, check `data.get("verification_id", "")`
   - If it matches UUID pattern (`^[0-9a-f]{8}-[0-9a-f]{4}-...`) and NOT `VERIFY-` prefix: emit `warning: verification_id is a UUID — grain verify ingest will reject this packet; use --verification-id VERIFY-XXXX-NNN`
   - Then proceed with copy as normal

2. Tests: `tests/test_submit_warn.py`
   - Warning emitted for UUID verification_id
   - No warning for VERIFY-XXXX-NNN verification_id
   - Submit still succeeds in both cases
