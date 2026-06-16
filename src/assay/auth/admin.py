# SPDX-FileCopyrightText: 2024-2026 Shaznay Sison
# SPDX-License-Identifier: AGPL-3.0-only

from __future__ import annotations

import os

import bcrypt


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


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bool(bcrypt.checkpw(plain.encode(), hashed.encode()))
