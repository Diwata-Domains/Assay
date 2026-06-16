# SPDX-FileCopyrightText: 2024-2026 Shaznay Sison
# SPDX-License-Identifier: AGPL-3.0-only

from __future__ import annotations

import datetime
import os
from typing import TYPE_CHECKING

import httpx

from assay.checks.models import AssertionResult, CheckResult

if TYPE_CHECKING:
    from assay.config import CheckConfig


def _resolve_key(value: str) -> str:
    if value.startswith("$"):
        return os.environ.get(value[1:], "")
    return value


def run_auth_check(check: CheckConfig) -> CheckResult:
    assertions: list[AssertionResult] = []
    passed = True
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    try:
        resp_unauth = httpx.get(
            check.target,
            timeout=float(check.timeout_seconds),
            follow_redirects=False,
        )
    except Exception as exc:
        return CheckResult(
            check_id=check.id,
            check_type="auth",
            target=check.target,
            passed=False,
            checked_at=now,
            error=str(exc),
        )

    unauth_ok = resp_unauth.status_code in (401, 403)
    a = AssertionResult(
        name="unauthenticated_rejected",
        passed=unauth_ok,
        expected="401 or 403",
        actual=str(resp_unauth.status_code),
    )
    assertions.append(a)
    if not a.passed:
        passed = False

    if check.api_key is not None:
        api_key = _resolve_key(check.api_key)
        try:
            resp_auth = httpx.get(
                check.target,
                timeout=float(check.timeout_seconds),
                follow_redirects=True,
                headers={"X-Assay-Key": api_key},
            )
        except Exception as exc:
            return CheckResult(
                check_id=check.id,
                check_type="auth",
                target=check.target,
                passed=False,
                assertions=assertions,
                checked_at=now,
                error=str(exc),
            )

        auth_ok = resp_auth.status_code == 200
        a2 = AssertionResult(
            name="authenticated_allowed",
            passed=auth_ok,
            expected="200",
            actual=str(resp_auth.status_code),
        )
        assertions.append(a2)
        if not a2.passed:
            passed = False

    return CheckResult(
        check_id=check.id,
        check_type="auth",
        target=check.target,
        passed=passed,
        assertions=assertions,
        checked_at=now,
    )
