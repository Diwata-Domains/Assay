"""Auth integration tests — valid key → 200, invalid → 401, missing → 401."""

from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from assay.ingest.app import app
from assay.keys.store import create_key, list_keys, revoke_key

_SCREENSHOT = base64.b64encode(b"fake-png").decode()

_PAYLOAD = {
    "captured_at": "2026-04-18T10:00:00Z",
    "url": "https://example.com",
    "viewport": {"width": 1280, "height": 800},
    "user_agent": "Mozilla/5.0",
    "screenshot": _SCREENSHOT,
}


@pytest.fixture()
def ingest_client(tmp_path: Path) -> tuple[TestClient, str, str]:
    """Returns (client, store_path, output_dir) with a fresh key store."""
    store = str(tmp_path / "keys.json")
    output = str(tmp_path / "output")
    app.state.key_store = store
    app.state.output_dir = output
    return TestClient(app), store, output


# ---------------------------------------------------------------------------
# Core auth outcomes
# ---------------------------------------------------------------------------


def test_valid_key_returns_200(ingest_client: tuple[TestClient, str, str]) -> None:
    client, store, _ = ingest_client
    raw = create_key(store, label="sdk")
    r = client.post("/ingest", json=_PAYLOAD, headers={"X-Assay-Key": raw})
    assert r.status_code == 200
    assert r.json() == {"status": "accepted"}


def test_missing_key_returns_401(ingest_client: tuple[TestClient, str, str]) -> None:
    client, _, _ = ingest_client
    r = client.post("/ingest", json=_PAYLOAD)
    assert r.status_code == 401


def test_invalid_key_returns_401(ingest_client: tuple[TestClient, str, str]) -> None:
    client, store, _ = ingest_client
    create_key(store, label="sdk")
    r = client.post("/ingest", json=_PAYLOAD, headers={"X-Assay-Key": "not-the-right-key"})
    assert r.status_code == 401


def test_revoked_key_returns_401(ingest_client: tuple[TestClient, str, str]) -> None:
    client, store, _ = ingest_client
    raw = create_key(store, label="sdk")
    key_id = str(list_keys(store)[0]["id"])
    revoke_key(store, key_id)
    r = client.post("/ingest", json=_PAYLOAD, headers={"X-Assay-Key": raw})
    assert r.status_code == 401


def test_empty_key_header_returns_401(ingest_client: tuple[TestClient, str, str]) -> None:
    client, _, _ = ingest_client
    r = client.post("/ingest", json=_PAYLOAD, headers={"X-Assay-Key": ""})
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# End-to-end: valid auth + packet written
# ---------------------------------------------------------------------------


def test_valid_auth_writes_packet_file(ingest_client: tuple[TestClient, str, str]) -> None:
    client, store, output = ingest_client
    raw = create_key(store, label="sdk")
    r = client.post("/ingest", json=_PAYLOAD, headers={"X-Assay-Key": raw})
    assert r.status_code == 200
    packets = list(Path(output).glob("assay-*.json"))
    assert len(packets) == 1


def test_valid_auth_packet_is_schema_valid(ingest_client: tuple[TestClient, str, str]) -> None:
    client, store, output = ingest_client
    raw = create_key(store, label="sdk")
    client.post("/ingest", json=_PAYLOAD, headers={"X-Assay-Key": raw})
    packet_file = next(Path(output).glob("assay-*.json"))
    packet = json.loads(packet_file.read_text())
    required = {"verification_id", "task_id", "issue_type", "severity", "outcome", "summary"}
    assert required.issubset(packet.keys())
    assert packet["issue_type"] == "screenshot_evidence"
    assert packet["severity"] == "info"
    assert packet["outcome"] == "inconclusive"


def test_multiple_keys_only_valid_one_succeeds(ingest_client: tuple[TestClient, str, str]) -> None:
    client, store, _ = ingest_client
    raw1 = create_key(store, label="key1")
    create_key(store, label="key2")
    r = client.post("/ingest", json=_PAYLOAD, headers={"X-Assay-Key": raw1})
    assert r.status_code == 200


def test_invalid_auth_does_not_write_packet(ingest_client: tuple[TestClient, str, str]) -> None:
    client, _, output = ingest_client
    client.post("/ingest", json=_PAYLOAD, headers={"X-Assay-Key": "bad-key"})
    assert not Path(output).exists() or not list(Path(output).glob("assay-*.json"))
