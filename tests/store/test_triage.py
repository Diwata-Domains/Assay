# SPDX-FileCopyrightText: 2024-2026 Shaznay Sison
# SPDX-License-Identifier: AGPL-3.0-only

"""Unit tests for triage_status + priority columns and helpers."""

from __future__ import annotations

from pathlib import Path

from assay.store.db import (
    count_packets,
    get_packet,
    init_db,
    insert_packet,
    list_packets_page,
    set_priority,
    set_severity,
    set_triage_status,
)


def _packet(vid: str) -> dict[str, object]:
    return {
        "verification_id": vid,
        "task_id": None,
        "issue_type": "report",
        "severity": "",
        "outcome": "report",
        "summary": "s",
        "artifact_refs": [],
        "followup_candidates": [],
        "verified_at": "2026-07-07T00:00:00Z",
    }


def test_triage_and_priority_roundtrip(tmp_path: Path) -> None:
    db = tmp_path / "s.db"
    init_db(db)
    insert_packet(_packet("v1"), db)
    set_triage_status("v1", "new", db)
    set_severity("v1", "warn", db)
    set_priority("v1", "high", db)
    p = get_packet("v1", db)
    assert p is not None
    assert p["triage_status"] == "new"
    assert p["severity"] == "warn"
    assert p["priority"] == "high"


def test_filter_by_triage_status(tmp_path: Path) -> None:
    db = tmp_path / "s.db"
    init_db(db)
    insert_packet(_packet("v1"), db)
    set_triage_status("v1", "new", db)
    insert_packet(_packet("v2"), db)
    set_triage_status("v2", "imported", db)
    page = list_packets_page(db, triage_status="new")
    assert [p["verification_id"] for p in page] == ["v1"]
    assert count_packets(db, triage_status="new") == 1
