"""Integration tests for T55's request-scoped dependency wiring:
`presentation/api/deps.py`'s `get_authentication_provider()`/
`get_authorization_service()`, against the real migrated schema.

`T52`/`T53` already prove `JwtAuthenticationProvider`/`RbacAuthorizationService`
correct in isolation (fakes/in-memory repositories); `T53`'s own tests
already prove `SqlAlchemyRolePermissionRepository`'s query correct against
real data. What's new and untested until now is the *wiring itself* --
that these two dependency functions actually construct a working service
from a real `AsyncSession`, and specifically that they use *the session
they were given*, not an independent one -- which is the whole reason T55
couldn't just be two `container.register(...)` lines.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.errors.exceptions import ForbiddenError
from app.application.interfaces.auth import CurrentUser
from app.infrastructure.config.settings import Settings
from app.infrastructure.persistence.models.identity import Permission, Role, RolePermission, User
from app.infrastructure.security.jwt_service import create_access_token
from app.presentation.api.deps import get_authentication_provider, get_authorization_service


def _settings() -> Settings:
    return Settings(_env_file=None, jwt_secret_key="test-secret")


async def _make_user(session: AsyncSession, **overrides: object) -> User:
    defaults = {"email": f"{uuid4()}@example.com", "full_name": "Test Advocate"}
    user = User(**{**defaults, **overrides})
    session.add(user)
    await session.flush()
    return user


class TestGetAuthenticationProvider:
    async def test_resolves_a_real_user_through_the_full_chain(
        self, db_session: AsyncSession
    ) -> None:
        settings = _settings()
        user = await _make_user(db_session)
        token = create_access_token(str(user.id), [], settings)

        provider = await get_authentication_provider(db_session, settings)
        current_user = await provider.get_current_user(token)

        assert current_user.is_authenticated is True
        assert current_user.id == str(user.id)
        assert current_user.display_name == user.full_name

    async def test_uses_the_exact_session_it_was_given(self, db_session: AsyncSession) -> None:
        """The user below is only `flush()`ed, never committed -- `db_session`'s
        own fixture rolls back at teardown. If `get_authentication_provider()`
        opened some other/independent session instead of using `db_session`,
        it would not see this uncommitted row, and resolution would fail.
        """
        settings = _settings()
        user = await _make_user(db_session)
        token = create_access_token(str(user.id), [], settings)

        provider = await get_authentication_provider(db_session, settings)
        current_user = await provider.get_current_user(token)

        assert current_user.id == str(user.id)

    async def test_unknown_user_id_resolves_to_anonymous(self, db_session: AsyncSession) -> None:
        settings = _settings()
        token = create_access_token(str(uuid4()), [], settings)

        provider = await get_authentication_provider(db_session, settings)
        current_user = await provider.get_current_user(token)

        assert current_user == CurrentUser()


class TestGetAuthorizationService:
    async def test_reflects_real_role_permissions_data(self, db_session: AsyncSession) -> None:
        role_name = f"Role-{uuid4()}"
        code = f"matters:{uuid4()}"
        role = Role(name=role_name)
        permission = Permission(code=code, category="test")
        db_session.add_all([role, permission])
        await db_session.flush()
        db_session.add(RolePermission(role_id=role.id, permission_id=permission.id))
        await db_session.flush()

        service = await get_authorization_service(db_session)
        user = CurrentUser(id="u1", roles=frozenset({role_name}), is_authenticated=True)

        service.require_permission(user, code)  # does not raise

    async def test_denies_a_permission_not_granted_to_the_users_roles(
        self, db_session: AsyncSession
    ) -> None:
        service = await get_authorization_service(db_session)
        user = CurrentUser(id="u1", roles=frozenset({"Some Role"}), is_authenticated=True)

        with pytest.raises(ForbiddenError):
            service.require_permission(user, "matters:read")

    async def test_uses_the_exact_session_it_was_given(self, db_session: AsyncSession) -> None:
        """Same proof as `TestGetAuthenticationProvider`'s equivalent test --
        this grant is only `flush()`ed, never committed."""
        role_name = f"Role-{uuid4()}"
        code = f"clients:{uuid4()}"
        role = Role(name=role_name)
        permission = Permission(code=code, category="test")
        db_session.add_all([role, permission])
        await db_session.flush()
        db_session.add(RolePermission(role_id=role.id, permission_id=permission.id))
        await db_session.flush()

        service = await get_authorization_service(db_session)
        user = CurrentUser(id="u1", roles=frozenset({role_name}), is_authenticated=True)

        service.require_permission(user, code)  # does not raise -- proves same-session visibility
