"""Tests: --verification-id flag and ingest metadata passthrough."""

from __future__ import annotations

import base64
import json
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from assay.cli.main import app
from assay.formatter.formatter import format_packet, format_sdk_packet
from assay.runner.artifacts import ArtifactBundle
from assay.runner.runner import RunResult

cli_runner = CliRunner(env={"NO_COLOR": "1"})

_PASS_BUNDLE = ArtifactBundle(
    outcome="pass",
    url="https://example.com",
    suite="default",
    timestamp="2026-05-08T10:00:00Z",
    error=None,
    screenshot_path=None,
    raw_result={},
)
_PASS_RESULT = RunResult(output_dir="/tmp/out", exit_code=0, stdout="", stderr="")


def test_format_packet_uses_provided_verification_id() -> None:
    packet = format_packet(_PASS_BUNDLE, verification_id="VERIFY-0041-001")
    assert packet["verification_id"] == "VERIFY-0041-001"


def test_format_packet_generates_uuid_when_not_provided() -> None:
    packet = format_packet(_PASS_BUNDLE)
    vid = str(packet["verification_id"])
    assert vid != "VERIFY-0041-001"
    assert len(vid) > 10


def test_format_sdk_packet_uses_provided_verification_id() -> None:
    from assay.ingest.app import IngestPayload, Viewport

    payload = IngestPayload(
        captured_at="2026-05-08T10:00:00Z",
        url="https://example.com",
        viewport=Viewport(width=1280, height=800),
        user_agent="Mozilla/5.0",
        screenshot=base64.b64encode(b"fake").decode(),
    )
    packet = format_sdk_packet(payload, verification_id="VERIFY-0041-002")
    assert packet["verification_id"] == "VERIFY-0041-002"


def test_cli_run_verification_id_flag(tmp_path: Path) -> None:
    db = tmp_path / "store.db"
    cfg_toml = tmp_path / "assay.toml"
    cfg_toml.write_text(f'[store]\ndb = "{db}"\n[output]\ndirectory = "{tmp_path}"\n')

    with patch("assay.cli.main._runner.run", return_value=_PASS_RESULT), \
         patch("assay.cli.main._artifacts.collect_artifacts", return_value=_PASS_BUNDLE):
        result = cli_runner.invoke(app, [
            "--config", str(cfg_toml),
            "run", "--target", "https://example.com",
            "--verification-id", "VERIFY-0041-001",
        ])

    assert result.exit_code == 0
    packets = list((tmp_path).glob("assay-*.json"))
    assert len(packets) == 1
    data = json.loads(packets[0].read_text())
    assert data["verification_id"] == "VERIFY-0041-001"


def test_ingest_metadata_verification_id_passthrough(tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    from assay.ingest.app import app as ingest_app
    from assay.keys.store import create_key

    key_file = str(tmp_path / "keys.json")
    raw_key = create_key(key_file)
    db = tmp_path / "store.db"

    ingest_app.state.key_store = key_file
    ingest_app.state.output_dir = str(tmp_path)
    ingest_app.state.store_db = str(db)

    client = TestClient(ingest_app)
    payload = {
        "captured_at": "2026-05-08T10:00:00Z",
        "url": "https://example.com",
        "viewport": {"width": 1280, "height": 800},
        "user_agent": "Mozilla/5.0",
        "screenshot": base64.b64encode(b"fake-png").decode(),
        "metadata": {"verification_id": "VERIFY-0041-003"},
    }
    resp = client.post("/ingest", json=payload, headers={"X-Assay-Key": raw_key})
    assert resp.status_code == 200

    packets = list(tmp_path.glob("assay-*.json"))
    assert len(packets) == 1
    data = json.loads(packets[0].read_text())
    assert data["verification_id"] == "VERIFY-0041-003"
