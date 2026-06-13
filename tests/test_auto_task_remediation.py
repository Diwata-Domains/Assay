"""Tests for remediation suggestions in auto-created Grain tasks (Phase 26 T05)."""

from __future__ import annotations

import json
from pathlib import Path

from assay.config import AssayConfig, GrainConfig, OutputConfig
from assay.grain.auto_task import (
    create_check_failure_task,
    create_regression_task,
    suggest_remediation,
)


def _config(tmp_path: Path) -> AssayConfig:
    cfg = AssayConfig()
    cfg.grain = GrainConfig(
        repo=str(tmp_path / "grain-repo"),
        auto_create=True,
        output_path="assay-output",
    )
    cfg.output = OutputConfig(directory=str(tmp_path / "assay-output"))
    return cfg


# ---------------------------------------------------------------------------
# suggest_remediation unit tests
# ---------------------------------------------------------------------------


def test_regression_remediation() -> None:
    r = suggest_remediation("visual_regression", target="https://example.com")
    assert "https://example.com" in r
    assert "baseline" in r.lower() or "review" in r.lower()


def test_header_check_remediation() -> None:
    r = suggest_remediation("check_failure", check_type="header", assertion_name="expect_header", target="https://api.example.com")
    assert "header" in r.lower()
    assert "api.example.com" in r


def test_auth_unauthenticated_remediation() -> None:
    r = suggest_remediation("check_failure", check_type="auth", assertion_name="unauthenticated_rejection", target="https://api.example.com")
    assert "auth" in r.lower() or "authentication" in r.lower()
    assert "api.example.com" in r


def test_auth_authenticated_remediation() -> None:
    r = suggest_remediation("check_failure", check_type="auth", assertion_name="authenticated_access")
    assert "api key" in r.lower() or "authenticated" in r.lower()


def test_http_status_remediation() -> None:
    r = suggest_remediation("check_failure", check_type="http", assertion_name="status_code", target="https://example.com/health")
    assert "status" in r.lower() or "endpoint" in r.lower()
    assert "example.com" in r


def test_expect_text_remediation() -> None:
    r = suggest_remediation("check_failure", assertion_name="expect_text")
    assert "page" in r.lower() or "content" in r.lower()


def test_expect_visible_remediation() -> None:
    r = suggest_remediation("check_failure", assertion_name="expect_visible")
    assert "page" in r.lower() or "content" in r.lower()


def test_expect_url_remediation() -> None:
    r = suggest_remediation("check_failure", assertion_name="expect_url")
    assert "navigation" in r.lower() or "content" in r.lower()


def test_fallback_remediation() -> None:
    r = suggest_remediation("check_failure", check_type="unknown", assertion_name="")
    assert "review" in r.lower()


# ---------------------------------------------------------------------------
# remediation field in packets
# ---------------------------------------------------------------------------


def test_regression_packet_has_remediation(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    path = create_regression_task(
        url="https://example.com",
        diff_pct=5.0,
        changed_pixels=900,
        total_pixels=18000,
        diff_image_path=None,
        config=cfg,
    )
    assert path is not None
    data = json.loads(Path(path).read_text())
    assert "remediation" in data
    assert isinstance(data["remediation"], str)
    assert len(data["remediation"]) > 0


def test_check_failure_packet_has_remediation(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    path = create_check_failure_task(
        check_id="cors",
        check_type="header",
        target="https://api.example.com",
        failed_assertions=[{"name": "expect_header", "expected": "access-control-allow-origin", "actual": "absent"}],
        error=None,
        config=cfg,
    )
    assert path is not None
    data = json.loads(Path(path).read_text())
    assert "remediation" in data
    assert "header" in data["remediation"].lower()
