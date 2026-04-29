"""Integration tests: packets written to SQLite on assay run and /ingest."""

from __future__ import annotations

import base64
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from assay.cli.main import app
from assay.runner.artifacts import ArtifactBundle
from assay.runner.runner import RunResult
from assay.store.db import list_packets

cli_runner = CliRunner(env={"NO_COLOR": "1"})

_PASS_BUNDLE = ArtifactBundle(
    outcome="pass",
    url="https://example.com",
    suite="default",
    timestamp="2026-04-29T10:00:00Z",
    error=None,
    screenshot_path=None,
    raw_result={},
)
_PASS_RESULT = RunResult(output_dir="/tmp/out", exit_code=0, stdout="", stderr="")


def test_run_writes_to_sqlite(tmp_path: Path) -> None:
    db = tmp_path / "store.db"
    cfg_toml = tmp_path / "assay.toml"
    cfg_toml.write_text(f'[store]\ndb = "{db}"\n[output]\ndirectory = "{tmp_path}"\n')

    with patch("assay.cli.main._runner.run", return_value=_PASS_RESULT), \
         patch("assay.cli.main._artifacts.collect_artifacts", return_value=_PASS_BUNDLE):
        result = cli_runner.invoke(app, ["--config", str(cfg_toml), "run", "--target", "https://example.com"])

    assert result.exit_code == 0
    rows = list_packets(db)
    assert len(rows) == 1
    assert rows[0]["outcome"] == "pass"


def test_run_sqlite_failure_does_not_abort(tmp_path: Path) -> None:
    db = tmp_path / "store.db"
    cfg_toml = tmp_path / "assay.toml"
    cfg_toml.write_text(f'[store]\ndb = "{db}"\n[output]\ndirectory = "{tmp_path}"\n')

    with patch("assay.cli.main._runner.run", return_value=_PASS_RESULT), \
         patch("assay.cli.main._artifacts.collect_artifacts", return_value=_PASS_BUNDLE), \
         patch("assay.store.db.insert_packet", side_effect=Exception("db exploded")):
        result = cli_runner.invoke(app, ["--config", str(cfg_toml), "run", "--target", "https://example.com"])

    assert result.exit_code == 0


def test_ingest_writes_to_sqlite(tmp_path: Path) -> None:
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
        "captured_at": "2026-04-29T10:00:00Z",
        "url": "https://example.com",
        "viewport": {"width": 1280, "height": 800},
        "user_agent": "Mozilla/5.0",
        "screenshot": base64.b64encode(b"fake-png").decode(),
    }
    resp = client.post("/ingest", json=payload, headers={"X-Assay-Key": raw_key})
    assert resp.status_code == 200

    rows = list_packets(db)
    assert len(rows) == 1
    assert rows[0]["issue_type"] == "screenshot_evidence"


def test_ingest_sqlite_failure_does_not_abort(tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    from assay.ingest.app import app as ingest_app
    from assay.keys.store import create_key

    key_file = str(tmp_path / "keys.json")
    raw_key = create_key(key_file)

    ingest_app.state.key_store = key_file
    ingest_app.state.output_dir = str(tmp_path)
    ingest_app.state.store_db = str(tmp_path / "store.db")

    payload = {
        "captured_at": "2026-04-29T10:00:00Z",
        "url": "https://example.com",
        "viewport": {"width": 1280, "height": 800},
        "user_agent": "Mozilla/5.0",
        "screenshot": base64.b64encode(b"fake").decode(),
    }

    with patch("assay.store.db.insert_packet", side_effect=Exception("db error")):
        from fastapi.testclient import TestClient
        client = TestClient(ingest_app)
        resp = client.post("/ingest", json=payload, headers={"X-Assay-Key": raw_key})

    assert resp.status_code == 200
