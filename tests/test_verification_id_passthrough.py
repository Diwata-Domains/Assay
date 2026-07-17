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


def test_format_packet_generates_canonical_id_when_not_provided() -> None:
    import re

    packet = format_packet(_PASS_BUNDLE)
    vid = str(packet["verification_id"])
    assert re.match(r"^VERIFY-\d+-\d+$", vid), f"not a canonical VERIFY id: {vid}"


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


def _ingest_client(tmp_path: Path) -> tuple[object, str, Path]:
    from fastapi.testclient import TestClient

    from assay.ingest.app import app as ingest_app
    from assay.keys.store import create_key

    key_file = str(tmp_path / "keys.json")
    raw_key = create_key(key_file)
    db = tmp_path / "store.db"
    ingest_app.state.key_store = key_file
    ingest_app.state.output_dir = str(tmp_path)
    ingest_app.state.store_db = str(db)
    return TestClient(ingest_app), raw_key, db


def _ingest_body() -> dict[str, object]:
    return {
        "captured_at": "2026-05-08T10:00:00Z",
        "url": "https://example.com",
        "viewport": {"width": 1280, "height": 800},
        "user_agent": "Mozilla/5.0",
        "screenshot": base64.b64encode(b"fake-png").decode(),
    }


def test_ingest_carries_source_ticket_id_field(tmp_path: Path) -> None:
    from assay.store.db import get_packet

    client, raw_key, db = _ingest_client(tmp_path)
    payload = {**_ingest_body(), "source_ticket_id": "ASSAY-7"}
    resp = client.post("/ingest", json=payload, headers={"X-Assay-Key": raw_key})
    assert resp.status_code == 200

    data = json.loads(next(tmp_path.glob("assay-*.json")).read_text())
    assert data["source_ticket_id"] == "ASSAY-7"

    vid = data["verification_id"]
    stored = get_packet(vid, db)
    assert stored is not None
    assert stored["source_ticket_id"] == "ASSAY-7"


def test_ingest_source_ticket_id_from_metadata_fallback(tmp_path: Path) -> None:
    client, raw_key, db = _ingest_client(tmp_path)
    payload = {**_ingest_body(), "metadata": {"source_ticket_id": "ASSAY-9"}}
    resp = client.post("/ingest", json=payload, headers={"X-Assay-Key": raw_key})
    assert resp.status_code == 200

    data = json.loads(next(tmp_path.glob("assay-*.json")).read_text())
    assert data["source_ticket_id"] == "ASSAY-9"


def test_ingest_generates_canonical_verify_id_not_uuid(tmp_path: Path) -> None:
    import re

    client, raw_key, db = _ingest_client(tmp_path)
    resp = client.post("/ingest", json=_ingest_body(), headers={"X-Assay-Key": raw_key})
    assert resp.status_code == 200

    data = json.loads(next(tmp_path.glob("assay-*.json")).read_text())
    vid = str(data["verification_id"])
    assert re.match(r"^VERIFY-\d+-\d+$", vid), f"not a canonical VERIFY id: {vid}"


def test_legacy_uuid_packet_reads_without_error(tmp_path: Path) -> None:
    # Backward-compat: historical packets minted with a uuid4 verification_id must still read
    # back cleanly (no 500 / no exception) even though new packets require VERIFY-####-NNN.
    from assay.store.db import get_packet, init_db, insert_packet

    db = tmp_path / "store.db"
    init_db(db)
    legacy = {
        "verification_id": "a1b2c3d4-1111-2222-3333-444444444444",
        "task_id": "TASK-0001",
        "issue_type": "test_failure",
        "severity": "error",
        "outcome": "fail",
        "summary": "legacy finding",
        "artifact_refs": [],
        "followup_candidates": [],
        "verified_at": "2026-01-01T00:00:00Z",
    }
    insert_packet(legacy, db)
    stored = get_packet("a1b2c3d4-1111-2222-3333-444444444444", db)
    assert stored is not None
    assert stored["verification_id"] == "a1b2c3d4-1111-2222-3333-444444444444"
