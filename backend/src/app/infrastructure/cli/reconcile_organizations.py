"""T105/ADR-0032: dedicated, interactive CLI that reconciles `User` rows
that predate `ADR/0031` (`organization_id IS NULL`) by requiring the
operator to explicitly map each one to an Organization -- creating one or
more Organizations as the operator's own mapping requires. Registered via
`backend/pyproject.toml`'s `[project.scripts]` as `reconcile-organizations`
(run via `uv run reconcile-organizations`).

Mirrors `bootstrap.py`'s shape deliberately (`ADR/0032` SS13: "mirroring
`bootstrap-admin`'s exact registration shape... mirroring `run_bootstrap()`'s
own `flush()`-then-caller-commits shape"), but is a *distinct* command, not
an extension of `bootstrap-admin` -- `ADR/0031`'s fresh-bootstrap path and
this reconciliation path are mutually exclusive by construction: a fresh
deployment's bootstrap never leaves a `NULL`-organization `User` behind for
this command to find (see `TestFreshBootstrapNeverNeedsReconciliation` in
this feature's test suite).

**No automatic grouping, ever.** `ADR/0032` SS3b/SS3a is explicit and this
command holds to it exactly: no heuristic (role, creation date, or any other
existing column) ever infers which Users belong together -- the operator
supplies the entire mapping. Organization identity (name/legal name) is
always operator-supplied per Organization, never hardcoded or defaulted.

Idempotent: if no `organization_id IS NULL` `User` row exists, the command
prints a message and exits cleanly -- no Organization created, no row
touched. Atomic: every Organization creation and every mapped `User` update
happens in one transaction (`ADR/0020`) -- a failure partway rolls back the
whole thing, per `ADR/0032` SS8, leaving no partially-reconciled state.

`run_reconciliation()` is the testable core (an already-resolved operator
mapping in, no `input()`/interactive I/O, never commits). `_async_main()` is
the actual interactive entry point.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.session import get_session_factory
from app.infrastructure.persistence.models.identity import User
from app.infrastructure.persistence.models.organization import Organization


@dataclass(frozen=True, slots=True)
class OrganizationMapping:
    """One operator-supplied Organization to create, and exactly which
    pre-existing, unassigned `User` ids the operator placed into it."""

    name: str
    user_ids: tuple[UUID, ...]
    legal_name: str | None = None


@dataclass(frozen=True, slots=True)
class ReconciliationResult:
    organizations_created: tuple[Organization, ...] = field(default_factory=tuple)
    users_updated: int = 0


async def _unassigned_users(session: AsyncSession) -> list[User]:
    result = await session.execute(select(User).where(User.organization_id.is_(None)))
    return list(result.scalars().all())


async def run_reconciliation(
    session: AsyncSession, mappings: list[OrganizationMapping]
) -> ReconciliationResult:
    """Creates each `OrganizationMapping`'s Organization and reassigns every
    listed `User.organization_id` to it -- one transaction, `flush()`-only
    (the caller commits). Every `organization_id IS NULL` `User` at the time
    of the call must be accounted for by `mappings` (`ADR/0032` SS7) --
    raises `ValueError` naming the unmapped/unknown ids otherwise, touching
    nothing.

    No `created_by`/`updated_by` attribution on the created Organizations:
    there is no legitimate acting User to attribute reconciliation to (these
    are, by definition, pre-existing Users being mapped after the fact) --
    left `None` rather than inventing an attribution `ADR/0032` never
    decided.
    """
    unassigned = await _unassigned_users(session)
    unassigned_by_id = {user.id: user for user in unassigned}

    mapped_ids: set[UUID] = set()
    for mapping in mappings:
        for user_id in mapping.user_ids:
            if user_id in mapped_ids:
                raise ValueError(f"user {user_id} was mapped to more than one Organization")
            if user_id not in unassigned_by_id:
                raise ValueError(
                    f"user {user_id} is not an unassigned (organization_id IS NULL) User"
                )
            mapped_ids.add(user_id)

    unmapped = set(unassigned_by_id) - mapped_ids
    if unmapped:
        raise ValueError(
            "every organization_id IS NULL user must be explicitly mapped -- "
            f"unmapped: {sorted(str(u) for u in unmapped)}"
        )

    created_organizations: list[Organization] = []
    users_updated = 0
    for mapping in mappings:
        organization = Organization(name=mapping.name, legal_name=mapping.legal_name)
        session.add(organization)
        await session.flush()
        created_organizations.append(organization)

        for user_id in mapping.user_ids:
            unassigned_by_id[user_id].organization_id = organization.id
            users_updated += 1

    await session.flush()
    return ReconciliationResult(
        organizations_created=tuple(created_organizations), users_updated=users_updated
    )


def _prompt_mappings(users: list[User]) -> list[OrganizationMapping]:
    """Interactive operator walkthrough -- never touched by `run_reconciliation()`
    or its tests. Lists every unassigned User, then repeatedly prompts for an
    Organization name (and optional legal name) plus which listed emails
    belong to it, until every user has been placed into exactly one group."""
    remaining = {user.id: user for user in users}
    mappings: list[OrganizationMapping] = []

    print(f"{len(remaining)} user(s) have no Organization:")
    for user in users:
        print(f"  - {user.id}  {user.email}")

    while remaining:
        print(f"\n{len(remaining)} user(s) still unmapped.")
        name = input("Organization name for the next group: ").strip()
        legal_name = input("Organization legal name (optional): ").strip() or None

        print("Enter the email of each user in this Organization, one per line.")
        print("Blank line to finish this group.")
        group_ids: list[UUID] = []
        while True:
            raw = input("  email (blank to finish): ").strip()
            if not raw:
                break
            match = next((u for u in remaining.values() if u.email == raw), None)
            if match is None:
                print(f"  {raw!r} is not an unmapped user -- try again.")
                continue
            group_ids.append(match.id)
            del remaining[match.id]

        if not group_ids:
            print("No users entered for this group -- skipping it, nothing created.")
            continue

        mappings.append(
            OrganizationMapping(name=name, legal_name=legal_name, user_ids=tuple(group_ids))
        )

    return mappings


async def _async_main() -> None:
    session_factory = get_session_factory()
    async with session_factory() as session:
        users = await _unassigned_users(session)
        if not users:
            print("No unassigned users -- nothing to reconcile.")
            return

        mappings = _prompt_mappings(users)

        result = await run_reconciliation(session, mappings)
        await session.commit()
        print(
            f"Created {len(result.organizations_created)} Organization(s), "
            f"reassigned {result.users_updated} user(s)."
        )


def main() -> None:
    asyncio.run(_async_main())


if __name__ == "__main__":
    main()
