# Task: Document canonical Grain-Assay handshake

## Metadata
- **ID:** TASK-0044
- **Status:** done
- **Phase:** P18-T01
- **Backlog:** P18-T01 — Document canonical Grain-Assay handshake
- **Packet Path:** tasks/P18-T01-TASK-0044/
- **Dependencies:** TASK-0036, P12 complete
- **Primary Adapter:** none
- **Secondary Adapters:** none

## Objective
Document the canonical end-to-end Grain<->Assay handshake in `docs/working/grain_assay_handshake.md`. Covers the full lifecycle: verify submit → assay run → assay submit → grain verify ingest.

## Why This Task Exists
The verification_id format mismatch is the blocking gap: grain requires VERIFY-XXXX-NNN in the payload but assay generates UUIDs. This doc captures that gap and defines the required changes for P18-T02 onward.

## Scope
- Write `docs/working/grain_assay_handshake.md`
- Cover: lifecycle steps, payload schema requirements, the verification_id gap, required assay changes

## Constraints
- No code changes — docs only

## Escalation Conditions
- None
