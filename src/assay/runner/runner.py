# SPDX-FileCopyrightText: 2024-2026 Shaznay Sison
# SPDX-License-Identifier: AGPL-3.0-only

"""Playwright runner module — Docker and direct (no-Docker) modes.

Starts an ephemeral Docker container from the Playwright runner image,
passes the target URL and suite name as environment variables, mounts
an output directory, and returns a RunResult with the exit code and
captured output.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_IMAGE = "assay-playwright:latest"

_DOCKER_FALLBACK_PATHS = [
    "/usr/local/bin/docker",
    "/Applications/Docker.app/Contents/Resources/bin/docker",
    "/opt/homebrew/bin/docker",
]


def _find_docker() -> str:
    """Return the docker binary path, checking PATH then known locations."""
    found = shutil.which("docker")
    if found:
        return found
    for path in _DOCKER_FALLBACK_PATHS:
        if shutil.which(path):
            return path
    raise FileNotFoundError(
        "docker binary not found on PATH or at known locations. Ensure Docker Desktop is installed and running."
    )


@dataclass
class RunResult:
    """Result of a single runner invocation."""

    exit_code: int
    output_dir: str
    stdout: str = field(default="")
    stderr: str = field(default="")

    @property
    def success(self) -> bool:
        return self.exit_code == 0


def run(
    target_url: str,
    suite: str = "default",
    output_dir: str | None = None,
    image: str = DEFAULT_IMAGE,
) -> RunResult:
    """Run the Playwright container against target_url.

    Args:
        target_url: URL to navigate to inside the container.
        suite: Suite name passed to the runner (metadata only in v1).
        output_dir: Host directory to mount as /output. Created via
            tempfile.mkdtemp() if not supplied.
        image: Docker image to use.

    Returns:
        RunResult with exit_code, output_dir, stdout, stderr.
    """
    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="assay-")

    cmd = [
        _find_docker(),
        "run",
        "--rm",
        "-e",
        f"ASSAY_TARGET_URL={target_url}",
        "-e",
        f"ASSAY_SUITE={suite}",
        "-e",
        "ASSAY_OUTPUT_DIR=/output",
        "-v",
        f"{output_dir}:/output",
        image,
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )

    return RunResult(
        exit_code=result.returncode,
        output_dir=output_dir,
        stdout=result.stdout,
        stderr=result.stderr,
    )


def _find_runner_script() -> Path:
    """Return path to the bundled Playwright runner script."""
    bundled = Path(__file__).parent / "runner_script.js"
    if bundled.exists():
        return bundled
    raise FileNotFoundError(
        "runner_script.js not found in assay package. "
        "Reinstall assay-kit or use Docker mode."
    )


def _node_env(output_dir: str) -> dict[str, str]:
    """Build env dict for direct Node.js runner execution."""
    env = dict(os.environ)
    env["ASSAY_OUTPUT_DIR"] = output_dir
    # Allow playwright installed in cwd node_modules to be found
    cwd_modules = str(Path.cwd() / "node_modules")
    existing = env.get("NODE_PATH", "")
    env["NODE_PATH"] = f"{cwd_modules}:{existing}" if existing else cwd_modules
    return env


def run_direct(
    target_url: str,
    suite: str = "default",
    output_dir: str | None = None,
) -> RunResult:
    """Run the Playwright runner directly via Node.js without Docker.

    Requires Node.js and the playwright npm package to be installed.
    playwright must be in NODE_PATH or ./node_modules (install with
    `npm install playwright && npx playwright install chromium`).
    """
    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="assay-")

    runner_script = _find_runner_script()
    env = _node_env(output_dir)
    env["ASSAY_TARGET_URL"] = target_url
    env["ASSAY_SUITE"] = suite

    result = subprocess.run(
        ["node", str(runner_script)],
        env=env,
        capture_output=True,
        text=True,
    )

    return RunResult(
        exit_code=result.returncode,
        output_dir=output_dir,
        stdout=result.stdout,
        stderr=result.stderr,
    )


def run_script_direct(
    script_path: Path,
    suite: str = "default",
    output_dir: str | None = None,
) -> RunResult:
    """Run a multi-step Assay script directly via Node.js without Docker."""
    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="assay-script-")

    runner_script = _find_runner_script()
    env = _node_env(output_dir)
    env["ASSAY_SCRIPT_FILE"] = str(script_path.resolve())
    env["ASSAY_SUITE"] = suite

    result = subprocess.run(
        ["node", str(runner_script)],
        env=env,
        capture_output=True,
        text=True,
    )

    return RunResult(
        exit_code=result.returncode,
        output_dir=output_dir,
        stdout=result.stdout,
        stderr=result.stderr,
    )
