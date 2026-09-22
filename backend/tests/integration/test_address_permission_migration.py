"""T130: `seed_address_permissions_and_role_grants` upgrade/downgrade —
PostgreSQL integration.

Proves the permission seed/grant migration against a disposable database
(never the shared development database): upgrade to `head` yields exactly the
three `addresses:*` codes granted to the six established roles (83
`role_permissions` associations in total), a downgrade to the prior head
(`c4e7a9b2d6f1`) removes only those codes/grants and restores the prior
21-code / 71-association contract, and a re-upgrade restores the new contract.
Only `permissions`/`role_permissions` are touched (mirroring T124's seed
migration shape) aside from the T126 `legal_dms_provenance` functions, whose
`alembic_version` guards this module confirms carry the supported
`5d8a3f2e9c6b` guard at head, the parent `c4e7a9b2d6f1` guard after downgrade,
and the new guard again after re-upgrade (T130's documented "future revision
must explicitly extend the supported runtime contract").
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from tests.support.synthetic_migration import (
    alembic_current_branch,
    drop_disposable_database,
    provision_disposable_database_with,
)

NEW_HEAD = "5d8a3f2e9c6b"
PARENT_HEAD = "c4e7a9b2d6f1"

PRE_EXISTING_PERMISSIONS = 21
PRE_EXISTING_ASSOCIATIONS = 71
NEW_PERMISSIONS = 24
NEW_ASSOCIATIONS = 83

PROVENANCE_FUNCTIONS = (
    "record_fresh_birth",
    "enter_operational_fresh",
)

ADDRESS_CODES = ("addresses:read", "addresses:write", "addresses:delete")

EXPECTED_ADDRESS_MATRIX = {
    "Administrator": ("addresses:read", "addresses:write", "addresses:delete"),
    "Advocate": ("addresses:read", "addresses:write", "addresses:delete"),
    "Paralegal": ("addresses:read", "addresses:write"),
    "Clerk": ("addresses:read", "addresses:write"),
    "Accountant": ("addresses:read",),
    "Read Only": ("addresses:read",),
}

BACKEND_DIR = Path(__file__).resolve().parents[2]


def _run_alembic_child(disposable_url: str, *args: str) -> None:
    env = dict(os.environ)
    env["DATABASE_URL"] = disposable_url
    env["PYTHONPATH"] = str(BACKEND_DIR / "src")
    proc = subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=str(BACKEND_DIR),
        env=env,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"alembic {' '.join(args)} failed:\n{proc.stdout}\n{proc.stderr}")


async def _count(url: str, table: str) -> int:
    engine = create_async_engine(url)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text(f"SELECT count(*) FROM {table}"))
            return int(result.scalar_one())
    finally:
        await engine.dispose()


async def _provenance_functions_guard(url: str, supported_revision: str) -> bool:
    engine = create_async_engine(url)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT p.proname, pg_get_functiondef(p.oid) FROM pg_proc p "
                    "JOIN pg_namespace n ON n.oid = p.pronamespace "
                    "WHERE n.nspname = 'legal_dms_provenance' "
                    "AND p.proname IN ('record_fresh_birth', 'enter_operational_fresh')"
                )
            )
            defs = dict(result.all())
            return set(defs) == set(PROVENANCE_FUNCTIONS) and all(
                supported_revision in definition for definition in defs.values()
            )
    finally:
        await engine.dispose()


async def _address_codes_present(url: str) -> bool:
    engine = create_async_engine(url)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text("SELECT code FROM permissions WHERE code LIKE 'addresses:%'")
            )
            return set(result.scalars()) == set(ADDRESS_CODES)
    finally:
        await engine.dispose()


async def _address_grants(url: str) -> dict[str, set[str]]:
    engine = create_async_engine(url)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT r.name, p.code FROM role_permissions rp "
                    "JOIN roles r ON r.id = rp.role_id "
                    "JOIN permissions p ON p.id = rp.permission_id "
                    "WHERE p.code LIKE 'addresses:%'"
                )
            )
            matrix: dict[str, set[str]] = {}
            for role_name, code in result.all():
                matrix.setdefault(role_name, set()).add(code)
            return matrix
    finally:
        await engine.dispose()


@pytest.fixture(scope="module")
def migrated_db() -> str:
    url, db_name = provision_disposable_database_with("legal_dms_t130_permissions")
    try:
        yield url
    finally:
        drop_disposable_database(db_name)


async def test_upgrade_reaches_t130_head(migrated_db: str) -> None:
    assert alembic_current_branch(migrated_db) == NEW_HEAD
    assert await _count(migrated_db, "permissions") == NEW_PERMISSIONS
    assert await _count(migrated_db, "role_permissions") == NEW_ASSOCIATIONS
    assert await _address_codes_present(migrated_db)
    assert await _provenance_functions_guard(migrated_db, NEW_HEAD)

    grants = await _address_grants(migrated_db)
    for role, expected_codes in EXPECTED_ADDRESS_MATRIX.items():
        assert grants.get(role) == set(expected_codes), f"mismatch for {role}: {grants.get(role)}"
    assert set(grants) == set(EXPECTED_ADDRESS_MATRIX)


async def test_downgrade_removes_only_address_seed_and_reupgrade_restores(
    migrated_db: str,
) -> None:
    original = {
        "permissions": await _count(migrated_db, "permissions"),
        "role_permissions": await _count(migrated_db, "role_permissions"),
    }

    _run_alembic_child(migrated_db, "downgrade", PARENT_HEAD)
    assert alembic_current_branch(migrated_db) == PARENT_HEAD
    assert await _count(migrated_db, "permissions") == PRE_EXISTING_PERMISSIONS
    assert await _count(migrated_db, "role_permissions") == PRE_EXISTING_ASSOCIATIONS
    assert not await _address_codes_present(migrated_db)
    assert await _address_grants(migrated_db) == {}
    assert await _provenance_functions_guard(migrated_db, PARENT_HEAD)

    _run_alembic_child(migrated_db, "upgrade", NEW_HEAD)
    assert alembic_current_branch(migrated_db) == NEW_HEAD
    assert await _count(migrated_db, "permissions") == original["permissions"]
    assert await _count(migrated_db, "role_permissions") == original["role_permissions"]
    assert await _address_codes_present(migrated_db)
    assert await _provenance_functions_guard(migrated_db, NEW_HEAD)
