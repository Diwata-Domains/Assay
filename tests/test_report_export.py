"""Tests: assay report --export option."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from assay.cli.main import app
from assay.store.db import init_db, insert_packet

cli_runner = CliRunner(env={"NO_COLOR": "1"})

_PACKET_PASS: dict[str, object] = {
    "verification_id": "aaaa-0001",
    "task_id": "TASK-0001",
    "issue_type": "test_result",
    "severity": "low",
    "outcome": "pass",
    "summary": "all good",
    "artifact_refs": [],
    "followup_candidates": [],
    "verified_at": "2026-04-29T10:00:00Z",
    "raw": "{}",
}

_PACKET_FAIL: dict[str, object] = {
    "verification_id": "bbbb-0002",
    "task_id": "TASK-0001",
    "issue_type": "test_result",
    "severity": "high",
    "outcome": "fail",
    "summary": "something broke",
    "artifact_refs": [],
    "followup_candidates": [],
    "verified_at": "2026-04-29T11:00:00Z",
    "raw": "{}",
}


def _setup(tmp_path: Path, packets: list[dict] | None = None) -> tuple[Path, Path]:
    db = tmp_path / "store.db"
    cfg = tmp_path / "assay.toml"
    cfg.write_text(f'[store]\ndb = "{db}"\n[output]\ndirectory = "{tmp_path}"\n')
    init_db(db)
    for p in (packets or []):
        insert_packet(p, db)
    return db, cfg


def test_export_writes_json_file(tmp_path: Path) -> None:
    _, cfg = _setup(tmp_path, [_PACKET_PASS])
    out = tmp_path / "dump.json"

    result = cli_runner.invoke(app, ["--config", str(cfg), "report", "--export", str(out)])

    assert result.exit_code == 0
    assert f"exported: {out}" in result.output
    data = json.loads(out.read_text())
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["outcome"] == "pass"


def test_export_respects_filter(tmp_path: Path) -> None:
    _, cfg = _setup(tmp_path, [_PACKET_PASS, _PACKET_FAIL])
    out = tmp_path / "dump.json"

    result = cli_runner.invoke(
        app, ["--config", str(cfg), "report", "--filter", "outcome=fail", "--export", str(out)]
    )

    assert result.exit_code == 0
    data = json.loads(out.read_text())
    assert len(data) == 1
    assert data[0]["outcome"] == "fail"


def test_export_with_text_format_still_renders_table(tmp_path: Path) -> None:
    _, cfg = _setup(tmp_path, [_PACKET_PASS])
    out = tmp_path / "dump.json"

    result = cli_runner.invoke(app, ["--config", str(cfg), "report", "--format", "text", "--export", str(out)])

    assert result.exit_code == 0
    assert "aaaa-0001" in result.output
    assert out.exists()


def test_export_empty_packets_writes_empty_array(tmp_path: Path) -> None:
    _, cfg = _setup(tmp_path)
    out = tmp_path / "dump.json"

    result = cli_runner.invoke(app, ["--config", str(cfg), "report", "--export", str(out)])

    assert result.exit_code == 0
    data = json.loads(out.read_text())
    assert data == []
