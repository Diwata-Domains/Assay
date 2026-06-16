# Task: `assay submit --packet` command + [grain] config section

## Metadata
- **ID:** TASK-0025
- **Status:** done
- **Phase:** Phase 12 — Grain Task Tagging + assay submit
- **Backlog:** P12-T03
- **Packet Path:** tasks/P12-T03-TASK-0025/
- **Dependencies:** TASK-0023
- **Primary Adapter:** none
- **Secondary Adapters:** none

## Objective
Implement `assay submit --packet <path>` command. It reads the packet JSON, validates it against the Assay payload schema, then copies it to `[grain].output_path` from config. Add `[grain]` section (project_root, output_path) to `assay.toml` schema and `AssayConfig`.

## Why This Task Exists
Assay verifications need to be placed where Grain can pick them up. `assay submit` is the operator action that bridges the two tools.

## Scope
- `GrainConfig` dataclass in `config.py` with `project_root` and `output_path` fields
- `[grain]` section parsing in `_parse()`
- `_do_submit()` helper: read packet, validate schema, `shutil.copy2` to output_path
- `assay submit` command wired to `_do_submit()`
- Error if `output_path` not configured

## Constraints
- Must schema-validate the packet before copying — reject invalid packets
- Must create `output_path` directory if it doesn't exist

## Escalation Conditions
- None
