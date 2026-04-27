"""Background scheduler daemon — start, stop, status."""

from __future__ import annotations

import os
import signal
import sys
import time
from pathlib import Path

_PID_FILE = Path("~/.assay/scheduler.pid").expanduser()
_LOG_FILE = Path("~/.assay/scheduler.log").expanduser()


def _pid_file() -> Path:
    return _PID_FILE


def _log_file() -> Path:
    return _LOG_FILE


def start(config_path: str | None = None) -> None:
    """Launch the scheduler as a background daemon process. Writes PID to ~/.assay/scheduler.pid."""
    pid_file = _pid_file()
    if pid_file.exists():
        existing_pid = int(pid_file.read_text().strip())
        if _is_running(existing_pid):
            print(f"scheduler already running (pid {existing_pid})", file=sys.stderr)
            sys.exit(1)
        # Stale PID file — clean up
        pid_file.unlink()

    pid_file.parent.mkdir(parents=True, exist_ok=True)
    log_file = _log_file()
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # fork to background
    child_pid = os.fork()
    if child_pid > 0:
        # parent — wait briefly for child to write PID file, then return
        for _ in range(20):
            if pid_file.exists():
                child_pid_written = int(pid_file.read_text().strip())
                print(f"scheduler started (pid {child_pid_written})")
                return
            time.sleep(0.1)
        print(f"scheduler started (pid {child_pid})")
        return

    # child — become session leader, redirect stdio, run loop
    os.setsid()
    pid_file.write_text(str(os.getpid()))

    with open(log_file, "a") as log:
        sys.stdout = log
        sys.stderr = log
        print(f"[daemon] started (pid {os.getpid()})", flush=True)
        try:
            from assay.config import load_config
            from assay.schedule.loop import run_scheduler
            config = load_config(config_path)
            run_scheduler(config)
        except Exception as exc:
            print(f"[daemon] error: {exc}", flush=True)
        finally:
            if pid_file.exists():
                try:
                    pid_file.unlink()
                except OSError:
                    pass
            print("[daemon] stopped", flush=True)
    os._exit(0)


def stop() -> None:
    """Send SIGTERM to the running scheduler daemon and clean up PID file."""
    pid_file = _pid_file()
    if not pid_file.exists():
        print("scheduler is not running", file=sys.stderr)
        sys.exit(1)

    pid = int(pid_file.read_text().strip())
    if not _is_running(pid):
        pid_file.unlink()
        print("scheduler is not running (stale PID file removed)", file=sys.stderr)
        sys.exit(1)

    os.kill(pid, signal.SIGTERM)
    # Wait for process to exit
    for _ in range(30):
        if not _is_running(pid):
            break
        time.sleep(0.1)

    if pid_file.exists():
        try:
            pid_file.unlink()
        except OSError:
            pass
    print(f"scheduler stopped (pid {pid})")


def status() -> dict[str, object]:
    """Return daemon status dict: running (bool), pid (int|None), log_file (str)."""
    pid_file = _pid_file()
    if not pid_file.exists():
        return {"running": False, "pid": None, "log_file": str(_log_file())}

    try:
        pid = int(pid_file.read_text().strip())
    except (ValueError, OSError):
        return {"running": False, "pid": None, "log_file": str(_log_file())}

    running = _is_running(pid)
    return {"running": running, "pid": pid if running else None, "log_file": str(_log_file())}


def _is_running(pid: int) -> bool:
    """Return True if a process with the given PID exists."""
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False
