# Grain <-> Assay Verification Handshake

**Last updated:** 2026-05-08
**Status:** authoritative for Phase 18 implementation

---

## Overview

Grain's `verify` command group bridges external verification tools into the task packet lifecycle. Assay is the only supported provider (`--provider assay`). The handshake has three actors: the Grain CLI (operator-side), the Assay CLI/ingest server (verifier-side), and the shared packet filesystem.

---

## Lifecycle

```
1. grain verify submit --id TASK-XXXX
   → Creates tasks/<packet-dir>/verification_request.json
   → Updates results.md: Verification Review state = pending
   → verification_id assigned: VERIFY-XXXX-NNN (e.g. VERIFY-0041-001)

2. assay run --target <url> --task-id TASK-XXXX --verification-id VERIFY-XXXX-NNN
   (or: assay serve + SDK POST /ingest with verification_id in metadata)
   → Generates packet with verification_id = VERIFY-XXXX-NNN (not a UUID)
   → Writes packet to output dir + SQLite store

3. assay submit --packet <packet.json>
   → Copies packet to grain output path (configured via [grain] output_path)
   → Packet lands in grain's "inbox"

4. grain verify ingest --verification-id VERIFY-XXXX-NNN --payload <packet.json>
   → Validates payload against request
   → Creates tasks/<packet-dir>/verification_result.json
   → Updates verification_request.json: status = complete / failed
   → Updates results.md: state = passed / failed, findings written
```

---

## Payload Requirements (grain verify ingest)

The assay packet JSON passed to `grain verify ingest --payload` must satisfy:

| Field | Type | Constraints |
|-------|------|-------------|
| `verification_id` | string | Must exactly match the `VERIFY-XXXX-NNN` from the request |
| `task_id` | string | Must match request's `task_id` |
| `issue_type` | string | One of: `test_failure`, `bug_finding`, `screenshot_evidence`, `trace_capture`, `human_annotation` |
| `severity` | string | One of: `info`, `warning`, `error`, `critical` |
| `outcome` | string | One of: `pass`, `fail`, `inconclusive` |
| `summary` | string | Non-empty |
| `artifact_refs` | list[str] | Optional |
| `followup_candidates` | list | Optional |
| `verified_at` | string | Optional ISO 8601 |

---

## The verification_id Gap

**Problem:** Assay currently generates a UUID for `verification_id` in every packet. Grain's `verify ingest` rejects any payload whose `verification_id` does not match the `VERIFY-XXXX-NNN` format from the submitted request.

**Solution (P18-T02):** Add `--verification-id` flag to `assay run`. When provided, the packet uses that value instead of generating a UUID. The ingest `/ingest` endpoint already accepts `task_id` passthrough; a `verification_id` field in `metadata` should be wired the same way.

---

## Idempotency

Grain's `_next_verification_id` increments a suffix per task. Re-running `grain verify submit` on the same task creates `VERIFY-XXXX-002`, `VERIFY-XXXX-003`, etc. The assay operator must pass the correct `--verification-id` matching the active request.

If `assay submit` (or `--submit`) is run before `grain verify submit`, the packet lands with a UUID `verification_id` — grain will reject it at ingest. **Always run `grain verify submit` first to get the verification_id, then pass it to assay.**

---

## File Locations (default paths)

| Artifact | Path |
|----------|------|
| Verification request | `tasks/<packet-dir>/verification_request.json` |
| Verification result | `tasks/<packet-dir>/verification_result.json` |
| Assay output packets | `[output.directory]/assay-*.json` (default `./assay-output/`) |
| Grain output path | `[grain.output_path]` in `assay.toml` |

---

## Required Assay Changes (Phase 18)

| Task | Change |
|------|--------|
| P18-T02 | `assay run --verification-id VERIFY-XXXX-NNN`: override verification_id in packet |
| P18-T02 | `/ingest` payload: accept `verification_id` in `metadata` dict → propagate to packet |
| P18-T03 | `GET /status/{verification_id}`: proxy request status from SQLite store |
| P18-T04 | `assay submit`: validate `verification_id` format before copy; warn if UUID-shaped |
| P18-T05 | Integration test: full submit → run → submit → ingest loop with fixtures |
