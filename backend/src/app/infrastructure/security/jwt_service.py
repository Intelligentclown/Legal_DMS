"""JWT encode/decode utility (D3/ADR-0018): PyJWT. Plain functions, not a
port -- no caller needs to swap the JWT library behind an interface, and
`jwt` is fully encapsulated here (only this module imports it). Reads
`Settings.jwt_secret_key`/`jwt_algorithm`/TTLs -- never hardcoded.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from app.infrastructure.config.settings import Settings


def create_access_token(user_id: str, roles: Iterable[str], settings: Settings) -> str:
    now = datetime.now(UTC)
    claims = {
        "sub": user_id,
        "roles": list(roles),
        "exp": now + timedelta(minutes=settings.access_token_ttl_minutes),
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(claims, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: str, settings: Settings) -> str:
    now = datetime.now(UTC)
    claims = {
        "sub": user_id,
        "exp": now + timedelta(days=settings.refresh_token_ttl_days),
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(claims, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str, settings: Settings) -> dict[str, Any] | None:
    """Returns the decoded claims, or `None` if the token is missing,
    malformed, expired, or its signature doesn't match -- a caller only ever
    needs to know "is this token currently valid," not which specific way it
    failed.
    """
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        return None
