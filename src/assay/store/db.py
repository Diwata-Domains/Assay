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
    raw             TEXT NOT NULL
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
    return path


def insert_packet(packet: dict[str, object], db_path: Optional[Path] = None) -> None:  # noqa: UP007
    """Insert a packet dict into the store. Raises StoreError on failure."""
    path = db_path or _DEFAULT_DB
    vid = str(packet.get("verification_id", ""))
    if not vid:
        raise StoreError("packet missing verification_id")
    try:
        with _connect(path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO packets
                    (verification_id, task_id, issue_type, severity, outcome,
                     summary, artifact_refs, followup_candidates, verified_at, raw)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
