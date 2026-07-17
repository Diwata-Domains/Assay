# SPDX-FileCopyrightText: 2024-2026 Shaznay Sison
# SPDX-License-Identifier: AGPL-3.0-only

"""Runtime wiring of the CP-006 ticket lifecycle through the live product paths.

These exercise the loop as it actually runs — POST /ingest, the /inbox promote/dismiss
action, POST /promotions/{vid}/ack, and the `assay store migrate` CLI — rather than
calling the store primitives directly, so the state machine cannot go inert at runtime.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from assay._vendor.warden import WardenConfig, issue_token
from assay.auth.admin import hash_password
from assay.cli.main import app as cli_app
from assay.ingest.app import app
from assay.keys.store import create_key
from assay.store.db import get_packet, get_ticket, insert_packet, list_packets_page, set_triage_status

app_module = importlib.import_module("assay.ingest.app")
cli_runner = CliRunner(env={"NO_COLOR": "1"})

_SECRET = "x" * 32
_EMAIL = "admin@test.com"


def _payload(kind: str | None = None, source_ticket_id: str | None = None) -> dict:
    p: dict = {
        "captured_at": "2026-07-07T00:00:00Z",
        "url": "https://x.test",
        "viewport": {"width": 800, "height": 600},
        "user_agent": "UA",
        "screenshot": "aGVsbG8=",
        "user_comment": None,
        "metadata": {},
    }
    if kind:
        p["kind"] = kind
    if source_ticket_id:
        p["source_ticket_id"] = source_ticket_id
    return p


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[TestClient, str, Path]:
    """Session-authed TestClient (for /inbox) that also carries an API key (for /ingest)."""
    monkeypatch.setenv("ASSAY_ADMIN_EMAIL", _EMAIL)
    monkeypatch.setenv("ASSAY_ADMIN_PASSWORD_HASH", hash_password("pw"))
    monkeypatch.setenv("WARDEN_SECRET", _SECRET)
    key = create_key(str(tmp_path / "keys.json"))
    app.state.key_store = str(tmp_path / "keys.json")
    app.state.store_db = str(tmp_path / "s.db")
    app.state.output_dir = str(tmp_path / "out")
    tc = TestClient(app, follow_redirects=False)
    tc.cookies.set("warden_session", issue_token(_EMAIL, WardenConfig(secret=_SECRET)))
    return tc, key, tmp_path / "s.db"


def _vid_of(db: Path, kind: str) -> str:
    packets = list_packets_page(db_path=db)
    match = [p for p in packets if p.get("kind") == kind]
    assert len(match) == 1, packets
    return str(match[0]["verification_id"])


def _force_outcome(monkeypatch: pytest.MonkeyPatch, outcome: str) -> None:
    original = app_module.format_sdk_packet

    def fake(payload: object, verification_id: str | None = None) -> dict[str, object]:
        packet = original(payload, verification_id=verification_id)
        packet["outcome"] = outcome
        return packet

    monkeypatch.setattr(app_module, "format_sdk_packet", fake)


def test_report_ingest_mints_triage_ticket(client: tuple[TestClient, str, Path]) -> None:
    tc, key, db = client
    r = tc.post("/ingest", json=_payload(kind="report"), headers={"X-Assay-Key": key})
    assert r.status_code == 200
    vid = _vid_of(db, "report")
    ticket_id = get_packet(vid, db)["source_ticket_id"]
    assert ticket_id == "ASSAY-1"
    assert get_ticket(str(ticket_id), db)["state"] == "triage"


def test_promote_advances_owning_ticket_to_todo(client: tuple[TestClient, str, Path]) -> None:
    tc, key, db = client
    tc.post("/ingest", json=_payload(kind="report"), headers={"X-Assay-Key": key})
    vid = _vid_of(db, "report")
    ticket_id = str(get_packet(vid, db)["source_ticket_id"])

    r = tc.post(f"/inbox/{vid}/triage", data={"action": "promote"})
    assert r.status_code == 303
    assert get_ticket(ticket_id, db)["state"] == "todo"


def test_dismiss_cancels_owning_ticket(client: tuple[TestClient, str, Path]) -> None:
    tc, key, db = client
    tc.post("/ingest", json=_payload(kind="report"), headers={"X-Assay-Key": key})
    vid = _vid_of(db, "report")
    ticket_id = str(get_packet(vid, db)["source_ticket_id"])

    tc.post(f"/inbox/{vid}/triage", data={"action": "dismiss"})
    assert get_ticket(ticket_id, db)["state"] == "canceled"


def _drive_to_in_progress(tc: TestClient, key: str, db: Path) -> str:
    tc.post("/ingest", json=_payload(kind="report"), headers={"X-Assay-Key": key})
    report_vid = _vid_of(db, "report")
    ticket_id = str(get_packet(report_vid, db)["source_ticket_id"])
    tc.post(f"/inbox/{report_vid}/triage", data={"action": "promote"})
    tc.post(f"/promotions/{report_vid}/ack", headers={"X-Assay-Key": key}, json={"grain_task_id": "TASK-0100"})
    assert get_ticket(ticket_id, db)["state"] == "in_progress"
    return ticket_id


def test_passing_verification_advances_ticket_to_in_review(
    client: tuple[TestClient, str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    tc, key, db = client
    ticket_id = _drive_to_in_progress(tc, key, db)

    _force_outcome(monkeypatch, "pass")
    r = tc.post(
        "/ingest",
        json=_payload(kind="verification", source_ticket_id=ticket_id),
        headers={"X-Assay-Key": key},
    )
    assert r.status_code == 200
    assert get_ticket(ticket_id, db)["state"] == "in_review"


def test_failing_verification_holds_ticket_in_progress(
    client: tuple[TestClient, str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    tc, key, db = client
    ticket_id = _drive_to_in_progress(tc, key, db)

    _force_outcome(monkeypatch, "fail")
    r = tc.post(
        "/ingest",
        json=_payload(kind="verification", source_ticket_id=ticket_id),
        headers={"X-Assay-Key": key},
    )
    assert r.status_code == 200
    # A FAIL keeps the same task open; the ticket must not advance out of in_progress.
    assert get_ticket(ticket_id, db)["state"] == "in_progress"


def test_store_migrate_backfills_legacy_packets(tmp_path: Path) -> None:
    db = tmp_path / "store.db"
    cfg = tmp_path / "assay.toml"
    cfg.write_text(f'[store]\ndb = "{db}"\n[output]\ndirectory = "{tmp_path}"\n')

    from assay.store.db import init_db

    init_db(db)
    insert_packet(
        {
            "verification_id": "legacy-1",
            "task_id": None,
            "issue_type": "bug_finding",
            "severity": "error",
            "outcome": "pass",
            "summary": "a legacy finding",
            "artifact_refs": [],
            "followup_candidates": [],
            "verified_at": "2026-04-29T10:00:00Z",
        },
        db,
    )
    set_triage_status("legacy-1", "promoted", db)

    result = cli_runner.invoke(cli_app, ["--config", str(cfg), "store", "migrate"])
    assert result.exit_code == 0, result.output
    assert "backfilled: 1 ticket(s)" in result.output
    ticket_id = str(get_packet("legacy-1", db)["source_ticket_id"])
    assert get_ticket(ticket_id, db)["state"] == "todo"

    result2 = cli_runner.invoke(cli_app, ["--config", str(cfg), "store", "migrate"])
    assert "backfilled: 0 ticket(s)" in result2.output
