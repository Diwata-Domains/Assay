"""API key store — create, list, revoke, and verify keys with bcrypt hashing."""

from __future__ import annotations

import json
import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import bcrypt


class KeyStoreError(Exception):
    """Raised when the key store is unreadable, malformed, or a key is not found."""


def _now() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"version": "1", "keys": []}
    try:
        data: dict[str, object] = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        raise KeyStoreError(f"failed to read key store {path}: {exc}") from exc
    return data


def _save(path: Path, data: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def create_key(store_path: str, label: Optional[str] = None) -> str:  # noqa: UP007
    """Generate a new API key, store its bcrypt hash, return the raw key.

    The raw key is returned exactly once and never stored.
    """
    path = Path(store_path).expanduser()
    data = _load(path)
    keys: list[dict[str, object]] = list(data.get("keys", []))  # type: ignore[arg-type]

    raw = secrets.token_urlsafe(32)
    hashed = bcrypt.hashpw(raw.encode(), bcrypt.gensalt()).decode()
    key_id = str(uuid.uuid4())

    keys.append(
        {
            "id": key_id,
            "label": label or key_id,
            "hash": hashed,
            "created_at": _now(),
            "revoked": False,
            "revoked_at": None,
        }
    )
    data["keys"] = keys
    _save(path, data)
    return raw


def list_keys(store_path: str) -> list[dict[str, object]]:
    """Return all key entries (id, label, created_at, revoked) — no hashes."""
    path = Path(store_path).expanduser()
    data = _load(path)
    keys: list[dict[str, object]] = list(data.get("keys", []))  # type: ignore[arg-type]
    return [
        {
            "id": k["id"],
            "label": k["label"],
            "created_at": k["created_at"],
            "revoked": k["revoked"],
            "revoked_at": k["revoked_at"],
        }
        for k in keys
    ]


def revoke_key(store_path: str, key_id: str) -> None:
    """Mark a key as revoked. Raises KeyStoreError if the ID is not found."""
    path = Path(store_path).expanduser()
    data = _load(path)
    keys: list[dict[str, object]] = list(data.get("keys", []))  # type: ignore[arg-type]

    for key in keys:
        if key["id"] == key_id:
            if key["revoked"]:
                raise KeyStoreError(f"key {key_id} is already revoked")
            key["revoked"] = True
            key["revoked_at"] = _now()
            data["keys"] = keys
            _save(path, data)
            return

    raise KeyStoreError(f"key {key_id} not found")


def verify_key(store_path: str, raw: str) -> bool:
    """Return True if raw matches any active (non-revoked) key hash."""
    path = Path(store_path).expanduser()
    data = _load(path)
    keys: list[dict[str, object]] = list(data.get("keys", []))  # type: ignore[arg-type]

    for key in keys:
        if key.get("revoked"):
            continue
        stored_hash = str(key.get("hash", ""))
        if stored_hash and bcrypt.checkpw(raw.encode(), stored_hash.encode()):
            return True
    return False
