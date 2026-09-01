"""Integration tests for T105/ADR-0032's `reconcile_organizations.py` --
the operator-driven, explicit-mapping reconciliation CLI for pre-existing
`organization_id IS NULL` `User` rows. Mirrors `test_bootstrap_admin.py`'s
shape (`run_reconciliation()` as the testable core, against the real
migrated schema via `db_session`).

Covers `ADR/0032` SS14's acceptance criteria verbatim: no-op on a clean
database; no assignment without explicit operator mapping; multi-
Organization support; the common single-Organization case; atomicity;
idempotency; no hardcoded/placeholder name; no inferred grouping;
interoperability with a fresh `ADR/0031` bootstrap.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.cli.bootstrap import run_bootstrap
from app.infrastructure.cli.reconcile_organizations import (
    OrganizationMapping,
    _unassigned_users,
    run_reconciliation,
)
from app.infrastructure.persistence.models.identity import User
from app.infrastructure.persistence.models.organization import Organization


async def _make_unassigned_user(session: AsyncSession, **overrides: object) -> User:
    defaults: dict[str, object] = {
        "email": f"{uuid4()}@example.com",
        "full_name": "Legacy User",
        "password_hash": "irrelevant-for-this-test",
    }
    user = User(**{**defaults, **overrides})
    session.add(user)
    await session.flush()
    return user


class TestNoOpOnCleanDatabase:
    async def test_no_organization_created_and_no_row_modified(
        self, db_session: AsyncSession
    ) -> None:
        result = await run_reconciliation(db_session, mappings=[])

        assert result.organizations_created == ()
        assert result.users_updated == 0
        assert (await db_session.execute(select(Organization))).scalars().all() == []


class TestNoAssignmentWithoutExplicitMapping:
    async def test_raises_when_an_unassigned_user_is_left_unmapped(
        self, db_session: AsyncSession
    ) -> None:
        await _make_unassigned_user(db_session)

        with pytest.raises(ValueError, match="unmapped"):
            await run_reconciliation(db_session, mappings=[])

    async def test_raises_for_an_id_that_is_not_actually_unassigned(
        self, db_session: AsyncSession
    ) -> None:
        organization = Organization(name="Already Assigned Org")
        db_session.add(organization)
        await db_session.flush()
        already_assigned = await _make_unassigned_user(db_session, organization_id=organization.id)

        with pytest.raises(ValueError, match="not an unassigned"):
            await run_reconciliation(
                db_session,
                mappings=[OrganizationMapping(name="New Org", user_ids=(already_assigned.id,))],
            )

    async def test_no_organization_created_when_mapping_is_rejected(
        self, db_session: AsyncSession
    ) -> None:
        await _make_unassigned_user(db_session)

        with pytest.raises(ValueError):
            await run_reconciliation(db_session, mappings=[])

        assert (await db_session.execute(select(Organization))).scalars().all() == []


class TestSingleOrganizationCase:
    async def test_all_users_mapped_to_one_new_organization(self, db_session: AsyncSession) -> None:
        first = await _make_unassigned_user(db_session)
        second = await _make_unassigned_user(db_session)

        result = await run_reconciliation(
            db_session,
            mappings=[OrganizationMapping(name="Legacy Practice", user_ids=(first.id, second.id))],
        )

        assert len(result.organizations_created) == 1
        assert result.users_updated == 2
        await db_session.refresh(first)
        await db_session.refresh(second)
        assert first.organization_id == second.organization_id == result.organizations_created[0].id


class TestMultiOrganizationSupport:
    async def test_produces_more_than_one_organization_when_mapping_calls_for_it(
        self, db_session: AsyncSession
    ) -> None:
        practice_a_user = await _make_unassigned_user(db_session)
        practice_b_user = await _make_unassigned_user(db_session)

        result = await run_reconciliation(
            db_session,
            mappings=[
                OrganizationMapping(name="Practice A", user_ids=(practice_a_user.id,)),
                OrganizationMapping(name="Practice B", user_ids=(practice_b_user.id,)),
            ],
        )

        assert len(result.organizations_created) == 2
        await db_session.refresh(practice_a_user)
        await db_session.refresh(practice_b_user)
        assert practice_a_user.organization_id != practice_b_user.organization_id

    async def test_mechanism_is_not_hardcoded_to_a_single_organization(
        self, db_session: AsyncSession
    ) -> None:
        users = [await _make_unassigned_user(db_session) for _ in range(3)]

        result = await run_reconciliation(
            db_session,
            mappings=[
                OrganizationMapping(name=f"Practice {i}", user_ids=(user.id,))
                for i, user in enumerate(users)
            ],
        )

        assert len(result.organizations_created) == 3


class TestNoHardcodedOrPlaceholderName:
    async def test_organization_name_is_exactly_what_the_operator_supplied(
        self, db_session: AsyncSession
    ) -> None:
        user = await _make_unassigned_user(db_session)
        operator_supplied_name = f"Operator-Supplied-{uuid4()}"

        result = await run_reconciliation(
            db_session,
            mappings=[OrganizationMapping(name=operator_supplied_name, user_ids=(user.id,))],
        )

        assert result.organizations_created[0].name == operator_supplied_name
        assert result.organizations_created[0].name not in ("Legacy", "Default", "Unknown")


class TestNoInferredGrouping:
    async def test_two_unassigned_users_are_never_auto_grouped(
        self, db_session: AsyncSession
    ) -> None:
        """No heuristic (role, creation date, or any other column) ever
        infers a grouping -- confirmed by construction: run_reconciliation()
        accepts no signal from User beyond the operator-supplied mapping's
        own user_ids, so two users left in *separate* mapping groups by the
        operator are never merged."""
        first = await _make_unassigned_user(db_session)
        second = await _make_unassigned_user(db_session)

        result = await run_reconciliation(
            db_session,
            mappings=[
                OrganizationMapping(name="Org 1", user_ids=(first.id,)),
                OrganizationMapping(name="Org 2", user_ids=(second.id,)),
            ],
        )

        await db_session.refresh(first)
        await db_session.refresh(second)
        assert first.organization_id != second.organization_id
        assert len(result.organizations_created) == 2

    async def test_created_organization_has_no_attributed_creator(
        self, db_session: AsyncSession
    ) -> None:
        """No legitimate acting User exists to attribute reconciliation to
        -- left unattributed rather than inventing one (ADR/0032 doesn't
        decide this)."""
        user = await _make_unassigned_user(db_session)

        result = await run_reconciliation(
            db_session, mappings=[OrganizationMapping(name="Org", user_ids=(user.id,))]
        )

        assert result.organizations_created[0].created_by is None
        assert result.organizations_created[0].updated_by is None


class TestAtomicity:
    async def test_a_user_mapped_twice_leaves_no_partial_state(
        self, db_session: AsyncSession
    ) -> None:
        """ADR/0032 SS8: a failure partway through must roll back the whole
        operation. A user id appearing in two mapping groups is rejected
        before any Organization is created -- verified directly."""
        user = await _make_unassigned_user(db_session)

        with pytest.raises(ValueError, match="more than one"):
            await run_reconciliation(
                db_session,
                mappings=[
                    OrganizationMapping(name="Org 1", user_ids=(user.id,)),
                    OrganizationMapping(name="Org 2", user_ids=(user.id,)),
                ],
            )

        assert (await db_session.execute(select(Organization))).scalars().all() == []


class TestIdempotency:
    async def test_second_run_against_a_fully_reconciled_database_is_a_no_op(
        self, db_session: AsyncSession
    ) -> None:
        user = await _make_unassigned_user(db_session)
        await run_reconciliation(
            db_session, mappings=[OrganizationMapping(name="Org", user_ids=(user.id,))]
        )
        await db_session.flush()

        remaining = await _unassigned_users(db_session)
        assert remaining == []

        second_run = await run_reconciliation(db_session, mappings=[])
        assert second_run.organizations_created == ()
        assert second_run.users_updated == 0


class TestFreshBootstrapNeverNeedsReconciliation:
    async def test_a_freshly_bootstrapped_user_is_never_unassigned(
        self, db_session: AsyncSession
    ) -> None:
        created = await run_bootstrap(
            db_session,
            email=f"{uuid4()}@example.com",
            password="correct horse battery staple",
            organization_name="Fresh Org",
        )
        assert created is not None
        assert created.organization_id is not None

        assert await _unassigned_users(db_session) == []
