"""Grain task ID auto-detection.

Checks GRAIN_TASK_ID env var first, then reads docs/working/current_task.md
from the current working directory (or a provided project root).
"""

from __future__ import annotations

import os
import re
from pathlib import Path

_TASK_ID_RE = re.compile(r"TASK-\d+")
_CURRENT_TASK_PATH = Path("docs/working/current_task.md")


def detect_task_id(project_root: str | None = None) -> str | None:
    """Return the active Grain task ID or None if undetectable.

    Resolution order:
    1. GRAIN_TASK_ID environment variable
    2. docs/working/current_task.md in project_root (or cwd)
    """
    env_val = os.environ.get("GRAIN_TASK_ID")
    if env_val:
        return env_val.strip()

    root = Path(project_root) if project_root else Path.cwd()
    task_file = root / _CURRENT_TASK_PATH
    if task_file.exists():
        try:
            text = task_file.read_text()
            match = _TASK_ID_RE.search(text)
            if match:
                return match.group(0)
        except OSError:
            pass

    return None
