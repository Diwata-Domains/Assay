# Plan: TASK-0041

1. Add `GET /` route in `ingest/app.py`:
   - Read `store_db` from `request.app.state.store_db`
   - Call `list_packets(Path(store_db).expanduser())`
   - Count totals by outcome
   - Render HTML string inline (summary counts + packet table)
   - Return `HTMLResponse`

2. Tests in `tests/test_dashboard.py`:
   - `GET /` returns 200
   - Response contains packet data from the store
   - Empty store renders "no packets" message
   - `/ingest` POST still works after adding the route
