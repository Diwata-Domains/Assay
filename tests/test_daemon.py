"""Tests for Phase 13: background scheduler daemon start/stop/status."""

from __future__ import annotations

import os
import signal
from pathlib import Path

import pytest
from typer.testing import CliRunner

from assay.cli.main import app
from assay.schedule.daemon import _is_running, start, status, stop

runner = CliRunner(env={"NO_COLOR": "1"})


# ---------------------------------------------------------------------------
# _is_running helper
# ---------------------------------------------------------------------------


def test_is_running_current_process() -> None:
    assert _is_running(os.getpid()) is True


def test_is_running_nonexistent_pid() -> None:
    # PID 99999999 almost certainly doesn't exist
    assert _is_running(99999999) is False


# ---------------------------------------------------------------------------
# status()
# ---------------------------------------------------------------------------


def test_status_not_running_no_pid_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("assay.schedule.daemon._PID_FILE", tmp_path / "scheduler.pid")
    info = status()
    assert info["running"] is False
    assert info["pid"] is None


def test_status_running_with_pid_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pid_file = tmp_path / "scheduler.pid"
    pid_file.write_text(str(os.getpid()))
    monkeypatch.setattr("assay.schedule.daemon._PID_FILE", pid_file)
    info = status()
    assert info["running"] is True
    assert info["pid"] == os.getpid()


def test_status_stale_pid_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pid_file = tmp_path / "scheduler.pid"
    pid_file.write_text("99999999")
    monkeypatch.setattr("assay.schedule.daemon._PID_FILE", pid_file)
    info = status()
    assert info["running"] is False
    assert info["pid"] is None


# ---------------------------------------------------------------------------
# stop()
# ---------------------------------------------------------------------------


def test_stop_no_pid_file_exits_1(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("assay.schedule.daemon._PID_FILE", tmp_path / "scheduler.pid")
    with pytest.raises(SystemExit) as exc:
        stop()
    assert exc.value.code == 1


def test_stop_stale_pid_file_exits_1(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pid_file = tmp_path / "scheduler.pid"
    pid_file.write_text("99999999")
    monkeypatch.setattr("assay.schedule.daemon._PID_FILE", pid_file)
    with pytest.raises(SystemExit) as exc:
        stop()
    assert exc.value.code == 1
    assert not pid_file.exists()


def test_stop_sends_sigterm(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pid_file = tmp_path / "scheduler.pid"
    pid_file.write_text(str(os.getpid()))
    monkeypatch.setattr("assay.schedule.daemon._PID_FILE", pid_file)

    sent_signals: list[int] = []
    call_count = 0

    def mock_is_running(pid: int) -> bool:
        nonlocal call_count
        call_count += 1
        # First call (alive check in stop()): True; subsequent (wait loop): False
        return call_count == 1

    def mock_kill(pid: int, sig: int) -> None:
        sent_signals.append(sig)

    monkeypatch.setattr("assay.schedule.daemon._is_running", mock_is_running)
    monkeypatch.setattr("assay.schedule.daemon.os.kill", mock_kill)

    stop()
    assert signal.SIGTERM in sent_signals


# ---------------------------------------------------------------------------
# start(): double-start prevention
# ---------------------------------------------------------------------------


def test_start_double_start_exits_1(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pid_file = tmp_path / "scheduler.pid"
    pid_file.write_text(str(os.getpid()))
    monkeypatch.setattr("assay.schedule.daemon._PID_FILE", pid_file)
    with pytest.raises(SystemExit) as exc:
        start()
    assert exc.value.code == 1


# ---------------------------------------------------------------------------
# CLI: schedule start/stop/status
# ---------------------------------------------------------------------------


def test_cli_schedule_status_stopped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("assay.schedule.daemon._PID_FILE", tmp_path / "scheduler.pid")
    result = runner.invoke(app, ["schedule", "status"])
    assert result.exit_code == 0
    assert "stopped" in result.output


def test_cli_schedule_status_running(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pid_file = tmp_path / "scheduler.pid"
    pid_file.write_text(str(os.getpid()))
    monkeypatch.setattr("assay.schedule.daemon._PID_FILE", pid_file)
    result = runner.invoke(app, ["schedule", "status"])
    assert result.exit_code == 0
    assert "running" in result.output
