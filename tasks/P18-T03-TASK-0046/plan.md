# Plan: TASK-0046

1. Add `GET /status/{verification_id}` to `ingest/app.py`:
   - Fetch all packets, find by verification_id
   - If found: return `{"status": "complete", "outcome": ..., "verified_at": ...}`
   - If not found: return 404 JSON `{"status": "not_found"}`

2. Tests in `tests/test_status_endpoint.py`:
   - 200 with complete status when packet exists
   - 404 when verification_id unknown
   - outcome field matches stored packet
