import warnings

import jwt
import pytest

from assay.auth.admin import (
    create_token,
    get_admin_email,
    get_admin_password_hash,
    get_jwt_secret,
    hash_password,
    verify_password,
    verify_token,
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


def test_get_jwt_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASSAY_JWT_SECRET", "a" * 32)
    assert get_jwt_secret() == "a" * 32


def test_get_jwt_secret_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ASSAY_JWT_SECRET", raising=False)
    with pytest.raises(RuntimeError, match="ASSAY_JWT_SECRET"):
        get_jwt_secret()


def test_jwt_secret_short_warns(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASSAY_JWT_SECRET", "tooshort")
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        get_jwt_secret()
    assert any("shorter than 32" in str(x.message) for x in w)


def test_create_and_verify_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASSAY_JWT_SECRET", "a" * 32)
    token = create_token("admin@example.com")
    assert verify_token(token) == "admin@example.com"


def test_verify_token_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASSAY_JWT_SECRET", "a" * 32)
    with pytest.raises(jwt.InvalidTokenError):
        verify_token("not.a.valid.token")


def test_verify_token_wrong_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASSAY_JWT_SECRET", "a" * 32)
    token = create_token("admin@example.com")
    monkeypatch.setenv("ASSAY_JWT_SECRET", "b" * 32)
    with pytest.raises(jwt.InvalidTokenError):
        verify_token(token)
