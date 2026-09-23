"""T133 disposable PostgreSQL migration and tenant/RLS coverage."""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine

from tests.support.synthetic_migration import (
    drop_disposable_database,
    provision_disposable_database_with,
)

PARENT = "7f1b9c3d4a2e"
HEAD = "9e6a4b2c8d1f"
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


async def _seed(url: str, conflict: bool = False) -> dict[str, str]:
    engine = create_async_engine(url)
    ids = {n: str(uuid4()) for n in ("org", "other", "property", "owner", "client")}
    try:
        async with engine.begin() as conn:
            for n in ("org", "other"):
                await conn.execute(
                    text("INSERT INTO organizations (id, name) VALUES (CAST(:id AS uuid), :name)"),
                    {"id": ids[n], "name": n},
                )
            await conn.execute(
                text(
                    "INSERT INTO clients (id, organization_id, client_type, full_name, "
                    "primary_phone) VALUES (CAST(:id AS uuid), CAST(:org AS uuid), "
                    "'individual', 'T133 Client', '9876543210')"
                ),
                {"id": ids["client"], "org": ids["org"]},
            )
            await conn.execute(
                text(
                    "INSERT INTO properties (id, organization_id, property_type, "
                    "survey_number) VALUES (CAST(:id AS uuid), CAST(:org AS uuid), "
                    "'agricultural', 'T133')"
                ),
                {"id": ids["property"], "org": ids["other"] if conflict else None},
            )
            await conn.execute(
                text(
                    "INSERT INTO property_owners (id, organization_id, property_id, "
                    "client_id, ownership_type, from_date) VALUES (CAST(:id AS uuid), NULL, "
                    "CAST(:property AS uuid), CAST(:client AS uuid), 'owner', CURRENT_DATE)"
                ),
                {"id": ids["owner"], "property": ids["property"], "client": ids["client"]},
            )
    finally:
        await engine.dispose()
    return ids


def test_upgrade_derives_tenant_from_legacy_client_and_preserves_shadow() -> None:
    url, name = provision_disposable_database_with("legal_dms_t133_legacy", upgrade_target=PARENT)
    try:
        ids = asyncio.run(_seed(url))
        result = _alembic(url, "upgrade", "head")
        assert result.returncode == 0, result.stdout + result.stderr

        async def verify() -> None:
            engine = create_async_engine(url)
            try:
                async with engine.connect() as conn:
                    row = (
                        await conn.execute(
                            text(
                                "SELECT p.organization_id::text, "
                                "po.organization_id::text, po.client_id IS NOT NULL "
                                "FROM properties p "
                                "JOIN property_owners po ON po.property_id = p.id"
                            )
                        )
                    ).one()
                    assert row == (ids["org"], ids["org"], True)
            finally:
                await engine.dispose()

        asyncio.run(verify())
    finally:
        drop_disposable_database(name)


def test_upgrade_fails_closed_for_conflicting_tenant_evidence() -> None:
    url, name = provision_disposable_database_with("legal_dms_t133_conflict", upgrade_target=PARENT)
    try:
        asyncio.run(_seed(url, True))
        result = _alembic(url, "upgrade", "head")
        assert result.returncode != 0
        assert "missing or contradictory" in (result.stdout + result.stderr)
    finally:
        drop_disposable_database(name)


def test_head_allows_party_only_owner_and_refuses_incompatible_downgrade() -> None:
    url, name = provision_disposable_database_with("legal_dms_t133_party", upgrade_target=HEAD)
    try:

        async def exercise() -> None:
            engine = create_async_engine(url)
            org, other_org, prop, party, other_party, other_client = (
                str(uuid4()) for _ in range(6)
            )
            try:
                async with engine.begin() as conn:
                    for organization_id, name in ((org, "T133"), (other_org, "Other")):
                        await conn.execute(
                            text(
                                "INSERT INTO organizations (id, name) VALUES "
                                "(CAST(:id AS uuid), :name)"
                            ),
                            {"id": organization_id, "name": name},
                        )
                    await conn.execute(
                        text(
                            "INSERT INTO properties (id, organization_id, property_type, "
                            "survey_number) VALUES (CAST(:id AS uuid), CAST(:org AS uuid), "
                            "'agricultural', 'Party-only')"
                        ),
                        {"id": prop, "org": org},
                    )
                    await conn.execute(
                        text(
                            "INSERT INTO parties (id, organization_id, party_type, "
                            "display_name, primary_phone) VALUES "
                            "(CAST(:id AS uuid), CAST(:org AS uuid), "
                            "'individual', 'Party owner', '9876543210')"
                        ),
                        {"id": party, "org": org},
                    )
                    await conn.execute(
                        text(
                            "INSERT INTO parties (id, organization_id, party_type, "
                            "display_name, primary_phone) VALUES "
                            "(CAST(:id AS uuid), CAST(:org AS uuid), "
                            "'individual', 'Other party', '9876543211')"
                        ),
                        {"id": other_party, "org": other_org},
                    )
                    await conn.execute(
                        text(
                            "INSERT INTO clients (id, organization_id, client_type, "
                            "full_name, primary_phone) VALUES "
                            "(CAST(:id AS uuid), CAST(:org AS uuid), "
                            "'individual', 'Other client', '9876543212')"
                        ),
                        {"id": other_client, "org": other_org},
                    )
                    await conn.execute(
                        text(
                            "INSERT INTO property_owners (id, organization_id, property_id, "
                            "party_id, ownership_type, from_date) VALUES "
                            "(CAST(:id AS uuid), CAST(:org AS uuid), "
                            "CAST(:property AS uuid), CAST(:party AS uuid), 'owner', CURRENT_DATE)"
                        ),
                        {"id": str(uuid4()), "org": org, "property": prop, "party": party},
                    )
                    rls_rows = (
                        await conn.execute(
                            text(
                                "SELECT relname, relrowsecurity, relforcerowsecurity "
                                "FROM pg_class "
                                "WHERE oid IN ('properties'::regclass, "
                                "'property_owners'::regclass) "
                                "ORDER BY relname"
                            )
                        )
                    ).all()
                    assert rls_rows == [
                        ("properties", True, True),
                        ("property_owners", True, True),
                    ]
                    assert (
                        await conn.execute(
                            text("SELECT count(*) FROM clients WHERE organization_id = :org"),
                            {"org": org},
                        )
                    ).scalar_one() == 0

                for foreign_column, foreign_id in (
                    ("party_id", other_party),
                    ("client_id", other_client),
                ):
                    async with engine.begin() as conn:
                        with pytest.raises(IntegrityError):
                            await conn.execute(
                                text(
                                    "INSERT INTO property_owners "
                                    "(id, organization_id, property_id, " + foreign_column + ", "
                                    "ownership_type, from_date) VALUES "
                                    "(CAST(:id AS uuid), CAST(:org AS uuid), "
                                    "CAST(:property AS uuid), CAST(:foreign AS uuid), "
                                    "'owner', CURRENT_DATE)"
                                ),
                                {
                                    "id": str(uuid4()),
                                    "org": org,
                                    "property": prop,
                                    "foreign": foreign_id,
                                },
                            )
            finally:
                await engine.dispose()

        asyncio.run(exercise())
        result = _alembic(url, "downgrade", PARENT)
        assert result.returncode != 0
        assert "Party-only PropertyOwner" in (result.stdout + result.stderr)
    finally:
        drop_disposable_database(name)
