"""File-change poller using mtime tracking — no external dependencies."""

from __future__ import annotations

import os
import time
from pathlib import Path


def parse_watch_target(s: str) -> tuple[Path, str | None]:
    """Split a watch-path string into (base_dir, glob_pattern).

    Plain paths (no glob chars) return (Path(s), None).
    Glob strings like 'src/**/*.py' return (Path('src'), '**/*.py').
    """
    glob_chars = {"*", "?", "["}
    if not any(c in s for c in glob_chars):
        return Path(s), None

    parts = Path(s).parts
    base_parts: list[str] = []
    glob_parts: list[str] = []
    in_glob = False
    for part in parts:
        if in_glob or any(c in part for c in glob_chars):
            in_glob = True
            glob_parts.append(part)
        else:
            base_parts.append(part)

    base = Path(*base_parts) if base_parts else Path(".")
    glob_pat = str(Path(*glob_parts)) if glob_parts else None
    return base, glob_pat


def _snapshot(watch_path: Path, glob: str | None = None) -> dict[str, float]:
    mtimes: dict[str, float] = {}
    if glob is not None:
        for fp in watch_path.glob(glob):
            if fp.is_file():
                try:
                    mtimes[str(fp)] = fp.stat().st_mtime
                except OSError:
                    pass
        return mtimes
    for root, _dirs, files in os.walk(watch_path):
        for name in files:
            fpath = os.path.join(root, name)
            try:
                mtimes[fpath] = os.stat(fpath).st_mtime
            except OSError:
                pass
    return mtimes


def watch_once(watch_path: Path, glob: str | None = None, poll_interval_ms: int = 200) -> None:
    """Block until a matching file under watch_path changes, then return."""
    baseline = _snapshot(watch_path, glob)
    while True:
        time.sleep(poll_interval_ms / 1000)
        current = _snapshot(watch_path, glob)
        if current != baseline:
            return


def debounce_and_wait(watch_path: Path, debounce_ms: int, glob: str | None = None, poll_interval_ms: int = 200) -> None:
    """Wait until no new changes are detected for debounce_ms, then return."""
    deadline = time.monotonic() + debounce_ms / 1000
    prev = _snapshot(watch_path, glob)
    while time.monotonic() < deadline:
        time.sleep(poll_interval_ms / 1000)
        current = _snapshot(watch_path, glob)
        if current != prev:
            deadline = time.monotonic() + debounce_ms / 1000
            prev = current
