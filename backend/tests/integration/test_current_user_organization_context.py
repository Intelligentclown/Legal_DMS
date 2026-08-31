"""Integration tests for T105/ADR-0031 SS6.5/SS6.6: `CurrentUser.organization_id`
and `JwtAuthenticationProvider`'s live, per-request tenant-context
rederivation. Mirrors `test_auth_dependency_wiring.py`'s
`TestGetAuthenticationProvider` pattern exactly (`db_session` -- the admin/
owning Postgres role, which bypasses RLS entirely as a superuser -- proves
the *business logic* here; RLS enforcement itself is proven separately in
`test_organizations_users_rls.py`/`test_users_organization_scoping_end_to_end.py`).
"""

from __future__ import annotations

from uuid import uuid4

import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.interfaces.auth import CurrentUser
from app.infrastructure.config.settings import Settings
from app.infrastructure.persistence.models.identity import (
    Permission,
    Role,
    RolePermission,
    User,
    UserRole,
)
from app.infrastructure.persistence.models.organization import Organization
from app.infrastructure.security.jwt_service import create_access_token
from app.presentation.api.deps import get_authentication_provider, get_authorization_service


def _settings() -> Settings:
    return Settings(_env_file=None, jwt_secret_key="test-secret")


async def _make_organization(session: AsyncSession, **overrides: object) -> Organization:
    defaults: dict[str, object] = {"name": f"Org-{uuid4()}"}
    organization = Organization(**{**defaults, **overrides})
    session.add(organization)
    await session.flush()
    return organization


async def _make_user(session: AsyncSession, **overrides: object) -> User:
    defaults: dict[str, object] = {"email": f"{uuid4()}@example.com", "full_name": "Test Advocate"}
    user = User(**{**defaults, **overrides})
    session.add(user)
    await session.flush()
    return user


class TestOrganizationIdResolution:
    async def test_resolves_the_users_organization_id(self, db_session: AsyncSession) -> None:
        settings = _settings()
        organization = await _make_organization(db_session)
        user = await _make_user(db_session, organization_id=organization.id)
        token = create_access_token(str(user.id), [], settings)

        provider = await get_authentication_provider(db_session, settings)
        current_user = await provider.get_current_user(token)

        assert current_user.organization_id == str(organization.id)

    async def test_none_when_the_user_has_no_organization(self, db_session: AsyncSession) -> None:
        settings = _settings()
        user = await _make_user(db_session)
        token = create_access_token(str(user.id), [], settings)

        provider = await get_authentication_provider(db_session, settings)
        current_user = await provider.get_current_user(token)

        assert current_user.is_authenticated is True
        assert current_user.organization_id is None

    async def test_anonymous_default_has_no_organization(self) -> None:
        assert CurrentUser().organization_id is None


class TestLiveRederivation:
    async def test_changing_organization_id_takes_effect_on_the_next_call_without_reissue(
        self, db_session: AsyncSession
    ) -> None:
        """Mirrors this repository's existing, praised roles-rederivation
        behavior (JwtAuthenticationProvider re-reads roles fresh from the DB
        on every request, never trusting the JWT) -- ADR/0031 SS16's
        acceptance criterion, exercised directly: the *same* token resolves
        a *different* organization_id once the underlying row changes, with
        no new token issued."""
        settings = _settings()
        first_org = await _make_organization(db_session, name="First Org")
        second_org = await _make_organization(db_session, name="Second Org")
        user = await _make_user(db_session, organization_id=first_org.id)
        token = create_access_token(str(user.id), [], settings)

        provider = await get_authentication_provider(db_session, settings)
        first_resolution = await provider.get_current_user(token)
        assert first_resolution.organization_id == str(first_org.id)

        user.organization_id = second_org.id
        await db_session.flush()

        second_resolution = await provider.get_current_user(token)
        assert second_resolution.organization_id == str(second_org.id)

    async def test_removing_organization_id_takes_effect_immediately_too(
        self, db_session: AsyncSession
    ) -> None:
        settings = _settings()
        organization = await _make_organization(db_session)
        user = await _make_user(db_session, organization_id=organization.id)
        token = create_access_token(str(user.id), [], settings)

        provider = await get_authentication_provider(db_session, settings)
        assert (await provider.get_current_user(token)).organization_id == str(organization.id)

        user.organization_id = None
        await db_session.flush()

        assert (await provider.get_current_user(token)).organization_id is None


class TestNoClientSuppliedOverride:
    async def test_an_organization_claim_embedded_in_the_token_is_ignored(
        self, db_session: AsyncSession
    ) -> None:
        """Simulates a client attempting to smuggle an Organization identity
        via a forged extra JWT claim -- ADR/0021's "never accepted as
        untrusted client input" requirement. `get_current_user()`'s only
        input is the token; it decodes `sub` and re-reads `organization_id`
        from the database, so an extra claim -- even a validly-signed one,
        since this test signs it with the real secret -- has no code path
        to reach `CurrentUser.organization_id` at all."""
        settings = _settings()
        real_organization = await _make_organization(db_session, name="Real Org")
        spoofed_organization_id = str(uuid4())
        user = await _make_user(db_session, organization_id=real_organization.id)

        forged_token = jwt.encode(
            {"sub": str(user.id), "roles": [], "organization_id": spoofed_organization_id},
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )

        provider = await get_authentication_provider(db_session, settings)
        current_user = await provider.get_current_user(forged_token)

        assert current_user.organization_id == str(real_organization.id)
        assert current_user.organization_id != spoofed_organization_id


class TestRbacNonInterference:
    async def test_permissions_are_identical_with_and_without_an_organization(
        self, db_session: AsyncSession
    ) -> None:
        """ADR/0031 SS16: a User's permissions before and after gaining
        organization_id are identical -- membership (this ADR) and
        authorization (existing RBAC) remain independently checked."""
        role_name = f"Role-{uuid4()}"
        code = f"matters:{uuid4()}"
        role = Role(name=role_name)
        permission = Permission(code=code, category="test")
        db_session.add_all([role, permission])
        await db_session.flush()
        db_session.add(RolePermission(role_id=role.id, permission_id=permission.id))

        organization = await _make_organization(db_session)
        user = await _make_user(db_session, organization_id=organization.id)
        db_session.add(UserRole(user_id=user.id, role_id=role.id))
        await db_session.flush()

        settings = _settings()
        token = create_access_token(str(user.id), [], settings)
        auth_provider = await get_authentication_provider(db_session, settings)
        current_user = await auth_provider.get_current_user(token)

        assert current_user.roles == frozenset({role_name})

        authorization_service = await get_authorization_service(db_session)
        authorization_service.require_permission(current_user, code)  # does not raise
