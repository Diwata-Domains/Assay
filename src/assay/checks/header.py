# SPDX-FileCopyrightText: 2024-2026 Shaznay Sison
# SPDX-License-Identifier: AGPL-3.0-only

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

import httpx

from assay.checks.models import AssertionResult, CheckResult

if TYPE_CHECKING:
    from assay.config import CheckConfig


def run_header_check(check: CheckConfig) -> CheckResult:
    assertions: list[AssertionResult] = []
    passed = True
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    try:
        resp = httpx.get(
            check.target,
            timeout=float(check.timeout_seconds),
            follow_redirects=True,
        )
    except Exception as exc:
        return CheckResult(
            check_id=check.id,
            check_type="header",
            target=check.target,
            passed=False,
            checked_at=now,
            error=str(exc),
        )

    headers_lower: dict[str, str] = {k.lower(): v for k, v in resp.headers.items()}

    if check.expect_header is not None:
        key = check.expect_header.lower()
        actual_value = headers_lower.get(key)
        present = actual_value is not None
        a = AssertionResult(
            name=f"header_present:{check.expect_header}",
            passed=present,
            expected="present",
            actual="present" if present else "absent",
        )
        assertions.append(a)
        if not a.passed:
            passed = False

        if present and check.expect_value is not None and actual_value is not None:
            value_match = actual_value == check.expect_value
            a2 = AssertionResult(
                name=f"header_value:{check.expect_header}",
                passed=value_match,
                expected=check.expect_value,
                actual=actual_value,
            )
            assertions.append(a2)
            if not a2.passed:
                passed = False

    if check.expect_absent is not None:
        key = check.expect_absent.lower()
        absent = key not in headers_lower
        a = AssertionResult(
            name=f"header_absent:{check.expect_absent}",
            passed=absent,
            expected="absent",
            actual="absent" if absent else f"present ({headers_lower.get(key, '')})",
        )
        assertions.append(a)
        if not a.passed:
            passed = False

    return CheckResult(
        check_id=check.id,
        check_type="header",
        target=check.target,
        passed=passed,
        assertions=assertions,
        checked_at=now,
    )
