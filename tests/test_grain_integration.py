"""Tests for Phase 12: Grain task tagging, auto-detection, submit, SDK taskId."""

from __future__ import annotations

import base64
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from assay.cli.main import app as cli_app
from assay.grain.detect import detect_task_id
from assay.ingest.app import app as ingest_app
from assay.keys.store import create_key

_PNG = base64.b64encode(b"PNG").decode()
_SDK_PAYLOAD = {
    "captured_at": "2026-04-21T10:00:00Z",
    "url": "https://example.com",
    "viewport": {"width": 1280, "height": 720},
    "user_agent": "Mozilla/5.0",
    "screenshot": _PNG,
    "metadata": {},
}

runner = CliRunner(env={"NO_COLOR": "1"})


# ---------------------------------------------------------------------------
# P12-T02: Grain auto-detection
# ---------------------------------------------------------------------------


def test_detect_task_id_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GRAIN_TASK_ID", "TASK-0099")
    assert detect_task_id() == "TASK-0099"


def test_detect_task_id_env_takes_precedence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GRAIN_TASK_ID", "TASK-0099")
    task_file = tmp_path / "docs/working/current_task.md"
    task_file.parent.mkdir(parents=True)
    task_file.write_text("# Current Task\nTask: TASK-0001")
    assert detect_task_id(str(tmp_path)) == "TASK-0099"


def test_detect_task_id_from_current_task_md(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GRAIN_TASK_ID", raising=False)
    task_file = tmp_path / "docs/working/current_task.md"
    task_file.parent.mkdir(parents=True)
    task_file.write_text("# Current Task\nTask: TASK-0070")
    assert detect_task_id(str(tmp_path)) == "TASK-0070"


def test_detect_task_id_no_file_returns_none(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GRAIN_TASK_ID", raising=False)
    assert detect_task_id(str(tmp_path)) is None


def test_detect_task_id_file_no_match_returns_none(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GRAIN_TASK_ID", raising=False)
    task_file = tmp_path / "docs/working/current_task.md"
    task_file.parent.mkdir(parents=True)
    task_file.write_text("# Current Task\nStatus: unset")
    assert detect_task_id(str(tmp_path)) is None


# ---------------------------------------------------------------------------
# P12-T01: assay run --task-id populates packet
# ---------------------------------------------------------------------------


def _make_runner_result(tmp_path: Path) -> MagicMock:
    (tmp_path / "result.json").write_text(json.dumps({
        "outcome": "pass", "url": "https://example.com",
        "suite": "default", "timestamp": "2026-04-21T10:00:00Z",
    }))
    mock = MagicMock()
    mock.exit_code = 0
    mock.stdout = ""
    mock.stderr = ""
    mock.output_dir = str(tmp_path)
    return mock


def test_run_task_id_flag_populates_packet(tmp_path: Path) -> None:
    mock_result = _make_runner_result(tmp_path)
    with patch("assay.runner.runner.run", return_value=mock_result):
        result = runner.invoke(cli_app, [
            "run", "--target", "https://example.com",
            "--output", str(tmp_path), "--task-id", "TASK-0070",
        ])
    assert result.exit_code == 0
    packet = json.loads(next(tmp_path.glob("assay-*.json")).read_text())
    assert packet["task_id"] == "TASK-0070"


def test_run_auto_detects_task_id(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GRAIN_TASK_ID", "TASK-0055")
    mock_result = _make_runner_result(tmp_path)
    with patch("assay.runner.runner.run", return_value=mock_result):
        result = runner.invoke(cli_app, [
            "run", "--target", "https://example.com", "--output", str(tmp_path),
        ])
    assert result.exit_code == 0
    packet = json.loads(next(tmp_path.glob("assay-*.json")).read_text())
    assert packet["task_id"] == "TASK-0055"


def test_run_no_task_id_packet_has_none(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GRAIN_TASK_ID", raising=False)
    mock_result = _make_runner_result(tmp_path)
    with patch("assay.runner.runner.run", return_value=mock_result):
        result = runner.invoke(cli_app, [
            "run", "--target", "https://example.com", "--output", str(tmp_path),
        ])
    assert result.exit_code == 0
    packet = json.loads(next(tmp_path.glob("assay-*.json")).read_text())
    assert packet["task_id"] is None


# ---------------------------------------------------------------------------
# P12-T03: assay submit
# ---------------------------------------------------------------------------


def _write_valid_packet(directory: Path, vid: str = "aabbccdd-0000-0000-0000-000000000001") -> Path:
    packet = {
        "verification_id": vid,
        "task_id": "TASK-0070",
        "issue_type": "test_failure",
        "severity": "info",
        "outcome": "pass",
        "summary": "pass: https://example.com",
        "artifact_refs": [],
        "followup_candidates": [],
        "verified_at": "2026-04-21T10:00:00Z",
    }
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"assay-20260421T100000Z-{vid}.json"
    path.write_text(json.dumps(packet))
    return path


def test_submit_copies_packet_to_grain_output(tmp_path: Path) -> None:
    src_dir = tmp_path / "src"
    packet_path = _write_valid_packet(src_dir)
    result = runner.invoke(cli_app, [
        "--config", "/dev/null",
        "submit", "--packet", str(packet_path),
    ], catch_exceptions=False)
    # No [grain] config → should error
    assert result.exit_code == 1
    assert "output_path" in result.output


def test_submit_with_grain_output_path(tmp_path: Path) -> None:
    src_dir = tmp_path / "src"
    grain_dir = tmp_path / "grain-out"
    packet_path = _write_valid_packet(src_dir)

    config_file = tmp_path / "assay.toml"
    config_file.write_text(f'[grain]\noutput_path = "{grain_dir}"\n')

    result = runner.invoke(cli_app, [
        "--config", str(config_file),
        "submit", "--packet", str(packet_path),
    ])
    assert result.exit_code == 0
    assert (grain_dir / packet_path.name).exists()


def test_submit_invalid_packet_fails(tmp_path: Path) -> None:
    src_dir = tmp_path / "src"
    grain_dir = tmp_path / "grain-out"
    src_dir.mkdir()
    bad_packet = src_dir / "assay-bad.json"
    bad_packet.write_text(json.dumps({"not": "a valid packet"}))

    config_file = tmp_path / "assay.toml"
    config_file.write_text(f'[grain]\noutput_path = "{grain_dir}"\n')

    result = runner.invoke(cli_app, [
        "--config", str(config_file),
        "submit", "--packet", str(bad_packet),
    ])
    assert result.exit_code == 1
    assert "schema invalid" in result.output


# ---------------------------------------------------------------------------
# P12-T04: assay run --submit
# ---------------------------------------------------------------------------


def test_run_submit_flag_copies_to_grain(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GRAIN_TASK_ID", raising=False)
    out_dir = tmp_path / "out"
    grain_dir = tmp_path / "grain"
    config_file = tmp_path / "assay.toml"
    config_file.write_text(f'[grain]\noutput_path = "{grain_dir}"\n')

    out_dir.mkdir(parents=True, exist_ok=True)
    mock_result = _make_runner_result(out_dir)

    with patch("assay.runner.runner.run", return_value=mock_result):
        result = runner.invoke(cli_app, [
            "--config", str(config_file),
            "run", "--target", "https://example.com",
            "--output", str(out_dir), "--submit",
        ])
    assert result.exit_code == 0
    assert list(grain_dir.glob("assay-*.json")), "packet not copied to grain output"


# ---------------------------------------------------------------------------
# P12-T05: SDK taskId passthrough
# ---------------------------------------------------------------------------


@pytest.fixture()
def ingest_client(tmp_path: Path) -> tuple[TestClient, str, str]:
    store = str(tmp_path / "keys.json")
    output = str(tmp_path / "out")
    ingest_app.state.key_store = store
    ingest_app.state.output_dir = output
    return TestClient(ingest_app), store, output


def test_sdk_task_id_passthrough(ingest_client: tuple[TestClient, str, str]) -> None:
    c, store, output = ingest_client
    key = create_key(store)
    payload = {**_SDK_PAYLOAD, "task_id": "TASK-0070"}
    c.post("/ingest", json=payload, headers={"X-Assay-Key": key})
    packet = json.loads(next(Path(output).glob("assay-*.json")).read_text())
    assert packet["task_id"] == "TASK-0070"


def test_sdk_no_task_id_defaults_to_none(ingest_client: tuple[TestClient, str, str]) -> None:
    c, store, output = ingest_client
    key = create_key(store)
    c.post("/ingest", json=_SDK_PAYLOAD, headers={"X-Assay-Key": key})
    packet = json.loads(next(Path(output).glob("assay-*.json")).read_text())
    assert packet["task_id"] is None
