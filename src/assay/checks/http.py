from __future__ import annotations

import datetime
import json
import time
from typing import TYPE_CHECKING

import httpx

from assay.checks.models import AssertionResult, CheckResult

if TYPE_CHECKING:
    from assay.config import CheckConfig


def run_http_check(check: CheckConfig) -> CheckResult:
    assertions: list[AssertionResult] = []
    passed = True
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    try:
        t0 = time.monotonic()
        resp = httpx.get(
            check.target,
            timeout=float(check.timeout_seconds),
            follow_redirects=True,
        )
        elapsed_ms = int((time.monotonic() - t0) * 1000)
    except Exception as exc:
        return CheckResult(
            check_id=check.id,
            check_type="http",
            target=check.target,
            passed=False,
            checked_at=now,
            error=str(exc),
        )

    if check.expect_status is not None:
        a = AssertionResult(
            name="status_code",
            passed=resp.status_code == check.expect_status,
            expected=str(check.expect_status),
            actual=str(resp.status_code),
        )
        assertions.append(a)
        if not a.passed:
            passed = False

    if check.max_response_ms is not None:
        a = AssertionResult(
            name="response_time_ms",
            passed=elapsed_ms <= check.max_response_ms,
            expected=f"<= {check.max_response_ms}",
            actual=str(elapsed_ms),
        )
        assertions.append(a)
        if not a.passed:
            passed = False

    if check.body_contains is not None:
        body = resp.text
        present = check.body_contains in body
        a = AssertionResult(
            name="body_contains",
            passed=present,
            expected=f"contains {check.body_contains!r}",
            actual="present" if present else "absent",
        )
        assertions.append(a)
        if not a.passed:
            passed = False

    if check.body_json_path is not None and check.body_json_value is not None:
        try:
            data: object = json.loads(resp.text)
            for part in check.body_json_path.split("."):
                data = data[part]  # type: ignore[index]
            actual_str = str(data)
            a = AssertionResult(
                name=f"json_path:{check.body_json_path}",
                passed=actual_str == check.body_json_value,
                expected=check.body_json_value,
                actual=actual_str,
            )
        except Exception as exc:
            a = AssertionResult(
                name=f"json_path:{check.body_json_path}",
                passed=False,
                expected=check.body_json_value,
                actual=f"error: {exc}",
            )
        assertions.append(a)
        if not a.passed:
            passed = False

    return CheckResult(
        check_id=check.id,
        check_type="http",
        target=check.target,
        passed=passed,
        assertions=assertions,
        checked_at=now,
    )
