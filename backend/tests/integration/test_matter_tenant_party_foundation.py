"""T132 PostgreSQL migration, tenant-integrity, and forced-RLS coverage.

All cases provision a random child database; none use a retained development
database.  The legacy backfill cases deliberately use the T130 head.
"""

# ruff: noqa: E501

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from app.infrastructure.config import get_settings
from tests.support.synthetic_migration import (
    drop_disposable_database,
    provision_disposable_database_with,
)

PARENT = "5d8a3f2e9c6b"
HEAD = "7f1b9c3d4a2e"
BACKEND_DIR = Path(__file__).resolve().parents[2]


def _upgrade(url: str, target: str = "head") -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["DATABASE_URL"] = url
    env["PYTHONPATH"] = str(BACKEND_DIR / "src")
    return subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", target],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
    )


async def _seed(
    url: str, *, null_matter_org: bool, client_org: str | None = None
) -> tuple[str, str]:
    engine = create_async_engine(url)
    org, client, typ, status, matter = (uuid4() for _ in range(5))
    client_org = client_org or str(org)
    try:
        async with engine.connect() as conn, conn.begin():
            await conn.execute(
                text("INSERT INTO organizations (id, name) VALUES (:id, 'T132 Org')"), {"id": org}
            )
            await conn.execute(
                text("INSERT INTO matter_types (id, code, name) VALUES (:id, :code, 'T132 Type')"),
                {"id": typ, "code": f"T{typ.hex[:12]}"},
            )
            await conn.execute(
                text(
                    "INSERT INTO matter_statuses (id, code, name) VALUES (:id, :code, 'T132 Status')"
                ),
                {"id": status, "code": f"S{status.hex[:12]}"},
            )
            await conn.execute(
                text(
                    "INSERT INTO clients (id, organization_id, client_type, full_name, primary_phone) VALUES (:id, CAST(:org AS uuid), 'individual', 'T132 Legacy Client', '9876543210')"
                ),
                {"id": client, "org": client_org},
            )
            await conn.execute(
                text(
                    "INSERT INTO matters (id, organization_id, matter_number, matter_type_id, matter_status_id, client_id, title, opened_at) VALUES (:id, :matter_org, :number, :typ, :status, :client, 'T132 Matter', now())"
                ),
                {
                    "id": matter,
                    "matter_org": None if null_matter_org else org,
                    "number": f"M-{matter.hex[:16]}",
                    "typ": typ,
                    "status": status,
                    "client": client,
                },
            )
    finally:
        await engine.dispose()
    return str(org), str(matter)


async def _matter_org(url: str, matter: str) -> str | None:
    engine = create_async_engine(url)
    try:
        async with engine.connect() as conn:
            return (
                await conn.execute(
                    text(
                        "SELECT CAST(organization_id AS text) FROM matters WHERE id = CAST(:id AS uuid)"
                    ),
                    {"id": matter},
                )
            ).scalar_one()
    finally:
        await engine.dispose()


def test_null_matter_org_backfills_only_from_client() -> None:
    url, name = provision_disposable_database_with("legal_dms_t132_backfill", upgrade_target=PARENT)
    try:
        org, matter = asyncio.run(_seed(url, null_matter_org=True))
        assert _upgrade(url).returncode == 0
        assert asyncio.run(_matter_org(url, matter)) == org
    finally:
        drop_disposable_database(name)


def test_null_matter_org_without_client_fails_closed() -> None:
    url, name = provision_disposable_database_with("legal_dms_t132_missing", upgrade_target=PARENT)
    try:
        _org, matter = asyncio.run(_seed(url, null_matter_org=True))
        engine = create_async_engine(url)

        async def remove_client() -> None:
            async with engine.connect() as conn, conn.begin():
                # Synthetic retained-state corruption: this is the only way a
                # NULL client reference is representable before T132 relaxes
                # the historical NOT NULL compatibility shadow.
                await conn.execute(text("ALTER TABLE matters ALTER COLUMN client_id DROP NOT NULL"))
                await conn.execute(
                    text("UPDATE matters SET client_id = NULL WHERE id = CAST(:id AS uuid)"),
                    {"id": matter},
                )

        asyncio.run(remove_client())
        asyncio.run(engine.dispose())
        result = _upgrade(url)
        assert result.returncode != 0
        assert "lacks Client-derived organization evidence" in (result.stdout + result.stderr)
    finally:
        drop_disposable_database(name)


def test_head_permits_party_canonical_matter_and_forces_rls() -> None:
    url, name = provision_disposable_database_with("legal_dms_t132_rls", upgrade_target=HEAD)

    async def exercise() -> None:
        admin = create_async_engine(url)
        app_url = (
            make_url(url)
            .set(
                username=make_url(get_settings().app_database_url).username,
                password=make_url(get_settings().app_database_url).password,
            )
            .render_as_string(hide_password=False)
        )
        app = create_async_engine(app_url)
        try:
            org, matter = await _seed(url, null_matter_org=False)
            async with admin.connect() as conn, conn.begin():
                await conn.execute(
                    text("UPDATE matters SET client_id = NULL WHERE id = CAST(:id AS uuid)"),
                    {"id": matter},
                )
                flags = (
                    await conn.execute(
                        text(
                            "SELECT relrowsecurity, relforcerowsecurity FROM pg_class WHERE oid = 'matters'::regclass"
                        )
                    )
                ).one()
                assert flags == (True, True)
                role = (
                    await conn.execute(
                        text(
                            "SELECT rolcanlogin, rolsuper, rolcreaterole, rolcreatedb, rolbypassrls FROM pg_roles WHERE rolname = 'legal_dms_app'"
                        )
                    )
                ).one()
                assert role == (True, False, False, False, False)
            async with app.connect() as conn:
                assert (await conn.execute(text("SELECT count(*) FROM matters"))).scalar_one() == 0
            async with app.connect() as conn, conn.begin():
                await conn.execute(
                    text("SELECT set_config('app.current_organization_id', :org, true)"),
                    {"org": org},
                )
                assert (await conn.execute(text("SELECT count(*) FROM matters"))).scalar_one() == 1
        finally:
            await app.dispose()
            await admin.dispose()

    try:
        asyncio.run(exercise())
    finally:
        drop_disposable_database(name)
