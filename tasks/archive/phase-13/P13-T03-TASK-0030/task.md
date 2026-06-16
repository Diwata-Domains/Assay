# Task: `assay schedule status`: running/stopped + log file path

## Metadata
- **ID:** TASK-0030
- **Status:** done
- **Phase:** Phase 13 — Background Scheduler (Daemon Mode)
- **Backlog:** P13-T03
- **Packet Path:** tasks/P13-T03-TASK-0030/
- **Dependencies:** TASK-0028
- **Primary Adapter:** none
- **Secondary Adapters:** none

## Objective
Implement `status()` in `daemon.py` and `assay schedule status` CLI command. Returns running state, PID (if running), and log file path.

## Why This Task Exists
Operators need to know whether the daemon is running without reading PID files manually.

## Scope
- `status() -> dict[str, object]` in `daemon.py`
- CLI: print "running (pid N)" or "stopped", then "log: <path>"
- Handles stale PID file gracefully (returns running=False)

## Constraints
- Must not raise — all errors handled internally, return stopped state

## Escalation Conditions
- None
