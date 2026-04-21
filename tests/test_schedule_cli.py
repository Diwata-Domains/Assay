"""Tests for assay schedule add/list/remove CLI commands and cron validation."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from assay.cli.main import app
from assay.schedule.cron import InvalidCronError, validate_cron

runner = CliRunner()

_VALID_CRON = "0 * * * *"
_INVALID_CRON = "not a cron"


# ---------------------------------------------------------------------------
# cron validator unit tests
# ---------------------------------------------------------------------------


def test_validate_cron_accepts_valid() -> None:
    validate_cron(_VALID_CRON)  # must not raise


def test_validate_cron_accepts_every_minute() -> None:
    validate_cron("* * * * *")


def test_validate_cron_accepts_complex() -> None:
    validate_cron("30 8 * * 1-5")


def test_validate_cron_rejects_invalid() -> None:
    with pytest.raises(InvalidCronError):
        validate_cron(_INVALID_CRON)


def test_validate_cron_rejects_four_field() -> None:
    with pytest.raises(InvalidCronError):
        validate_cron("0 * * *")


# ---------------------------------------------------------------------------
# schedule add
# ---------------------------------------------------------------------------


def test_schedule_add_prints_id(tmp_path: Path) -> None:
    store = str(tmp_path / "schedules.json")
    with patch("assay.cli.main.AssayConfig") as _mc:
        pass  # we rely on config default override via env

    # invoke directly with a real temp store
    with patch("assay.schedule.store.Path") as _mp:
        pass

    # Use mix-in env override via monkey-patching config
    from assay.config import AssayConfig, ScheduleConfig

    cfg = AssayConfig()
    cfg.schedule = ScheduleConfig(store=store)

    with patch("assay.cli.main.load_config", return_value=cfg):
        result = runner.invoke(app, ["schedule", "add", "--cron", _VALID_CRON])
    assert result.exit_code == 0
    assert "schedule added:" in result.output


def test_schedule_add_invalid_cron_exits_2(tmp_path: Path) -> None:
    store = str(tmp_path / "schedules.json")
    from assay.config import AssayConfig, ScheduleConfig

    cfg = AssayConfig()
    cfg.schedule = ScheduleConfig(store=store)

    with patch("assay.cli.main.load_config", return_value=cfg):
        result = runner.invoke(app, ["schedule", "add", "--cron", _INVALID_CRON])
    assert result.exit_code == 2


def test_schedule_add_with_suite_and_target(tmp_path: Path) -> None:
    store = str(tmp_path / "schedules.json")
    from assay.config import AssayConfig, ScheduleConfig

    cfg = AssayConfig()
    cfg.schedule = ScheduleConfig(store=store)

    with patch("assay.cli.main.load_config", return_value=cfg):
        result = runner.invoke(
            app,
            ["schedule", "add", "--cron", _VALID_CRON, "--suite", "smoke", "--target", "https://example.com"],
        )
    assert result.exit_code == 0
    assert "schedule added:" in result.output


# ---------------------------------------------------------------------------
# schedule list
# ---------------------------------------------------------------------------


def test_schedule_list_no_schedules(tmp_path: Path) -> None:
    store = str(tmp_path / "schedules.json")
    from assay.config import AssayConfig, ScheduleConfig

    cfg = AssayConfig()
    cfg.schedule = ScheduleConfig(store=store)

    with patch("assay.cli.main.load_config", return_value=cfg):
        result = runner.invoke(app, ["schedule", "list"])
    assert result.exit_code == 0
    assert "no schedules" in result.output


def test_schedule_list_shows_entry(tmp_path: Path) -> None:
    store = str(tmp_path / "schedules.json")
    from assay.config import AssayConfig, ScheduleConfig
    from assay.schedule.store import add_schedule

    cfg = AssayConfig()
    cfg.schedule = ScheduleConfig(store=store)
    add_schedule(store, _VALID_CRON, suite="smoke", target="https://example.com")

    with patch("assay.cli.main.load_config", return_value=cfg):
        result = runner.invoke(app, ["schedule", "list"])
    assert result.exit_code == 0
    assert _VALID_CRON in result.output
    assert "smoke" in result.output
    assert "https://example.com" in result.output


# ---------------------------------------------------------------------------
# schedule remove
# ---------------------------------------------------------------------------


def test_schedule_remove_success(tmp_path: Path) -> None:
    store = str(tmp_path / "schedules.json")
    from assay.config import AssayConfig, ScheduleConfig
    from assay.schedule.store import add_schedule, list_schedules

    cfg = AssayConfig()
    cfg.schedule = ScheduleConfig(store=store)
    sid = add_schedule(store, _VALID_CRON)

    with patch("assay.cli.main.load_config", return_value=cfg):
        result = runner.invoke(app, ["schedule", "remove", sid])
    assert result.exit_code == 0
    assert sid in result.output
    assert list_schedules(store) == []


def test_schedule_remove_not_found_exits_1(tmp_path: Path) -> None:
    store = str(tmp_path / "schedules.json")
    from assay.config import AssayConfig, ScheduleConfig

    cfg = AssayConfig()
    cfg.schedule = ScheduleConfig(store=store)

    with patch("assay.cli.main.load_config", return_value=cfg):
        result = runner.invoke(app, ["schedule", "remove", "00000000-0000-0000-0000-000000000000"])
    assert result.exit_code == 1
