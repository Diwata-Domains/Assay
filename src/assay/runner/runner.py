"""Playwright Docker runner module.

Starts an ephemeral Docker container from the Playwright runner image,
passes the target URL and suite name as environment variables, mounts
an output directory, and returns a RunResult with the exit code and
captured output.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field

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
