"""File-change poller using mtime tracking — no external dependencies."""

from __future__ import annotations

import os
import time
from pathlib import Path


def _snapshot(watch_path: Path) -> dict[str, float]:
    mtimes: dict[str, float] = {}
    for root, _dirs, files in os.walk(watch_path):
        for name in files:
            fp = os.path.join(root, name)
            try:
                mtimes[fp] = os.stat(fp).st_mtime
            except OSError:
                pass
    return mtimes


def watch_once(watch_path: Path, poll_interval_ms: int = 200) -> None:
    """Block until any file under watch_path changes, then return.

    poll_interval_ms controls how often the directory is scanned.
    """
    baseline = _snapshot(watch_path)
    while True:
        time.sleep(poll_interval_ms / 1000)
        current = _snapshot(watch_path)
        if current != baseline:
            return


def debounce_and_wait(watch_path: Path, debounce_ms: int, poll_interval_ms: int = 200) -> None:
    """Wait until no new changes are detected for debounce_ms, then return."""
    deadline = time.monotonic() + debounce_ms / 1000
    prev = _snapshot(watch_path)
    while time.monotonic() < deadline:
        time.sleep(poll_interval_ms / 1000)
        current = _snapshot(watch_path)
        if current != prev:
            deadline = time.monotonic() + debounce_ms / 1000
            prev = current
