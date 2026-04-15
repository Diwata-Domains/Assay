"""Artifact collection — reads Docker runner output directory into a structured bundle."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from assay.runner.runner import RunResult

_RESULT_FILE = "result.json"
_SCREENSHOT_FILE = "screenshot.png"


class ArtifactError(Exception):
    """Raised when artifact files are unreadable or malformed."""


@dataclass
class ArtifactBundle:
    """Structured output from a single runner invocation."""

    outcome: str  # "pass" | "fail" | "inconclusive"
    url: str
    suite: str
    timestamp: str
    error: Optional[str]  # noqa: UP007
    screenshot_path: Optional[str]  # noqa: UP007
    raw_result: dict[str, object]


def collect_artifacts(output_dir: str, runner_result: RunResult) -> ArtifactBundle:
    """Read runner output directory and return a structured ArtifactBundle.

    Falls back to deriving outcome from runner_result.exit_code when result.json
    is absent (e.g. container crashed before writing outputs).

    Raises ArtifactError if result.json is present but malformed.
    """
    base = Path(output_dir)
    result_file = base / _RESULT_FILE
    screenshot_file = base / _SCREENSHOT_FILE

    screenshot_path = str(screenshot_file) if screenshot_file.exists() else None

    if result_file.exists():
        try:
            raw: dict[str, object] = json.loads(result_file.read_text())
        except (json.JSONDecodeError, OSError) as exc:
            raise ArtifactError(f"failed to parse {result_file}: {exc}") from exc

        return ArtifactBundle(
            outcome=str(raw.get("outcome", "inconclusive")),
            url=str(raw.get("url", "")),
            suite=str(raw.get("suite", "default")),
            timestamp=str(raw.get("timestamp", "")),
            error=str(raw["error"]) if raw.get("error") else None,
            screenshot_path=screenshot_path,
            raw_result=raw,
        )

    # result.json absent — derive from exit code
    outcome = "pass" if runner_result.exit_code == 0 else "fail"
    return ArtifactBundle(
        outcome=outcome,
        url="",
        suite="default",
        timestamp="",
        error=runner_result.stderr or None,
        screenshot_path=screenshot_path,
        raw_result={},
    )
