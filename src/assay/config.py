# SPDX-FileCopyrightText: 2024-2026 Shaznay Sison
# SPDX-License-Identifier: AGPL-3.0-only

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
from typing import cast

_KNOWN_SECTIONS = {"project", "runner", "output", "serve", "keys", "schedule", "grain", "store", "ci", "checks"}


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
class GrainConfig:
    project_root: str = ""
    output_path: str = ""
    repo: str = ""
    auto_create: bool = False
    phase: str = ""
    branch: str = ""


@dataclass
class StoreConfig:
    db: str = "~/.assay/store.db"


@dataclass
class CheckConfig:
    id: str
    type: str
    target: str
    expect_status: int | None = None
    max_response_ms: int | None = None
    body_contains: str | None = None
    body_json_path: str | None = None
    body_json_value: str | None = None
    expect_header: str | None = None
    expect_absent: str | None = None
    expect_value: str | None = None
    api_key: str | None = None
    timeout_seconds: int = 10


@dataclass
class CiConfig:
    compare: bool = False
    threshold: float = 0.1
    fail_on_regression: bool = True
    comment: bool = True


@dataclass
class AssayConfig:
    project: ProjectConfig = field(default_factory=ProjectConfig)
    runner: RunnerConfig = field(default_factory=RunnerConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    serve: ServeConfig = field(default_factory=ServeConfig)
    keys: KeysConfig = field(default_factory=KeysConfig)
    schedule: ScheduleConfig = field(default_factory=ScheduleConfig)
    grain: GrainConfig = field(default_factory=GrainConfig)
    store: StoreConfig = field(default_factory=StoreConfig)
    ci: CiConfig = field(default_factory=CiConfig)
    checks: list[CheckConfig] = field(default_factory=list)


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


def _parse_grain_auto_create(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        if value.lower() == "true":
            return True
        if value.lower() == "false":
            return False
    raise ConfigError(f"[grain] auto_create must be a boolean, got {value!r}")


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
    grain = _section("grain")
    store = _section("store")
    ci = _section("ci")

    raw_checks = raw.get("checks", [])
    if not isinstance(raw_checks, list):
        raise ConfigError("config section [checks] must be an array-of-tables")
    parsed_checks: list[CheckConfig] = []
    for i, item in enumerate(raw_checks):
        if not isinstance(item, dict):
            raise ConfigError(f"checks[{i}] must be a table")
        check_id = item.get("id")
        check_type = item.get("type")
        check_target = item.get("target")
        if not check_id or not isinstance(check_id, str):
            raise ConfigError(f"checks[{i}] missing required field: id")
        if not check_type or not isinstance(check_type, str):
            raise ConfigError(f"checks[{i}] missing required field: type")
        if not check_target or not isinstance(check_target, str):
            raise ConfigError(f"checks[{i}] missing required field: target")
        raw_timeout = item.get("timeout_seconds", 10)
        if not isinstance(raw_timeout, int):
            raise ConfigError(f"checks[{i}].timeout_seconds must be an integer")
        raw_status = item.get("expect_status")
        if raw_status is not None and not isinstance(raw_status, int):
            raise ConfigError(f"checks[{i}].expect_status must be an integer")
        raw_ms = item.get("max_response_ms")
        if raw_ms is not None and not isinstance(raw_ms, int):
            raise ConfigError(f"checks[{i}].max_response_ms must be an integer")
        parsed_checks.append(CheckConfig(
            id=check_id,
            type=check_type,
            target=check_target,
            expect_status=raw_status,
            max_response_ms=raw_ms,
            body_contains=str(item["body_contains"]) if item.get("body_contains") is not None else None,
            body_json_path=str(item["body_json_path"]) if item.get("body_json_path") is not None else None,
            body_json_value=str(item["body_json_value"]) if item.get("body_json_value") is not None else None,
            expect_header=str(item["expect_header"]) if item.get("expect_header") is not None else None,
            expect_absent=str(item["expect_absent"]) if item.get("expect_absent") is not None else None,
            expect_value=str(item["expect_value"]) if item.get("expect_value") is not None else None,
            api_key=str(item["api_key"]) if item.get("api_key") is not None else None,
            timeout_seconds=raw_timeout,
        ))

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
        grain=GrainConfig(
            project_root=str(grain.get("project_root", "")),
            output_path=str(grain.get("output_path", "")),
            repo=str(grain.get("repo", "")),
            auto_create=_parse_grain_auto_create(grain.get("auto_create", False)),
            phase=str(grain.get("phase", "")),
            branch=str(grain.get("branch", "")),
        ),
        store=StoreConfig(db=str(store.get("db", "~/.assay/store.db"))),
        ci=CiConfig(
            compare=bool(ci.get("compare", False)),
            threshold=float(cast(float, ci.get("threshold", 0.1))),
            fail_on_regression=bool(ci.get("fail_on_regression", True)),
            comment=bool(ci.get("comment", True)),
        ),
        checks=parsed_checks,
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
