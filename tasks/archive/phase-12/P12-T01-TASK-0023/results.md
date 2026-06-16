# Results: P12-T01-TASK-0023

## Packet State
- **Current Task Status:** done
- **Review Readiness:** approved
- **Recommended Next Status:** done

## Summary

Added `--task-id` option to `assay run`. Passed to `format_packet()`. When not provided and no auto-detection resolves a value, `task_id=None` in packet. 3 tests covering explicit flag, auto-detect override, and None fallback.

## Closure Decision
- **Decision:** closed
- **Reason:** Deliverable complete and verified.
