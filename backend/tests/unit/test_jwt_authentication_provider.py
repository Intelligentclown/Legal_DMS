"""Tests for T52's `JwtAuthenticationProvider` (D7/ADR-0019)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.application.interfaces.auth import CurrentUser
from app.infrastructure.auth.jwt_authentication_provider import JwtAuthenticationProvider
from app.infrastructure.config.settings import Settings
from app.infrastructure.persistence.models.identity import User
from app.infrastructure.security.jwt_service import create_access_token
from tests.support.in_memory_user_repository import InMemoryUserRepository


@pytest.fixture
def settings() -> Settings:
    return Settings(_env_file=None, jwt_secret_key="test-secret")


@pytest.fixture
def user_repository() -> InMemoryUserRepository:
    return InMemoryUserRepository()


@pytest.fixture
def provider(
    user_repository: InMemoryUserRepository, settings: Settings
) -> JwtAuthenticationProvider:
    return JwtAuthenticationProvider(user_repository, settings)


def _make_user(*, is_active: bool = True) -> User:
    return User(
        id=uuid4(),
        email=f"{uuid4()}@example.com",
        full_name="Test Advocate",
        is_active=is_active,
    )


class TestNoOrInvalidToken:
    async def test_none_token_returns_anonymous(self, provider: JwtAuthenticationProvider) -> None:
        result = await provider.get_current_user(None)

        assert result == CurrentUser()

    async def test_malformed_token_returns_anonymous(
        self, provider: JwtAuthenticationProvider
    ) -> None:
        result = await provider.get_current_user("not-a-real-token")

        assert result == CurrentUser()

    async def test_expired_token_returns_anonymous(
        self,
        provider: JwtAuthenticationProvider,
        user_repository: InMemoryUserRepository,
    ) -> None:
        user = _make_user()
        await user_repository.add(user)
        expired_settings = Settings(
            _env_file=None, jwt_secret_key="test-secret", access_token_ttl_minutes=-1
        )
        token = create_access_token(str(user.id), [], expired_settings)

        result = await provider.get_current_user(token)

        assert result == CurrentUser()

    async def test_tampered_signature_returns_anonymous(
        self,
        provider: JwtAuthenticationProvider,
        user_repository: InMemoryUserRepository,
        settings: Settings,
    ) -> None:
        user = _make_user()
        await user_repository.add(user)
        token = create_access_token(str(user.id), [], settings)
        header, payload, signature = token.split(".")
        flipped_first_char = "A" if signature[0] != "A" else "B"
        tampered = f"{header}.{payload}.{flipped_first_char}{signature[1:]}"

        result = await provider.get_current_user(tampered)

        assert result == CurrentUser()

    async def test_token_signed_with_a_different_secret_returns_anonymous(
        self, provider: JwtAuthenticationProvider
    ) -> None:
        other_settings = Settings(_env_file=None, jwt_secret_key="a-different-secret")
        token = create_access_token(str(uuid4()), [], other_settings)

        result = await provider.get_current_user(token)

        assert result == CurrentUser()

    async def test_malformed_sub_claim_returns_anonymous_rather_than_raising(
        self, provider: JwtAuthenticationProvider, settings: Settings
    ) -> None:
        token = create_access_token("not-a-uuid", [], settings)

        result = await provider.get_current_user(token)

        assert result == CurrentUser()


class TestDatabaseResolution:
    async def test_unknown_user_id_returns_anonymous(
        self, provider: JwtAuthenticationProvider, settings: Settings
    ) -> None:
        token = create_access_token(str(uuid4()), [], settings)

        result = await provider.get_current_user(token)

        assert result == CurrentUser()

    async def test_inactive_user_returns_anonymous(
        self,
        provider: JwtAuthenticationProvider,
        user_repository: InMemoryUserRepository,
        settings: Settings,
    ) -> None:
        user = _make_user(is_active=False)
        await user_repository.add(user)
        token = create_access_token(str(user.id), [], settings)

        result = await provider.get_current_user(token)

        assert result == CurrentUser()

    async def test_valid_token_returns_a_populated_current_user(
        self,
        provider: JwtAuthenticationProvider,
        user_repository: InMemoryUserRepository,
        settings: Settings,
    ) -> None:
        user = _make_user()
        await user_repository.add(user)
        user_repository.set_role_names(user.id, frozenset({"Advocate"}))
        token = create_access_token(str(user.id), ["Advocate"], settings)

        result = await provider.get_current_user(token)

        assert result.is_authenticated is True
        assert result.id == str(user.id)
        assert result.display_name == user.full_name
        assert result.roles == frozenset({"Advocate"})

    async def test_roles_are_re_derived_from_the_database_not_the_token_claims(
        self,
        provider: JwtAuthenticationProvider,
        user_repository: InMemoryUserRepository,
        settings: Settings,
    ) -> None:
        """The token's own `roles` claim (set at issuance) is deliberately
        ignored -- a role change since the token was issued must be
        reflected immediately, not only on the next login/refresh."""
        user = _make_user()
        await user_repository.add(user)
        token = create_access_token(str(user.id), ["Stale Role"], settings)

        user_repository.set_role_names(user.id, frozenset({"Administrator"}))
        result = await provider.get_current_user(token)

        assert result.roles == frozenset({"Administrator"})

    async def test_deactivating_the_user_after_token_issuance_returns_anonymous(
        self,
        provider: JwtAuthenticationProvider,
        user_repository: InMemoryUserRepository,
        settings: Settings,
    ) -> None:
        user = _make_user()
        await user_repository.add(user)
        token = create_access_token(str(user.id), [], settings)

        user.is_active = False
        await user_repository.update(user)
        result = await provider.get_current_user(token)

        assert result == CurrentUser()
