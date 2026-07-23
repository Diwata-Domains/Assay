# SPDX-FileCopyrightText: 2024-2026 Shaznay Sison
# SPDX-License-Identifier: AGPL-3.0-only

"""SQLite store for Assay result packets — stdlib sqlite3 only."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional, cast

from grain_contracts.verification import Priority, State

_DEFAULT_DB = Path.home() / ".assay" / "store.db"

_PRIORITY_VALUES = frozenset(p.value for p in Priority)

_ALLOWED_TRANSITIONS: dict[State, frozenset[State]] = {
    State.TRIAGE: frozenset({State.TODO, State.CANCELED}),
    State.TODO: frozenset({State.IN_PROGRESS, State.CANCELED}),
    State.IN_PROGRESS: frozenset({State.IN_REVIEW, State.CANCELED}),
    State.IN_REVIEW: frozenset({State.DONE, State.CANCELED}),
    State.DONE: frozenset(),
    State.CANCELED: frozenset(),
}

_CREATE_PACKETS = """
CREATE TABLE IF NOT EXISTS packets (
    verification_id TEXT PRIMARY KEY,
    task_id         TEXT,
    issue_type      TEXT NOT NULL,
    severity        TEXT NOT NULL,
    outcome         TEXT NOT NULL,
    summary         TEXT NOT NULL,
    artifact_refs   TEXT NOT NULL DEFAULT '[]',
    followup_candidates TEXT NOT NULL DEFAULT '[]',
    verified_at     TEXT,
    diff_result     TEXT,
    review_status   TEXT,
    raw             TEXT NOT NULL
)
"""

_CREATE_BASELINES = """
CREATE TABLE IF NOT EXISTS baselines (
    url              TEXT PRIMARY KEY,
    verification_id  TEXT NOT NULL
)
"""

_CREATE_CHECK_RESULTS = """
CREATE TABLE IF NOT EXISTS check_results (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    check_id    TEXT NOT NULL,
    check_type  TEXT NOT NULL,
    target      TEXT NOT NULL,
    passed      INTEGER NOT NULL,
    assertions  TEXT NOT NULL DEFAULT '[]',
    error       TEXT,
    checked_at  TEXT NOT NULL
)
"""


_CREATE_TICKETS = """
CREATE TABLE IF NOT EXISTS tickets (
    id            TEXT PRIMARY KEY,
    title         TEXT NOT NULL,
    severity      TEXT NOT NULL,
    priority      TEXT NOT NULL,
    state         TEXT NOT NULL,
    grain_task_id TEXT,
    parent_id     TEXT REFERENCES tickets(id),
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL
)
"""

UNASSIGNED_PROJECT_ID = "unassigned"

_CREATE_PROJECTS = """
CREATE TABLE IF NOT EXISTS projects (
    id         TEXT PRIMARY KEY,
    name       TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""

_CREATE_PROJECT_ORIGINS = """
CREATE TABLE IF NOT EXISTS project_origins (
    origin     TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id)
)
"""


class StoreError(Exception):
    """Raised on unrecoverable store failures."""


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _enum_value(value: object) -> str:
    return str(value.value) if isinstance(value, Enum) else str(value)


def _coerce_state(value: object) -> State:
    raw = _enum_value(value)
    try:
        return State(raw)
    except ValueError as exc:
        raise StoreError(f"invalid ticket state: {raw!r}") from exc


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db(db_path: Optional[Path] = None) -> Path:  # noqa: UP007
    """Ensure the database and schema exist. Returns the resolved db path."""
    path = db_path or _DEFAULT_DB
    with _connect(path) as conn:
        conn.execute(_CREATE_PACKETS)
        conn.execute(_CREATE_BASELINES)
        conn.execute(_CREATE_CHECK_RESULTS)
        conn.execute(_CREATE_TICKETS)
        conn.execute(_CREATE_PROJECTS)
        conn.execute(_CREATE_PROJECT_ORIGINS)
        try:
            conn.execute("ALTER TABLE packets ADD COLUMN diff_result TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE packets ADD COLUMN source_ticket_id TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE packets ADD COLUMN review_status TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE packets ADD COLUMN triage_status TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE packets ADD COLUMN priority TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE packets ADD COLUMN project_id TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE tickets ADD COLUMN project_id TEXT")
        except sqlite3.OperationalError:
            pass
    return path


def insert_packet(packet: dict[str, object], db_path: Optional[Path] = None) -> None:  # noqa: UP007
    """Insert a packet dict into the store. Raises StoreError on failure."""
    path = db_path or _DEFAULT_DB
    vid = str(packet.get("verification_id", ""))
    if not vid:
        raise StoreError("packet missing verification_id")
    diff_raw = packet.get("diff_result")
    diff_json: Optional[str] = json.dumps(diff_raw) if diff_raw is not None else None
    review = packet.get("review_status")
    review_str: Optional[str] = str(review) if review is not None else None
    try:
        with _connect(path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO packets
                    (verification_id, task_id, issue_type, severity, outcome,
                     summary, artifact_refs, followup_candidates, verified_at,
                     diff_result, review_status, raw)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    vid,
                    packet.get("task_id"),
                    str(packet.get("issue_type", "")),
                    str(packet.get("severity", "")),
                    str(packet.get("outcome", "")),
                    str(packet.get("summary", "")),
                    json.dumps(packet.get("artifact_refs", [])),
                    json.dumps(packet.get("followup_candidates", [])),
                    packet.get("verified_at"),
                    diff_json,
                    review_str,
                    json.dumps(packet),
                ),
            )
    except sqlite3.Error as exc:
        raise StoreError(f"insert failed: {exc}") from exc


def list_packets(
    db_path: Optional[Path] = None,  # noqa: UP007
    outcome: Optional[str] = None,  # noqa: UP007
    task_id: Optional[str] = None,  # noqa: UP007
) -> list[dict[str, object]]:
    """Return all packets, optionally filtered by outcome or task_id."""
    path = db_path or _DEFAULT_DB
    if not path.exists():
        return []
    clauses: list[str] = []
    params: list[str] = []
    if outcome:
        clauses.append("outcome = ?")
        params.append(outcome)
    if task_id:
        clauses.append("task_id = ?")
        params.append(task_id)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    try:
        with _connect(path) as conn:
            rows = conn.execute(
                f"SELECT raw FROM packets {where} ORDER BY verified_at ASC",
                params,
            ).fetchall()
    except sqlite3.Error as exc:
        raise StoreError(f"list failed: {exc}") from exc
    return [json.loads(row["raw"]) for row in rows]


def count_packets(
    db_path: Optional[Path] = None,  # noqa: UP007
    outcome: Optional[str] = None,  # noqa: UP007
    task_id: Optional[str] = None,  # noqa: UP007
    triage_status: Optional[str] = None,  # noqa: UP007
) -> int:
    """Return the total packet count, optionally filtered by outcome, task_id, or triage_status."""
    path = db_path or _DEFAULT_DB
    if not path.exists():
        return 0
    clauses: list[str] = []
    params: list[str] = []
    if outcome:
        clauses.append("outcome = ?")
        params.append(outcome)
    if task_id:
        clauses.append("task_id = ?")
        params.append(task_id)
    if triage_status:
        clauses.append("triage_status = ?")
        params.append(triage_status)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    try:
        with _connect(path) as conn:
            row = conn.execute(
                f"SELECT COUNT(*) AS n FROM packets {where}",
                params,
            ).fetchone()
    except sqlite3.Error as exc:
        raise StoreError(f"count failed: {exc}") from exc
    return int(row["n"]) if row is not None else 0


def list_packets_page(
    db_path: Optional[Path] = None,  # noqa: UP007
    outcome: Optional[str] = None,  # noqa: UP007
    task_id: Optional[str] = None,  # noqa: UP007
    triage_status: Optional[str] = None,  # noqa: UP007
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, object]]:
    """Return a page of packets (newest first), filtered + paged at the SQL level.

    Unlike :func:`list_packets`, this never materialises the full table — the
    LIMIT/OFFSET is applied by SQLite so large stores stay cheap to page through.
    """
    path = db_path or _DEFAULT_DB
    if not path.exists():
        return []
    clauses: list[str] = []
    params: list[str] = []
    if outcome:
        clauses.append("outcome = ?")
        params.append(outcome)
    if task_id:
        clauses.append("task_id = ?")
        params.append(task_id)
    if triage_status:
        clauses.append("triage_status = ?")
        params.append(triage_status)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    safe_limit = max(0, int(limit))
    safe_offset = max(0, int(offset))
    try:
        with _connect(path) as conn:
            rows = conn.execute(
                f"SELECT raw, severity, triage_status, priority, project_id FROM packets {where} "
                "ORDER BY verified_at DESC, verification_id DESC LIMIT ? OFFSET ?",
                [*params, safe_limit, safe_offset],
            ).fetchall()
    except sqlite3.Error as exc:
        raise StoreError(f"list page failed: {exc}") from exc
    return [_row_to_packet(row) for row in rows]


def _row_to_packet(row: sqlite3.Row) -> dict[str, object]:
    """Parse a packet's raw JSON and overlay the mutable triage columns.

    ``severity``/``triage_status``/``priority`` are updated in-place via the
    setters below without rewriting ``raw``, so the row's live column values
    take precedence over whatever was captured in ``raw`` at insert time.
    """
    packet = cast(dict[str, object], json.loads(row["raw"]))
    packet["severity"] = row["severity"]
    packet["triage_status"] = row["triage_status"]
    packet["priority"] = row["priority"]
    if "source_ticket_id" in row.keys():
        packet["source_ticket_id"] = row["source_ticket_id"]
    if "project_id" in row.keys():
        packet["project_id"] = row["project_id"]
    return packet


def get_packet(
    verification_id: str,
    db_path: Optional[Path] = None,  # noqa: UP007
) -> Optional[dict[str, object]]:  # noqa: UP007
    """Return a single packet by verification_id, or None if not found."""
    path = db_path or _DEFAULT_DB
    if not path.exists():
        return None
    try:
        with _connect(path) as conn:
            row = conn.execute(
                "SELECT raw, severity, triage_status, priority, source_ticket_id, project_id "
                "FROM packets WHERE verification_id = ?",
                (verification_id,),
            ).fetchone()
    except sqlite3.Error as exc:
        raise StoreError(f"get_packet failed: {exc}") from exc
    if row is None:
        return None
    return _row_to_packet(row)


def import_packets(packets: list[dict[str, object]], db_path: Optional[Path] = None) -> int:  # noqa: UP007
    """Bulk-insert a list of packet dicts. Returns count inserted."""
    path = db_path or _DEFAULT_DB
    init_db(path)
    count = 0
    for packet in packets:
        try:
            insert_packet(packet, path)
            count += 1
        except StoreError:
            continue
    return count


def set_baseline(verification_id: str, db_path: Optional[Path] = None) -> str:  # noqa: UP007
    """Mark a packet as the baseline for its URL. Returns the URL. Raises StoreError if packet not found."""
    path = db_path or _DEFAULT_DB
    packets = list_packets(path)
    packet = next((p for p in packets if str(p.get("verification_id", "")) == verification_id), None)
    if packet is None:
        raise StoreError(f"packet {verification_id} not found")
    url = str(packet.get("url", "")).strip()
    if not url:
        raise StoreError(f"packet {verification_id} has no url field")
    try:
        with _connect(path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO baselines (url, verification_id) VALUES (?, ?)",
                (url, verification_id),
            )
    except sqlite3.Error as exc:
        raise StoreError(f"set_baseline failed: {exc}") from exc
    return url


def get_baseline_for_url(url: str, db_path: Optional[Path] = None) -> Optional[dict[str, object]]:  # noqa: UP007
    """Return the baseline packet for a URL, or None if no baseline is set."""
    path = db_path or _DEFAULT_DB
    if not path.exists():
        return None
    try:
        with _connect(path) as conn:
            row = conn.execute(
                "SELECT verification_id FROM baselines WHERE url = ?", (url,)
            ).fetchone()
    except sqlite3.Error as exc:
        raise StoreError(f"get_baseline_for_url failed: {exc}") from exc
    if row is None:
        return None
    vid = row["verification_id"]
    packets = list_packets(path)
    return next((p for p in packets if str(p.get("verification_id", "")) == vid), None)


def list_baselines(db_path: Optional[Path] = None) -> dict[str, str]:  # noqa: UP007
    """Return a mapping of {url: verification_id} for all set baselines."""
    path = db_path or _DEFAULT_DB
    if not path.exists():
        return {}
    try:
        with _connect(path) as conn:
            rows = conn.execute("SELECT url, verification_id FROM baselines").fetchall()
    except sqlite3.Error as exc:
        raise StoreError(f"list_baselines failed: {exc}") from exc
    return {row["url"]: row["verification_id"] for row in rows}


def insert_check_result(result: dict[str, object], db_path: Optional[Path] = None) -> None:  # noqa: UP007
    """Insert a check result dict into the check_results table."""
    path = db_path or _DEFAULT_DB
    try:
        with _connect(path) as conn:
            conn.execute(
                """
                INSERT INTO check_results
                    (check_id, check_type, target, passed, assertions, error, checked_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(result.get("check_id", "")),
                    str(result.get("check_type", "")),
                    str(result.get("target", "")),
                    1 if result.get("passed") else 0,
                    json.dumps(result.get("assertions", [])),
                    result.get("error"),
                    str(result.get("checked_at", "")),
                ),
            )
    except sqlite3.Error as exc:
        raise StoreError(f"insert_check_result failed: {exc}") from exc


def list_check_results(db_path: Optional[Path] = None) -> list[dict[str, object]]:  # noqa: UP007
    """Return all check results ordered by checked_at ascending."""
    path = db_path or _DEFAULT_DB
    if not path.exists():
        return []
    try:
        with _connect(path) as conn:
            rows = conn.execute(
                "SELECT check_id, check_type, target, passed, assertions, error, checked_at"
                " FROM check_results ORDER BY checked_at ASC"
            ).fetchall()
    except sqlite3.Error as exc:
        raise StoreError(f"list_check_results failed: {exc}") from exc
    return [
        {
            "check_id": row["check_id"],
            "check_type": row["check_type"],
            "target": row["target"],
            "passed": bool(row["passed"]),
            "assertions": json.loads(row["assertions"]),
            "error": row["error"],
            "checked_at": row["checked_at"],
        }
        for row in rows
    ]


def set_review_status(
    verification_id: str,
    status: str,
    db_path: Optional[Path] = None,  # noqa: UP007
) -> None:
    """Set review_status on a packet and update its raw JSON. Raises StoreError if not found."""
    if status not in ("approved", "rejected"):
        raise StoreError(f"invalid review_status: {status!r}")
    path = db_path or _DEFAULT_DB
    packets = list_packets(path)
    packet = next((p for p in packets if str(p.get("verification_id", "")) == verification_id), None)
    if packet is None:
        raise StoreError(f"packet {verification_id} not found")
    packet["review_status"] = status
    try:
        with _connect(path) as conn:
            conn.execute(
                "UPDATE packets SET review_status=?, raw=? WHERE verification_id=?",
                (status, json.dumps(packet), verification_id),
            )
    except sqlite3.Error as exc:
        raise StoreError(f"set_review_status failed: {exc}") from exc


def _set_column(
    verification_id: str,
    column: str,
    value: str,
    db_path: Optional[Path] = None,  # noqa: UP007
) -> None:
    """Update a single triage column and its raw JSON. Raises StoreError if not found.

    ``column`` is interpolated into the SQL string, which is only safe because
    it is always one of the fixed literals passed by the setters below —
    never caller-supplied. The value and verification_id are always bound as
    parameters. Mirrors :func:`set_review_status`'s read/mutate/write of
    ``raw`` so every consumer (including ``list_packets``, which has no
    column overlay) sees the current value.
    """
    path = db_path or _DEFAULT_DB
    packets = list_packets(path)
    packet = next((p for p in packets if str(p.get("verification_id", "")) == verification_id), None)
    if packet is None:
        raise StoreError(f"packet {verification_id} not found")
    packet[column] = value
    try:
        with _connect(path) as conn:
            conn.execute(
                f"UPDATE packets SET {column} = ?, raw = ? WHERE verification_id = ?",
                (value, json.dumps(packet), verification_id),
            )
    except sqlite3.Error as exc:
        raise StoreError(f"set_{column} failed: {exc}") from exc


def set_packet_project(
    verification_id: str,
    project_id: str,
    db_path: Optional[Path] = None,  # noqa: UP007
) -> None:
    """Set project_id on a packet (column + raw JSON). Raises StoreError if not found."""
    _set_column(verification_id, "project_id", project_id, db_path)


def set_triage_status(
    verification_id: str,
    status: str,
    db_path: Optional[Path] = None,  # noqa: UP007
) -> None:
    """Set triage_status on a packet. Raises StoreError if not found."""
    _set_column(verification_id, "triage_status", status, db_path)


def set_severity(
    verification_id: str,
    severity: str,
    db_path: Optional[Path] = None,  # noqa: UP007
) -> None:
    """Set severity on a packet. Raises StoreError if not found."""
    _set_column(verification_id, "severity", severity, db_path)


def set_priority(
    verification_id: str,
    priority: str,
    db_path: Optional[Path] = None,  # noqa: UP007
) -> None:
    """Set priority on a packet. Raises StoreError if not found."""
    _set_column(verification_id, "priority", priority, db_path)


def _next_ticket_id(conn: sqlite3.Connection) -> str:
    """Return the next monotonic ``ASSAY-<n>`` id. Must run inside a write transaction."""
    row = conn.execute(
        "SELECT id FROM tickets WHERE id GLOB 'ASSAY-[0-9]*' "
        "ORDER BY CAST(SUBSTR(id, 7) AS INTEGER) DESC LIMIT 1"
    ).fetchone()
    n = int(str(row["id"]).split("-", 1)[1]) if row is not None else 0
    return f"ASSAY-{n + 1}"


def insert_ticket(
    title: str,
    severity: str,
    priority: str = "none",
    state: object = State.TRIAGE,
    grain_task_id: Optional[str] = None,  # noqa: UP007
    parent_id: Optional[str] = None,  # noqa: UP007
    db_path: Optional[Path] = None,  # noqa: UP007
    project_id: Optional[str] = None,  # noqa: UP007
) -> str:
    """Create a ticket with a freshly minted ``ASSAY-<n>`` id. Returns the id.

    The id is minted under a ``BEGIN IMMEDIATE`` write lock so concurrent writers
    to the single-writer SQLite store cannot mint the same number.
    """
    path = db_path or _DEFAULT_DB
    state_value = _coerce_state(state).value
    priority_value = _enum_value(priority)
    severity_value = _enum_value(severity)
    if priority_value not in _PRIORITY_VALUES:
        raise StoreError(f"invalid priority: {priority_value!r}")
    if not title:
        raise StoreError("ticket requires a non-empty title")
    now = _utcnow()
    try:
        with _connect(path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            ticket_id = _next_ticket_id(conn)
            conn.execute(
                """
                INSERT INTO tickets
                    (id, title, severity, priority, state, grain_task_id,
                     parent_id, created_at, updated_at, project_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ticket_id,
                    title,
                    severity_value,
                    priority_value,
                    state_value,
                    grain_task_id,
                    parent_id,
                    now,
                    now,
                    project_id,
                ),
            )
    except sqlite3.Error as exc:
        raise StoreError(f"insert_ticket failed: {exc}") from exc
    return ticket_id


def get_ticket(
    ticket_id: str,
    db_path: Optional[Path] = None,  # noqa: UP007
) -> Optional[dict[str, object]]:  # noqa: UP007
    """Return a single ticket by id, or None if not found."""
    path = db_path or _DEFAULT_DB
    if not path.exists():
        return None
    try:
        with _connect(path) as conn:
            row = conn.execute(
                "SELECT id, title, severity, priority, state, grain_task_id, "
                "parent_id, created_at, updated_at, project_id FROM tickets WHERE id = ?",
                (ticket_id,),
            ).fetchone()
    except sqlite3.Error as exc:
        raise StoreError(f"get_ticket failed: {exc}") from exc
    return cast(dict[str, object], dict(row)) if row is not None else None


def list_tickets(
    state: object = None,
    db_path: Optional[Path] = None,  # noqa: UP007
) -> list[dict[str, object]]:
    """Return tickets newest-first; filter by ``state`` (str or State) when given."""
    path = db_path or _DEFAULT_DB
    if not path.exists():
        return []
    state_value = _coerce_state(state).value if state is not None else None
    try:
        with _connect(path) as conn:
            if state_value is None:
                rows = conn.execute(
                    "SELECT id, title, severity, priority, state, grain_task_id, "
                    "parent_id, created_at, updated_at FROM tickets "
                    "ORDER BY created_at DESC"
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id, title, severity, priority, state, grain_task_id, "
                    "parent_id, created_at, updated_at FROM tickets "
                    "WHERE state = ? ORDER BY created_at DESC",
                    (state_value,),
                ).fetchall()
    except sqlite3.Error as exc:
        raise StoreError(f"list_tickets failed: {exc}") from exc
    return [cast(dict[str, object], dict(row)) for row in rows]


def advance_ticket(
    ticket_id: str,
    new_state: object,
    db_path: Optional[Path] = None,  # noqa: UP007
) -> None:
    """Move a ticket to ``new_state`` if the transition is legal. Raises StoreError otherwise.

    Legal path: triage -> todo -> in_progress -> in_review -> done, with canceled
    reachable from any non-terminal state. done and canceled are terminal.
    """
    path = db_path or _DEFAULT_DB
    target = _coerce_state(new_state)
    try:
        with _connect(path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT state FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
            if row is None:
                raise StoreError(f"ticket {ticket_id} not found")
            current = _coerce_state(row["state"])
            if target not in _ALLOWED_TRANSITIONS[current]:
                raise StoreError(f"illegal transition {current.value} -> {target.value}")
            conn.execute(
                "UPDATE tickets SET state = ?, updated_at = ? WHERE id = ?",
                (target.value, _utcnow(), ticket_id),
            )
    except sqlite3.Error as exc:
        raise StoreError(f"advance_ticket failed: {exc}") from exc


def set_ticket_grain_task_id(
    ticket_id: str,
    grain_task_id: str,
    db_path: Optional[Path] = None,  # noqa: UP007
) -> None:
    """Bind a ticket to the Grain ``TASK-####`` minted for it. Ticket<->task stays 1:1 (CP-006 §3)."""
    path = db_path or _DEFAULT_DB
    try:
        with _connect(path) as conn:
            cur = conn.execute(
                "UPDATE tickets SET grain_task_id = ?, updated_at = ? WHERE id = ?",
                (grain_task_id, _utcnow(), ticket_id),
            )
            if cur.rowcount == 0:
                raise StoreError(f"ticket {ticket_id} not found")
    except sqlite3.Error as exc:
        raise StoreError(f"set_ticket_grain_task_id failed: {exc}") from exc


def set_source_ticket_id(
    verification_id: str,
    ticket_id: str,
    db_path: Optional[Path] = None,  # noqa: UP007
) -> None:
    """Link a packet to its owning ticket via ``packets.source_ticket_id``."""
    path = db_path or _DEFAULT_DB
    try:
        with _connect(path) as conn:
            cur = conn.execute(
                "UPDATE packets SET source_ticket_id = ? WHERE verification_id = ?",
                (ticket_id, verification_id),
            )
            if cur.rowcount == 0:
                raise StoreError(f"packet {verification_id} not found")
    except sqlite3.Error as exc:
        raise StoreError(f"set_source_ticket_id failed: {exc}") from exc


def _derive_backfill_state(
    triage_status: Optional[str],  # noqa: UP007
    review_status: Optional[str],  # noqa: UP007
    outcome: Optional[str],  # noqa: UP007
) -> State:
    """Map a legacy packet's live status columns onto the single ticket lifecycle.

    A human-approved review is terminal (done); a dismissal is canceled. An imported
    packet had a Grain task open, so a passing verification proposed closure (in_review)
    while a failing/rejected one stayed in_progress. Promoted-but-unpulled is todo;
    everything earlier is still triage.
    """
    if review_status == "approved":
        return State.DONE
    if triage_status == "dismissed":
        return State.CANCELED
    if triage_status == "imported":
        if review_status == "rejected":
            return State.IN_PROGRESS
        return State.IN_REVIEW if outcome == "pass" else State.IN_PROGRESS
    if triage_status == "promoted":
        return State.TODO
    return State.TRIAGE


def backfill_tickets(db_path: Optional[Path] = None) -> int:  # noqa: UP007
    """Create one ticket per packet that has none yet, deriving state from live columns.

    State is derived from the LIVE ``triage_status``/``review_status``/``outcome`` columns
    (via :func:`_row_to_packet`'s overlay), never from stale ``raw``. Returns the count of
    tickets created. Idempotent: packets already linked via ``source_ticket_id`` are skipped.
    """
    path = db_path or _DEFAULT_DB
    init_db(path)
    with _connect(path) as conn:
        rows = conn.execute(
            "SELECT verification_id, raw, severity, triage_status, priority, "
            "review_status, outcome FROM packets WHERE source_ticket_id IS NULL "
            "ORDER BY verified_at ASC, verification_id ASC"
        ).fetchall()
    count = 0
    for row in rows:
        packet = _row_to_packet(row)
        state = _derive_backfill_state(
            _opt_str(packet.get("triage_status")),
            _opt_str(row["review_status"]),
            _opt_str(row["outcome"]),
        )
        severity = _opt_str(packet.get("severity")) or "info"
        priority = _opt_str(packet.get("priority")) or "none"
        title = _opt_str(packet.get("summary")) or str(row["verification_id"])
        grain_task_id = _opt_str(packet.get("task_id"))
        ticket_id = insert_ticket(
            title=title,
            severity=severity,
            priority=priority,
            state=state,
            grain_task_id=grain_task_id,
            db_path=path,
        )
        set_source_ticket_id(str(row["verification_id"]), ticket_id, path)
        count += 1
    return count


def _opt_str(value: object) -> Optional[str]:  # noqa: UP007
    return str(value) if value is not None else None


def insert_project(
    name: str,
    project_id: Optional[str] = None,  # noqa: UP007
    db_path: Optional[Path] = None,  # noqa: UP007
) -> str:
    """Create a project, returning its id. Generates a uuid id when none is given."""
    if not name:
        raise StoreError("project requires a non-empty name")
    path = db_path or _DEFAULT_DB
    pid = project_id or uuid.uuid4().hex
    now = _utcnow()
    try:
        with _connect(path) as conn:
            conn.execute(_CREATE_PROJECTS)
            conn.execute(
                "INSERT OR IGNORE INTO projects (id, name, created_at, updated_at) "
                "VALUES (?, ?, ?, ?)",
                (pid, name, now, now),
            )
    except sqlite3.Error as exc:
        raise StoreError(f"insert_project failed: {exc}") from exc
    return pid


def get_project(
    project_id: str,
    db_path: Optional[Path] = None,  # noqa: UP007
) -> Optional[dict[str, object]]:  # noqa: UP007
    """Return a project by id, or None."""
    path = db_path or _DEFAULT_DB
    if not path.exists():
        return None
    try:
        with _connect(path) as conn:
            row = conn.execute(
                "SELECT id, name, created_at, updated_at FROM projects WHERE id = ?",
                (project_id,),
            ).fetchone()
    except sqlite3.Error as exc:
        raise StoreError(f"get_project failed: {exc}") from exc
    return cast(dict[str, object], dict(row)) if row is not None else None


def list_projects(
    db_path: Optional[Path] = None,  # noqa: UP007
) -> list[dict[str, object]]:
    """Return all projects, newest first (deterministic via the monotonic rowid tiebreaker)."""
    path = db_path or _DEFAULT_DB
    if not path.exists():
        return []
    try:
        with _connect(path) as conn:
            rows = conn.execute(
                "SELECT id, name, created_at, updated_at FROM projects "
                "ORDER BY created_at DESC, rowid DESC"
            ).fetchall()
    except sqlite3.Error as exc:
        raise StoreError(f"list_projects failed: {exc}") from exc
    return [cast(dict[str, object], dict(row)) for row in rows]


def add_project_origin(
    project_id: str,
    origin: str,
    db_path: Optional[Path] = None,  # noqa: UP007
) -> None:
    """Bind an origin to a project. Origin is globally UNIQUE; a duplicate raises StoreError."""
    path = db_path or _DEFAULT_DB
    if not origin:
        raise StoreError("origin must be non-empty")
    try:
        with _connect(path) as conn:
            conn.execute(_CREATE_PROJECT_ORIGINS)
            conn.execute(
                "INSERT INTO project_origins (origin, project_id) VALUES (?, ?)",
                (origin, project_id),
            )
    except sqlite3.IntegrityError as exc:
        raise StoreError(f"origin already registered: {origin}") from exc
    except sqlite3.Error as exc:
        raise StoreError(f"add_project_origin failed: {exc}") from exc


def list_project_origins(
    project_id: Optional[str] = None,  # noqa: UP007
    db_path: Optional[Path] = None,  # noqa: UP007
) -> list[dict[str, object]]:
    """Return origins, optionally scoped to a single project."""
    path = db_path or _DEFAULT_DB
    if not path.exists():
        return []
    try:
        with _connect(path) as conn:
            if project_id is None:
                rows = conn.execute(
                    "SELECT origin, project_id FROM project_origins ORDER BY origin ASC"
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT origin, project_id FROM project_origins "
                    "WHERE project_id = ? ORDER BY origin ASC",
                    (project_id,),
                ).fetchall()
    except sqlite3.Error as exc:
        raise StoreError(f"list_project_origins failed: {exc}") from exc
    return [cast(dict[str, object], dict(row)) for row in rows]


def get_project_for_origin(
    origin: str,
    db_path: Optional[Path] = None,  # noqa: UP007
) -> Optional[str]:  # noqa: UP007
    """Return the project id owning ``origin``, or None."""
    path = db_path or _DEFAULT_DB
    if not path.exists():
        return None
    try:
        with _connect(path) as conn:
            row = conn.execute(
                "SELECT project_id FROM project_origins WHERE origin = ?",
                (origin,),
            ).fetchone()
    except sqlite3.Error as exc:
        raise StoreError(f"get_project_for_origin failed: {exc}") from exc
    return str(row["project_id"]) if row is not None else None


def delete_project_origin(
    project_id: str,
    origin: str,
    db_path: Optional[Path] = None,  # noqa: UP007
) -> None:
    """Unbind ``origin`` from ``project_id``. Raises StoreError if the pair is not registered.

    The DELETE is scoped by BOTH origin and project_id, so an operator cannot unbind an
    origin that belongs to a different project. A zero-rowcount delete raises so the API
    layer can surface a 404 rather than silently succeeding on a stale/foreign origin.
    """
    path = db_path or _DEFAULT_DB
    try:
        with _connect(path) as conn:
            conn.execute(_CREATE_PROJECT_ORIGINS)
            cur = conn.execute(
                "DELETE FROM project_origins WHERE origin = ? AND project_id = ?",
                (origin, project_id),
            )
            if cur.rowcount == 0:
                raise StoreError(f"origin not bound to project {project_id}: {origin}")
    except sqlite3.Error as exc:
        raise StoreError(f"delete_project_origin failed: {exc}") from exc
