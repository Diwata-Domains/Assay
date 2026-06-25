"""JWT issuance and verification."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import jwt

from .config import WardenConfig
from .exceptions import TokenExpired, TokenInvalid


def issue_token(subject: str, config: WardenConfig, extra: dict[str, Any] | None = None) -> str:
    """Issue a signed JWT for the given subject.

    Args:
        subject: Identity being authenticated (e.g. email address or user ID).
        config: WardenConfig with signing secret and TTL.
        extra: Optional additional claims to include in the payload.

    Returns:
        Signed JWT string.
    """
    now = datetime.now(tz=UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": now.timestamp() + config.ttl_seconds,
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, config.secret, algorithm=config.algorithm)


def verify_token(token: str, config: WardenConfig) -> dict[str, Any]:
    """Verify and decode a JWT.

    Args:
        token: JWT string to verify.
        config: WardenConfig with signing secret.

    Returns:
        Decoded payload dict.

    Raises:
        TokenExpired: Token has passed its expiry time.
        TokenInvalid: Token signature is invalid or malformed.
    """
    try:
        return jwt.decode(token, config.secret, algorithms=[config.algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise TokenExpired("token has expired") from exc
    except jwt.PyJWTError as exc:
        raise TokenInvalid(f"invalid token: {exc}") from exc


def decode_token_unverified(token: str) -> dict[str, Any]:
    """Decode a JWT without verifying the signature.

    Use only for inspecting claims on trusted internal tokens (e.g. logging).
    Never use for access control decisions.
    """
    return jwt.decode(token, options={"verify_signature": False})
