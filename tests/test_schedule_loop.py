"""Tests for the scheduler loop (run_scheduler) and schedule run CLI command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from assay.cli.main import app
from assay.schedule.loop import _parse_cron, _run_one, run_scheduler

runner = CliRunner(env={"NO_COLOR": "1"})


# ---------------------------------------------------------------------------
# _parse_cron helper
# ---------------------------------------------------------------------------


def test_parse_cron_splits_correctly() -> None:
    result = _parse_cron("5 4 * * 1-5")
    assert result == {"minute": "5", "hour": "4", "day": "*", "month": "*", "day_of_week": "1-5"}


def test_parse_cron_every_minute() -> None:
    result = _parse_cron("* * * * *")
    assert result == {"minute": "*", "hour": "*", "day": "*", "month": "*", "day_of_week": "*"}


# ---------------------------------------------------------------------------
# run_scheduler — no schedules
# ---------------------------------------------------------------------------


def test_run_scheduler_empty_store(tmp_path: Path) -> None:
    from assay.config import AssayConfig, ScheduleConfig

    cfg = AssayConfig()
    cfg.schedule = ScheduleConfig(store=str(tmp_path / "schedules.json"))

    with patch("apscheduler.schedulers.blocking.BlockingScheduler") as _mock_sched:
        run_scheduler(cfg)

    _mock_sched.assert_not_called()


# ---------------------------------------------------------------------------
# run_scheduler — jobs added
# ---------------------------------------------------------------------------


def test_run_scheduler_adds_job_for_each_schedule(tmp_path: Path) -> None:
    from assay.config import AssayConfig, ScheduleConfig
    from assay.schedule.store import add_schedule

    store = str(tmp_path / "schedules.json")
    cfg = AssayConfig()
    cfg.schedule = ScheduleConfig(store=store)

    add_schedule(store, "0 * * * *", suite="default")
    add_schedule(store, "0 0 * * *", suite="nightly")

    mock_scheduler = MagicMock()
    mock_scheduler.start.side_effect = KeyboardInterrupt

    with patch("apscheduler.schedulers.blocking.BlockingScheduler", return_value=mock_scheduler):
        run_scheduler(cfg)

    assert mock_scheduler.add_job.call_count == 2


def test_run_scheduler_shuts_down_on_keyboard_interrupt(tmp_path: Path) -> None:
    from assay.config import AssayConfig, ScheduleConfig
    from assay.schedule.store import add_schedule

    store = str(tmp_path / "schedules.json")
    cfg = AssayConfig()
    cfg.schedule = ScheduleConfig(store=store)
    add_schedule(store, "* * * * *")

    mock_scheduler = MagicMock()
    mock_scheduler.start.side_effect = KeyboardInterrupt

    with patch("apscheduler.schedulers.blocking.BlockingScheduler", return_value=mock_scheduler):
        run_scheduler(cfg)

    mock_scheduler.shutdown.assert_called_once_with(wait=False)


# ---------------------------------------------------------------------------
# _run_one — records result in store
# ---------------------------------------------------------------------------


def test_run_one_records_pass(tmp_path: Path) -> None:
    from assay.config import AssayConfig, ScheduleConfig
    from assay.runner.runner import RunResult
    from assay.schedule.store import add_schedule, list_schedules

    store = str(tmp_path / "schedules.json")
    cfg = AssayConfig()
    cfg.schedule = ScheduleConfig(store=store)
    sid = add_schedule(store, "* * * * *", target="https://example.com")

    mock_result = MagicMock(spec=RunResult)
    mock_result.exit_code = 0

    with patch("assay.runner.runner.run", return_value=mock_result):
        _run_one(cfg, sid, "default", "https://example.com")

    s = list_schedules(store)[0]
    assert s["last_result"] == "pass"
    assert s["last_run"] is not None


def test_run_one_records_error_on_exception(tmp_path: Path) -> None:
    from assay.config import AssayConfig, ScheduleConfig
    from assay.schedule.store import add_schedule, list_schedules

    store = str(tmp_path / "schedules.json")
    cfg = AssayConfig()
    cfg.schedule = ScheduleConfig(store=store)
    sid = add_schedule(store, "* * * * *")

    with patch("assay.runner.runner.run", side_effect=RuntimeError("docker not found")):
        _run_one(cfg, sid, "default", None)

    s = list_schedules(store)[0]
    assert s["last_result"] is not None
    assert "error" in str(s["last_result"])


# ---------------------------------------------------------------------------
# CLI: assay schedule run
# ---------------------------------------------------------------------------


def test_schedule_run_cli_no_schedules(tmp_path: Path) -> None:
    from assay.config import AssayConfig, ScheduleConfig

    cfg = AssayConfig()
    cfg.schedule = ScheduleConfig(store=str(tmp_path / "schedules.json"))

    with patch("assay.cli.main.load_config", return_value=cfg):
        result = runner.invoke(app, ["schedule", "run"])
    assert result.exit_code == 0
    assert "no schedules" in result.output
