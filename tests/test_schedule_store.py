"""Unit tests for src/assay/schedule/store.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from assay.schedule.store import (
    ScheduleStoreError,
    add_schedule,
    list_schedules,
    remove_schedule,
    update_last_run,
)


def store_path(tmp_path: Path) -> str:
    return str(tmp_path / ".assay" / "schedules.json")


# ---------------------------------------------------------------------------
# add_schedule
# ---------------------------------------------------------------------------


def test_add_schedule_returns_uuid(tmp_path: Path) -> None:
    sid = add_schedule(store_path(tmp_path), "0 * * * *")
    assert len(sid) == 36
    assert sid.count("-") == 4


def test_add_schedule_creates_file(tmp_path: Path) -> None:
    add_schedule(store_path(tmp_path), "0 * * * *")
    path = Path(tmp_path / ".assay" / "schedules.json")
    assert path.exists()


def test_add_schedule_defaults(tmp_path: Path) -> None:
    add_schedule(store_path(tmp_path), "0 * * * *")
    schedules = list_schedules(store_path(tmp_path))
    assert len(schedules) == 1
    s = schedules[0]
    assert s["cron"] == "0 * * * *"
    assert s["suite"] == "default"
    assert s["target"] is None
    assert s["last_run"] is None
    assert s["last_result"] is None
    assert "created_at" in s


def test_add_schedule_custom_suite_and_target(tmp_path: Path) -> None:
    add_schedule(store_path(tmp_path), "*/5 * * * *", suite="smoke", target="https://example.com")
    s = list_schedules(store_path(tmp_path))[0]
    assert s["suite"] == "smoke"
    assert s["target"] == "https://example.com"


def test_add_multiple_schedules(tmp_path: Path) -> None:
    add_schedule(store_path(tmp_path), "0 * * * *")
    add_schedule(store_path(tmp_path), "0 0 * * *")
    assert len(list_schedules(store_path(tmp_path))) == 2


def test_add_schedule_unique_ids(tmp_path: Path) -> None:
    id1 = add_schedule(store_path(tmp_path), "0 * * * *")
    id2 = add_schedule(store_path(tmp_path), "0 * * * *")
    assert id1 != id2


# ---------------------------------------------------------------------------
# list_schedules
# ---------------------------------------------------------------------------


def test_list_schedules_empty_when_no_file(tmp_path: Path) -> None:
    result = list_schedules(store_path(tmp_path))
    assert result == []


def test_list_schedules_returns_all(tmp_path: Path) -> None:
    for cron in ["0 * * * *", "0 0 * * *", "*/15 * * * *"]:
        add_schedule(store_path(tmp_path), cron)
    result = list_schedules(store_path(tmp_path))
    assert len(result) == 3


# ---------------------------------------------------------------------------
# remove_schedule
# ---------------------------------------------------------------------------


def test_remove_schedule_removes_by_id(tmp_path: Path) -> None:
    sid = add_schedule(store_path(tmp_path), "0 * * * *")
    remove_schedule(store_path(tmp_path), sid)
    assert list_schedules(store_path(tmp_path)) == []


def test_remove_schedule_leaves_others(tmp_path: Path) -> None:
    sid1 = add_schedule(store_path(tmp_path), "0 * * * *")
    sid2 = add_schedule(store_path(tmp_path), "0 0 * * *")
    remove_schedule(store_path(tmp_path), sid1)
    remaining = list_schedules(store_path(tmp_path))
    assert len(remaining) == 1
    assert remaining[0]["id"] == sid2


def test_remove_schedule_raises_if_not_found(tmp_path: Path) -> None:
    with pytest.raises(ScheduleStoreError, match="not found"):
        remove_schedule(store_path(tmp_path), "00000000-0000-0000-0000-000000000000")


# ---------------------------------------------------------------------------
# update_last_run
# ---------------------------------------------------------------------------


def test_update_last_run_sets_fields(tmp_path: Path) -> None:
    sid = add_schedule(store_path(tmp_path), "0 * * * *")
    update_last_run(store_path(tmp_path), sid, "pass")
    s = list_schedules(store_path(tmp_path))[0]
    assert s["last_result"] == "pass"
    assert s["last_run"] is not None


def test_update_last_run_fail_result(tmp_path: Path) -> None:
    sid = add_schedule(store_path(tmp_path), "0 * * * *")
    update_last_run(store_path(tmp_path), sid, "fail")
    s = list_schedules(store_path(tmp_path))[0]
    assert s["last_result"] == "fail"


def test_update_last_run_raises_if_not_found(tmp_path: Path) -> None:
    with pytest.raises(ScheduleStoreError, match="not found"):
        update_last_run(store_path(tmp_path), "00000000-0000-0000-0000-000000000000", "pass")


# ---------------------------------------------------------------------------
# corrupt store
# ---------------------------------------------------------------------------


def test_load_raises_on_malformed_json(tmp_path: Path) -> None:
    p = tmp_path / ".assay" / "schedules.json"
    p.parent.mkdir(parents=True)
    p.write_text("{not valid json")
    with pytest.raises(ScheduleStoreError, match="failed to read"):
        list_schedules(str(p))
