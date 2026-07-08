# SPDX-FileCopyrightText: 2024-2026 Shaznay Sison
# SPDX-License-Identifier: AGPL-3.0-only

"""Promotions API tests — key-authed pull (`GET /promotions`) + ack (`POST /promotions/{vid}/ack`).

Mirrors the auth trust model of `POST /ingest`: both endpoints are gated by
`X-Assay-Key` (via the shared `_require_api_key` dependency) rather than a Warden
session, since Grain (the machine consumer) has no browser session to present.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from assay.ingest.app import app
from assay.keys.store import create_key
from assay.store.db import get_packet, init_db, insert_packet, set_triage_status


def _packet(vid: str, **overrides: object) -> dict[str, object]:
    packet: dict[str, object] = {
        "verification_id": vid,
        "task_id": None,
        "issue_type": "report",
        "severity": "medium",
        "outcome": "report",
        "summary": f"summary for {vid}",
        "url": "https://example.test/page",
        "artifact_refs": [],
        "followup_candidates": [],
        "verified_at": "2026-07-07T00:00:00Z",
        "user_comment": "please check this",
        "kind": "report",
    }
    packet.update(overrides)
    return packet


@pytest.fixture()
def promo_client(tmp_path: Path) -> tuple[TestClient, str, Path]:
    key_store = str(tmp_path / "keys.json")
    store_db = tmp_path / "s.db"
    key = create_key(key_store)

    app.state.key_store = key_store
    app.state.store_db = str(store_db)
    app.state.output_dir = str(tmp_path / "out")

    init_db(store_db)
    insert_packet(_packet("v_new"), store_db)
    set_triage_status("v_new", "new", store_db)

    insert_packet(
        _packet("v_prom", remediation="bump the z-index on the modal"),
        store_db,
    )
    set_triage_status("v_prom", "promoted", store_db)

    return TestClient(app), key, store_db


def test_requires_key(promo_client: tuple[TestClient, str, Path]) -> None:
    client, key, db = promo_client
    assert client.get("/promotions").status_code == 401


def test_rejects_bad_key(promo_client: tuple[TestClient, str, Path]) -> None:
    client, key, db = promo_client
    resp = client.get("/promotions", headers={"X-Assay-Key": "not-a-real-key"})
    assert resp.status_code == 401


def test_lists_only_promoted(promo_client: tuple[TestClient, str, Path]) -> None:
    client, key, db = promo_client
    body = client.get("/promotions", headers={"X-Assay-Key": key}).json()
    assert [p["verification_id"] for p in body["promotions"]] == ["v_prom"]


def test_promotion_row_shape(promo_client: tuple[TestClient, str, Path]) -> None:
    client, key, db = promo_client
    body = client.get("/promotions", headers={"X-Assay-Key": key}).json()
    row = body["promotions"][0]
    assert row["url"] == "https://example.test/page"
    assert row["summary"] == "summary for v_prom"
    assert row["severity"] == "medium"
    assert row["user_comment"] == "please check this"
    assert row["kind"] == "report"
    assert row["remediation"] == "bump the z-index on the modal"
    assert row["screenshot_ref"] is None


def test_ack_marks_imported_and_is_idempotent(promo_client: tuple[TestClient, str, Path]) -> None:
    client, key, db = promo_client
    assert client.post("/promotions/v_prom/ack", headers={"X-Assay-Key": key}).status_code == 200

    assert get_packet("v_prom", db)["triage_status"] == "imported"

    # Idempotent: acking an already-imported vid still returns 200, not an error.
    assert client.post("/promotions/v_prom/ack", headers={"X-Assay-Key": key}).status_code == 200

    assert client.get("/promotions", headers={"X-Assay-Key": key}).json()["promotions"] == []


def test_ack_requires_key(promo_client: tuple[TestClient, str, Path]) -> None:
    client, key, db = promo_client
    assert client.post("/promotions/v_prom/ack").status_code == 401


def test_ack_missing_packet_is_404(promo_client: tuple[TestClient, str, Path]) -> None:
    client, key, db = promo_client
    resp = client.post("/promotions/does-not-exist/ack", headers={"X-Assay-Key": key})
    assert resp.status_code == 404


def test_ack_not_currently_promoted_is_idempotent_200(promo_client: tuple[TestClient, str, Path]) -> None:
    # v_new exists but is not "promoted" — acking it should still be a 200, not an error,
    # since ack is idempotent over triage state and only 404s when the packet doesn't exist.
    client, key, db = promo_client
    resp = client.post("/promotions/v_new/ack", headers={"X-Assay-Key": key})
    assert resp.status_code == 200
    assert get_packet("v_new", db)["triage_status"] == "imported"
