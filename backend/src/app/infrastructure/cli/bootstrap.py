"""T67: one-time CLI command that bootstraps this deployment's first
Administrator user (ADR-0018 D4). Registered via `backend/pyproject.toml`'s
`[project.scripts]` as `bootstrap-admin` (run via `uv run bootstrap-admin`).

Idempotent by design: if any `User` row already exists, the command prints
a message and exits cleanly -- no error, no second admin created. Otherwise
it interactively prompts for an email and a password via `getpass` (never
argv, an environment variable, or a config file, so no credential material
ever touches shell history, process listings, or CI logs), hashes the
password with the existing `hash_password()` (T46), and creates exactly one
`User` assigned the `Administrator` role -- the exact role name seeded by
`9963e15f2752_seed_lookup_data.py`.

T105/ADR-0031 SS6.2/SS6.3: in the same idempotency check and the same
transaction, also creates exactly one `Organization` and links the new
`User` to it -- so a deployment can never reach a state with a User but no
Organization, or vice versa. Organization identity (name/legal name) is
always operator-supplied at the interactive prompt, never hardcoded or
defaulted (mirroring D4's reasoning for why identity-bearing data belongs
to an interactive prompt, not argv/env/config). Ordering mirrors this
file's own pre-existing `UserRole.assigned_by=user.id` self-attribution
precedent ("no other actor exists at bootstrap time"): the `User` is
created and flushed first (so its id exists), then the `Organization` is
created with `created_by`/`updated_by` attributed to that same user (which
now legally satisfies `AuditMixin`'s FK), then the user's own
`organization_id` is set to point at it.

`run_bootstrap()` is the testable core (takes an already-open session,
never touches `input()`/`getpass()`, never commits -- mirrors this
codebase's `get_db()`/repository-layer split, where the caller owns the
transaction boundary). `main()` is the actual entry point: it owns the
process-level concerns (opening the session, prompting, committing,
printing) that a test has no reason to exercise.
"""

from __future__ import annotations

import asyncio
from getpass import getpass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.session import get_session_factory
from app.infrastructure.persistence.models.identity import Role, User, UserRole
from app.infrastructure.persistence.models.organization import Organization
from app.infrastructure.security.password_hasher import hash_password

ADMINISTRATOR_ROLE_NAME = "Administrator"


async def _any_user_exists(session: AsyncSession) -> bool:
    result = await session.execute(select(func.count()).select_from(User))
    return result.scalar_one() > 0


async def run_bootstrap(
    session: AsyncSession,
    *,
    email: str,
    password: str,
    organization_name: str,
    organization_legal_name: str | None = None,
) -> User | None:
    """Creates the first admin `User`, the first `Organization`, links the
    two, and assigns the `Administrator` role -- one atomic unit (T105/
    ADR-0031 SS6.2/SS6.3) -- or returns `None` without touching the session
    if a `User` row already exists. Doesn't commit -- `main()` owns that."""
    if await _any_user_exists(session):
        return None

    result = await session.execute(select(Role).where(Role.name == ADMINISTRATOR_ROLE_NAME))
    admin_role = result.scalar_one_or_none()
    if admin_role is None:
        raise RuntimeError(
            f"No {ADMINISTRATOR_ROLE_NAME!r} role found -- run migrations "
            "(`uv run alembic upgrade head`) before bootstrapping the first admin."
        )

    user = User(
        email=email,
        full_name=ADMINISTRATOR_ROLE_NAME,
        password_hash=hash_password(password),
    )
    session.add(user)
    await session.flush()

    organization = Organization(
        name=organization_name,
        legal_name=organization_legal_name,
        created_by=user.id,
        updated_by=user.id,
    )
    session.add(organization)
    await session.flush()

    user.organization_id = organization.id

    session.add(UserRole(user_id=user.id, role_id=admin_role.id, assigned_by=user.id))
    await session.flush()

    return user


async def _async_main() -> None:
    session_factory = get_session_factory()
    async with session_factory() as session:
        # Checked here too (not just inside run_bootstrap) so the process
        # skips straight to the "already exists" message instead of
        # prompting for credentials it's about to discard.
        if await _any_user_exists(session):
            print("A user already exists -- skipping first-admin bootstrap.")
            return

        email = input("Administrator email: ").strip()
        password = getpass("Administrator password: ")
        organization_name = input("Organization name: ").strip()
        organization_legal_name = input("Organization legal name (optional): ").strip() or None

        user = await run_bootstrap(
            session,
            email=email,
            password=password,
            organization_name=organization_name,
            organization_legal_name=organization_legal_name,
        )
        if user is None:
            print("A user already exists -- skipping first-admin bootstrap.")
            return

        await session.commit()
        print(f"Created administrator {user.email!r} and its Organization {organization_name!r}.")


def main() -> None:
    asyncio.run(_async_main())


if __name__ == "__main__":
    main()
