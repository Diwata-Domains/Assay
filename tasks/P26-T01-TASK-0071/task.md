# Task: Extend [grain] config for auto-task creation

## Metadata
- **ID:** TASK-0071
- **Status:** done
- **Phase:** Phase 26 — Auto Grain Task on Failure
- **Backlog:** P26-T01
- **Packet Path:** tasks/P26-T01-TASK-0071/
- **Dependencies:** Phase 25 complete
- **Primary Adapter:** code

## Objective
Extend `GrainConfig` in `config.py` with four new fields that control automatic Grain task creation: `repo`, `auto_create`, `phase`, and `branch`. These fields are parsed from the existing `[grain]` section in `assay.toml` — no new TOML section needed.

## Why This Task Exists
Phase 26 needs a place to configure where to write auto-created Grain tasks and whether to do so at all. These config fields gate all T02–T05 behaviour.

## Scope
- Add to `GrainConfig`: `repo: str = ""`, `auto_create: bool = False`, `phase: str = ""`, `branch: str = ""`
- Parse them in `_parse()` from the `[grain]` table
- `auto_create` must parse as bool (TOML native bool or string "true"/"false")
- Tests: config parsing, defaults, all four fields present, invalid auto_create type rejected

## Deliverable
`GrainConfig` has all four new fields; tests passing; ruff + mypy clean.

## Constraints
- Backwards compatible — existing configs without new fields must not break
- `repo`, `phase`, `branch` default to `""` (not required)
- `auto_create` defaults to `False`
