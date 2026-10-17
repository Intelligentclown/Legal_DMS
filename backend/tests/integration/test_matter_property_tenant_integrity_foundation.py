"""Real-PostgreSQL coverage for T155's canonical MatterProperty foundation."""

# ruff: noqa: E501

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine

from app.infrastructure.config import get_settings
from tests.support.synthetic_migration import (
    alembic_current_branch,
    drop_disposable_database,
    provision_disposable_database_with,
)

PARENT = "8d77007b9d7f"
HEAD = "b155caa6d4e1"
BACKEND_DIR = Path(__file__).resolve().parents[2]


def _alembic(url: str, *args: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ, DATABASE_URL=url, PYTHONPATH=str(BACKEND_DIR / "src"))
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
    )


async def _seed_endpoints(url: str) -> dict[str, str]:
    engine = create_async_engine(url)
    ids = {
        name: str(uuid4())
        for name in (
            "org",
            "other_org",
            "type",
            "status",
            "matter",
            "other_matter",
            "property",
            "other_property",
        )
    }
    try:
        async with engine.begin() as conn:
            for key in ("org", "other_org"):
                await conn.execute(
                    text("INSERT INTO organizations (id, name) VALUES (CAST(:id AS uuid), :name)"),
                    {"id": ids[key], "name": key},
                )
            await conn.execute(
                text(
                    "INSERT INTO matter_types (id, code, name) VALUES (CAST(:id AS uuid), :code, 'T155 Type')"
                ),
                {"id": ids["type"], "code": f"T-{uuid4().hex[:12]}"},
            )
            await conn.execute(
                text(
                    "INSERT INTO matter_statuses (id, code, name) VALUES (CAST(:id AS uuid), :code, 'T155 Status')"
                ),
                {"id": ids["status"], "code": f"S-{uuid4().hex[:12]}"},
            )
            for key, org_key in (("matter", "org"), ("other_matter", "other_org")):
                await conn.execute(
                    text(
                        "INSERT INTO matters (id, organization_id, matter_number, matter_type_id, matter_status_id, title, opened_at) VALUES (CAST(:id AS uuid), CAST(:org AS uuid), :number, CAST(:type AS uuid), CAST(:status AS uuid), 'T155 Matter', now())"
                    ),
                    {
                        "id": ids[key],
                        "org": ids[org_key],
                        "number": f"M-{uuid4().hex[:16]}",
                        "type": ids["type"],
                        "status": ids["status"],
                    },
                )
            for key, org_key in (("property", "org"), ("other_property", "other_org")):
                await conn.execute(
                    text(
                        "INSERT INTO properties (id, organization_id, property_type, survey_number) VALUES (CAST(:id AS uuid), CAST(:org AS uuid), 'agricultural', :survey)"
                    ),
                    {"id": ids[key], "org": ids[org_key], "survey": f"T155-{uuid4().hex[:12]}"},
                )
    finally:
        await engine.dispose()
    return ids


def _insert_sql() -> str:
    return "INSERT INTO matter_properties (id, organization_id, matter_id, property_id) VALUES (CAST(:id AS uuid), CAST(:org AS uuid), CAST(:matter AS uuid), CAST(:property AS uuid))"


def test_upgrade_from_t155_parent_creates_one_sole_head_and_preserves_legacy_shadow() -> None:
    url, name = provision_disposable_database_with("legal_dms_t155_upgrade", upgrade_target=PARENT)
    try:
        result = _alembic(url, "upgrade", HEAD)
        assert result.returncode == 0, result.stdout + result.stderr
        assert alembic_current_branch(url) == HEAD

        async def verify() -> None:
            engine = create_async_engine(url)
            try:
                async with engine.connect() as conn:
                    assert (
                        await conn.execute(
                            text(
                                "SELECT count(*) FROM pg_constraint WHERE conrelid = 'matters'::regclass AND pg_get_constraintdef(oid) LIKE '%property_id%'"
                            )
                        )
                    ).scalar_one() >= 1
                    flags = (
                        await conn.execute(
                            text(
                                "SELECT relrowsecurity, relforcerowsecurity FROM pg_class WHERE oid = 'matter_properties'::regclass"
                            )
                        )
                    ).one()
                    assert flags == (True, True)
            finally:
                await engine.dispose()

        asyncio.run(verify())
    finally:
        drop_disposable_database(name)


def test_database_rejects_duplicate_and_cross_organization_associations() -> None:
    url, name = provision_disposable_database_with("legal_dms_t155_integrity", upgrade_target=HEAD)
    try:
        ids = asyncio.run(_seed_endpoints(url))

        async def exercise() -> None:
            engine = create_async_engine(url)
            try:
                async with engine.begin() as conn:
                    values = {
                        "id": str(uuid4()),
                        "org": ids["org"],
                        "matter": ids["matter"],
                        "property": ids["property"],
                    }
                    await conn.execute(text(_insert_sql()), values)
                async with engine.begin() as conn:
                    with pytest.raises(IntegrityError):
                        await conn.execute(text(_insert_sql()), {**values, "id": str(uuid4())})
                for matter, property_id in (
                    (ids["other_matter"], ids["property"]),
                    (ids["matter"], ids["other_property"]),
                ):
                    async with engine.begin() as conn:
                        with pytest.raises(IntegrityError):
                            await conn.execute(
                                text(_insert_sql()),
                                {
                                    "id": str(uuid4()),
                                    "org": ids["org"],
                                    "matter": matter,
                                    "property": property_id,
                                },
                            )
                async with engine.connect() as conn:
                    assert (
                        await conn.execute(text("SELECT count(*) FROM parties"))
                    ).scalar_one() == 0
                    assert (
                        await conn.execute(text("SELECT count(*) FROM matter_parties"))
                    ).scalar_one() == 0
                    assert (
                        await conn.execute(text("SELECT count(*) FROM property_owners"))
                    ).scalar_one() == 0
                    assert (
                        await conn.execute(
                            text(
                                "SELECT property_id::text FROM matters WHERE id = CAST(:id AS uuid)"
                            ),
                            {"id": ids["matter"]},
                        )
                    ).scalar_one() is None
            finally:
                await engine.dispose()

        asyncio.run(exercise())
    finally:
        drop_disposable_database(name)


def test_forced_rls_allows_only_trusted_current_organization_and_default_denies() -> None:
    url, name = provision_disposable_database_with("legal_dms_t155_rls", upgrade_target=HEAD)
    try:
        ids = asyncio.run(_seed_endpoints(url))

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
                async with admin.begin() as conn:
                    await conn.execute(
                        text(_insert_sql()),
                        {
                            "id": str(uuid4()),
                            "org": ids["org"],
                            "matter": ids["matter"],
                            "property": ids["property"],
                        },
                    )
                async with app.connect() as conn:
                    assert (
                        await conn.execute(text("SELECT count(*) FROM matter_properties"))
                    ).scalar_one() == 0
                async with app.connect() as conn, conn.begin():
                    await conn.execute(
                        text("SELECT set_config('app.current_organization_id', :org, true)"),
                        {"org": ids["org"]},
                    )
                    assert (
                        await conn.execute(text("SELECT count(*) FROM matter_properties"))
                    ).scalar_one() == 1
                async with app.connect() as conn, conn.begin():
                    await conn.execute(
                        text("SELECT set_config('app.current_organization_id', :org, true)"),
                        {"org": ids["other_org"]},
                    )
                    assert (
                        await conn.execute(text("SELECT count(*) FROM matter_properties"))
                    ).scalar_one() == 0
            finally:
                await app.dispose()
                await admin.dispose()

        asyncio.run(exercise())
    finally:
        drop_disposable_database(name)
