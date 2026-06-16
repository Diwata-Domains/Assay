# Task: `assay run --submit` one-step flag

## Metadata
- **ID:** TASK-0026
- **Status:** done
- **Phase:** Phase 12 — Grain Task Tagging + assay submit
- **Backlog:** P12-T04
- **Packet Path:** tasks/P12-T04-TASK-0026/
- **Dependencies:** TASK-0025
- **Primary Adapter:** none
- **Secondary Adapters:** none

## Objective
Add `--submit` boolean flag to `assay run`. When set, after writing the packet, call `_do_submit()` to copy it to `[grain].output_path`. This enables run + submit in one command without a separate `assay submit` invocation.

## Why This Task Exists
Reduces friction for Grain users who want every run automatically submitted.

## Scope
- `--submit` flag on `assay run`
- After `write_packet()`, if `--submit`: call `_do_submit(str(packet_path), config)`
- Exit codes unchanged — `--submit` failure prints error but doesn't override run exit code

## Constraints
- `--submit` without `[grain].output_path` configured should error (inherits from `_do_submit`)

## Escalation Conditions
- None
