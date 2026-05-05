"""Tests: assay store import --dir subcommand."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from assay.cli.main import app
from assay.store.db import list_packets

cli_runner = CliRunner(env={"NO_COLOR": "1"})

_PACKET: dict[str, object] = {
    "verification_id": "cccc-0003",
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


def _write_json(directory: Path, packet: dict, filename: str = "assay-20260429-cccc.json") -> None:
    (directory / filename).write_text(json.dumps(packet))


def _make_cfg(tmp_path: Path) -> tuple[Path, Path]:
    db = tmp_path / "store.db"
    cfg = tmp_path / "assay.toml"
    cfg.write_text(f'[store]\ndb = "{db}"\n[output]\ndirectory = "{tmp_path}"\n')
    return db, cfg


def test_import_writes_packets_to_sqlite(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    _write_json(src, _PACKET)
    db, cfg = _make_cfg(tmp_path)

    result = cli_runner.invoke(app, ["--config", str(cfg), "store", "import", "--dir", str(src)])

    assert result.exit_code == 0
    assert "imported: 1 packet(s)" in result.output
    rows = list_packets(db)
    assert len(rows) == 1
    assert rows[0]["outcome"] == "pass"


def test_import_skips_malformed_json(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "assay-bad.json").write_text("{not valid json")
    db, cfg = _make_cfg(tmp_path)

    result = cli_runner.invoke(app, ["--config", str(cfg), "store", "import", "--dir", str(src)])

    assert result.exit_code == 0
    assert "warning:" in result.output
    assert "imported: 0 packet(s)" in result.output


def test_import_duplicate_does_not_error(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    _write_json(src, _PACKET)
    db, cfg = _make_cfg(tmp_path)

    cli_runner.invoke(app, ["--config", str(cfg), "store", "import", "--dir", str(src)])
    result = cli_runner.invoke(app, ["--config", str(cfg), "store", "import", "--dir", str(src)])

    assert result.exit_code == 0
    assert "imported: 1 packet(s)" in result.output
    assert len(list_packets(db)) == 1


def test_import_empty_dir_reports_zero(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    _, cfg = _make_cfg(tmp_path)

    result = cli_runner.invoke(app, ["--config", str(cfg), "store", "import", "--dir", str(src)])

    assert result.exit_code == 0
    assert "imported: 0 packet(s)" in result.output


def test_import_missing_dir_exits_1(tmp_path: Path) -> None:
    _, cfg = _make_cfg(tmp_path)

    result = cli_runner.invoke(app, ["--config", str(cfg), "store", "import", "--dir", str(tmp_path / "nope")])

    assert result.exit_code == 1
