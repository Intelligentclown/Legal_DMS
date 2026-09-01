"""Schema-level tests for T105's `organizations` table and
`users.organization_id` -- constraints and FKs, against the real migrated
schema. Mirrors `test_identity_models.py`'s shape.

Runs via `db_session` (the admin/owning Postgres role, unchanged by T105) --
a superuser role bypasses RLS entirely, so these tests exercise the schema's
own constraints, not the RLS backstop (see `test_organizations_users_rls.py`
for that).
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.models.identity import User
from app.infrastructure.persistence.models.organization import Organization


async def _make_organization(session: AsyncSession, **overrides: object) -> Organization:
    defaults: dict[str, object] = {"name": f"Org-{uuid4()}"}
    organization = Organization(**{**defaults, **overrides})
    session.add(organization)
    await session.flush()
    return organization


async def _make_user(session: AsyncSession, **overrides: object) -> User:
    defaults: dict[str, object] = {"email": f"{uuid4()}@example.com", "full_name": "Test User"}
    user = User(**{**defaults, **overrides})
    session.add(user)
    await session.flush()
    return user


class TestOrganization:
    async def test_create_succeeds_with_audit_defaults(self, db_session: AsyncSession) -> None:
        organization = await _make_organization(db_session, legal_name="Acme Legal LLP")

        assert organization.id is not None
        assert organization.created_at is not None
        assert organization.updated_at is not None
        assert organization.deleted_at is None
        assert organization.version == 1
        assert organization.legal_name == "Acme Legal LLP"

    async def test_legal_name_is_optional(self, db_session: AsyncSession) -> None:
        organization = await _make_organization(db_session)

        assert organization.legal_name is None

    async def test_name_is_required(self, db_session: AsyncSession) -> None:
        organization = Organization(name=None)
        db_session.add(organization)

        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_name_is_not_required_to_be_unique(self, db_session: AsyncSession) -> None:
        """No uniqueness constraint is decided by any accepted ADR -- two
        Organizations may share a name."""
        name = f"Org-{uuid4()}"
        await _make_organization(db_session, name=name)
        second = await _make_organization(db_session, name=name)

        assert second.id is not None


class TestUserOrganizationId:
    async def test_organization_id_defaults_to_null(self, db_session: AsyncSession) -> None:
        user = await _make_user(db_session)

        assert user.organization_id is None

    async def test_can_be_set_to_an_existing_organization(self, db_session: AsyncSession) -> None:
        organization = await _make_organization(db_session)
        user = await _make_user(db_session, organization_id=organization.id)

        assert user.organization_id == organization.id

    async def test_requires_an_existing_organization(self, db_session: AsyncSession) -> None:
        db_session.add(
            User(
                email=f"{uuid4()}@example.com",
                full_name="Dangling FK",
                organization_id=uuid4(),
            )
        )

        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_multiple_users_can_share_one_organization(
        self, db_session: AsyncSession
    ) -> None:
        organization = await _make_organization(db_session)
        first = await _make_user(db_session, organization_id=organization.id)
        second = await _make_user(db_session, organization_id=organization.id)

        assert first.organization_id == second.organization_id == organization.id
