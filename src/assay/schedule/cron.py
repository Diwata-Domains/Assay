"""Cron expression validation and next-run computation via APScheduler."""

from __future__ import annotations

from datetime import datetime, timezone


class InvalidCronError(ValueError):
    """Raised when a cron expression is not a valid 5-field cron string."""


def validate_cron(expr: str) -> None:
    """Raise InvalidCronError if *expr* is not a valid 5-field cron expression."""
    from apscheduler.triggers.cron import CronTrigger  # type: ignore[import-untyped]

    try:
        CronTrigger.from_crontab(expr)
    except (ValueError, KeyError) as exc:
        raise InvalidCronError(f"invalid cron expression {expr!r}: {exc}") from exc


def next_run(expr: str, after: datetime | None = None) -> datetime | None:
    """Return the next fire time for *expr* after *after* (defaults to now UTC)."""
    from apscheduler.triggers.cron import CronTrigger  # noqa: F811

    trigger = CronTrigger.from_crontab(expr)
    base = after or datetime.now(tz=timezone.utc)
    result: datetime | None = trigger.get_next_fire_time(None, base)
    return result
