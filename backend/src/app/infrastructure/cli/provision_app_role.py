"""T105: one-time CLI command that provisions the non-owning Postgres
runtime role (`legal_dms_app`) the live app's `get_db()` connects as
(ADR/0021's "distinct, non-table-owning Postgres role" requirement).
Registered via `backend/pyproject.toml`'s `[project.scripts]` as
`provision-app-role` (run via `uv run provision-app-role`), **before**
`uv run alembic upgrade head` -- the RLS/grant migration references this
role by name and fails loudly if it doesn't exist yet.

Deliberately kept out of Alembic: migration files are replayed on every
environment and version-controlled, the wrong place for a one-time,
secret-bearing operation. This command owns role *creation* only; the
migration owns *grants*/RLS (DDL/DCL referencing the role by name, no
secret in it at all).

Connects via the existing, unchanged `database_url` (the admin/owning
role -- same trust boundary already used for Alembic and `bootstrap-admin`).

Idempotent by design, but *existence* and *correctness* are checked
separately (not "exists therefore fine"): if `legal_dms_app` already
exists, this command validates its required non-privileged attributes
(`LOGIN`, and NOT `SUPERUSER`/`CREATEROLE`/`CREATEDB`/`BYPASSRLS`) and
exits non-zero with a precise message if any are wrong -- it never
`ALTER`s an existing role to fix this automatically, and it never rotates
an existing role's password on any re-run (a deployed credential must
never be silently invalidated by re-running this command).

`POSTGRES_APP_USER`/`POSTGRES_APP_PASSWORD` env-var defaults below are
**local-development-only** (mirroring `docker-compose.yml`'s own
`POSTGRES_USER`/`POSTGRES_PASSWORD` pattern) -- a production deployment
must supply the real credential externally; no code-level default is
trusted there. This is a *service* credential, not the human Administrator
credential `ADR/0018` D4's "interactive-only, no argv/env/config" rule
targets -- this repository already manages service-level DB credentials
via env vars everywhere (`database_url`, `jwt_secret_key`,
`POSTGRES_PASSWORD`), so reading this one from the environment is
consistent with, not a departure from, that convention.

The password is never printed to stdout/stderr, in any code path,
including failure paths -- only the role name and, on a real database
error, the exception *type* (never its message, which some drivers embed
the failed statement/parameters into) are ever surfaced.
"""

from __future__ import annotations

import asyncio
import os
import re
import sys
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.session import get_session_factory

ROLE_NAME = "legal_dms_app"
_VALID_ROLE_NAME = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

_REQUIRED_FALSE_ATTRS = ("rolsuper", "rolbypassrls", "rolcreaterole", "rolcreatedb")


@dataclass(frozen=True, slots=True)
class ProvisionResult:
    created: bool
    """True if a new role was created; False if one already existed
    (whether valid or not -- see `attribute_problems`)."""
    attribute_problems: tuple[str, ...] = ()
    """Non-empty only when an *existing* role's attributes don't match
    what's required -- `created` is always False in that case."""


class ProvisioningError(Exception):
    """Raised for a condition this command refuses to proceed past.
    `str(exc)` is always operator-safe -- never includes a password."""


async def _connecting_role_can_create_roles(session: AsyncSession) -> bool:
    result = await session.execute(
        text("SELECT rolsuper OR rolcreaterole FROM pg_roles WHERE rolname = current_user")
    )
    return bool(result.scalar_one())


async def _existing_role_attributes(
    session: AsyncSession, role_name: str
) -> dict[str, bool] | None:
    result = await session.execute(
        text(
            "SELECT rolcanlogin, rolsuper, rolbypassrls, rolcreaterole, rolcreatedb "
            "FROM pg_roles WHERE rolname = :role_name"
        ).bindparams(role_name=role_name)
    )
    row = result.mappings().one_or_none()
    return dict(row) if row is not None else None


def _validate_attributes(attrs: dict[str, bool]) -> tuple[str, ...]:
    problems: list[str] = []
    if not attrs["rolcanlogin"]:
        problems.append("rolcanlogin must be true (role must be able to LOGIN)")
    for attr in _REQUIRED_FALSE_ATTRS:
        if attrs[attr]:
            problems.append(f"{attr} must be false")
    return tuple(problems)


def _escape_password_literal(password: str) -> str:
    """Postgres string-literal escaping (doubled single quotes) -- the
    role name is a validated, fixed identifier (never interpolated from
    untrusted input beyond this module's own constant), but the password
    always goes through this before ever reaching SQL text, defense in
    depth even though it originates from a trusted env var."""
    return password.replace("'", "''")


async def run_provision(session: AsyncSession, *, role_name: str, password: str) -> ProvisionResult:
    """Testable core -- takes an already-open session, never commits
    (mirrors `bootstrap.py`'s `run_bootstrap()` split; the caller owns the
    transaction boundary)."""
    if not _VALID_ROLE_NAME.match(role_name):
        raise ProvisioningError(f"{role_name!r} is not a safe SQL role identifier")

    if not await _connecting_role_can_create_roles(session):
        raise ProvisioningError(
            "the database_url role lacks CREATEROLE -- ask a database administrator to run "
            "this command, or grant CREATEROLE to that role"
        )

    existing = await _existing_role_attributes(session, role_name)
    if existing is not None:
        problems = _validate_attributes(existing)
        return ProvisionResult(created=False, attribute_problems=problems)

    escaped_password = _escape_password_literal(password)
    try:
        await session.execute(
            text(
                f"CREATE ROLE {role_name} WITH LOGIN PASSWORD '{escaped_password}' "
                "NOSUPERUSER NOCREATEROLE NOCREATEDB NOBYPASSRLS"
            )
        )
    except Exception as exc:
        # Never surface str(exc) -- some drivers embed the failed statement
        # (and therefore the password literal) in their exception message.
        raise ProvisioningError(
            f"failed to create role {role_name!r} ({type(exc).__name__})"
        ) from None

    return ProvisionResult(created=True)


async def _async_main() -> None:
    role_name = os.environ.get("POSTGRES_APP_USER", ROLE_NAME)
    password = os.environ.get("POSTGRES_APP_PASSWORD", ROLE_NAME)

    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            result = await run_provision(session, role_name=role_name, password=password)
        except ProvisioningError as exc:
            print(f"provision-app-role failed: {exc}")
            await session.rollback()
            sys.exit(1)

        if result.created:
            await session.commit()
            print(f"Created role {role_name!r}.")
            return

        if result.attribute_problems:
            await session.rollback()
            print(f"Role {role_name!r} already exists but has unexpected attributes:")
            for problem in result.attribute_problems:
                print(f"  - {problem}")
            print("This command never auto-corrects an existing role -- fix it manually.")
            sys.exit(1)

        await session.rollback()
        print(f"Role {role_name!r} already exists with the expected attributes -- nothing to do.")


def main() -> None:
    asyncio.run(_async_main())


if __name__ == "__main__":
    main()
