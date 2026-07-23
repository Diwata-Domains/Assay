"""Unit tests for the durable Ticket entity, its state machine, and packet backfill."""

from __future__ import annotations

from pathlib import Path

import pytest
from grain_contracts.verification import Priority, State

from assay.store.db import (
    StoreError,
    advance_ticket,
    backfill_tickets,
    get_packet,
    get_ticket,
    init_db,
    insert_packet,
    insert_ticket,
    list_tickets,
)


def _packet(
    vid: str,
    *,
    outcome: str = "pass",
    task_id: str | None = "TASK-0001",
    summary: str = "a finding",
) -> dict[str, object]:
    return {
        "verification_id": vid,
        "task_id": task_id,
        "issue_type": "test_failure",
        "severity": "error",
        "outcome": outcome,
        "summary": summary,
        "artifact_refs": [],
        "followup_candidates": [],
        "verified_at": "2026-04-29T10:00:00Z",
    }


def test_insert_ticket_returns_first_id(tmp_path: Path) -> None:
    db = tmp_path / "store.db"
    init_db(db)
    tid = insert_ticket("first", "error", "high", db_path=db)
    assert tid == "ASSAY-1"
    ticket = get_ticket(tid, db)
    assert ticket is not None
    assert ticket["title"] == "first"
    assert ticket["severity"] == "error"
    assert ticket["priority"] == "high"
    assert ticket["state"] == State.TRIAGE.value


def test_ticket_ids_are_monotonic(tmp_path: Path) -> None:
    db = tmp_path / "store.db"
    init_db(db)
    ids = [insert_ticket(f"t{i}", "info", db_path=db) for i in range(5)]
    assert ids == ["ASSAY-1", "ASSAY-2", "ASSAY-3", "ASSAY-4", "ASSAY-5"]


def test_ticket_id_survives_gap(tmp_path: Path) -> None:
    db = tmp_path / "store.db"
    init_db(db)
    insert_ticket("a", "info", db_path=db)
    insert_ticket("b", "info", db_path=db)
    third = insert_ticket("c", "info", db_path=db)
    assert third == "ASSAY-3"


def test_insert_ticket_defaults(tmp_path: Path) -> None:
    db = tmp_path / "store.db"
    init_db(db)
    tid = insert_ticket("d", "info", db_path=db)
    ticket = get_ticket(tid, db)
    assert ticket is not None
    assert ticket["priority"] == Priority.NONE.value
    assert ticket["state"] == State.TRIAGE.value
    assert ticket["grain_task_id"] is None
    assert ticket["parent_id"] is None


def test_insert_ticket_accepts_enums(tmp_path: Path) -> None:
    db = tmp_path / "store.db"
    init_db(db)
    tid = insert_ticket("e", "info", Priority.URGENT, state=State.TODO, db_path=db)
    ticket = get_ticket(tid, db)
    assert ticket is not None
    assert ticket["priority"] == "urgent"
    assert ticket["state"] == "todo"


def test_insert_ticket_rejects_bad_priority(tmp_path: Path) -> None:
    db = tmp_path / "store.db"
    init_db(db)
    with pytest.raises(StoreError):
        insert_ticket("f", "info", "sky-high", db_path=db)


def test_list_tickets_returns_all(tmp_path: Path) -> None:
    db = tmp_path / "store.db"
    init_db(db)
    a = insert_ticket("first", "info", db_path=db)
    b = insert_ticket("second", "error", project_id="proj-x", db_path=db)
    tickets = {t["id"]: t for t in list_tickets(db_path=db)}
    assert set(tickets) == {a, b}
    assert tickets[a]["project_id"] is None
    assert tickets[b]["project_id"] == "proj-x"


def test_list_tickets_filters_by_state(tmp_path: Path) -> None:
    db = tmp_path / "store.db"
    init_db(db)
    triaged = insert_ticket("stays", "info", db_path=db)
    moved = insert_ticket("moves", "info", db_path=db)
    advance_ticket(moved, State.TODO, db_path=db)
    ids = [t["id"] for t in list_tickets("todo", db_path=db)]
    assert ids == [moved]
    assert triaged not in ids


def test_list_tickets_empty_when_no_db(tmp_path: Path) -> None:
    assert list_tickets(db_path=tmp_path / "nope.db") == []


def test_insert_ticket_rejects_bad_state(tmp_path: Path) -> None:
    db = tmp_path / "store.db"
    init_db(db)
    with pytest.raises(StoreError):
        insert_ticket("g", "info", state="frozen", db_path=db)


def test_parent_id_self_reference(tmp_path: Path) -> None:
    db = tmp_path / "store.db"
    init_db(db)
    parent = insert_ticket("parent", "info", db_path=db)
    child = insert_ticket("child", "info", parent_id=parent, db_path=db)
    ticket = get_ticket(child, db)
    assert ticket is not None
    assert ticket["parent_id"] == parent


_LEGAL = [
    (State.TRIAGE, State.TODO),
    (State.TRIAGE, State.CANCELED),
    (State.TODO, State.IN_PROGRESS),
    (State.TODO, State.CANCELED),
    (State.IN_PROGRESS, State.IN_REVIEW),
    (State.IN_PROGRESS, State.CANCELED),
    (State.IN_REVIEW, State.DONE),
    (State.IN_REVIEW, State.CANCELED),
]


@pytest.mark.parametrize("start,target", _LEGAL)
def test_legal_transition(tmp_path: Path, start: State, target: State) -> None:
    db = tmp_path / "store.db"
    init_db(db)
    tid = insert_ticket("t", "info", state=start, db_path=db)
    advance_ticket(tid, target, db)
    ticket = get_ticket(tid, db)
    assert ticket is not None
    assert ticket["state"] == target.value


_ILLEGAL = [
    (State.TRIAGE, State.IN_PROGRESS),
    (State.TRIAGE, State.IN_REVIEW),
    (State.TRIAGE, State.DONE),
    (State.TODO, State.IN_REVIEW),
    (State.TODO, State.DONE),
    (State.TODO, State.TRIAGE),
    (State.IN_PROGRESS, State.DONE),
    (State.IN_PROGRESS, State.TODO),
    (State.IN_REVIEW, State.IN_PROGRESS),
    (State.IN_REVIEW, State.TODO),
    (State.DONE, State.IN_REVIEW),
    (State.DONE, State.CANCELED),
    (State.CANCELED, State.TODO),
    (State.CANCELED, State.DONE),
]


@pytest.mark.parametrize("start,target", _ILLEGAL)
def test_illegal_transition_rejected(tmp_path: Path, start: State, target: State) -> None:
    db = tmp_path / "store.db"
    init_db(db)
    tid = insert_ticket("t", "info", state=start, db_path=db)
    with pytest.raises(StoreError):
        advance_ticket(tid, target, db)
    ticket = get_ticket(tid, db)
    assert ticket is not None
    assert ticket["state"] == start.value


def test_advance_updates_timestamp(tmp_path: Path) -> None:
    db = tmp_path / "store.db"
    init_db(db)
    tid = insert_ticket("t", "info", db_path=db)
    before = get_ticket(tid, db)
    advance_ticket(tid, State.TODO, db)
    after = get_ticket(tid, db)
    assert before is not None and after is not None
    assert after["created_at"] == before["created_at"]
    assert after["updated_at"] >= before["updated_at"]


def test_advance_missing_ticket_raises(tmp_path: Path) -> None:
    db = tmp_path / "store.db"
    init_db(db)
    with pytest.raises(StoreError):
        advance_ticket("ASSAY-999", State.TODO, db)


def test_backfill_one_ticket_per_packet(tmp_path: Path) -> None:
    db = tmp_path / "store.db"
    init_db(db)
    insert_packet(_packet("v1"), db)
    insert_packet(_packet("v2"), db)
    created = backfill_tickets(db)
    assert created == 2


def test_backfill_is_idempotent(tmp_path: Path) -> None:
    db = tmp_path / "store.db"
    init_db(db)
    insert_packet(_packet("v1"), db)
    assert backfill_tickets(db) == 1
    assert backfill_tickets(db) == 0


def test_backfill_links_packet_to_ticket(tmp_path: Path) -> None:
    db = tmp_path / "store.db"
    init_db(db)
    insert_packet(_packet("v1"), db)
    backfill_tickets(db)
    packet = get_packet("v1", db)
    assert packet is not None
    assert packet["source_ticket_id"] == "ASSAY-1"


def _make_and_backfill(
    tmp_path: Path,
    *,
    triage_status: str | None,
    review_status: str | None,
    outcome: str,
) -> str:
    db = tmp_path / "store.db"
    init_db(db)
    insert_packet(_packet("v1", outcome=outcome), db)
    from assay.store.db import set_review_status, set_triage_status

    if triage_status is not None:
        set_triage_status("v1", triage_status, db)
    if review_status is not None:
        set_review_status("v1", review_status, db)
    backfill_tickets(db)
    ticket = get_ticket("ASSAY-1", db)
    assert ticket is not None
    return str(ticket["state"])


def test_backfill_new_derives_triage(tmp_path: Path) -> None:
    assert _make_and_backfill(tmp_path, triage_status="new", review_status=None, outcome="pass") == State.TRIAGE.value


def test_backfill_none_derives_triage(tmp_path: Path) -> None:
    assert _make_and_backfill(tmp_path, triage_status=None, review_status=None, outcome="fail") == State.TRIAGE.value


def test_backfill_promoted_derives_todo(tmp_path: Path) -> None:
    assert (
        _make_and_backfill(tmp_path, triage_status="promoted", review_status=None, outcome="pass")
        == State.TODO.value
    )


def test_backfill_dismissed_derives_canceled(tmp_path: Path) -> None:
    assert (
        _make_and_backfill(tmp_path, triage_status="dismissed", review_status=None, outcome="pass")
        == State.CANCELED.value
    )


def test_backfill_imported_pass_derives_in_review(tmp_path: Path) -> None:
    assert (
        _make_and_backfill(tmp_path, triage_status="imported", review_status=None, outcome="pass")
        == State.IN_REVIEW.value
    )


def test_backfill_imported_fail_derives_in_progress(tmp_path: Path) -> None:
    assert (
        _make_and_backfill(tmp_path, triage_status="imported", review_status=None, outcome="fail")
        == State.IN_PROGRESS.value
    )


def test_backfill_imported_rejected_derives_in_progress(tmp_path: Path) -> None:
    assert (
        _make_and_backfill(tmp_path, triage_status="imported", review_status="rejected", outcome="pass")
        == State.IN_PROGRESS.value
    )


def test_backfill_approved_derives_done(tmp_path: Path) -> None:
    assert (
        _make_and_backfill(tmp_path, triage_status="imported", review_status="approved", outcome="fail")
        == State.DONE.value
    )
