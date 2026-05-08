# Task: End-to-end integration tests for verify flow

## Metadata
- **ID:** TASK-0048
- **Status:** done
- **Phase:** P18-T05
- **Backlog:** P18-T05 — End-to-end integration tests for verify flow
- **Packet Path:** tasks/P18-T05-TASK-0048/
- **Dependencies:** TASK-0044, TASK-0045, TASK-0046, TASK-0047
- **Primary Adapter:** none
- **Secondary Adapters:** none

## Objective
Write `tests/test_verify_e2e.py` covering the full Grain-Assay verify loop using fixtures — from packet generation with `--verification-id` through submit, status check, and simulated `grain verify ingest` payload validation.

## Why This Task Exists
The individual pieces are tested in isolation. This test verifies the complete handshake works end-to-end: correct verification_id propagation, packet format accepted by grain's `_validate_ingest_payload`, status endpoint reflecting the result.

## Scope
- Generate assay packet with `--verification-id VERIFY-XXXX-NNN`
- Verify packet matches grain's `_validate_ingest_payload` requirements
- Submit packet; verify it lands in grain output path with correct verification_id
- Call `GET /status/{verification_id}`; verify complete status
- All without mocking the verification_id path

## Constraints
- Does not call `grain verify ingest` CLI (avoid cross-product dependency in unit tests)
- Validates payload against grain's schema rules directly in the test

## Escalation Conditions
- None
