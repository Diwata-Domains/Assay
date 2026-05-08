# Task: Harden assay submit and --submit flows

## Metadata
- **ID:** TASK-0047
- **Status:** done
- **Phase:** P18-T04
- **Backlog:** P18-T04 — Harden assay submit and --submit flows
- **Packet Path:** tasks/P18-T04-TASK-0047/
- **Dependencies:** TASK-0045
- **Primary Adapter:** none
- **Secondary Adapters:** none

## Objective
Warn operators when `assay submit` (or `--submit`) submits a packet whose `verification_id` is a UUID (not `VERIFY-XXXX-NNN` format). The packet is still submitted — warn only, do not abort.

## Why This Task Exists
Submitting a UUID-verification_id packet to grain's output path will cause `grain verify ingest` to reject it with a mismatched verification_id error. An early warning prevents silent failures.

## Scope
- Add UUID-detection check in `_do_submit`
- Emit warning to stderr if `verification_id` matches UUID pattern and not VERIFY-XXXX-NNN
- Do not abort — warning only
- Tests: update `tests/test_submit.py` or add new test

## Constraints
- Backwards compatible: submit still succeeds
- Warning only on stdout/stderr, no exit code change

## Escalation Conditions
- None
