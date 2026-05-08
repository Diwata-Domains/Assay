# Deliverable Spec: TASK-0046

- `GET /status/{verification_id}` returns JSON status
- 200 with complete/outcome/verified_at when found
- 404 when not found
- Tests: `tests/test_status_endpoint.py`
