# Plan: TASK-0042

1. In `ingest/app.py` dashboard route:
   - Add `screenshot` column to thead
   - For each row: check `artifact_refs` for any `.png` item → "yes" / "no"
   - `verification_id` already links to `/packet/{vid}`

2. Update `test_dashboard.py`:
   - Test screenshot "yes" when artifact_refs contains a png path
   - Test screenshot "no" when artifact_refs is empty
