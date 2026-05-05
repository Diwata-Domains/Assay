# Plan: TASK-0043

1. Add `GET /packet/{verification_id}` to `ingest/app.py`:
   - Fetch all packets, find by verification_id
   - Return 404 HTMLResponse if not found
   - Render detail page: `<dl>` for all fields
   - If artifact_refs has a `.png` path that exists → inline `<img src="data:image/png;base64,...">`

2. Tests in `tests/test_packet_detail.py`:
   - 200 with packet fields rendered
   - inline screenshot when png exists on disk
   - screenshot omitted when file missing
   - 404 for unknown verification_id
