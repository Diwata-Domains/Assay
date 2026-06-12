"""Artifact collection — reads Docker runner output directory into a structured bundle."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from assay.runner.runner import RunResult

_RESULT_FILE = "result.json"
_SCRIPT_RESULT_FILE = "script_result.json"
_SCREENSHOT_FILE = "screenshot.png"


class ArtifactError(Exception):
    """Raised when artifact files are unreadable or malformed."""


@dataclass
class StepResult:
    """Result of a single step in a multi-step script run."""

    index: int
    type: str
    label: str
    outcome: str  # "pass" | "fail"
    error: Optional[str] = None  # noqa: UP007
    screenshot_path: Optional[str] = None  # full path on host


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
    steps: list[StepResult] = field(default_factory=list)  # non-empty for script runs
    script_name: str = ""  # set for script runs


def collect_artifacts(output_dir: str, runner_result: RunResult) -> ArtifactBundle:
    """Read runner output directory and return a structured ArtifactBundle.

    Falls back to deriving outcome from runner_result.exit_code when result.json
    is absent (e.g. container crashed before writing outputs).

    Raises ArtifactError if result.json is present but malformed.
    """
    base = Path(output_dir)
    script_result_file = base / _SCRIPT_RESULT_FILE
    result_file = base / _RESULT_FILE
    screenshot_file = base / _SCREENSHOT_FILE

    screenshot_path = str(screenshot_file) if screenshot_file.exists() else None

    # Script mode — script_result.json takes precedence
    if script_result_file.exists():
        return _collect_script_artifacts(base, script_result_file, runner_result)

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


def _collect_script_artifacts(
    base: Path,
    script_result_file: Path,
    runner_result: RunResult,
) -> ArtifactBundle:
    """Collect artifacts from a multi-step script run."""
    try:
        raw: dict[str, object] = json.loads(script_result_file.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        raise ArtifactError(f"failed to parse {script_result_file}: {exc}") from exc

    raw_steps = raw.get("steps", [])
    steps: list[StepResult] = []
    first_screenshot: Optional[str] = None

    for i, s in enumerate(raw_steps if isinstance(raw_steps, list) else []):
        screenshot_filename = s.get("screenshot") if isinstance(s, dict) else None
        screenshot_path: Optional[str] = None
        if screenshot_filename:
            candidate = base / str(screenshot_filename)
            if candidate.exists():
                screenshot_path = str(candidate)
                if first_screenshot is None:
                    first_screenshot = screenshot_path

        steps.append(StepResult(
            index=int(s.get("index", i)) if isinstance(s, dict) else i,
            type=str(s.get("type", "")) if isinstance(s, dict) else "",
            label=str(s.get("label", "")) if isinstance(s, dict) else "",
            outcome=str(s.get("outcome", "inconclusive")) if isinstance(s, dict) else "inconclusive",
            error=str(s["error"]) if isinstance(s, dict) and s.get("error") else None,
            screenshot_path=screenshot_path,
        ))

    return ArtifactBundle(
        outcome=str(raw.get("outcome", "fail" if runner_result.exit_code != 0 else "pass")),
        url=str(raw.get("url", "")),
        suite=str(raw.get("suite", "default")),
        timestamp=str(raw.get("timestamp", "")),
        error=str(raw["error"]) if raw.get("error") else None,
        screenshot_path=first_screenshot,
        raw_result=raw,
        steps=steps,
        script_name=str(raw.get("name", "")),
    )
