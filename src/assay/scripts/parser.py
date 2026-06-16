# SPDX-FileCopyrightText: 2024-2026 Shaznay Sison
# SPDX-License-Identifier: AGPL-3.0-only

"""Script format parser and validator for Assay multi-step scripts.

Script format (JSON):
    {
      "name": "Login flow",
      "steps": [
        { "type": "navigate",   "url": "https://example.com" },
        { "type": "screenshot", "label": "homepage" },
        { "type": "click",      "selector": "#login-btn" },
        { "type": "fill",       "selector": "#email",    "value": "user@example.com" },
        { "type": "fill",       "selector": "#password", "value": "secret" },
        { "type": "click",      "selector": "[type=submit]" },
        { "type": "wait_for",   "selector": ".dashboard", "timeout": 5000 },
        { "type": "screenshot", "label": "dashboard" }
      ]
    }

Step types:
    navigate    — page.goto(url)
    click       — page.click(selector)
    fill        — page.fill(selector, value)
    screenshot  — full-page screenshot saved as step-{index}-{label}.png
    wait_for    — page.waitForSelector(selector, { timeout })
    wait        — page.waitForTimeout(ms)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

VALID_STEP_TYPES = frozenset({
    "navigate", "click", "fill", "screenshot", "wait_for", "wait",
    "expect_text", "expect_not_text", "expect_visible", "expect_url",
})


class ScriptParseError(Exception):
    """Raised when a script file is malformed or contains invalid step definitions."""


@dataclass
class ScriptStep:
    type: str
    url: str = ""
    selector: str = ""
    value: str = ""
    label: str = ""
    timeout: int = 5000
    ms: int = 1000
    text: str = ""
    pattern: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "type": self.type,
            "url": self.url,
            "selector": self.selector,
            "value": self.value,
            "label": self.label,
            "timeout": self.timeout,
            "ms": self.ms,
            "text": self.text,
            "pattern": self.pattern,
        }


@dataclass
class AssayScript:
    name: str
    steps: list[ScriptStep] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {"name": self.name, "steps": [s.to_dict() for s in self.steps]}


def parse_script(path: Path) -> AssayScript:
    """Parse and validate an Assay script JSON file.

    Raises ScriptParseError on any validation failure.
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise ScriptParseError(f"failed to read script: {exc}") from exc

    if not isinstance(data, dict):
        raise ScriptParseError("script must be a JSON object with 'name' and 'steps' fields")

    name = str(data.get("name", path.stem))
    raw_steps = data.get("steps", [])

    if not isinstance(raw_steps, list):
        raise ScriptParseError("'steps' must be a JSON array")
    if not raw_steps:
        raise ScriptParseError("'steps' must not be empty")

    steps: list[ScriptStep] = []
    for i, raw in enumerate(raw_steps):
        if not isinstance(raw, dict):
            raise ScriptParseError(f"step {i}: must be an object, got {type(raw).__name__}")

        step_type = raw.get("type", "")
        if step_type not in VALID_STEP_TYPES:
            raise ScriptParseError(
                f"step {i}: unknown type {step_type!r} — "
                f"valid types: {', '.join(sorted(VALID_STEP_TYPES))}"
            )

        if step_type == "navigate" and not raw.get("url"):
            raise ScriptParseError(f"step {i} (navigate): 'url' is required")
        if step_type in ("click", "fill", "wait_for") and not raw.get("selector"):
            raise ScriptParseError(f"step {i} ({step_type}): 'selector' is required")
        if step_type in ("expect_text", "expect_not_text"):
            if not raw.get("selector"):
                raise ScriptParseError(f"step {i} ({step_type}): 'selector' is required")
            if not raw.get("text") and raw.get("text") != "":
                raise ScriptParseError(f"step {i} ({step_type}): 'text' is required")
        if step_type == "expect_visible" and not raw.get("selector"):
            raise ScriptParseError(f"step {i} (expect_visible): 'selector' is required")
        if step_type == "expect_url" and not raw.get("pattern"):
            raise ScriptParseError(f"step {i} (expect_url): 'pattern' is required")

        steps.append(ScriptStep(
            type=step_type,
            url=str(raw.get("url", "")),
            selector=str(raw.get("selector", "")),
            value=str(raw.get("value", "")),
            label=str(raw.get("label", step_type)),
            timeout=int(raw.get("timeout", 5000)),
            ms=int(raw.get("ms", 1000)),
            text=str(raw.get("text", "")),
            pattern=str(raw.get("pattern", "")),
        ))

    return AssayScript(name=name, steps=steps)
