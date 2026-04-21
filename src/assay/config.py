"""Assay configuration loader.

Reads assay.toml from (in priority order):
  1. explicit path passed to load_config()
  2. ./assay.toml  (project-local)
  3. ~/.assay/config.toml  (global user)
  4. built-in defaults (all fields optional)

Exit code 2 is expected when ConfigError propagates to the CLI layer.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

_KNOWN_SECTIONS = {"project", "runner", "output", "serve", "keys", "schedule"}


class ConfigError(Exception):
    """Raised on config parse or validation failure."""


@dataclass
class ProjectConfig:
    name: str = "assay"


@dataclass
class RunnerConfig:
    docker_image: str = "assay-playwright:latest"
    timeout_seconds: int = 300


@dataclass
class OutputConfig:
    directory: str = "./assay-output"


@dataclass
class ServeConfig:
    host: str = "127.0.0.1"
    port: int = 8000


@dataclass
class KeysConfig:
    store: str = "~/.assay/keys.json"


@dataclass
class ScheduleConfig:
    store: str = "~/.assay/schedules.json"


@dataclass
class AssayConfig:
    project: ProjectConfig = field(default_factory=ProjectConfig)
    runner: RunnerConfig = field(default_factory=RunnerConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    serve: ServeConfig = field(default_factory=ServeConfig)
    keys: KeysConfig = field(default_factory=KeysConfig)
    schedule: ScheduleConfig = field(default_factory=ScheduleConfig)


def _resolve_path(override: str | None) -> Path | None:
    if override is not None:
        p = Path(override)
        if not p.exists():
            raise ConfigError(f"config file not found: {override}")
        return p
    local = Path("assay.toml")
    if local.exists():
        return local
    global_ = Path.home() / ".assay" / "config.toml"
    if global_.exists():
        return global_
    return None


def _parse(raw: dict[str, object]) -> AssayConfig:
    unknown = set(raw.keys()) - _KNOWN_SECTIONS
    if unknown:
        raise ConfigError(f"unknown config section(s): {', '.join(sorted(unknown))}")

    def _section(key: str) -> dict[str, object]:
        val = raw.get(key, {})
        if not isinstance(val, dict):
            raise ConfigError(f"config section [{key}] must be a table")
        return val

    proj = _section("project")
    runner = _section("runner")
    output = _section("output")
    serve = _section("serve")
    keys = _section("keys")
    schedule = _section("schedule")

    raw_timeout = runner.get("timeout_seconds", 300)
    raw_port = serve.get("port", 8000)
    if not isinstance(raw_timeout, int):
        raise ConfigError(f"runner.timeout_seconds must be an integer, got {raw_timeout!r}")
    if not isinstance(raw_port, int):
        raise ConfigError(f"serve.port must be an integer, got {raw_port!r}")

    return AssayConfig(
        project=ProjectConfig(name=str(proj.get("name", "assay"))),
        runner=RunnerConfig(
            docker_image=str(runner.get("docker_image", "assay-playwright:latest")),
            timeout_seconds=raw_timeout,
        ),
        output=OutputConfig(directory=str(output.get("directory", "./assay-output"))),
        serve=ServeConfig(
            host=str(serve.get("host", "127.0.0.1")),
            port=raw_port,
        ),
        keys=KeysConfig(store=str(keys.get("store", "~/.assay/keys.json"))),
        schedule=ScheduleConfig(store=str(schedule.get("store", "~/.assay/schedules.json"))),
    )


def load_config(path: str | None = None) -> AssayConfig:
    """Load and return AssayConfig from the resolved config file path.

    Returns all-defaults AssayConfig if no config file is found.
    Raises ConfigError on file-not-found (when explicit path given), parse error,
    or unknown section.
    """
    resolved = _resolve_path(path)
    if resolved is None:
        return AssayConfig()
    try:
        raw = tomllib.loads(resolved.read_text())
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"invalid TOML in {resolved}: {exc}") from exc
    return _parse(raw)
