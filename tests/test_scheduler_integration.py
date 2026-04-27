"""Scheduler integration tests: full lifecycle via CLI and loop."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from assay.cli.main import app

cli = CliRunner(env={"NO_COLOR": "1"})


def _cfg(tmp_path: Path):
    from assay.config import AssayConfig, ScheduleConfig

    cfg = AssayConfig()
    cfg.schedule = ScheduleConfig(store=str(tmp_path / ".assay" / "schedules.json"))
    return cfg


# ---------------------------------------------------------------------------
# Full CLI lifecycle: add → list → remove
# ---------------------------------------------------------------------------


def test_add_list_remove_lifecycle(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)

    with patch("assay.cli.main.load_config", return_value=cfg):
        # add
        result = cli.invoke(app, ["schedule", "add", "--cron", "0 8 * * *", "--suite", "smoke"])
        assert result.exit_code == 0
        sid = result.output.strip().split("schedule added: ")[1].strip()

        # list shows the new entry
        result = cli.invoke(app, ["schedule", "list"])
        assert result.exit_code == 0
        assert sid in result.output
        assert "0 8 * * *" in result.output
        assert "smoke" in result.output

        # remove
        result = cli.invoke(app, ["schedule", "remove", sid])
        assert result.exit_code == 0
        assert sid in result.output

        # list is now empty
        result = cli.invoke(app, ["schedule", "list"])
        assert result.exit_code == 0
        assert "no schedules" in result.output


def test_add_multiple_and_remove_one(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)

    with patch("assay.cli.main.load_config", return_value=cfg):
        r1 = cli.invoke(app, ["schedule", "add", "--cron", "0 * * * *"])
        r2 = cli.invoke(app, ["schedule", "add", "--cron", "0 0 * * *", "--suite", "nightly"])
        sid1 = r1.output.strip().split("schedule added: ")[1].strip()
        sid2 = r2.output.strip().split("schedule added: ")[1].strip()

        cli.invoke(app, ["schedule", "remove", sid1])

        result = cli.invoke(app, ["schedule", "list"])
        assert sid1 not in result.output
        assert sid2 in result.output


# ---------------------------------------------------------------------------
# schedule run fires job and updates store
# ---------------------------------------------------------------------------


def test_schedule_run_fires_and_records_result(tmp_path: Path) -> None:
    from assay.runner.runner import RunResult
    from assay.schedule.store import list_schedules

    cfg = _cfg(tmp_path)
    store = cfg.schedule.store

    from assay.schedule.store import add_schedule

    add_schedule(store, "* * * * *", target="https://example.com")

    mock_result = MagicMock(spec=RunResult)
    mock_result.exit_code = 0

    mock_scheduler = MagicMock()
    mock_scheduler.start.side_effect = KeyboardInterrupt
    job_fns: list = []

    def capture_add_job(fn, *args, **kwargs):
        job_fns.append(fn)

    mock_scheduler.add_job.side_effect = capture_add_job

    with (
        patch("apscheduler.schedulers.blocking.BlockingScheduler", return_value=mock_scheduler),
        patch("assay.runner.runner.run", return_value=mock_result),
    ):
        from assay.schedule.loop import run_scheduler

        run_scheduler(cfg)

        # manually invoke the captured job function to simulate a scheduled firing
        assert len(job_fns) == 1
        job_fns[0]()

    entry = list_schedules(store)[0]
    assert entry["last_result"] == "pass"
    assert entry["last_run"] is not None


def test_schedule_run_records_failure(tmp_path: Path) -> None:
    from assay.schedule.store import add_schedule, list_schedules

    cfg = _cfg(tmp_path)
    store = cfg.schedule.store
    add_schedule(store, "* * * * *")

    mock_scheduler = MagicMock()
    mock_scheduler.start.side_effect = KeyboardInterrupt
    job_fns: list = []

    def capture_add_job(fn, *args, **kwargs):
        job_fns.append(fn)

    mock_scheduler.add_job.side_effect = capture_add_job

    with (
        patch("apscheduler.schedulers.blocking.BlockingScheduler", return_value=mock_scheduler),
        patch("assay.runner.runner.run", side_effect=RuntimeError("connection refused")),
    ):
        from assay.schedule.loop import run_scheduler

        run_scheduler(cfg)
        job_fns[0]()

    entry = list_schedules(store)[0]
    assert "error" in str(entry["last_result"])


# ---------------------------------------------------------------------------
# cron validation end-to-end through CLI
# ---------------------------------------------------------------------------


def test_invalid_cron_not_stored(tmp_path: Path) -> None:
    from assay.schedule.store import list_schedules

    cfg = _cfg(tmp_path)

    with patch("assay.cli.main.load_config", return_value=cfg):
        result = cli.invoke(app, ["schedule", "add", "--cron", "not-a-cron"])
    assert result.exit_code == 2
    assert list_schedules(cfg.schedule.store) == []
