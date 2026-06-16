# SPDX-FileCopyrightText: 2024-2026 Shaznay Sison
# SPDX-License-Identifier: AGPL-3.0-only

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AssertionResult:
    name: str
    passed: bool
    expected: str
    actual: str


@dataclass
class CheckResult:
    check_id: str
    check_type: str
    target: str
    passed: bool
    assertions: list[AssertionResult] = field(default_factory=list)
    checked_at: str = ""
    error: str | None = None
