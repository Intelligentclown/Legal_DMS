"""Tests for T50's `AuthService` -- login, token issuance, refresh
rotation, and revocation. Uses `InMemoryUserRepository`/
`InMemoryRefreshTokenRepository` (tests/support/), not a real database --
`AuthService` itself has no SQLAlchemy/session dependency, only the two
repository ports, so it's fully unit-testable this way. T49's own
integration tests already cover the real `SqlAlchemyRepository`-backed
persistence path for `RefreshToken`.

Covers T51's named acceptance scenarios (correct credentials, wrong
password, unknown email, inactive user, expired/invalid/already-revoked
refresh token, refresh rotation) in the same batch as T50's implementation
-- see this batch's Design Decisions note in
docs/ImplementationLog/Stage3/Phase1.md for why.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.application.auth_service import AuthService
from app.application.errors import UnauthorizedError
from app.infrastructure.config.settings import Settings
from app.infrastructure.persistence.models.identity import RefreshToken, User
from app.infrastructure.security.jwt_service import create_refresh_token, decode_token
from app.infrastructure.security.password_hasher import hash_password
from app.infrastructure.security.token_hasher import hash_token
from tests.support.in_memory_refresh_token_repository import InMemoryRefreshTokenRepository
from tests.support.in_memory_user_repository import InMemoryUserRepository

_PASSWORD = "correct horse battery staple"


@pytest.fixture
def settings() -> Settings:
    return Settings(_env_file=None, jwt_secret_key="test-secret", refresh_token_ttl_days=14)


@pytest.fixture
def user_repository() -> InMemoryUserRepository:
    return InMemoryUserRepository()


@pytest.fixture
def refresh_token_repository() -> InMemoryRefreshTokenRepository:
    return InMemoryRefreshTokenRepository()


@pytest.fixture
def auth_service(
    user_repository: InMemoryUserRepository,
    refresh_token_repository: InMemoryRefreshTokenRepository,
    settings: Settings,
) -> AuthService:
    return AuthService(user_repository, refresh_token_repository, settings)


def _make_user(*, is_active: bool = True, password: str | None = _PASSWORD) -> User:
    return User(
        id=uuid4(),
        email="advocate@example.com",
        full_name="Test Advocate",
        password_hash=hash_password(password) if password is not None else None,
        is_active=is_active,
    )


class TestAuthenticate:
    async def test_correct_credentials_returns_the_user(
        self, auth_service: AuthService, user_repository: InMemoryUserRepository
    ) -> None:
        user = _make_user()
        await user_repository.add(user)

        result = await auth_service.authenticate("advocate@example.com", _PASSWORD)

        assert result.is_success
        assert result.value.id == user.id

    async def test_wrong_password_fails(
        self, auth_service: AuthService, user_repository: InMemoryUserRepository
    ) -> None:
        await user_repository.add(_make_user())

        result = await auth_service.authenticate("advocate@example.com", "wrong password")

        assert result.is_failure
        assert isinstance(result.error, UnauthorizedError)

    async def test_unknown_email_fails(self, auth_service: AuthService) -> None:
        result = await auth_service.authenticate("nobody@example.com", _PASSWORD)

        assert result.is_failure
        assert isinstance(result.error, UnauthorizedError)

    async def test_inactive_user_fails(
        self, auth_service: AuthService, user_repository: InMemoryUserRepository
    ) -> None:
        await user_repository.add(_make_user(is_active=False))

        result = await auth_service.authenticate("advocate@example.com", _PASSWORD)

        assert result.is_failure
        assert isinstance(result.error, UnauthorizedError)

    async def test_user_with_no_password_hash_fails_rather_than_raising(
        self, auth_service: AuthService, user_repository: InMemoryUserRepository
    ) -> None:
        await user_repository.add(_make_user(password=None))

        result = await auth_service.authenticate("advocate@example.com", _PASSWORD)

        assert result.is_failure
        assert isinstance(result.error, UnauthorizedError)

    async def test_wrong_password_and_unknown_email_return_the_same_message(
        self, auth_service: AuthService, user_repository: InMemoryUserRepository
    ) -> None:
        """Neither error should let a caller distinguish "this email exists"
        from "this email doesn't" by response content."""
        await user_repository.add(_make_user())

        wrong_password = await auth_service.authenticate("advocate@example.com", "wrong password")
        unknown_email = await auth_service.authenticate("nobody@example.com", _PASSWORD)

        assert wrong_password.error.message == unknown_email.error.message

    async def test_success_records_last_login_at(
        self, auth_service: AuthService, user_repository: InMemoryUserRepository
    ) -> None:
        user = _make_user()
        await user_repository.add(user)
        assert user.last_login_at is None

        result = await auth_service.authenticate("advocate@example.com", _PASSWORD)

        assert result.is_success
        assert result.value.last_login_at is not None


class TestIssueTokens:
    async def test_returns_an_access_and_a_refresh_token(
        self, auth_service: AuthService, settings: Settings
    ) -> None:
        access_token, refresh_token = await auth_service.issue_tokens(_make_user())

        assert decode_token(access_token, settings) is not None
        assert decode_token(refresh_token, settings) is not None
        assert access_token != refresh_token

    async def test_persists_a_refresh_token_row(
        self,
        auth_service: AuthService,
        refresh_token_repository: InMemoryRefreshTokenRepository,
    ) -> None:
        user = _make_user()

        _, refresh_token = await auth_service.issue_tokens(user)

        stored = await refresh_token_repository.get_by_token_hash(hash_token(refresh_token))
        assert stored is not None
        assert stored.user_id == user.id
        assert stored.revoked_at is None

    async def test_access_token_carries_the_users_role_names(
        self,
        auth_service: AuthService,
        user_repository: InMemoryUserRepository,
        settings: Settings,
    ) -> None:
        user = _make_user()
        user_repository.set_role_names(user.id, frozenset({"Administrator"}))

        access_token, _ = await auth_service.issue_tokens(user)

        claims = decode_token(access_token, settings)
        assert claims is not None
        assert claims["roles"] == ["Administrator"]


class TestRefresh:
    async def test_valid_refresh_token_returns_a_new_token_pair(
        self, auth_service: AuthService, user_repository: InMemoryUserRepository
    ) -> None:
        user = _make_user()
        await user_repository.add(user)
        _, refresh_token = await auth_service.issue_tokens(user)

        result = await auth_service.refresh(refresh_token)

        assert result.is_success
        _new_access, new_refresh = result.value
        assert new_refresh != refresh_token

    async def test_rotation_revokes_the_presented_token(
        self,
        auth_service: AuthService,
        user_repository: InMemoryUserRepository,
        refresh_token_repository: InMemoryRefreshTokenRepository,
    ) -> None:
        user = _make_user()
        await user_repository.add(user)
        _, refresh_token = await auth_service.issue_tokens(user)

        await auth_service.refresh(refresh_token)

        stored = await refresh_token_repository.get_by_token_hash(hash_token(refresh_token))
        assert stored is not None
        assert stored.revoked_at is not None

    async def test_rotated_token_cannot_be_reused(
        self, auth_service: AuthService, user_repository: InMemoryUserRepository
    ) -> None:
        user = _make_user()
        await user_repository.add(user)
        _, refresh_token = await auth_service.issue_tokens(user)

        first_use = await auth_service.refresh(refresh_token)
        second_use = await auth_service.refresh(refresh_token)

        assert first_use.is_success
        assert second_use.is_failure
        assert isinstance(second_use.error, UnauthorizedError)

    async def test_invalid_token_fails(self, auth_service: AuthService) -> None:
        result = await auth_service.refresh("not-a-real-token")

        assert result.is_failure
        assert isinstance(result.error, UnauthorizedError)

    async def test_expired_jwt_fails(self, auth_service: AuthService, settings: Settings) -> None:
        expired_settings = Settings(
            _env_file=None, jwt_secret_key=settings.jwt_secret_key, refresh_token_ttl_days=-1
        )
        expired_token = create_refresh_token("some-user-id", expired_settings)

        result = await auth_service.refresh(expired_token)

        assert result.is_failure
        assert isinstance(result.error, UnauthorizedError)

    async def test_jwt_valid_but_db_row_expired_fails(
        self,
        auth_service: AuthService,
        user_repository: InMemoryUserRepository,
        refresh_token_repository: InMemoryRefreshTokenRepository,
        settings: Settings,
    ) -> None:
        """Defense in depth: even if a refresh token's own `exp` claim
        hasn't elapsed yet, an `expires_at` in the past on its stored row
        must still reject it."""
        user = _make_user()
        await user_repository.add(user)
        refresh_token = create_refresh_token(str(user.id), settings)
        await refresh_token_repository.add(
            RefreshToken(
                id=uuid4(),
                user_id=user.id,
                token_hash=hash_token(refresh_token),
                issued_at=datetime.now(UTC) - timedelta(days=30),
                expires_at=datetime.now(UTC) - timedelta(days=1),
            )
        )

        result = await auth_service.refresh(refresh_token)

        assert result.is_failure
        assert isinstance(result.error, UnauthorizedError)

    async def test_unknown_token_fails(self, auth_service: AuthService, settings: Settings) -> None:
        """A syntactically valid, correctly-signed refresh token that was
        never actually issued by this service (no matching stored row)."""
        never_issued = create_refresh_token(str(uuid4()), settings)

        result = await auth_service.refresh(never_issued)

        assert result.is_failure
        assert isinstance(result.error, UnauthorizedError)

    async def test_already_revoked_token_fails(
        self, auth_service: AuthService, user_repository: InMemoryUserRepository
    ) -> None:
        user = _make_user()
        await user_repository.add(user)
        _, refresh_token = await auth_service.issue_tokens(user)
        await auth_service.revoke(refresh_token)

        result = await auth_service.refresh(refresh_token)

        assert result.is_failure
        assert isinstance(result.error, UnauthorizedError)

    async def test_inactive_user_at_refresh_time_fails(
        self, auth_service: AuthService, user_repository: InMemoryUserRepository
    ) -> None:
        user = _make_user()
        await user_repository.add(user)
        _, refresh_token = await auth_service.issue_tokens(user)

        user.is_active = False
        await user_repository.update(user)

        result = await auth_service.refresh(refresh_token)

        assert result.is_failure
        assert isinstance(result.error, UnauthorizedError)

    async def test_new_access_token_reflects_current_roles_not_stale_ones(
        self,
        auth_service: AuthService,
        user_repository: InMemoryUserRepository,
        settings: Settings,
    ) -> None:
        user = _make_user()
        await user_repository.add(user)
        user_repository.set_role_names(user.id, frozenset({"Clerk"}))
        _, refresh_token = await auth_service.issue_tokens(user)

        user_repository.set_role_names(user.id, frozenset({"Administrator"}))
        result = await auth_service.refresh(refresh_token)

        assert result.is_success
        new_access, _ = result.value
        claims = decode_token(new_access, settings)
        assert claims is not None
        assert claims["roles"] == ["Administrator"]


class TestRevoke:
    async def test_revokes_a_valid_token(
        self,
        auth_service: AuthService,
        user_repository: InMemoryUserRepository,
        refresh_token_repository: InMemoryRefreshTokenRepository,
    ) -> None:
        user = _make_user()
        await user_repository.add(user)
        _, refresh_token = await auth_service.issue_tokens(user)

        await auth_service.revoke(refresh_token)

        stored = await refresh_token_repository.get_by_token_hash(hash_token(refresh_token))
        assert stored is not None
        assert stored.revoked_at is not None

    async def test_revoked_token_can_no_longer_refresh(
        self, auth_service: AuthService, user_repository: InMemoryUserRepository
    ) -> None:
        user = _make_user()
        await user_repository.add(user)
        _, refresh_token = await auth_service.issue_tokens(user)

        await auth_service.revoke(refresh_token)
        result = await auth_service.refresh(refresh_token)

        assert result.is_failure

    async def test_revoking_an_unknown_token_does_not_raise(
        self, auth_service: AuthService
    ) -> None:
        await auth_service.revoke("not-a-real-token")  # does not raise

    async def test_revoking_an_already_revoked_token_is_idempotent(
        self, auth_service: AuthService, user_repository: InMemoryUserRepository
    ) -> None:
        user = _make_user()
        await user_repository.add(user)
        _, refresh_token = await auth_service.issue_tokens(user)

        await auth_service.revoke(refresh_token)
        await auth_service.revoke(refresh_token)  # does not raise, second call is a no-op
