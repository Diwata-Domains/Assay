from __future__ import annotations

from typing import TYPE_CHECKING

from assay.checks.models import CheckResult

if TYPE_CHECKING:
    from assay.config import CheckConfig


class UnknownCheckType(Exception):
    pass


def run_check(check: CheckConfig) -> CheckResult:
    if check.type == "http":
        from assay.checks.http import run_http_check
        return run_http_check(check)
    raise UnknownCheckType(f"unsupported check type: {check.type!r}")
