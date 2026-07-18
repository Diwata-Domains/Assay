"""Tests: `assay ticket confirm` / `assay ticket list` — the CP-006 operator seam."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from assay.cli.main import app
from assay.store.db import advance_ticket, get_ticket, init_db, insert_ticket

cli_runner = CliRunner(env={"NO_COLOR": "1"})


def _make_cfg(tmp_path: Path) -> tuple[Path, Path]:
    db = tmp_path / "store.db"
    cfg = tmp_path / "assay.toml"
    cfg.write_text(f'[store]\ndb = "{db}"\n[output]\ndirectory = "{tmp_path}"\n')
    return db, cfg


def _ticket_in_review(db: Path) -> str:
    init_db(db)
    tid = insert_ticket("a finding", "error", db_path=db)
    for state in ("todo", "in_progress", "in_review"):
        advance_ticket(tid, state, db_path=db)
    return tid


def _state(db: Path, tid: str) -> object:
    ticket = get_ticket(tid, db)
    assert ticket is not None
    return ticket["state"]


def test_confirm_moves_in_review_to_done(tmp_path: Path) -> None:
    db, cfg = _make_cfg(tmp_path)
    tid = _ticket_in_review(db)
    result = cli_runner.invoke(app, ["--config", str(cfg), "ticket", "confirm", tid])
    assert result.exit_code == 0
    assert f"{tid}: confirmed done" in result.output
    assert _state(db, tid) == "done"


def test_confirm_unknown_ticket_exits_1(tmp_path: Path) -> None:
    _, cfg = _make_cfg(tmp_path)
    result = cli_runner.invoke(app, ["--config", str(cfg), "ticket", "confirm", "ASSAY-999"])
    assert result.exit_code == 1
    assert "not found" in result.output


def test_confirm_triage_ticket_is_rejected(tmp_path: Path) -> None:
    db, cfg = _make_cfg(tmp_path)
    init_db(db)
    tid = insert_ticket("fresh", "error", db_path=db)  # stays in triage
    result = cli_runner.invoke(app, ["--config", str(cfg), "ticket", "confirm", tid])
    assert result.exit_code == 1
    assert "illegal transition" in result.output
    assert _state(db, tid) == "triage"


def test_list_filters_by_state(tmp_path: Path) -> None:
    db, cfg = _make_cfg(tmp_path)
    reviewed = _ticket_in_review(db)
    fresh = insert_ticket("fresh one", "warning", db_path=db)  # triage
    result = cli_runner.invoke(app, ["--config", str(cfg), "ticket", "list", "--state", "in_review"])
    assert result.exit_code == 0
    assert reviewed in result.output
    assert fresh not in result.output


def test_list_empty_reports_none(tmp_path: Path) -> None:
    _, cfg = _make_cfg(tmp_path)
    result = cli_runner.invoke(app, ["--config", str(cfg), "ticket", "list"])
    assert result.exit_code == 0
    assert "(no tickets)" in result.output
