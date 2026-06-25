"""Tests: agent-facing CLI surface — --format json, non-interactive init, baseline cmds."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from assay.auth.admin import verify_password
from assay.cli.main import app
from assay.store import db as store

runner = CliRunner(env={"NO_COLOR": "1", "TERM": "dumb"})

_PACKET: dict[str, object] = {
    "verification_id": "VERIFY-0060-001",
    "task_id": "TASK-0060",
    "issue_type": "test_failure",
    "severity": "info",
    "outcome": "pass",
    "summary": "agent cli test",
    "artifact_refs": [],
    "followup_candidates": [],
    "verified_at": "2026-06-25T10:00:00Z",
    "url": "https://example.com/page",
    "raw": "{}",
}


def _cfg(tmp_path: Path) -> Path:
    cfg = tmp_path / "assay.toml"
    cfg.write_text(
        f'[keys]\nstore = "{tmp_path}/keys.json"\n[store]\ndb = "{tmp_path}/store.db"\n'
        f'[schedule]\nstore = "{tmp_path}/sched.json"\n'
    )
    return cfg


# --- non-interactive init ---


def test_init_non_interactive_no_prompt(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(
        app,
        [
            "init",
            "--non-interactive",
            "--name",
            "agentproj",
            "--admin-email",
            "agent@example.com",
            "--admin-password",
            "s3cret",
        ],
    )
    assert result.exit_code == 0, result.output
    assert (tmp_path / "assay.toml").exists()
    assert "ASSAY_ADMIN_PASSWORD_HASH=" in result.output
    assert "agent@example.com" in result.output


def test_init_json_emits_env_block(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(
        app,
        [
            "init",
            "--format",
            "json",
            "--admin-email",
            "agent@example.com",
            "--admin-password",
            "pw123",
        ],
    )
    assert result.exit_code == 0, result.output
    data = json.loads(result.output.strip().splitlines()[-1])
    assert data["env"]["ASSAY_ADMIN_EMAIL"] == "agent@example.com"
    assert verify_password("pw123", data["env"]["ASSAY_ADMIN_PASSWORD_HASH"])


def test_init_non_interactive_requires_email(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["init", "--non-interactive", "--admin-password", "pw"])
    assert result.exit_code == 2
    assert "admin-email" in result.output


def test_init_non_interactive_reads_env(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ASSAY_ADMIN_EMAIL", "env@example.com")
    monkeypatch.setenv("ASSAY_ADMIN_PASSWORD", "envpw")
    result = runner.invoke(app, ["init", "--non-interactive"])
    assert result.exit_code == 0, result.output
    assert "env@example.com" in result.output


# --- key json ---


def test_key_create_json(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    result = runner.invoke(app, ["--config", str(cfg), "key", "create", "--name", "ci", "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output.strip().splitlines()[-1])
    assert data["label"] == "ci"
    assert data["key"]


def test_key_list_json(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    runner.invoke(app, ["--config", str(cfg), "key", "create", "--name", "ci"])
    result = runner.invoke(app, ["--config", str(cfg), "key", "list", "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output.strip().splitlines()[-1])
    assert len(data["keys"]) == 1


# --- schedule json ---


def test_schedule_list_json_empty(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    result = runner.invoke(app, ["--config", str(cfg), "schedule", "list", "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output.strip().splitlines()[-1])
    assert data == {"schedules": []}


# --- check json ---


def test_check_json_no_checks(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    result = runner.invoke(app, ["--config", str(cfg), "check", "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output.strip().splitlines()[-1])
    assert data == {"checks": [], "passed": True}


# --- baseline cmds ---


def test_baseline_list_empty_json(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    store.init_db(tmp_path / "store.db")
    result = runner.invoke(app, ["--config", str(cfg), "baseline", "list", "--format", "json"])
    assert result.exit_code == 0
    assert json.loads(result.output.strip().splitlines()[-1]) == {"baselines": []}


def test_baseline_approve_then_list(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    db = tmp_path / "store.db"
    store.init_db(db)
    store.insert_packet(_PACKET, db)
    result = runner.invoke(
        app, ["--config", str(cfg), "baseline", "approve", "VERIFY-0060-001", "--format", "json"]
    )
    assert result.exit_code == 0
    data = json.loads(result.output.strip().splitlines()[-1])
    assert data["review_status"] == "approved"

    listed = runner.invoke(app, ["--config", str(cfg), "baseline", "list", "--format", "json"])
    parsed = json.loads(listed.output.strip().splitlines()[-1])
    assert parsed["baselines"] == [
        {"url": "https://example.com/page", "verification_id": "VERIFY-0060-001"}
    ]


def test_baseline_reject(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    db = tmp_path / "store.db"
    store.init_db(db)
    store.insert_packet(_PACKET, db)
    result = runner.invoke(
        app, ["--config", str(cfg), "baseline", "reject", "VERIFY-0060-001", "--format", "json"]
    )
    assert result.exit_code == 0
    assert json.loads(result.output.strip().splitlines()[-1])["review_status"] == "rejected"


def test_baseline_set_unknown_exits_1(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    store.init_db(tmp_path / "store.db")
    result = runner.invoke(
        app, ["--config", str(cfg), "baseline", "set", "missing", "--format", "json"]
    )
    assert result.exit_code == 1
    assert "error" in json.loads(result.output.strip().splitlines()[-1])
