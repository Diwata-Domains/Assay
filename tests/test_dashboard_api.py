"""Tests: dashboard REST API (/api/*), image serving, and /dashboard SPA mount.

All routes are session-authenticated via the same Warden login as the HTML
dashboard; they are NOT in the middleware's public lists, so an unauthenticated
request must be denied (303 redirect to /login).
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from assay._vendor.warden import WardenConfig, issue_token
from assay.auth.admin import hash_password
from assay.ingest.app import app as ingest_app
from assay.keys.store import create_key
from assay.store.db import init_db, insert_packet, set_baseline

_SECRET = "x" * 32
_EMAIL = "admin@test.com"
_URL = "https://example.com/page"


def _png_bytes(color: tuple[int, int, int] = (10, 20, 30)) -> bytes:
    img = Image.new("RGB", (10, 10), color)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def _setup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("ASSAY_ADMIN_EMAIL", _EMAIL)
    monkeypatch.setenv("ASSAY_ADMIN_PASSWORD_HASH", hash_password("pw"))
    monkeypatch.setenv("WARDEN_SECRET", _SECRET)
    ingest_app.state.key_store = str(tmp_path / "keys.json")
    create_key(ingest_app.state.key_store)
    ingest_app.state.output_dir = str(tmp_path)
    ingest_app.state.store_db = str(tmp_path / "store.db")
    client = TestClient(ingest_app, follow_redirects=False)
    client.cookies.set("warden_session", issue_token(_EMAIL, WardenConfig(secret=_SECRET)))
    return client


def _unauth_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("ASSAY_ADMIN_EMAIL", _EMAIL)
    monkeypatch.setenv("ASSAY_ADMIN_PASSWORD_HASH", hash_password("pw"))
    monkeypatch.setenv("WARDEN_SECRET", _SECRET)
    ingest_app.state.store_db = str(tmp_path / "store.db")
    return TestClient(ingest_app, follow_redirects=False)


def _seed(tmp_path: Path) -> tuple[str, str]:
    """Seed a baseline packet + a candidate packet with a diff. Returns (baseline_vid, candidate_vid)."""
    db = Path(tmp_path) / "store.db"
    init_db(db)

    baseline_png = tmp_path / "base-0001.png"
    baseline_png.write_bytes(_png_bytes((0, 0, 0)))
    baseline: dict[str, object] = {
        "verification_id": "base-0001",
        "task_id": "TASK-0001",
        "issue_type": "test_result",
        "severity": "low",
        "outcome": "pass",
        "summary": "baseline packet",
        "url": _URL,
        "artifact_refs": [str(baseline_png)],
        "followup_candidates": [],
        "verified_at": "2026-05-01T09:00:00Z",
    }
    baseline["raw"] = "{}"
    insert_packet(baseline, db)
    set_baseline("base-0001", db)

    cand_png = tmp_path / "cand-0002.png"
    cand_png.write_bytes(_png_bytes((255, 255, 255)))
    diff_png = tmp_path / "cand-0002_diff.png"
    diff_png.write_bytes(_png_bytes((255, 0, 0)))
    candidate: dict[str, object] = {
        "verification_id": "cand-0002",
        "task_id": "TASK-0002",
        "issue_type": "visual_regression",
        "severity": "high",
        "outcome": "fail",
        "summary": "candidate packet with diff",
        "url": _URL,
        "artifact_refs": [str(cand_png), str(diff_png)],
        "followup_candidates": [],
        "verified_at": "2026-05-01T10:00:00Z",
        "diff_result": {
            "changed_pixels": 100,
            "total_pixels": 100,
            "diff_pct": 100.0,
            "diff_image_path": str(diff_png),
        },
    }
    candidate["raw"] = "{}"
    insert_packet(candidate, db)
    return "base-0001", "cand-0002"


# --------------------------------------------------------------------------- auth


def test_api_packets_requires_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _unauth_client(tmp_path, monkeypatch)
    r = client.get("/api/packets")
    assert r.status_code == 303
    assert r.headers["location"] == "/login"


def test_api_packet_detail_requires_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _unauth_client(tmp_path, monkeypatch)
    r = client.get("/api/packets/cand-0002")
    assert r.status_code == 303


def test_dashboard_requires_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _unauth_client(tmp_path, monkeypatch)
    r = client.get("/dashboard")
    assert r.status_code == 303
    assert r.headers["location"] == "/login"


def test_dashboard_assets_require_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _unauth_client(tmp_path, monkeypatch)
    r = client.get("/dashboard/assets/app.js")
    assert r.status_code == 303


# --------------------------------------------------------------------------- listing


def test_api_packets_lists_with_total(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _setup(tmp_path, monkeypatch)
    _seed(tmp_path)
    r = client.get("/api/packets")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2
    assert body["limit"] == 50
    assert body["offset"] == 0
    vids = {p["verification_id"] for p in body["packets"]}
    assert vids == {"base-0001", "cand-0002"}
    cand = next(p for p in body["packets"] if p["verification_id"] == "cand-0002")
    assert cand["has_diff"] is True
    assert cand["diff_pct"] == 100.0
    assert cand["outcome"] == "fail"


def test_api_packets_paging(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _setup(tmp_path, monkeypatch)
    _seed(tmp_path)
    r = client.get("/api/packets", params={"limit": 1, "offset": 0})
    body = r.json()
    assert body["total"] == 2
    assert len(body["packets"]) == 1
    first = body["packets"][0]["verification_id"]

    r2 = client.get("/api/packets", params={"limit": 1, "offset": 1})
    body2 = r2.json()
    assert len(body2["packets"]) == 1
    assert body2["packets"][0]["verification_id"] != first


def test_api_packets_filter_outcome(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _setup(tmp_path, monkeypatch)
    _seed(tmp_path)
    r = client.get("/api/packets", params={"outcome": "fail"})
    body = r.json()
    assert body["total"] == 1
    assert body["packets"][0]["verification_id"] == "cand-0002"


def test_api_packets_filter_task_id(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _setup(tmp_path, monkeypatch)
    _seed(tmp_path)
    r = client.get("/api/packets", params={"task_id": "TASK-0001"})
    body = r.json()
    assert body["total"] == 1
    assert body["packets"][0]["verification_id"] == "base-0001"


# --------------------------------------------------------------------------- detail


def test_api_packet_detail_shape(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _setup(tmp_path, monkeypatch)
    _seed(tmp_path)
    r = client.get("/api/packets/cand-0002")
    assert r.status_code == 200
    body = r.json()
    assert body["verification_id"] == "cand-0002"
    assert body["task_id"] == "TASK-0002"
    assert body["outcome"] == "fail"
    assert body["severity"] == "high"
    assert body["url"] == _URL
    assert body["has_candidate"] is True
    assert body["has_baseline"] is True
    assert body["has_diff"] is True
    assert isinstance(body["diff_result"], dict)
    assert body["diff_result"]["diff_pct"] == 100.0


def test_api_packet_detail_404(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _setup(tmp_path, monkeypatch)
    _seed(tmp_path)
    r = client.get("/api/packets/nope")
    assert r.status_code == 404


# --------------------------------------------------------------------------- images


def test_api_candidate_png_200(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _setup(tmp_path, monkeypatch)
    _seed(tmp_path)
    r = client.get("/api/packets/cand-0002/candidate.png")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"
    assert r.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_api_baseline_png_200(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _setup(tmp_path, monkeypatch)
    _seed(tmp_path)
    r = client.get("/api/packets/cand-0002/baseline.png")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"


def test_api_diff_png_200(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _setup(tmp_path, monkeypatch)
    _seed(tmp_path)
    r = client.get("/api/packets/cand-0002/diff.png")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"


def test_api_diff_png_404_when_absent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _setup(tmp_path, monkeypatch)
    _seed(tmp_path)
    # baseline packet has no diff_result
    r = client.get("/api/packets/base-0001/diff.png")
    assert r.status_code == 404


def test_api_baseline_png_404_when_no_baseline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _setup(tmp_path, monkeypatch)
    db = Path(tmp_path) / "store.db"
    init_db(db)
    cand_png = tmp_path / "solo-0003.png"
    cand_png.write_bytes(_png_bytes())
    insert_packet(
        {
            "verification_id": "solo-0003",
            "task_id": None,
            "issue_type": "test_result",
            "severity": "low",
            "outcome": "pass",
            "summary": "no baseline url",
            "url": "https://example.com/never-baselined",
            "artifact_refs": [str(cand_png)],
            "followup_candidates": [],
            "verified_at": "2026-05-02T10:00:00Z",
            "raw": "{}",
        },
        db,
    )
    r = client.get("/api/packets/solo-0003/baseline.png")
    assert r.status_code == 404


def test_api_candidate_png_404_when_absent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _setup(tmp_path, monkeypatch)
    db = Path(tmp_path) / "store.db"
    init_db(db)
    insert_packet(
        {
            "verification_id": "noimg-0004",
            "task_id": None,
            "issue_type": "test_result",
            "severity": "low",
            "outcome": "pass",
            "summary": "no image",
            "url": "https://example.com/noimg",
            "artifact_refs": [],
            "followup_candidates": [],
            "verified_at": "2026-05-02T11:00:00Z",
            "raw": "{}",
        },
        db,
    )
    r = client.get("/api/packets/noimg-0004/candidate.png")
    assert r.status_code == 404


# --------------------------------------------------------------------------- review


def test_api_review_set_baseline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _setup(tmp_path, monkeypatch)
    _seed(tmp_path)
    r = client.post("/api/packets/cand-0002/review", json={"action": "set-baseline"})
    assert r.status_code == 200
    assert r.json()["verification_id"] == "cand-0002"
    from assay.store.db import list_baselines

    assert list_baselines(Path(tmp_path) / "store.db")[_URL] == "cand-0002"


def test_api_review_approve(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _setup(tmp_path, monkeypatch)
    _seed(tmp_path)
    r = client.post("/api/packets/cand-0002/review", json={"action": "approve"})
    assert r.status_code == 200
    assert r.json()["review_status"] == "approved"
    from assay.store.db import get_packet, list_baselines

    db = Path(tmp_path) / "store.db"
    assert list_baselines(db)[_URL] == "cand-0002"
    pkt = get_packet("cand-0002", db)
    assert pkt is not None and pkt["review_status"] == "approved"


def test_api_review_reject(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _setup(tmp_path, monkeypatch)
    _seed(tmp_path)
    r = client.post("/api/packets/cand-0002/review", json={"action": "reject"})
    assert r.status_code == 200
    assert r.json()["review_status"] == "rejected"
    from assay.store.db import get_packet, list_baselines

    db = Path(tmp_path) / "store.db"
    # reject must NOT move the baseline
    assert list_baselines(db)[_URL] == "base-0001"
    pkt = get_packet("cand-0002", db)
    assert pkt is not None and pkt["review_status"] == "rejected"


def test_api_review_unknown_action_422(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _setup(tmp_path, monkeypatch)
    _seed(tmp_path)
    r = client.post("/api/packets/cand-0002/review", json={"action": "explode"})
    assert r.status_code == 422


def test_api_review_404_for_missing_packet(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _setup(tmp_path, monkeypatch)
    _seed(tmp_path)
    r = client.post("/api/packets/ghost/review", json={"action": "approve"})
    assert r.status_code == 404


# --------------------------------------------------------------------------- SPA mount


def test_dashboard_serves_index_with_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _setup(tmp_path, monkeypatch)
    r = client.get("/dashboard")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]


def test_dashboard_spa_fallback_serves_index(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _setup(tmp_path, monkeypatch)
    r = client.get("/dashboard/packets/cand-0002")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
