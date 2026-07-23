"""`assay store migrate` runs both the ticket and default-project backfills."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from assay.cli.main import app as cli_app
from assay.store.db import (
    UNASSIGNED_PROJECT_ID,
    get_packet,
    init_db,
    insert_packet,
)

cli_runner = CliRunner(env={"NO_COLOR": "1"})


def _make_cfg(tmp_path: Path) -> Path:
    db = tmp_path / "store.db"
    cfg = tmp_path / "assay.toml"
    cfg.write_text(f'[store]\ndb = "{db}"\n')
    return cfg


def test_store_migrate_backfills_default_project(tmp_path: Path) -> None:
    db = tmp_path / "store.db"
    init_db(db)
    insert_packet(
        {
            "verification_id": "VERIFY-9",
            "issue_type": "bug_finding",
            "severity": "info",
            "outcome": "fail",
            "summary": "orphan",
        },
        db,
    )
    cfg = _make_cfg(tmp_path)

    result = cli_runner.invoke(cli_app, ["--config", str(cfg), "store", "migrate"])

    assert result.exit_code == 0
    packet = get_packet("VERIFY-9", db)
    assert packet is not None
    assert packet["project_id"] == UNASSIGNED_PROJECT_ID
