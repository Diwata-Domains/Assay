# Task: Pixel diff engine — compare new capture against baseline, generate diff image

## Metadata
- **ID:** TASK-0058
- **Status:** in_progress
- **Phase:** P21-T02
- **Backlog:** P21-T02 — Pixel diff engine: compare new capture against baseline, generate diff image
- **Packet Path:** tasks/P21-T02-TASK-0058/
- **Dependencies:** P21-T01 complete (baseline capture)
- **Primary Adapter:** none
- **Secondary Adapters:** none

## Objective
Add a pixel-level diff engine that compares a new screenshot against the stored baseline screenshot for the same URL. Store the diff result (diff image + stats) as part of the packet. Expose diff data via the store so the dashboard and API can surface it.

## Scope
- `src/assay/diff/engine.py`: `diff_images(baseline_path, candidate_path, diff_path) -> DiffResult`
  - Use `Pillow` (already available or add as dependency) for per-pixel comparison
  - `DiffResult`: dataclass with `changed_pixels: int`, `total_pixels: int`, `diff_pct: float`, `diff_image_path: str`
  - Highlight differing pixels in red on a copy of the candidate image; save to `diff_path`
- `src/assay/store/db.py`: add `diff_result TEXT` column to `packets` table (nullable, JSON); update `insert_packet`, `list_packets`, `init_db`
- On `/ingest`: after saving screenshot, if a baseline exists for the URL, run diff and attach `diff_result` to packet before storing
- `GET /packet/{id}` detail view: if packet has `diff_result`, show diff stats (changed px, %) and inline diff image
- Tests: `tests/test_diff_engine.py` — identical images (0% diff), fully different images (100%), partial diff, missing file raises
- Tests: `tests/test_diff_ingest.py` — ingest with baseline present attaches diff_result; without baseline no diff_result

## Constraints
- Pillow must be added to pyproject.toml if not already present
- diff column is nullable — packets without a baseline comparison have no diff_result
- Diff image stored in the same output dir as screenshots: `{verification_id}_diff.png`
- No schema migration needed beyond `ALTER TABLE IF NOT EXISTS` — use `ADD COLUMN IF NOT EXISTS` pattern or re-create via `init_db` (new installs already get it; existing DBs need migration)

## Escalation Conditions
- None
