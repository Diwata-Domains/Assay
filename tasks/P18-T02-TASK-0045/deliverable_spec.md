# Deliverable Spec: TASK-0045

- `assay run --verification-id VERIFY-XXXX-NNN` sets packet verification_id
- `/ingest` metadata.verification_id propagates to packet
- Backwards compatible (no flag = UUID as before)
- Tests: `tests/test_verification_id_passthrough.py`
