"""SDK → ingest integration test.

Simulates the full path a browser SDK capture takes:
  SDK payload  →  POST /ingest  →  formatter  →  packet file on disk

Verifies payload contract (data_contracts.md §2) and packet output (§1).
"""

from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from assay.ingest.app import app
from assay.keys.store import create_key

_SCREENSHOT = base64.b64encode(b"fake-png-data").decode()

_SDK_PAYLOAD = {
    "captured_at": "2026-04-20T10:00:00Z",
    "url": "https://app.example.com/dashboard",
    "viewport": {"width": 1440, "height": 900},
    "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "screenshot": _SCREENSHOT,
    "user_comment": "Button label is truncated on mobile",
    "metadata": {"env": "staging", "version": "1.2.3"},
}


@pytest.fixture()
def ingest_client(tmp_path: Path) -> tuple[TestClient, str, str]:
    store = str(tmp_path / "keys.json")
    output = str(tmp_path / "output")
    app.state.key_store = store
    app.state.output_dir = output
    return TestClient(app), store, output


def test_sdk_capture_returns_200(ingest_client: tuple[TestClient, str, str]) -> None:
    client, store, _ = ingest_client
    key = create_key(store, label="sdk-integration")
    r = client.post("/ingest", json=_SDK_PAYLOAD, headers={"X-Assay-Key": key})
    assert r.status_code == 200
    assert r.json() == {"status": "accepted"}


def test_sdk_capture_writes_exactly_one_packet(ingest_client: tuple[TestClient, str, str]) -> None:
    client, store, output = ingest_client
    key = create_key(store, label="sdk-integration")
    client.post("/ingest", json=_SDK_PAYLOAD, headers={"X-Assay-Key": key})
    packets = list(Path(output).glob("assay-*.json"))
    assert len(packets) == 1


def test_sdk_packet_has_required_fields(ingest_client: tuple[TestClient, str, str]) -> None:
    client, store, output = ingest_client
    key = create_key(store, label="sdk-integration")
    client.post("/ingest", json=_SDK_PAYLOAD, headers={"X-Assay-Key": key})
    packet = json.loads(next(Path(output).glob("assay-*.json")).read_text())
    required = {"verification_id", "task_id", "issue_type", "severity", "outcome", "summary"}
    assert required.issubset(packet.keys())


def test_sdk_packet_issue_type_is_screenshot_evidence(ingest_client: tuple[TestClient, str, str]) -> None:
    client, store, output = ingest_client
    key = create_key(store, label="sdk-integration")
    client.post("/ingest", json=_SDK_PAYLOAD, headers={"X-Assay-Key": key})
    packet = json.loads(next(Path(output).glob("assay-*.json")).read_text())
    assert packet["issue_type"] == "screenshot_evidence"


def test_sdk_packet_severity_is_info(ingest_client: tuple[TestClient, str, str]) -> None:
    client, store, output = ingest_client
    key = create_key(store, label="sdk-integration")
    client.post("/ingest", json=_SDK_PAYLOAD, headers={"X-Assay-Key": key})
    packet = json.loads(next(Path(output).glob("assay-*.json")).read_text())
    assert packet["severity"] == "info"


def test_sdk_packet_outcome_is_inconclusive(ingest_client: tuple[TestClient, str, str]) -> None:
    client, store, output = ingest_client
    key = create_key(store, label="sdk-integration")
    client.post("/ingest", json=_SDK_PAYLOAD, headers={"X-Assay-Key": key})
    packet = json.loads(next(Path(output).glob("assay-*.json")).read_text())
    assert packet["outcome"] == "inconclusive"


def test_sdk_packet_verified_at_matches_captured_at(ingest_client: tuple[TestClient, str, str]) -> None:
    client, store, output = ingest_client
    key = create_key(store, label="sdk-integration")
    client.post("/ingest", json=_SDK_PAYLOAD, headers={"X-Assay-Key": key})
    packet = json.loads(next(Path(output).glob("assay-*.json")).read_text())
    assert packet["verified_at"] == _SDK_PAYLOAD["captured_at"]


def test_sdk_packet_summary_contains_url(ingest_client: tuple[TestClient, str, str]) -> None:
    client, store, output = ingest_client
    key = create_key(store, label="sdk-integration")
    client.post("/ingest", json=_SDK_PAYLOAD, headers={"X-Assay-Key": key})
    packet = json.loads(next(Path(output).glob("assay-*.json")).read_text())
    assert "app.example.com" in packet["summary"]


def test_sdk_multiple_captures_write_separate_packets(ingest_client: tuple[TestClient, str, str]) -> None:
    client, store, output = ingest_client
    key = create_key(store, label="sdk-integration")
    headers = {"X-Assay-Key": key}
    client.post("/ingest", json=_SDK_PAYLOAD, headers=headers)
    client.post("/ingest", json={**_SDK_PAYLOAD, "url": "https://app.example.com/settings"}, headers=headers)
    packets = list(Path(output).glob("assay-*.json"))
    assert len(packets) == 2
