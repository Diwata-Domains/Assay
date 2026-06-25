"""Tests for /checks dashboard route and assay report --checks flag."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from assay.ingest.app import app as ingest_app
from assay.store.db import init_db, insert_check_result

_SECRET = "x" * 32
_EMAIL = "admin@test.com"


def _setup_app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    from assay._vendor.warden import WardenConfig, issue_token
    from assay.auth.admin import hash_password

    monkeypatch.setenv("ASSAY_ADMIN_EMAIL", _EMAIL)
    monkeypatch.setenv("ASSAY_ADMIN_PASSWORD_HASH", hash_password("pw"))
    monkeypatch.setenv("WARDEN_SECRET", _SECRET)
    db = tmp_path / "store.db"
    init_db(db)
    ingest_app.state.store_db = str(db)
    ingest_app.state.key_store = str(tmp_path / "keys.json")
    ingest_app.state.output_dir = str(tmp_path)
    client = TestClient(ingest_app, follow_redirects=False)
    client.cookies.set("warden_session", issue_token(_EMAIL, WardenConfig(secret=_SECRET)))
    return client


def _insert(db: Path, **kw: object) -> None:
    insert_check_result(
        {
            "check_id": kw.get("check_id", "ping"),
            "check_type": kw.get("check_type", "http"),
            "target": kw.get("target", "https://example.com"),
            "passed": kw.get("passed", True),
            "assertions": kw.get("assertions", []),
            "error": kw.get("error", None),
            "checked_at": kw.get("checked_at", "2026-06-13T00:00:00"),
        },
        db,
    )


# ---------------------------------------------------------------------------
# /checks dashboard
# ---------------------------------------------------------------------------


def test_checks_route_empty(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _setup_app(tmp_path, monkeypatch)
    resp = client.get("/checks")
    assert resp.status_code == 200
    assert "no checks run yet" in resp.text


def test_checks_route_shows_result(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _setup_app(tmp_path, monkeypatch)
    db = tmp_path / "store.db"
    _insert(db, check_id="homepage", check_type="http", passed=True)
    resp = client.get("/checks")
    assert resp.status_code == 200
    assert "homepage" in resp.text
    assert "PASS" in resp.text


def test_checks_route_shows_fail(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _setup_app(tmp_path, monkeypatch)
    db = tmp_path / "store.db"
    _insert(
        db,
        check_id="api-health",
        check_type="http",
        passed=False,
        assertions=[{"name": "status_code", "passed": False, "expected": "200", "actual": "503"}],
    )
    resp = client.get("/checks")
    assert resp.status_code == 200
    assert "FAIL" in resp.text
    assert "status_code" in resp.text
    assert "503" in resp.text


def test_checks_route_in_nav(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _setup_app(tmp_path, monkeypatch)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "/checks" in resp.text


def test_checks_route_protected_without_auth(tmp_path: Path) -> None:
    db = tmp_path / "store.db"
    init_db(db)
    ingest_app.state.store_db = str(db)
    c = TestClient(ingest_app, follow_redirects=False)
    resp = c.get("/checks")
    assert resp.status_code == 303
    assert resp.headers["location"] == "/login"


# ---------------------------------------------------------------------------
# assay report --checks (CLI)
# ---------------------------------------------------------------------------


def _make_config(tmp_path: Path) -> Path:
    db = tmp_path / "store.db"
    init_db(db)
    cfg = tmp_path / "assay.toml"
    cfg.write_text(
        f"""
[project]
name = "test"
[output]
directory = "{tmp_path}"
[store]
db = "{db}"
[keys]
store = "{tmp_path}/keys.json"
[schedule]
store = "{tmp_path}/schedules.json"
""",
        encoding="utf-8",
    )
    return cfg


def test_report_checks_flag_no_results(tmp_path: Path) -> None:
    from typer.testing import CliRunner

    from assay.cli.main import app as cli_app

    cfg = _make_config(tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli_app, ["--config", str(cfg), "report", "--checks"])
    assert result.exit_code == 0
    assert "no check results found" in result.output


def test_report_checks_flag_shows_results(tmp_path: Path) -> None:
    from typer.testing import CliRunner

    from assay.cli.main import app as cli_app

    cfg = _make_config(tmp_path)
    db = tmp_path / "store.db"
    _insert(db, check_id="ping", check_type="http", passed=True)

    runner = CliRunner()
    result = runner.invoke(cli_app, ["--config", str(cfg), "report", "--checks"])
    assert result.exit_code == 0
    assert "ping" in result.output
    assert "PASS" in result.output


def test_report_checks_json_includes_checks_key(tmp_path: Path) -> None:
    from typer.testing import CliRunner

    from assay.cli.main import app as cli_app

    cfg = _make_config(tmp_path)
    db = tmp_path / "store.db"
    _insert(db, check_id="api", check_type="auth", passed=False)

    runner = CliRunner()
    result = runner.invoke(cli_app, ["--config", str(cfg), "report", "--format", "json", "--checks"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "packets" in data
    assert "checks" in data
    assert data["checks"][0]["check_id"] == "api"


def test_report_json_without_checks_is_array(tmp_path: Path) -> None:
    from typer.testing import CliRunner

    from assay.cli.main import app as cli_app

    cfg = _make_config(tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli_app, ["--config", str(cfg), "report", "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
