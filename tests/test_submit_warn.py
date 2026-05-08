"""Tests: assay submit warns when verification_id is UUID-shaped."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from assay.cli.main import app

cli_runner = CliRunner(env={"NO_COLOR": "1"})

_BASE_PACKET: dict[str, object] = {
    "verification_id": "00000000-0000-0000-0000-000000000000",
    "task_id": "TASK-0001",
    "issue_type": "test_failure",
    "severity": "info",
    "outcome": "pass",
    "summary": "ok",
    "artifact_refs": [],
    "followup_candidates": [],
    "verified_at": "2026-05-08T10:00:00Z",
}


def _write_packet(directory: Path, overrides: dict | None = None) -> Path:
    data = {**_BASE_PACKET, **(overrides or {})}
    path = directory / "assay-20260508-test.json"
    path.write_text(json.dumps(data))
    return path


def _make_cfg(tmp_path: Path) -> Path:
    grain_out = tmp_path / "grain-out"
    grain_out.mkdir()
    cfg = tmp_path / "assay.toml"
    cfg.write_text(f'[grain]\noutput_path = "{grain_out}"\n[store]\ndb = "{tmp_path}/store.db"\n')
    return cfg


def test_submit_warns_for_uuid_verification_id(tmp_path: Path) -> None:
    cfg = _make_cfg(tmp_path)
    pkt = _write_packet(tmp_path, {"verification_id": "a1b2c3d4-0000-0000-0000-000000000000"})

    result = cli_runner.invoke(app, ["--config", str(cfg), "submit", "--packet", str(pkt)])

    assert result.exit_code == 0
    assert "warning" in result.output.lower()
    assert "uuid" in result.output.lower()


def test_submit_no_warning_for_verify_id(tmp_path: Path) -> None:
    cfg = _make_cfg(tmp_path)
    pkt = _write_packet(tmp_path, {"verification_id": "VERIFY-0041-001"})

    result = cli_runner.invoke(app, ["--config", str(cfg), "submit", "--packet", str(pkt)])

    assert result.exit_code == 0
    assert "warning: verification_id" not in result.output.lower()


def test_submit_still_succeeds_with_uuid(tmp_path: Path) -> None:
    cfg = _make_cfg(tmp_path)
    pkt = _write_packet(tmp_path, {"verification_id": "a1b2c3d4-1111-2222-3333-444444444444"})
    grain_out = tmp_path / "grain-out"

    result = cli_runner.invoke(app, ["--config", str(cfg), "submit", "--packet", str(pkt)])

    assert result.exit_code == 0
    assert (grain_out / pkt.name).exists()
