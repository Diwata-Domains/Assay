# Task: verification_id idempotency for resubmits

## Metadata
- **ID:** TASK-0045
- **Status:** done
- **Phase:** P18-T02
- **Backlog:** P18-T02 — verification_id idempotency for resubmits
- **Packet Path:** tasks/P18-T02-TASK-0045/
- **Dependencies:** TASK-0044
- **Primary Adapter:** none
- **Secondary Adapters:** none

## Objective
Add `--verification-id` flag to `assay run` so operators can pass the grain-issued `VERIFY-XXXX-NNN` ID. When provided, the packet uses that value instead of generating a UUID. Also wire `verification_id` passthrough in `/ingest` via the `metadata` dict.

## Why This Task Exists
`grain verify ingest` validates that the payload's `verification_id` exactly matches the request's `VERIFY-XXXX-NNN`. Assay currently generates UUIDs — the mismatch blocks the handshake.

## Scope
- Add `--verification-id` Option to `assay run`
- Pass it to `format_packet()` so packet uses it instead of UUID
- Accept `verification_id` key in `IngestPayload.metadata` → propagate to packet
- Tests cover both CLI flag and ingest metadata passthrough

## Constraints
- Backwards compatible: omitting the flag behaves as today (UUID generated)
- `format_packet` must accept an optional `verification_id` override

## Escalation Conditions
- None
