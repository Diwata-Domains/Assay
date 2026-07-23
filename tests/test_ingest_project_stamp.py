"""A packet ingested with a project-bound key is stamped with that project_id.

Also proves that, post-CP-007, `project_id` rides on the on-disk packet file and the
file stays schema-valid against the amended `ASSAY_PAYLOAD` schema, and that
report-kind ingests tag the minted ticket with the project.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path

import jsonschema
import pytest
from fastapi.testclient import TestClient

from assay.ingest.app import app
from assay.keys.store import create_key
from assay.schemas import ASSAY_PAYLOAD
from assay.store.db import get_packet, get_ticket, list_packets

_SCREENSHOT = base64.b64encode(b"fake-png-data").decode()


def _payload(kind: str = "report") -> dict[str, object]:
    # `kind` is a real IngestPayload field (default "report"); the packet outcome is derived
    # by format_sdk_packet, not supplied on the payload.
    return {
        "captured_at": "2026-07-23T10:00:00Z",
        "url": "https://crm.example/dashboard",
        "viewport": {"width": 1440, "height": 900},
        "user_agent": "Mozilla/5.0",
        "screenshot": _SCREENSHOT,
        "user_comment": "label truncated",
        "metadata": {},
        "kind": kind,
    }


@pytest.fixture()
def client(tmp_path: Path) -> tuple[TestClient, str, Path, Path]:
    store = str(tmp_path / "keys.json")
    app.state.key_store = store
    app.state.store_db = str(tmp_path / "store.db")
    out = tmp_path / "output"
    app.state.output_dir = str(out)
    return TestClient(app), store, Path(str(tmp_path / "store.db")), out


def test_ingest_stamps_project_id_from_key(
    client: tuple[TestClient, str, Path, Path],
) -> None:
    c, store, db, out = client
    key = create_key(store, label="crm", project_id="proj-crm")
    r = c.post("/ingest", json=_payload(), headers={"X-Assay-Key": key})
    assert r.status_code == 200
    packets = list_packets(db)
    assert packets, "expected one stored packet"
    assert packets[0]["project_id"] == "proj-crm"

    # CP-007 is applied: project_id now rides on the on-disk packet and stays schema-valid.
    on_disk = json.loads(next(Path(out).glob("assay-*.json")).read_text())
    assert on_disk["project_id"] == "proj-crm"
    jsonschema.validate(instance=on_disk, schema=ASSAY_PAYLOAD)


def test_ingest_without_project_key_leaves_project_null(
    client: tuple[TestClient, str, Path, Path],
) -> None:
    c, store, db, _out = client
    key = create_key(store, label="legacy")
    c.post("/ingest", json=_payload(), headers={"X-Assay-Key": key})
    packets = list_packets(db)
    assert packets[0].get("project_id") is None


def test_report_ingest_tags_minted_ticket_with_project(
    client: tuple[TestClient, str, Path, Path],
) -> None:
    c, store, db, _out = client
    key = create_key(store, label="crm", project_id="proj-crm")
    c.post("/ingest", json=_payload(kind="report"), headers={"X-Assay-Key": key})
    verification_id = list_packets(db)[0]["verification_id"]
    # source_ticket_id is written to the `packets` column by set_source_ticket_id, not synced
    # back into the raw JSON blob that list_packets reads — get_packet is column-aware and
    # sees it (mirrors tests/test_tickets.py's assertion pattern).
    packet = get_packet(str(verification_id), db)
    assert packet is not None
    ticket_id = packet.get("source_ticket_id")
    assert ticket_id, "report ingest should mint a durable ticket"
    ticket = get_ticket(str(ticket_id), db)
    assert ticket is not None
    assert ticket["project_id"] == "proj-crm"
