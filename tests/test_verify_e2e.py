"""End-to-end integration tests: Grain-Assay verify loop."""

from __future__ import annotations

import json
import re
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from typer.testing import CliRunner

from assay.cli.main import app
from assay.formatter.formatter import format_packet
from assay.ingest.app import app as ingest_app
from assay.runner.artifacts import ArtifactBundle
from assay.runner.runner import RunResult
from assay.store.db import init_db, insert_packet

cli_runner = CliRunner(env={"NO_COLOR": "1"})

_BUNDLE = ArtifactBundle(
    outcome="pass",
    url="https://example.com",
    suite="default",
    timestamp="2026-05-08T10:00:00Z",
    error=None,
    screenshot_path=None,
    raw_result={},
)
_PASS_RESULT = RunResult(output_dir="/tmp/out", exit_code=0, stdout="", stderr="")

_VALID_ISSUE_TYPES = {"test_failure", "bug_finding", "screenshot_evidence", "trace_capture", "human_annotation"}
_VALID_SEVERITIES = {"info", "warning", "error", "critical"}
_VALID_OUTCOMES = {"pass", "fail", "inconclusive"}
_VERIFY_RE = re.compile(r"^VERIFY-\d{4}-\d{3}$")
_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)


def _validate_grain_payload(payload: dict, expected_verification_id: str) -> list[str]:
    """Reimplementation of grain's _validate_ingest_payload for test isolation."""
    errors: list[str] = []
    required = ("verification_id", "task_id", "issue_type", "severity", "outcome", "summary")
    for field in required:
        value = payload.get(field)
        if not isinstance(value, str) or not str(value).strip():
            errors.append(f"missing required field: {field}")
    if payload.get("verification_id") != expected_verification_id:
        errors.append(f"verification_id mismatch: {payload.get('verification_id')} != {expected_verification_id}")
    if payload.get("issue_type") not in _VALID_ISSUE_TYPES:
        errors.append(f"invalid issue_type: {payload.get('issue_type')}")
    if payload.get("severity") not in _VALID_SEVERITIES:
        errors.append(f"invalid severity: {payload.get('severity')}")
    if payload.get("outcome") not in _VALID_OUTCOMES:
        errors.append(f"invalid outcome: {payload.get('outcome')}")
    return errors


def test_packet_with_verify_id_passes_grain_validation() -> None:
    packet = format_packet(_BUNDLE, task_id="TASK-0041", verification_id="VERIFY-0041-001")
    errors = _validate_grain_payload(packet, "VERIFY-0041-001")
    assert errors == [], f"grain validation errors: {errors}"


def test_packet_without_verify_id_fails_verify_format_check() -> None:
    packet = format_packet(_BUNDLE, task_id="TASK-0041")
    vid = str(packet["verification_id"])
    assert _UUID_RE.match(vid), "expected UUID"
    assert not _VERIFY_RE.match(vid), "UUID should not match VERIFY format"
    errors = _validate_grain_payload(packet, "VERIFY-0041-001")
    assert any("mismatch" in e for e in errors)


def test_submit_delivers_verify_id_to_grain_output(tmp_path: Path) -> None:
    grain_out = tmp_path / "grain-out"
    grain_out.mkdir()
    cfg = tmp_path / "assay.toml"
    cfg.write_text(
        f'[grain]\noutput_path = "{grain_out}"\n'
        f'[store]\ndb = "{tmp_path}/store.db"\n'
        f'[output]\ndirectory = "{tmp_path}"\n'
    )

    packet = format_packet(_BUNDLE, task_id="TASK-0041", verification_id="VERIFY-0041-001")
    pkt_path = tmp_path / "assay-e2e-test.json"
    pkt_path.write_text(json.dumps(packet))

    result = cli_runner.invoke(app, ["--config", str(cfg), "submit", "--packet", str(pkt_path)])

    assert result.exit_code == 0
    submitted = grain_out / pkt_path.name
    assert submitted.exists()
    data = json.loads(submitted.read_text())
    assert data["verification_id"] == "VERIFY-0041-001"
    assert "warning" not in result.output.lower()


def test_status_endpoint_reflects_verify_id(tmp_path: Path) -> None:
    db = tmp_path / "store.db"
    init_db(db)

    packet = format_packet(_BUNDLE, task_id="TASK-0041", verification_id="VERIFY-0041-001")
    insert_packet(packet, db)

    ingest_app.state.key_store = str(tmp_path / "keys.json")
    ingest_app.state.output_dir = str(tmp_path)
    ingest_app.state.store_db = str(db)
    client = TestClient(ingest_app)

    resp = client.get("/status/VERIFY-0041-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "complete"
    assert data["outcome"] == "pass"
    assert data["verification_id"] == "VERIFY-0041-001"


def test_full_run_to_status_via_cli(tmp_path: Path) -> None:
    db = tmp_path / "store.db"
    cfg = tmp_path / "assay.toml"
    cfg.write_text(f'[store]\ndb = "{db}"\n[output]\ndirectory = "{tmp_path}"\n')

    with patch("assay.cli.main._runner.run", return_value=_PASS_RESULT), \
         patch("assay.cli.main._artifacts.collect_artifacts", return_value=_BUNDLE):
        result = cli_runner.invoke(app, [
            "--config", str(cfg),
            "run", "--target", "https://example.com",
            "--task-id", "TASK-0041",
            "--verification-id", "VERIFY-0041-001",
        ])

    assert result.exit_code == 0

    ingest_app.state.store_db = str(db)
    ingest_app.state.output_dir = str(tmp_path)
    ingest_app.state.key_store = str(tmp_path / "keys.json")
    client = TestClient(ingest_app)

    resp = client.get("/status/VERIFY-0041-001")
    assert resp.status_code == 200
    assert resp.json()["outcome"] == "pass"
