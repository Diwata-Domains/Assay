"""Packet file writer — serialises a Grain Sentinel payload dict to disk."""

from __future__ import annotations

import json
from pathlib import Path


def write_packet(packet: dict[str, object], output_dir: str) -> Path:
    """Write a Grain Sentinel payload dict to a JSON file in output_dir.

    The filename is derived from the packet's verified_at and verification_id
    fields so it is both human-sortable and globally unique.

    Args:
        packet: Grain Sentinel payload dict from format_packet().
        output_dir: Directory to write into. Created if it does not exist.

    Returns:
        Path of the written file.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    verified_at = str(packet.get("verified_at", ""))
    verification_id = str(packet.get("verification_id", ""))

    # Make verified_at filename-safe: drop colons and dots
    ts_safe = verified_at.replace(":", "").replace(".", "").replace("-", "")

    filename = f"assay-{ts_safe}-{verification_id}.json"
    path = out / filename
    path.write_text(json.dumps(packet))
    return path
