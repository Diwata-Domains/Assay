# Task: `assay schedule stop`: SIGTERM + PID cleanup

## Metadata
- **ID:** TASK-0029
- **Status:** done
- **Phase:** Phase 13 — Background Scheduler (Daemon Mode)
- **Backlog:** P13-T02
- **Packet Path:** tasks/P13-T02-TASK-0029/
- **Dependencies:** TASK-0028
- **Primary Adapter:** none
- **Secondary Adapters:** none

## Objective
Implement `stop()` in `daemon.py`. Reads PID from `~/.assay/scheduler.pid`, sends `SIGTERM`, waits up to 3s for the process to exit, then removes the PID file.

## Why This Task Exists
`assay schedule start` needs a corresponding stop command. Without it, users would have to find the PID manually.

## Scope
- `stop()` in `daemon.py`
- `assay schedule stop` CLI command wired to `stop()`
- Stale PID file detection: if PID not running, remove file and exit 1
- No PID file → exit 1

## Constraints
- Must wait for process exit before returning, up to a reasonable timeout

## Escalation Conditions
- None
