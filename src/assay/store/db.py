# SPDX-FileCopyrightText: 2024-2026 Shaznay Sison
# SPDX-License-Identifier: AGPL-3.0-only

"""SQLite store for Assay result packets — stdlib sqlite3 only."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Optional

_DEFAULT_DB = Path.home() / ".assay" / "store.db"

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


class StoreError(Exception):
    """Raised on unrecoverable store failures."""


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
        try:
            conn.execute("ALTER TABLE packets ADD COLUMN diff_result TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE packets ADD COLUMN review_status TEXT")
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
