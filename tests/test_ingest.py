"""Tests for the FastAPI ingest endpoint — payload validation and auth."""

from __future__ import annotations

import base64
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from assay.ingest.app import app
from assay.keys.store import create_key

_VALID_SCREENSHOT = base64.b64encode(b"fake-png-bytes").decode()

_VALID_PAYLOAD: dict = {
    "captured_at": "2026-04-18T10:00:00Z",
    "url": "https://example.com",
    "viewport": {"width": 1280, "height": 800},
    "user_agent": "Mozilla/5.0",
    "screenshot": _VALID_SCREENSHOT,
}


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    store = str(tmp_path / "keys.json")
    app.state.key_store = store
    return TestClient(app)


@pytest.fixture()
def client_with_key(tmp_path: Path) -> tuple[TestClient, str]:
    store = str(tmp_path / "keys.json")
    app.state.key_store = store
    raw = create_key(store, label="test")
    return TestClient(app), raw


# ---------------------------------------------------------------------------
# Auth tests
# ---------------------------------------------------------------------------


def test_missing_key_returns_401(client: TestClient) -> None:
    r = client.post("/ingest", json=_VALID_PAYLOAD)
    assert r.status_code == 401


def test_invalid_key_returns_401(client: TestClient) -> None:
    r = client.post("/ingest", json=_VALID_PAYLOAD, headers={"X-Assay-Key": "bad-key"})
    assert r.status_code == 401


def test_valid_key_returns_200(client_with_key: tuple[TestClient, str]) -> None:
    c, key = client_with_key
    r = c.post("/ingest", json=_VALID_PAYLOAD, headers={"X-Assay-Key": key})
    assert r.status_code == 200
    assert r.json() == {"status": "accepted"}


def test_revoked_key_returns_401(tmp_path: Path) -> None:
    from assay.keys.store import list_keys, revoke_key

    store = str(tmp_path / "keys.json")
    app.state.key_store = store
    raw = create_key(store, label="to-revoke")
    key_id = str(list_keys(store)[0]["id"])
    revoke_key(store, key_id)
    c = TestClient(app)
    r = c.post("/ingest", json=_VALID_PAYLOAD, headers={"X-Assay-Key": raw})
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# Payload validation tests (auth satisfied via fixture)
# ---------------------------------------------------------------------------


def test_valid_payload_returns_200(client_with_key: tuple[TestClient, str]) -> None:
    c, key = client_with_key
    r = c.post("/ingest", json=_VALID_PAYLOAD, headers={"X-Assay-Key": key})
    assert r.status_code == 200
    assert r.json() == {"status": "accepted"}


def test_valid_payload_with_optional_fields(client_with_key: tuple[TestClient, str]) -> None:
    c, key = client_with_key
    payload = {**_VALID_PAYLOAD, "user_comment": "looks broken", "metadata": {"env": "staging"}}
    r = c.post("/ingest", json=payload, headers={"X-Assay-Key": key})
    assert r.status_code == 200


def test_user_comment_null_is_valid(client_with_key: tuple[TestClient, str]) -> None:
    c, key = client_with_key
    r = c.post("/ingest", json={**_VALID_PAYLOAD, "user_comment": None}, headers={"X-Assay-Key": key})
    assert r.status_code == 200


def test_missing_captured_at_returns_422(client_with_key: tuple[TestClient, str]) -> None:
    c, key = client_with_key
    payload = {k: v for k, v in _VALID_PAYLOAD.items() if k != "captured_at"}
    r = c.post("/ingest", json=payload, headers={"X-Assay-Key": key})
    assert r.status_code == 422


def test_missing_url_returns_422(client_with_key: tuple[TestClient, str]) -> None:
    c, key = client_with_key
    payload = {k: v for k, v in _VALID_PAYLOAD.items() if k != "url"}
    r = c.post("/ingest", json=payload, headers={"X-Assay-Key": key})
    assert r.status_code == 422


def test_missing_user_agent_returns_422(client_with_key: tuple[TestClient, str]) -> None:
    c, key = client_with_key
    payload = {k: v for k, v in _VALID_PAYLOAD.items() if k != "user_agent"}
    r = c.post("/ingest", json=payload, headers={"X-Assay-Key": key})
    assert r.status_code == 422


def test_missing_screenshot_returns_422(client_with_key: tuple[TestClient, str]) -> None:
    c, key = client_with_key
    payload = {k: v for k, v in _VALID_PAYLOAD.items() if k != "screenshot"}
    r = c.post("/ingest", json=payload, headers={"X-Assay-Key": key})
    assert r.status_code == 422


def test_missing_viewport_returns_422(client_with_key: tuple[TestClient, str]) -> None:
    c, key = client_with_key
    payload = {k: v for k, v in _VALID_PAYLOAD.items() if k != "viewport"}
    r = c.post("/ingest", json=payload, headers={"X-Assay-Key": key})
    assert r.status_code == 422


def test_empty_url_returns_422(client_with_key: tuple[TestClient, str]) -> None:
    c, key = client_with_key
    r = c.post("/ingest", json={**_VALID_PAYLOAD, "url": ""}, headers={"X-Assay-Key": key})
    assert r.status_code == 422


def test_empty_user_agent_returns_422(client_with_key: tuple[TestClient, str]) -> None:
    c, key = client_with_key
    r = c.post("/ingest", json={**_VALID_PAYLOAD, "user_agent": ""}, headers={"X-Assay-Key": key})
    assert r.status_code == 422


def test_empty_captured_at_returns_422(client_with_key: tuple[TestClient, str]) -> None:
    c, key = client_with_key
    r = c.post("/ingest", json={**_VALID_PAYLOAD, "captured_at": ""}, headers={"X-Assay-Key": key})
    assert r.status_code == 422


def test_invalid_base64_screenshot_returns_422(client_with_key: tuple[TestClient, str]) -> None:
    c, key = client_with_key
    r = c.post("/ingest", json={**_VALID_PAYLOAD, "screenshot": "not-valid-base64!!!"}, headers={"X-Assay-Key": key})
    assert r.status_code == 422


def test_empty_screenshot_returns_422(client_with_key: tuple[TestClient, str]) -> None:
    c, key = client_with_key
    r = c.post("/ingest", json={**_VALID_PAYLOAD, "screenshot": ""}, headers={"X-Assay-Key": key})
    assert r.status_code == 422


def test_zero_viewport_width_returns_422(client_with_key: tuple[TestClient, str]) -> None:
    c, key = client_with_key
    payload = {**_VALID_PAYLOAD, "viewport": {"width": 0, "height": 800}}
    r = c.post("/ingest", json=payload, headers={"X-Assay-Key": key})
    assert r.status_code == 422


def test_zero_viewport_height_returns_422(client_with_key: tuple[TestClient, str]) -> None:
    c, key = client_with_key
    payload = {**_VALID_PAYLOAD, "viewport": {"width": 1280, "height": 0}}
    r = c.post("/ingest", json=payload, headers={"X-Assay-Key": key})
    assert r.status_code == 422


def test_negative_viewport_dimension_returns_422(client_with_key: tuple[TestClient, str]) -> None:
    c, key = client_with_key
    payload = {**_VALID_PAYLOAD, "viewport": {"width": -1, "height": 800}}
    r = c.post("/ingest", json=payload, headers={"X-Assay-Key": key})
    assert r.status_code == 422


def test_valid_ingest_writes_packet_file(tmp_path: Path) -> None:
    from assay.keys.store import create_key

    store = str(tmp_path / "keys.json")
    out = str(tmp_path / "output")
    app.state.key_store = store
    app.state.output_dir = out
    raw = create_key(store, label="test")
    c = TestClient(app)
    r = c.post("/ingest", json=_VALID_PAYLOAD, headers={"X-Assay-Key": raw})
    assert r.status_code == 200
    packets = list(Path(out).glob("assay-*.json"))
    assert len(packets) == 1
