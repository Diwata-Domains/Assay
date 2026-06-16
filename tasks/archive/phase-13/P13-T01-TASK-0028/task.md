# Task: `assay schedule start`: background process + PID file

## Metadata
- **ID:** TASK-0028
- **Status:** done
- **Phase:** Phase 13 — Background Scheduler (Daemon Mode)
- **Backlog:** P13-T01
- **Packet Path:** tasks/P13-T01-TASK-0028/
- **Dependencies:** Phase 7 complete
- **Primary Adapter:** none
- **Secondary Adapters:** none

## Objective
Implement `assay schedule start` to fork the scheduler into a background daemon process. The child writes its PID to `~/.assay/scheduler.pid` and redirects stdout/stderr to `~/.assay/scheduler.log`. The parent returns immediately after confirming the PID file was written.

## Why This Task Exists
The existing `assay schedule run` blocks the terminal. Daemon mode allows the scheduler to run in the background without occupying a terminal session.

## Scope
- `src/assay/schedule/daemon.py`: `start()` function using `os.fork()`
- PID written to `~/.assay/scheduler.pid`
- Double-start prevention: if PID file exists and process is alive, print error and exit 1
- Stale PID file cleanup on start

## Constraints
- POSIX only (`os.fork()` / `os.setsid()` not available on Windows)
- Log file created before child forks

## Escalation Conditions
- None
