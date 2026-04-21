"""Schedule state persistence — add, list, remove schedules in ~/.assay/schedules.json."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, cast


class ScheduleStoreError(Exception):
    """Raised when the schedule store is unreadable, malformed, or an ID is not found."""


def _now() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"version": "1", "schedules": []}
    try:
        data: dict[str, object] = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        raise ScheduleStoreError(f"failed to read schedule store {path}: {exc}") from exc
    return data


def _save(path: Path, data: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def add_schedule(
    store_path: str,
    cron: str,
    suite: str = "default",
    target: Optional[str] = None,  # noqa: UP007
) -> str:
    """Add a new schedule entry. Returns the new schedule ID."""
    path = Path(store_path).expanduser()
    data = _load(path)
    schedules: list[dict[str, object]] = cast(list[dict[str, object]], data.get("schedules", []))

    schedule_id = str(uuid.uuid4())
    schedules.append(
        {
            "id": schedule_id,
            "cron": cron,
            "suite": suite,
            "target": target,
            "created_at": _now(),
            "last_run": None,
            "last_result": None,
        }
    )
    data["schedules"] = schedules
    _save(path, data)
    return schedule_id


def list_schedules(store_path: str) -> list[dict[str, object]]:
    """Return all schedule entries."""
    path = Path(store_path).expanduser()
    data = _load(path)
    return cast(list[dict[str, object]], data.get("schedules", []))


def remove_schedule(store_path: str, schedule_id: str) -> None:
    """Remove a schedule by ID. Raises ScheduleStoreError if not found."""
    path = Path(store_path).expanduser()
    data = _load(path)
    schedules: list[dict[str, object]] = cast(list[dict[str, object]], data.get("schedules", []))

    remaining = [s for s in schedules if s["id"] != schedule_id]
    if len(remaining) == len(schedules):
        raise ScheduleStoreError(f"schedule {schedule_id} not found")

    data["schedules"] = remaining
    _save(path, data)


def update_last_run(store_path: str, schedule_id: str, result: str) -> None:
    """Update last_run timestamp and last_result for a schedule after execution."""
    path = Path(store_path).expanduser()
    data = _load(path)
    schedules: list[dict[str, object]] = cast(list[dict[str, object]], data.get("schedules", []))

    for schedule in schedules:
        if schedule["id"] == schedule_id:
            schedule["last_run"] = _now()
            schedule["last_result"] = result
            data["schedules"] = schedules
            _save(path, data)
            return

    raise ScheduleStoreError(f"schedule {schedule_id} not found")
