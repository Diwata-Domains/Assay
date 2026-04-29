"""Unit tests for the SQLite packet store."""

from __future__ import annotations

from pathlib import Path

import pytest

from assay.store.db import StoreError, import_packets, init_db, insert_packet, list_packets


def _packet(
    vid: str = "aaaa-0000-4000-8000-000000000001",
    outcome: str = "pass",
    task_id: str | None = "TASK-0001",
) -> dict[str, object]:
    return {
        "verification_id": vid,
        "task_id": task_id,
        "issue_type": "test_failure",
        "severity": "info",
        "outcome": outcome,
        "summary": f"{outcome}: https://example.com",
        "artifact_refs": [],
        "followup_candidates": [],
        "verified_at": "2026-04-29T10:00:00Z",
    }


def test_init_db_creates_file(tmp_path: Path) -> None:
    db = tmp_path / "store.db"
    result = init_db(db)
    assert result == db
    assert db.exists()


def test_init_db_creates_parent_dirs(tmp_path: Path) -> None:
    db = tmp_path / "nested" / "dir" / "store.db"
    init_db(db)
    assert db.exists()


def test_init_db_idempotent(tmp_path: Path) -> None:
    db = tmp_path / "store.db"
    init_db(db)
    init_db(db)
    assert db.exists()


def test_insert_and_list(tmp_path: Path) -> None:
    db = tmp_path / "store.db"
    init_db(db)
    insert_packet(_packet(), db)
    rows = list_packets(db)
    assert len(rows) == 1
    assert rows[0]["verification_id"] == "aaaa-0000-4000-8000-000000000001"


def test_insert_multiple(tmp_path: Path) -> None:
    db = tmp_path / "store.db"
    init_db(db)
    insert_packet(_packet("aaa1"), db)
    insert_packet(_packet("aaa2"), db)
    assert len(list_packets(db)) == 2


def test_list_empty_when_db_missing(tmp_path: Path) -> None:
    db = tmp_path / "nonexistent.db"
    assert list_packets(db) == []


def test_list_filter_by_outcome(tmp_path: Path) -> None:
    db = tmp_path / "store.db"
    init_db(db)
    insert_packet(_packet("p1", outcome="pass"), db)
    insert_packet(_packet("p2", outcome="fail"), db)
    rows = list_packets(db, outcome="fail")
    assert len(rows) == 1
    assert rows[0]["outcome"] == "fail"


def test_list_filter_by_task_id(tmp_path: Path) -> None:
    db = tmp_path / "store.db"
    init_db(db)
    insert_packet(_packet("p1", task_id="TASK-0001"), db)
    insert_packet(_packet("p2", task_id="TASK-0002"), db)
    rows = list_packets(db, task_id="TASK-0001")
    assert len(rows) == 1
    assert rows[0]["task_id"] == "TASK-0001"


def test_insert_missing_verification_id_raises(tmp_path: Path) -> None:
    db = tmp_path / "store.db"
    init_db(db)
    bad = {k: v for k, v in _packet().items() if k != "verification_id"}
    with pytest.raises(StoreError):
        insert_packet(bad, db)


def test_insert_upserts_on_duplicate_id(tmp_path: Path) -> None:
    db = tmp_path / "store.db"
    init_db(db)
    insert_packet(_packet("dup", outcome="pass"), db)
    insert_packet(_packet("dup", outcome="fail"), db)
    rows = list_packets(db)
    assert len(rows) == 1
    assert rows[0]["outcome"] == "fail"


def test_import_packets_returns_count(tmp_path: Path) -> None:
    db = tmp_path / "store.db"
    packets = [_packet("i1"), _packet("i2"), _packet("i3")]
    count = import_packets(packets, db)
    assert count == 3
    assert len(list_packets(db)) == 3


def test_import_skips_invalid_packets(tmp_path: Path) -> None:
    db = tmp_path / "store.db"
    bad: dict[str, object] = {"no_id": True}
    count = import_packets([bad], db)
    assert count == 0


def test_packet_round_trips_all_fields(tmp_path: Path) -> None:
    db = tmp_path / "store.db"
    init_db(db)
    p = _packet("rt1", outcome="inconclusive", task_id=None)
    insert_packet(p, db)
    rows = list_packets(db)
    assert rows[0] == p
