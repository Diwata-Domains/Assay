# SPDX-FileCopyrightText: 2024-2026 Shaznay Sison
# SPDX-License-Identifier: AGPL-3.0-only

"""Tests: `kind` routing into the triage inbox on POST /ingest."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from assay.ingest.app import app
from assay.keys.store import create_key
from assay.store.db import get_packet, list_packets_page

# `assay.ingest.__init__` does `from assay.ingest.app import app`, which rebinds the
# `app` attribute on the `assay.ingest` package from the submodule to the FastAPI
# instance. `import assay.ingest.app as x` resolves via that (now-shadowed) attribute
# chain and would hand back the FastAPI instance instead of the module, so the actual
# module object is fetched straight from the import machinery instead.
app_module = importlib.import_module("assay.ingest.app")


def _payload(kind: str | None = None) -> dict:
    p = {
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
    return p


def _client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[TestClient, str]:
    key = create_key(str(tmp_path / "keys.json"))
    app.state.key_store = str(tmp_path / "keys.json")
    app.state.store_db = str(tmp_path / "s.db")
    app.state.output_dir = str(tmp_path / "out")
    return TestClient(app), key


def _only_vid(store_db: str) -> str:
    packets = list_packets_page(db_path=Path(store_db).expanduser())
    assert len(packets) == 1
    return str(packets[0]["verification_id"])


def _get_packet(verification_id: str, store_db: str) -> dict[str, object] | None:
    return get_packet(verification_id, Path(store_db).expanduser())


def _force_outcome(monkeypatch: pytest.MonkeyPatch, outcome: str) -> None:
    """Patch format_sdk_packet so the resulting packet carries the given outcome.

    The SDK ingest formatter always produces outcome="inconclusive" — there is no
    payload field for a caller to set outcome directly — so exercising the
    verification+fail / verification+pass triage branches requires patching the
    call site used by the /ingest handler.
    """
    original = app_module.format_sdk_packet

    def fake_format_sdk_packet(payload: object, verification_id: str | None = None) -> dict[str, object]:
        packet = original(payload, verification_id=verification_id)
        packet["outcome"] = outcome
        return packet

    monkeypatch.setattr(app_module, "format_sdk_packet", fake_format_sdk_packet)


def test_report_enters_inbox(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client, key = _client(tmp_path, monkeypatch)
    r = client.post("/ingest", json=_payload(kind="report"), headers={"X-Assay-Key": key})
    assert r.status_code == 200
    vid = _only_vid(app.state.store_db)
    assert _get_packet(vid, app.state.store_db)["triage_status"] == "new"


def test_default_kind_is_report_and_enters_inbox(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client, key = _client(tmp_path, monkeypatch)
    r = client.post("/ingest", json=_payload(), headers={"X-Assay-Key": key})
    assert r.status_code == 200
    vid = _only_vid(app.state.store_db)
    packet = _get_packet(vid, app.state.store_db)
    assert packet["kind"] == "report"
    assert packet["triage_status"] == "new"


def test_invalid_kind_returns_422(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client, key = _client(tmp_path, monkeypatch)
    r = client.post("/ingest", json=_payload(kind="bogus"), headers={"X-Assay-Key": key})
    assert r.status_code == 422


def test_failed_verification_enters_inbox(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client, key = _client(tmp_path, monkeypatch)
    _force_outcome(monkeypatch, "fail")
    r = client.post("/ingest", json=_payload(kind="verification"), headers={"X-Assay-Key": key})
    assert r.status_code == 200
    vid = _only_vid(app.state.store_db)
    packet = _get_packet(vid, app.state.store_db)
    assert packet["kind"] == "verification"
    assert packet["triage_status"] == "new"


def test_passing_verification_does_not_enter_inbox(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client, key = _client(tmp_path, monkeypatch)
    _force_outcome(monkeypatch, "pass")
    r = client.post("/ingest", json=_payload(kind="verification"), headers={"X-Assay-Key": key})
    assert r.status_code == 200
    vid = _only_vid(app.state.store_db)
    packet = _get_packet(vid, app.state.store_db)
    assert packet["kind"] == "verification"
    assert packet["triage_status"] is None
