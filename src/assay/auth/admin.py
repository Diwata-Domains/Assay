from __future__ import annotations

import os
import warnings
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

_TOKEN_EXPIRY_HOURS = 24 * 7


def get_admin_email() -> str:
    val = os.environ.get("ASSAY_ADMIN_EMAIL", "").strip()
    if not val:
        raise RuntimeError("ASSAY_ADMIN_EMAIL env var is not set")
    return val


def get_admin_password_hash() -> str:
    val = os.environ.get("ASSAY_ADMIN_PASSWORD_HASH", "").strip()
    if not val:
        raise RuntimeError("ASSAY_ADMIN_PASSWORD_HASH env var is not set")
    return val


def get_jwt_secret() -> str:
    val = os.environ.get("ASSAY_JWT_SECRET", "").strip()
    if not val:
        raise RuntimeError("ASSAY_JWT_SECRET env var is not set")
    if len(val) < 32:
        warnings.warn(
            "ASSAY_JWT_SECRET is shorter than 32 characters — use a longer secret in production",
            stacklevel=2,
        )
    return val


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bool(bcrypt.checkpw(plain.encode(), hashed.encode()))


def create_token(email: str) -> str:
    secret = get_jwt_secret()
    payload: dict[str, Any] = {
        "sub": email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=_TOKEN_EXPIRY_HOURS),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def verify_token(token: str) -> str:
    """Verify JWT and return the email (sub). Raises jwt.InvalidTokenError on failure."""
    secret = get_jwt_secret()
    payload = jwt.decode(token, secret, algorithms=["HS256"])
    sub = payload.get("sub", "")
    if not isinstance(sub, str) or not sub:
        raise jwt.InvalidTokenError("missing sub claim")
    return sub
