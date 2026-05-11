# Task: SDK taskId and verificationId passthrough

## Metadata
- **ID:** TASK-0051
- **Status:** done
- **Phase:** P19-T03
- **Backlog:** P19-T03 — SDK taskId and verificationId passthrough
- **Packet Path:** tasks/P19-T03-TASK-0051/
- **Dependencies:** P12-T05 complete, P18 complete
- **Primary Adapter:** none
- **Secondary Adapters:** none

## Objective
Add `taskId` and `verificationId` optional fields to `CaptureOptions` in the browser SDK so callers can pass Grain-issued identifiers through to the ingest payload without needing post-hoc hacks.

## Why This Task Exists
The ingest endpoint already accepts `task_id` and `verification_id`, and the CLI supports `--task-id` and `--verification-id`. The SDK `capture()` call is the missing link — CRM apps calling `sdk.capture()` need to be able to pass these IDs inline at capture time.

## Scope
- Add `taskId?: string` and `verificationId?: string` to `CaptureOptions` in `sdk.ts`
- Include `task_id` and `verification_id` in the payload when provided
- Update `capture.test.ts` with tests for both fields
- No changes to the ingest endpoint (already accepts both fields)

## Constraints
- Fields are optional; existing captures without them must continue to work
- No public API breakage

## Escalation Conditions
- None
