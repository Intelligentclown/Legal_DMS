"""Tests for the auth/authorization framework: CurrentUser,
AnonymousAuthenticationProvider, PermissiveAuthorizationService, and the
CurrentUserDep FastAPI dependency.
"""

from __future__ import annotations

import ast
import inspect

import pytest
from pydantic import ValidationError

from app.application.errors.exceptions import ForbiddenError
from app.application.interfaces import auth as auth_port_module
from app.application.interfaces.auth import (
    AuthenticationProvider,
    AuthorizationService,
    CurrentUser,
)
from app.infrastructure.auth.anonymous_auth_provider import AnonymousAuthenticationProvider
from app.infrastructure.auth.permissive_authorization_service import PermissiveAuthorizationService
from app.infrastructure.config.settings import Settings
from app.infrastructure.di.container import configure_container, container
from app.presentation.api.deps import RequirePermission, get_current_user


class TestCurrentUser:
    def test_default_is_anonymous(self) -> None:
        user = CurrentUser()

        assert user.is_authenticated is False
        assert user.display_name == "Anonymous"
        assert user.roles == frozenset()


class TestAuthenticationProviderSignature:
    """D7/ADR-0019: get_current_user() takes an explicit token parameter.
    These tests exercise the port's contract directly (via a minimal fake),
    independent of any concrete implementation."""

    async def test_a_conforming_implementation_accepts_a_token_argument(self) -> None:
        class _FakeProvider(AuthenticationProvider):
            async def get_current_user(self, token: str | None) -> CurrentUser:
                return CurrentUser(id="from-token") if token else CurrentUser()

        provider = _FakeProvider()

        assert (await provider.get_current_user(None)).id is None
        assert (await provider.get_current_user("some-token")).id == "from-token"


class TestAuthenticationProviderPortHasNoFrameworkImports:
    """T45 requirement: keep framework types (FastAPI Request, Depends,
    etc.) outside the port. A static import check on the port module
    itself, not a runtime behavior test -- catches a future edit that
    accidentally imports FastAPI into application/interfaces/auth.py,
    regardless of whether any test happens to exercise that import path."""

    def test_the_port_module_imports_nothing_from_fastapi(self) -> None:
        source = inspect.getsource(auth_port_module)
        tree = ast.parse(source)

        imported_names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_names.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_names.add(node.module)

        assert not any(name.startswith("fastapi") for name in imported_names), imported_names


class TestAnonymousAuthenticationProvider:
    async def test_returns_an_anonymous_current_user_with_no_token(self) -> None:
        provider = AnonymousAuthenticationProvider()

        user = await provider.get_current_user(None)

        assert user.is_authenticated is False

    async def test_ignores_a_present_token_and_still_returns_anonymous(self) -> None:
        """This stub predates real login (D7/ADR-0019 changed the port's
        shape, not this stub's behavior) -- it must not pretend to validate
        a token it has no way to check."""
        provider = AnonymousAuthenticationProvider()

        user = await provider.get_current_user("some-token-value")

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


class _RecordingAuthorizationService(AuthorizationService):
    """Fake that records every `require_permission()` call, for asserting
    exactly what `RequirePermission()`'s returned dependency forwards."""

    def __init__(self, *, allow: bool) -> None:
        self.allow = allow
        self.calls: list[tuple[CurrentUser, str]] = []

    def require_permission(self, user: CurrentUser, permission: str) -> None:
        self.calls.append((user, permission))
        if not self.allow:
            raise ForbiddenError(f"denied: {permission}")


class TestRequirePermission:
    """T54: the `RequirePermission(...)` FastAPI dependency factory. Its
    returned dependency is called directly here (matching
    `TestGetCurrentUserDependency`'s pattern above), bypassing FastAPI's own
    `Depends()` wiring, since that wiring itself is FastAPI's job to prove
    correct, not this project's.
    """

    async def test_allows_when_the_authorization_service_permits(self) -> None:
        check = RequirePermission("matters:read")
        user = CurrentUser(id="u1", is_authenticated=True)

        await check(user, _RecordingAuthorizationService(allow=True))  # does not raise

    async def test_raises_forbidden_when_the_authorization_service_denies(self) -> None:
        check = RequirePermission("matters:read")
        user = CurrentUser(id="u1", is_authenticated=True)

        with pytest.raises(ForbiddenError):
            await check(user, _RecordingAuthorizationService(allow=False))

    async def test_passes_the_configured_permission_and_user_through_unchanged(self) -> None:
        check = RequirePermission("clients:write")
        user = CurrentUser(id="u1", is_authenticated=True)
        service = _RecordingAuthorizationService(allow=True)

        await check(user, service)

        assert service.calls == [(user, "clients:write")]

    async def test_denies_anonymous_via_a_real_authorization_service(self) -> None:
        check = RequirePermission("matters:read")

        with pytest.raises(ForbiddenError, match="Authentication is required"):
            await check(CurrentUser(), PermissiveAuthorizationService())

    async def test_allows_authenticated_via_a_real_authorization_service(self) -> None:
        check = RequirePermission("matters:read")
        user = CurrentUser(id="u1", is_authenticated=True)

        await check(user, PermissiveAuthorizationService())  # does not raise


class TestConfigureContainer:
    def test_does_not_register_auth_ports(self) -> None:
        """T55: `AuthenticationProvider`/`AuthorizationService` are
        deliberately NOT container-registered — both real implementations
        need a per-request session the container can't supply, so
        `presentation/api/deps.py` constructs them directly from
        `DBSessionDep` instead. This replaces the old assertion that the
        container held the Stage 1 stub defaults, which stopped being true
        once T55 removed those registrations."""
        configure_container()

        assert not container.is_registered(AuthenticationProvider)
        assert not container.is_registered(AuthorizationService)


class TestSettingsAuthConfig:
    """T44: JWT signing/TTL configuration added to Settings. No JWT is
    encoded/decoded anywhere yet -- these tests only prove the config shape
    T47's future token utility will read from."""

    def test_jwt_secret_key_has_no_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # CI sets a job-level JWT_SECRET_KEY env var (.github/workflows/backend.yml) so the rest
        # of the suite can construct Settings() -- _env_file=None only suppresses the .env file
        # source, not the process environment, so that ambient var must be cleared explicitly for
        # this test to actually exercise "no value from any source".
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)

        with pytest.raises(ValidationError, match="jwt_secret_key"):
            Settings(_env_file=None)

    def test_jwt_secret_key_is_accepted_when_provided(self) -> None:
        settings = Settings(_env_file=None, jwt_secret_key="test-secret")

        assert settings.jwt_secret_key == "test-secret"

    def test_algorithm_and_ttl_fields_have_sensible_defaults(self) -> None:
        settings = Settings(_env_file=None, jwt_secret_key="test-secret")

        assert settings.jwt_algorithm == "HS256"
        assert settings.access_token_ttl_minutes == 20
        assert settings.refresh_token_ttl_days == 14

    def test_ttl_fields_are_overridable(self) -> None:
        settings = Settings(
            _env_file=None,
            jwt_secret_key="test-secret",
            access_token_ttl_minutes=30,
            refresh_token_ttl_days=7,
        )

        assert settings.access_token_ttl_minutes == 30
        assert settings.refresh_token_ttl_days == 7
