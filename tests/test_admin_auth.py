import pytest

from assay.auth.admin import (
    get_admin_email,
    get_admin_password_hash,
    hash_password,
    verify_password,
)


def test_hash_and_verify_password() -> None:
    h = hash_password("correcthorse")
    assert verify_password("correcthorse", h)
    assert not verify_password("wrong", h)


def test_get_admin_email(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASSAY_ADMIN_EMAIL", "admin@example.com")
    assert get_admin_email() == "admin@example.com"


def test_get_admin_email_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ASSAY_ADMIN_EMAIL", raising=False)
    with pytest.raises(RuntimeError, match="ASSAY_ADMIN_EMAIL"):
        get_admin_email()


def test_get_admin_password_hash(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASSAY_ADMIN_PASSWORD_HASH", "$2b$12$fakehash")
    assert get_admin_password_hash() == "$2b$12$fakehash"


def test_get_admin_password_hash_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ASSAY_ADMIN_PASSWORD_HASH", raising=False)
    with pytest.raises(RuntimeError, match="ASSAY_ADMIN_PASSWORD_HASH"):
        get_admin_password_hash()
