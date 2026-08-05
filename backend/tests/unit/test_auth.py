"""Tests for the auth/authorization framework: CurrentUser,
AnonymousAuthenticationProvider, PermissiveAuthorizationService, and the
CurrentUserDep FastAPI dependency.
"""

from __future__ import annotations

import pytest

from app.application.errors.exceptions import ForbiddenError
from app.application.interfaces.auth import (
    AuthenticationProvider,
    AuthorizationService,
    CurrentUser,
)
from app.infrastructure.auth.anonymous_auth_provider import AnonymousAuthenticationProvider
from app.infrastructure.auth.permissive_authorization_service import PermissiveAuthorizationService
from app.infrastructure.di.container import configure_container, container
from app.presentation.api.deps import get_current_user


class TestCurrentUser:
    def test_default_is_anonymous(self) -> None:
        user = CurrentUser()

        assert user.is_authenticated is False
        assert user.display_name == "Anonymous"
        assert user.roles == frozenset()


class TestAnonymousAuthenticationProvider:
    async def test_returns_an_anonymous_current_user(self) -> None:
        provider = AnonymousAuthenticationProvider()

        user = await provider.get_current_user()

        assert user.is_authenticated is False


class TestPermissiveAuthorizationService:
    def test_denies_anonymous_users(self) -> None:
        service = PermissiveAuthorizationService()

        with pytest.raises(ForbiddenError, match="Authentication is required"):
            service.require_permission(CurrentUser(), "matters:read")

    def test_allows_authenticated_users(self) -> None:
        service = PermissiveAuthorizationService()
        user = CurrentUser(id="u1", is_authenticated=True)

        service.require_permission(user, "matters:read")  # does not raise


class TestGetCurrentUserDependency:
    async def test_resolves_to_anonymous_via_the_configured_provider(self) -> None:
        user = await get_current_user(AnonymousAuthenticationProvider())

        assert user.is_authenticated is False


class TestConfigureContainer:
    def test_registers_auth_ports_with_stage_one_defaults(self) -> None:
        configure_container()

        assert isinstance(
            container.resolve(AuthenticationProvider), AnonymousAuthenticationProvider
        )
        assert isinstance(container.resolve(AuthorizationService), PermissiveAuthorizationService)
