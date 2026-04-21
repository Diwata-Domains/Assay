"""Unit tests for the API key store."""

from __future__ import annotations

from pathlib import Path

import pytest

from assay.keys.store import KeyStoreError, create_key, list_keys, revoke_key, verify_key


def _store(tmp_path: Path) -> str:
    return str(tmp_path / "keys.json")


def test_create_key_returns_raw_string(tmp_path: Path) -> None:
    raw = create_key(_store(tmp_path))
    assert isinstance(raw, str)
    assert len(raw) >= 32


def test_create_key_writes_store_file(tmp_path: Path) -> None:
    create_key(_store(tmp_path))
    assert (tmp_path / "keys.json").exists()


def test_create_key_with_label(tmp_path: Path) -> None:
    create_key(_store(tmp_path), label="production")
    keys = list_keys(_store(tmp_path))
    assert keys[0]["label"] == "production"


def test_create_multiple_keys(tmp_path: Path) -> None:
    create_key(_store(tmp_path))
    create_key(_store(tmp_path))
    assert len(list_keys(_store(tmp_path))) == 2


def test_list_keys_empty_store(tmp_path: Path) -> None:
    assert list_keys(_store(tmp_path)) == []


def test_list_keys_no_hash_in_output(tmp_path: Path) -> None:
    create_key(_store(tmp_path))
    keys = list_keys(_store(tmp_path))
    assert "hash" not in keys[0]


def test_list_keys_shows_active_status(tmp_path: Path) -> None:
    create_key(_store(tmp_path))
    keys = list_keys(_store(tmp_path))
    assert keys[0]["revoked"] is False


def test_verify_key_valid(tmp_path: Path) -> None:
    raw = create_key(_store(tmp_path))
    assert verify_key(_store(tmp_path), raw) is True


def test_verify_key_invalid(tmp_path: Path) -> None:
    create_key(_store(tmp_path))
    assert verify_key(_store(tmp_path), "wrong-key") is False


def test_verify_key_empty_store(tmp_path: Path) -> None:
    assert verify_key(_store(tmp_path), "any-key") is False


def test_revoke_key(tmp_path: Path) -> None:
    create_key(_store(tmp_path))
    key_id = list_keys(_store(tmp_path))[0]["id"]
    revoke_key(_store(tmp_path), str(key_id))
    keys = list_keys(_store(tmp_path))
    assert keys[0]["revoked"] is True
    assert keys[0]["revoked_at"] is not None


def test_revoked_key_fails_verify(tmp_path: Path) -> None:
    raw = create_key(_store(tmp_path))
    key_id = list_keys(_store(tmp_path))[0]["id"]
    revoke_key(_store(tmp_path), str(key_id))
    assert verify_key(_store(tmp_path), raw) is False


def test_revoke_unknown_key_raises(tmp_path: Path) -> None:
    with pytest.raises(KeyStoreError, match="not found"):
        revoke_key(_store(tmp_path), "nonexistent-id")


def test_revoke_already_revoked_raises(tmp_path: Path) -> None:
    create_key(_store(tmp_path))
    key_id = list_keys(_store(tmp_path))[0]["id"]
    revoke_key(_store(tmp_path), str(key_id))
    with pytest.raises(KeyStoreError, match="already revoked"):
        revoke_key(_store(tmp_path), str(key_id))


def test_store_created_in_nested_dir(tmp_path: Path) -> None:
    store = str(tmp_path / "a" / "b" / "keys.json")
    create_key(store)
    assert Path(store).exists()
