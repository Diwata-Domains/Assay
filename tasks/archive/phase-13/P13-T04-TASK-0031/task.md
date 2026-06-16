# Task: PID file locking; log file at ~/.assay/scheduler.log

## Metadata
- **ID:** TASK-0031
- **Status:** done
- **Phase:** Phase 13 — Background Scheduler (Daemon Mode)
- **Backlog:** P13-T04
- **Packet Path:** tasks/P13-T04-TASK-0031/
- **Dependencies:** TASK-0028
- **Primary Adapter:** none
- **Secondary Adapters:** none

## Objective
Ensure PID file and log file are at stable paths (`~/.assay/scheduler.pid` and `~/.assay/scheduler.log`). Double-start is prevented by checking the PID before writing a new one. Log file is opened in append mode by the child process.

## Why This Task Exists
Without stable, well-known paths, tooling (shell scripts, monitoring) can't find the PID or log reliably.

## Scope
- Constants `_PID_FILE` and `_LOG_FILE` in `daemon.py` pointing to `~/.assay/`
- `_pid_file()` and `_log_file()` accessors (patchable in tests)
- Append mode log so multiple restarts accumulate in one file
- Parent creates log file directory before forking

## Constraints
- `~/.assay/` directory must be created if absent

## Escalation Conditions
- None
