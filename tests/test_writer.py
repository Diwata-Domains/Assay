"""Unit tests for the packet file writer."""

from __future__ import annotations

import json
from pathlib import Path

from assay.formatter.writer import write_packet

_SAMPLE_PACKET: dict[str, object] = {
    "verification_id": "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
    "task_id": None,
    "issue_type": "test_failure",
    "severity": "info",
    "outcome": "pass",
    "summary": "pass: https://example.com",
    "artifact_refs": [],
    "followup_candidates": [],
    "verified_at": "2026-04-16T10:00:00Z",
}


def test_file_created(tmp_path: Path) -> None:
    path = write_packet(_SAMPLE_PACKET, str(tmp_path))
    assert path.exists()


def test_returns_path_inside_output_dir(tmp_path: Path) -> None:
    path = write_packet(_SAMPLE_PACKET, str(tmp_path))
    assert path.parent == tmp_path


def test_filename_contains_verification_id(tmp_path: Path) -> None:
    path = write_packet(_SAMPLE_PACKET, str(tmp_path))
    assert "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee" in path.name


def test_filename_starts_with_assay(tmp_path: Path) -> None:
    path = write_packet(_SAMPLE_PACKET, str(tmp_path))
    assert path.name.startswith("assay-")


def test_filename_ends_with_json(tmp_path: Path) -> None:
    path = write_packet(_SAMPLE_PACKET, str(tmp_path))
    assert path.suffix == ".json"


def test_file_contains_valid_json(tmp_path: Path) -> None:
    path = write_packet(_SAMPLE_PACKET, str(tmp_path))
    data = json.loads(path.read_text())
    assert data["outcome"] == "pass"
    assert data["verification_id"] == "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"


def test_output_dir_created_if_missing(tmp_path: Path) -> None:
    nested = tmp_path / "a" / "b" / "c"
    assert not nested.exists()
    write_packet(_SAMPLE_PACKET, str(nested))
    assert nested.exists()


def test_full_packet_round_trips(tmp_path: Path) -> None:
    path = write_packet(_SAMPLE_PACKET, str(tmp_path))
    data = json.loads(path.read_text())
    assert data == _SAMPLE_PACKET
