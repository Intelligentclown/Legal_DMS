"""T122: fail-closed rejection of a NULL-Organization legacy Address.

The T122 queue-row precondition: the address finalization forward migration is
only for genuinely empty/fresh targets; dev/test-only data does not qualify,
and the migration must not backfill, reset, or delete retained data. This test
proves that behavior **fail closed** -- the only operationally-loadable thing
to do with a deliberately constructed NULL-org legacy row:

- a disposable database is migrated to exactly the T120 head
  (`f3b7c9d1e2a4`), i.e. the last schema state where a NULL-org Address is
  allowed;
- one NULL-org Address is inserted (simulating the retained legacy data a
  fresh-target guard would be protecting);
- `alembic upgrade head` is then run against that database;
- the migration must abort before applying anything (the `NOT NULL` ALTER
  raises `... contains null values` on the NULL row), leaving the database at
  the T120 head with no Address RLS and no partial T122 residue.

All writes happen on the disposable database only; the shared development
database is never touched.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from tests.support.synthetic_migration import (
    alembic_current_branch,
    drop_disposable_database,
    provision_disposable_database_with,
)

LEGACY_HEAD = "f3b7c9d1e2a4"

BACKEND_DIR = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def legacy_disposable_db() -> Iterator[tuple[str, str]]:
    """One disposable database pinned at the T120 legacy head (where
    `addresses.organization_id` is still nullable), destroyed in teardown."""
    url, db_name = provision_disposable_database_with(
        "legal_dms_t122_null", upgrade_target=LEGACY_HEAD
    )
    try:
        yield url, db_name
    finally:
        drop_disposable_database(db_name)


def test_null_org_legacy_address_makes_upgrade_to_head_fail_closed(
    legacy_disposable_db: tuple[str, str],
) -> None:
    url, _db_name = legacy_disposable_db
    asyncio.run(_seed_legacy_null_org_address(url))

    # Precondition evidence: the NULL-org row really exists at the T120 head.
    assert asyncio.run(_null_org_address_count(url)) == 1

    proc = _run_alembic_upgrade_head_expect_failure(url)
    combined = f"{proc.stdout}\n{proc.stderr}"

    assert proc.returncode != 0
    assert "contains null values" in combined or "not-null constraint" in combined

    # Nothing from the T122 migration was applied: still at the T120 head, no
    # Address RLS, organization_id still nullable.
    assert alembic_current_branch(url) == LEGACY_HEAD
    assert asyncio.run(_addresses_rls_force_flags(url)) == (False, False)
    assert asyncio.run(_addresses_policy_names(url)) == []
    assert asyncio.run(_addresses_organization_id_nullable(url)) is True
    # And the retained legacy row is untouched (no backfill/reset/delete).
    assert asyncio.run(_null_org_address_count(url)) == 1


def _run_alembic_upgrade_head_expect_failure(
    disposable_url: str,
) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["DATABASE_URL"] = disposable_url
    env["PYTHONPATH"] = str(BACKEND_DIR / "src")
    return subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(BACKEND_DIR),
        env=env,
        capture_output=True,
        text=True,
    )


async def _seed_legacy_null_org_address(url: str) -> None:
    engine = create_async_engine(url)
    try:
        async with engine.connect() as conn, conn.begin():
            org_id = uuid4()
            await conn.execute(
                text(
                    "INSERT INTO organizations (id, name) "
                    "VALUES (CAST(:id AS uuid), 'T122 Legacy Org')"
                ).bindparams(id=str(org_id))
            )
            country_id = uuid4()
            iso_code = f"{str(uuid4())[:2].upper()}"
            await conn.execute(
                text(
                    "INSERT INTO countries (id, name, iso_code) "
                    "VALUES (CAST(:id AS uuid), 'T122 Legacy Country', :iso_code)"
                ).bindparams(id=str(country_id), iso_code=iso_code)
            )
            await conn.execute(
                text(
                    "INSERT INTO addresses (id, organization_id, line1, country_id, "
                    "address_type) VALUES (CAST(:id AS uuid), NULL, "
                    "'Legacy No-Org Address', CAST(:country_id AS uuid), 'registered')"
                ).bindparams(id=str(uuid4()), country_id=str(country_id))
            )
    finally:
        await engine.dispose()


async def _null_org_address_count(url: str) -> int:
    engine = create_async_engine(url)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text("SELECT count(*) FROM addresses WHERE organization_id IS NULL")
            )
            return int(result.scalar_one())
    finally:
        await engine.dispose()


async def _addresses_rls_force_flags(url: str) -> tuple[bool, bool]:
    engine = create_async_engine(url)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT relrowsecurity, relforcerowsecurity FROM pg_class "
                    "WHERE oid = 'addresses'::regclass"
                )
            )
            rls, force = result.one()
            return bool(rls), bool(force)
    finally:
        await engine.dispose()


async def _addresses_policy_names(url: str) -> list[str]:
    engine = create_async_engine(url)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text("SELECT policyname FROM pg_policies WHERE tablename = 'addresses'")
            )
            return sorted(result.scalars())
    finally:
        await engine.dispose()


async def _addresses_organization_id_nullable(url: str) -> bool:
    engine = create_async_engine(url)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT NOT attnotnull FROM pg_attribute "
                    "WHERE attrelid = 'addresses'::regclass AND attname = 'organization_id'"
                )
            )
            return bool(result.scalar_one())
    finally:
        await engine.dispose()
