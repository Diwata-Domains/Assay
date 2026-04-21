"""Foreground scheduler loop — loads schedules from store and fires runner jobs."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from assay.config import AssayConfig


def run_scheduler(config: "AssayConfig") -> None:
    """Start a blocking scheduler; runs until KeyboardInterrupt."""
    from apscheduler.schedulers.blocking import BlockingScheduler  # type: ignore[import-untyped]

    from assay.schedule.store import list_schedules

    schedules = list_schedules(config.schedule.store)
    if not schedules:
        print("no schedules configured — nothing to run")
        return

    scheduler = BlockingScheduler()

    for entry in schedules:
        schedule_id = str(entry["id"])
        cron = str(entry["cron"])
        suite = str(entry["suite"])
        target = str(entry["target"]) if entry["target"] is not None else None

        def _make_job(sid: str, _suite: str, _target: str | None) -> "Callable[[], None]":
            def job() -> None:
                _run_one(config, sid, _suite, _target)

            return job

        scheduler.add_job(
            _make_job(schedule_id, suite, target),
            "cron",
            id=schedule_id,
            **_parse_cron(cron),
        )
        print(f"scheduled: {schedule_id}  cron={cron}  suite={suite}  target={target or '(config default)'}")

    print("scheduler running — press Ctrl+C to stop")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown(wait=False)
        print("scheduler stopped")


def _parse_cron(expr: str) -> dict[str, str]:
    """Split a 5-field cron expression into APScheduler keyword args."""
    minute, hour, day, month, day_of_week = expr.split()
    return {
        "minute": minute,
        "hour": hour,
        "day": day,
        "month": month,
        "day_of_week": day_of_week,
    }


def _run_one(config: "AssayConfig", schedule_id: str, suite: str, target: str | None) -> None:
    """Execute one scheduled run and record the result."""
    from assay.runner import runner as _runner
    from assay.schedule.store import update_last_run

    effective_target = target or config.runner.docker_image
    try:
        result = _runner.run(
            effective_target,
            suite=suite,
            output_dir=config.output.directory,
            image=config.runner.docker_image,
        )
        outcome = "pass" if result.exit_code == 0 else "fail"
    except Exception as exc:
        outcome = f"error: {exc}"

    update_last_run(config.schedule.store, schedule_id, outcome)
    print(f"job complete: {schedule_id}  result={outcome}")
