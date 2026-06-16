# Task: Save SDK screenshot to disk on ingest; populate artifact_refs

## Metadata
- **ID:** TASK-0020
- **Status:** done
- **Phase:** Phase 11 — Screenshot Persistence + assay report
- **Backlog:** P11-T01
- **Packet Path:** tasks/P11-T01-TASK-0020/
- **Dependencies:** Phase 5 complete
- **Primary Adapter:** none
- **Secondary Adapters:** none

## Objective
When `POST /ingest` receives a base64 screenshot from the browser SDK, decode and write it as `{verification_id}.png` in the output directory. Populate `artifact_refs` in the packet with the saved file path.

## Why This Task Exists
Previously the base64 screenshot was validated but discarded — it was never persisted to disk. Phase 11 exit criterion requires a `.png` file alongside every packet.

## Scope
- `_save_screenshot()` helper in `src/assay/ingest/app.py`
- Decode base64 → write bytes to `{output_dir}/{verification_id}.png`
- Set `packet["artifact_refs"] = [screenshot_path]` before `write_packet()`

## Constraints
- Screenshot filename must be `{verification_id}.png` for consistency with runner flow

## Escalation Conditions
- None
