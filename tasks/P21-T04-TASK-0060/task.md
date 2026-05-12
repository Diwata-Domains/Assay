# Task: Approve/reject workflow — accept new baseline or flag as regression

## Metadata
- **ID:** TASK-0060
- **Status:** done
- **Phase:** P21-T04
- **Backlog:** P21-T04 — Approve/reject workflow: accept new baseline or flag as regression
- **Packet Path:** tasks/P21-T04-TASK-0060/
- **Dependencies:** P21-T03 complete (diff view)
- **Primary Adapter:** none
- **Secondary Adapters:** none

## Objective
Add an approve/reject workflow to packet detail. When viewing a packet that has a diff_result, the user can:
- **Approve**: promote this capture as the new baseline for its URL
- **Reject**: mark the packet outcome as "regression" and record the reviewer decision

## Scope
- `store/db.py`: add `review_status TEXT` column (nullable: "approved" | "rejected"); add `set_review_status(verification_id, status, db_path)` function
- `ingest/app.py`:
  - `POST /packet/{id}/approve` — sets this packet as baseline AND sets review_status="approved"; redirects to /packet/{id}
  - `POST /packet/{id}/reject` — sets review_status="rejected"; redirects to /packet/{id}
  - Packet detail: show Approve / Reject buttons when diff_result is present AND packet is not already baseline
  - Packet detail: show review_status badge when set ("approved" / "regression")
- Tests: `tests/test_review.py` — approve sets baseline + status; reject sets status; both redirect; badge shown in detail

## Constraints
- Approve/Reject only meaningful on packets with diff_result
- review_status stored in both the `review_status` DB column and in the raw JSON (so it's surfaced via list_packets)
- Migration: `ALTER TABLE IF NOT EXISTS` pattern (same as diff_result)

## Escalation Conditions
- None
