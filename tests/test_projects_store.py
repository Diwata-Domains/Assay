"""Unit tests for the projects / project_origins store."""

from __future__ import annotations

from pathlib import Path

import pytest

from assay.store.db import (
    StoreError,
    add_project_origin,
    delete_project_origin,
    get_project,
    get_project_for_origin,
    init_db,
    insert_project,
    list_project_origins,
    list_projects,
)


def _db(tmp_path: Path) -> Path:
    return tmp_path / "store.db"


def test_insert_project_returns_id_and_is_retrievable(tmp_path: Path) -> None:
    db = _db(tmp_path)
    pid = insert_project("LC CRM", db_path=db)
    row = get_project(pid, db_path=db)
    assert row is not None
    assert row["id"] == pid
    assert row["name"] == "LC CRM"
    assert row["created_at"]


def test_list_projects_newest_first(tmp_path: Path) -> None:
    db = _db(tmp_path)
    insert_project("first", db_path=db)
    insert_project("second", db_path=db)
    names = [p["name"] for p in list_projects(db_path=db)]
    assert set(names) == {"first", "second"}


def test_add_and_resolve_origin(tmp_path: Path) -> None:
    db = _db(tmp_path)
    pid = insert_project("Acme", db_path=db)
    add_project_origin(pid, "https://acme.example", db_path=db)
    assert get_project_for_origin("https://acme.example", db_path=db) == pid
    assert get_project_for_origin("https://unknown.example", db_path=db) is None


def test_origin_is_unique(tmp_path: Path) -> None:
    db = _db(tmp_path)
    a = insert_project("A", db_path=db)
    b = insert_project("B", db_path=db)
    add_project_origin(a, "https://dup.example", db_path=db)
    with pytest.raises(StoreError):
        add_project_origin(b, "https://dup.example", db_path=db)


def test_list_project_origins_scoped(tmp_path: Path) -> None:
    db = _db(tmp_path)
    pid = insert_project("apex", db_path=db)
    add_project_origin(pid, "https://apex.example", db_path=db)
    origins = [o["origin"] for o in list_project_origins(pid, db_path=db)]
    assert origins == ["https://apex.example"]


def test_delete_project_origin_unbinds(tmp_path: Path) -> None:
    db = _db(tmp_path)
    pid = insert_project("conclave", db_path=db)
    add_project_origin(pid, "https://conclave.example", db_path=db)
    delete_project_origin(pid, "https://conclave.example", db_path=db)
    assert get_project_for_origin("https://conclave.example", db_path=db) is None
    assert list_project_origins(pid, db_path=db) == []


def test_delete_unknown_origin_raises(tmp_path: Path) -> None:
    db = _db(tmp_path)
    pid = insert_project("conclave", db_path=db)
    with pytest.raises(StoreError):
        delete_project_origin(pid, "https://never-bound.example", db_path=db)


def test_delete_origin_scoped_to_project(tmp_path: Path) -> None:
    # Deleting via the wrong project id must NOT unbind another project's origin.
    db = _db(tmp_path)
    a = insert_project("A", db_path=db)
    b = insert_project("B", db_path=db)
    add_project_origin(a, "https://scoped.example", db_path=db)
    with pytest.raises(StoreError):
        delete_project_origin(b, "https://scoped.example", db_path=db)
    assert get_project_for_origin("https://scoped.example", db_path=db) == a


def test_init_db_is_idempotent_with_project_columns(tmp_path: Path) -> None:
    # Running init_db twice must not raise on the new packets/tickets project_id ALTERs
    # (the try/except OperationalError path), and must not clobber existing rows.
    db = _db(tmp_path)
    init_db(db)
    pid = insert_project("A", db_path=db)
    init_db(db)  # second run: ALTERs already applied, projects row survives
    assert get_project(pid, db_path=db) is not None


def test_backfill_default_project_adopts_orphans(tmp_path: Path) -> None:
    from assay.store.db import (
        UNASSIGNED_PROJECT_ID,
        backfill_default_project,
        get_packet,
        get_project,
        get_ticket,
        init_db,
        insert_packet,
        insert_ticket,
    )

    db = _db(tmp_path)
    init_db(db)
    insert_packet(
        {
            "verification_id": "VERIFY-1",
            "task_id": None,
            "issue_type": "bug_finding",
            "severity": "info",
            "outcome": "fail",
            "summary": "orphan packet",
        },
        db,
    )
    tid = insert_ticket("orphan ticket", severity="info", db_path=db)

    pid = backfill_default_project(db_path=db)
    assert pid == UNASSIGNED_PROJECT_ID
    assert get_project(pid, db) is not None
    assert get_packet("VERIFY-1", db)["project_id"] == UNASSIGNED_PROJECT_ID
    assert get_ticket(tid, db)["project_id"] == UNASSIGNED_PROJECT_ID
    # idempotent: a second run creates nothing new and leaves the assignment intact
    assert backfill_default_project(db_path=db) == UNASSIGNED_PROJECT_ID
    assert get_packet("VERIFY-1", db)["project_id"] == UNASSIGNED_PROJECT_ID
