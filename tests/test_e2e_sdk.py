"""E2E tests: SDK capture → POST /ingest → formatter → schema-valid packet file.

Complements test_sdk_ingest.py with explicit schema validation and
auth rejection coverage for Phase 8 exit criteria.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path

import jsonschema
import pytest
from fastapi.testclient import TestClient

from assay.ingest.app import app
from assay.keys.store import create_key, revoke_key
from assay.schemas import ASSAY_PAYLOAD

_SCREENSHOT = base64.b64encode(b"fake-png-bytes").decode()

_SDK_PAYLOAD = {
    "captured_at": "2026-04-18T12:00:00Z",
    "url": "https://staging.example.com/checkout",
    "viewport": {"width": 1280, "height": 720},
    "user_agent": "Mozilla/5.0 (compatible; AssaySDK/1.0)",
    "screenshot": _SCREENSHOT,
    "user_comment": "Price display misaligned on Safari",
    "metadata": {},
}


@pytest.fixture()
def client(tmp_path: Path) -> tuple[TestClient, str, str]:
    store = str(tmp_path / "keys.json")
    output = str(tmp_path / "out")
    app.state.key_store = store
    app.state.output_dir = output
    return TestClient(app), store, output


# ---------------------------------------------------------------------------
# E2E: full SDK capture path produces schema-valid packet
# ---------------------------------------------------------------------------


def test_sdk_e2e_packet_is_schema_valid(client: tuple[TestClient, str, str]) -> None:
    c, store, output = client
    key = create_key(store)
    c.post("/ingest", json=_SDK_PAYLOAD, headers={"X-Assay-Key": key})
    packet = json.loads(next(Path(output).glob("assay-*.json")).read_text())
    jsonschema.validate(instance=packet, schema=ASSAY_PAYLOAD)


def test_sdk_e2e_comment_included_in_summary(client: tuple[TestClient, str, str]) -> None:
    c, store, output = client
    key = create_key(store)
    c.post("/ingest", json=_SDK_PAYLOAD, headers={"X-Assay-Key": key})
    packet = json.loads(next(Path(output).glob("assay-*.json")).read_text())
    assert "Price display misaligned" in packet["summary"]


def test_sdk_e2e_no_comment_still_schema_valid(client: tuple[TestClient, str, str]) -> None:
    c, store, output = client
    key = create_key(store)
    payload = {**_SDK_PAYLOAD, "user_comment": None}
    c.post("/ingest", json=payload, headers={"X-Assay-Key": key})
    packet = json.loads(next(Path(output).glob("assay-*.json")).read_text())
    jsonschema.validate(instance=packet, schema=ASSAY_PAYLOAD)


# ---------------------------------------------------------------------------
# Auth rejection E2E (P8-T03 coverage)
# ---------------------------------------------------------------------------


def test_auth_missing_key_returns_401(client: tuple[TestClient, str, str]) -> None:
    c, _, _ = client
    r = c.post("/ingest", json=_SDK_PAYLOAD)
    assert r.status_code == 401


def test_auth_invalid_key_returns_401(client: tuple[TestClient, str, str]) -> None:
    c, _, _ = client
    r = c.post("/ingest", json=_SDK_PAYLOAD, headers={"X-Assay-Key": "invalid-key-value"})
    assert r.status_code == 401


def test_auth_revoked_key_returns_401(client: tuple[TestClient, str, str]) -> None:
    c, store, _ = client
    key = create_key(store)
    # extract ID to revoke — need to list keys; find the one whose raw key matches
    from assay.keys.store import list_keys

    keys = list_keys(store)
    assert len(keys) == 1
    revoke_key(store, keys[0]["id"])

    r = c.post("/ingest", json=_SDK_PAYLOAD, headers={"X-Assay-Key": key})
    assert r.status_code == 401


def test_auth_valid_key_does_not_write_on_401(client: tuple[TestClient, str, str]) -> None:
    c, _, output = client
    c.post("/ingest", json=_SDK_PAYLOAD, headers={"X-Assay-Key": "bad-key"})
    assert list(Path(output).glob("assay-*.json")) == []
