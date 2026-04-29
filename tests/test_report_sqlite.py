"""Tests: assay report reads from SQLite store."""

from __future__ import annotations

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


def _make_cfg(tmp_path: Path) -> tuple[Path, Path]:
    db = tmp_path / "store.db"
    cfg = tmp_path / "assay.toml"
    cfg.write_text(f'[store]\ndb = "{db}"\n[output]\ndirectory = "{tmp_path}"\n')
    return db, cfg


def test_report_reads_from_sqlite(tmp_path: Path) -> None:
    db, cfg = _make_cfg(tmp_path)
    init_db(db)
    insert_packet(_PACKET_PASS, db)

    result = cli_runner.invoke(app, ["--config", str(cfg), "report"])

    assert result.exit_code == 0
    assert "aaaa-0001" in result.output
    assert "pass" in result.output


def test_report_empty_db_no_error(tmp_path: Path) -> None:
    db, cfg = _make_cfg(tmp_path)

    result = cli_runner.invoke(app, ["--config", str(cfg), "report"])

    assert result.exit_code == 0
    assert "no packets found" in result.output


def test_report_missing_db_no_error(tmp_path: Path) -> None:
    cfg = tmp_path / "assay.toml"
    cfg.write_text(f'[store]\ndb = "{tmp_path}/nonexistent.db"\n[output]\ndirectory = "{tmp_path}"\n')

    result = cli_runner.invoke(app, ["--config", str(cfg), "report"])

    assert result.exit_code == 0
    assert "no packets found" in result.output


def test_report_filter_outcome(tmp_path: Path) -> None:
    db, cfg = _make_cfg(tmp_path)
    init_db(db)
    insert_packet(_PACKET_PASS, db)
    insert_packet(_PACKET_FAIL, db)

    result = cli_runner.invoke(app, ["--config", str(cfg), "report", "--filter", "outcome=fail"])

    assert result.exit_code == 0
    assert "bbbb-0002" in result.output
    assert "aaaa-0001" not in result.output


def test_report_format_json(tmp_path: Path) -> None:
    import json

    db, cfg = _make_cfg(tmp_path)
    init_db(db)
    insert_packet(_PACKET_PASS, db)

    result = cli_runner.invoke(app, ["--config", str(cfg), "report", "--format", "json"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["outcome"] == "pass"


def test_report_format_html(tmp_path: Path) -> None:
    db, cfg = _make_cfg(tmp_path)
    init_db(db)
    insert_packet(_PACKET_PASS, db)

    result = cli_runner.invoke(app, ["--config", str(cfg), "report", "--format", "html"])

    assert result.exit_code == 0
    assert "report:" in result.output
    report_path = result.output.strip().split("report: ")[-1]
    assert Path(report_path).exists()
    assert "aaaa-0001" in Path(report_path).read_text()
