# SPDX-FileCopyrightText: 2024-2026 Shaznay Sison
# SPDX-License-Identifier: AGPL-3.0-only

"""Roster test — Assay's payload schema enums equal the shared crossing vocabulary.

CP-006 §6: `issue_type` / `severity` / `outcome` are defined once in
`grain_contracts.verification`. This pins Assay's JSON Schema `enum` lists to those members so
the two sides can never drift into duplicated literals. Grain carries the mirror-image test.
"""

from __future__ import annotations

from grain_contracts.verification import IssueType, Outcome, Priority, Severity, State

from assay.schemas import ASSAY_PAYLOAD


def _schema_enum(*path: str) -> set[str]:
    node = ASSAY_PAYLOAD
    for key in path:
        node = node[key]
    return set(node["enum"])


def test_issue_type_enum_matches_contract() -> None:
    assert _schema_enum("properties", "issue_type") == {m.value for m in IssueType}


def test_severity_enum_matches_contract() -> None:
    assert _schema_enum("properties", "severity") == {m.value for m in Severity}


def test_outcome_enum_matches_contract() -> None:
    assert _schema_enum("properties", "outcome") == {m.value for m in Outcome}


def test_review_block_reuses_the_shared_severity_and_outcome() -> None:
    props = ASSAY_PAYLOAD["properties"]["review"]["properties"]
    assert set(props["verdict"]["enum"]) == {m.value for m in Outcome}
    finding = props["findings"]["items"]["properties"]
    assert set(finding["severity"]["enum"]) == {m.value for m in Severity}


def test_state_and_priority_are_not_on_the_packet() -> None:
    # CP-006: ticket lifecycle `state` and operator `priority` live on the ticket, never on the
    # verification packet. The packet keeps `outcome`. State/Priority exist as shared vocab even
    # though the payload schema does not carry them.
    packet_props = set(ASSAY_PAYLOAD["properties"])
    assert "state" not in packet_props
    assert "priority" not in packet_props
    assert "outcome" in packet_props
    assert "source_ticket_id" in packet_props
    assert {s.value for s in State}
    assert {p.value for p in Priority}
