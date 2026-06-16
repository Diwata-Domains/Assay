# Task: Verify runner screenshot is copied + referenced in artifact_refs

## Metadata
- **ID:** TASK-0021
- **Status:** done
- **Phase:** Phase 11 — Screenshot Persistence + assay report
- **Backlog:** P11-T02
- **Packet Path:** tasks/P11-T02-TASK-0021/
- **Dependencies:** P3-T05
- **Primary Adapter:** none
- **Secondary Adapters:** none

## Objective
After `assay run` collects artifacts, copy `screenshot.png` from the runner output directory to `{verification_id}.png` in the final output directory. Update `artifact_refs` in the packet to point to the stable path.

## Why This Task Exists
The runner wrote `screenshot.png` to the output dir but `artifact_refs` either contained the temp path or the generic `screenshot.png` name. Phase 11 requires a `{verification_id}.png` stable name alongside the packet JSON.

## Scope
- In `assay run` command (cli/main.py): after `format_packet()`, `shutil.copy2(src, dest)` where dest is `{output_dir}/{verification_id}.png`
- Update `packet["artifact_refs"]` to the stable destination path

## Constraints
- Only copy if screenshot file actually exists (runner may not produce one in all cases)

## Escalation Conditions
- None
