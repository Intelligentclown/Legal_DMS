"""AuthService (T50, D1/D2/D3/ADR-0018): login, token issuance, refresh
rotation, and revocation. The first consumer of `T46`'s password hashing,
`T47`'s JWT utility, and `T49`'s `refresh_tokens` persistence together.

Not a port/interface -- this is application-layer orchestration logic
with exactly one real shape, not a capability a future caller needs to
swap behind an interface (same reasoning `T46`/`T47` already applied to
`hash_password`/`create_access_token`, one level up).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.application.errors import AppError, UnauthorizedError
from app.application.interfaces.refresh_token_repository import RefreshTokenRepository
from app.application.interfaces.user_repository import UserRepository
from app.domain.common.result import Result
from app.infrastructure.config.settings import Settings
from app.infrastructure.persistence.models.identity import RefreshToken, User
from app.infrastructure.security.jwt_service import (
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.infrastructure.security.password_hasher import verify_password
from app.infrastructure.security.token_hasher import hash_token

_INVALID_CREDENTIALS = "Invalid email or password"
_INVALID_REFRESH_TOKEN = "Refresh token is invalid, expired, or has been revoked"


class AuthService:
    def __init__(
        self,
        user_repository: UserRepository,
        refresh_token_repository: RefreshTokenRepository,
        settings: Settings,
    ) -> None:
        self._user_repository = user_repository
        self._refresh_token_repository = refresh_token_repository
        self._settings = settings

    async def authenticate(self, email: str, password: str) -> Result[User, AppError]:
        """Verifies credentials and, on success, records `last_login_at`.
        Never distinguishes "unknown email" from "wrong password" from
        "correct password but inactive account" in the returned error --
        all three collapse to the same message/error code, so a caller
        can't use response differences to enumerate valid emails or
        account states.
        """
        user = await self._user_repository.get_by_email(email)
        if user is None or user.password_hash is None:
            return Result.fail(UnauthorizedError(_INVALID_CREDENTIALS))
        if not verify_password(password, user.password_hash):
            return Result.fail(UnauthorizedError(_INVALID_CREDENTIALS))
        if not user.is_active:
            return Result.fail(UnauthorizedError(_INVALID_CREDENTIALS))

        user.last_login_at = datetime.now(UTC)
        await self._user_repository.update(user)
        return Result.ok(user)

    async def issue_tokens(self, user: User) -> tuple[str, str]:
        """Issues a fresh access + refresh token pair for `user` and
        persists the refresh token's hash. Roles are re-derived from the
        database on every call, never carried over from a prior token --
        see `refresh()`'s docstring for why that matters."""
        roles = await self._user_repository.get_role_names(user.id)
        access_token = create_access_token(str(user.id), roles, self._settings)
        refresh_token = create_refresh_token(str(user.id), self._settings)

        now = datetime.now(UTC)
        await self._refresh_token_repository.add(
            RefreshToken(
                # Explicit id, not relied-upon-flush-time default: the
                # column's `default=uuid4` only applies when a real
                # SQLAlchemy session flushes this row -- setting it here
                # keeps issue_tokens() correct regardless of which
                # RefreshTokenRepository implementation is behind it
                # (including the in-memory test fake, which never flushes).
                id=uuid4(),
                user_id=user.id,
                token_hash=hash_token(refresh_token),
                issued_at=now,
                expires_at=now + timedelta(days=self._settings.refresh_token_ttl_days),
            )
        )
        return access_token, refresh_token

    async def refresh(self, refresh_token: str) -> Result[tuple[str, str], AppError]:
        """Validates `refresh_token` at both the JWT level (signature,
        expiry) and the database level (not revoked, row still exists,
        owning user still active), then rotates it: the presented token
        is revoked and a brand-new access + refresh pair is issued. A
        caller can never redeem the same refresh token twice. Roles for
        the new access token are re-read from the database, not copied
        from the old one -- a role change mid-session takes effect on the
        next refresh, not just the next login.
        """
        claims = decode_token(refresh_token, self._settings)
        if claims is None:
            return Result.fail(UnauthorizedError(_INVALID_REFRESH_TOKEN))

        stored = await self._refresh_token_repository.get_by_token_hash(hash_token(refresh_token))
        if stored is None or stored.revoked_at is not None:
            return Result.fail(UnauthorizedError(_INVALID_REFRESH_TOKEN))
        if stored.expires_at <= datetime.now(UTC):
            return Result.fail(UnauthorizedError(_INVALID_REFRESH_TOKEN))

        user = await self._user_repository.get_by_id(stored.user_id)
        if user is None or not user.is_active:
            return Result.fail(UnauthorizedError(_INVALID_REFRESH_TOKEN))

        stored.revoked_at = datetime.now(UTC)
        await self._refresh_token_repository.update(stored)

        new_access_token, new_refresh_token = await self.issue_tokens(user)
        return Result.ok((new_access_token, new_refresh_token))

    async def revoke(self, refresh_token: str) -> None:
        """Revokes `refresh_token` (logout). Silently does nothing if the
        token is unknown or already revoked -- logout is idempotent, not
        an error condition to report back to an already-logged-out caller.
        """
        stored = await self._refresh_token_repository.get_by_token_hash(hash_token(refresh_token))
        if stored is not None and stored.revoked_at is None:
            stored.revoked_at = datetime.now(UTC)
            await self._refresh_token_repository.update(stored)
