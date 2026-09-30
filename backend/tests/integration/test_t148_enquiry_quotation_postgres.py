"""T148 PostgreSQL migration and tenant-RLS coverage on disposable databases."""

from __future__ import annotations

import asyncio
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from app.infrastructure.config import get_settings
from tests.support.synthetic_migration import (
    alembic_current_branch,
    drop_disposable_database,
    provision_disposable_database_with,
)

HEAD = "e148c0f5a8b2"


def _app_url(url: str) -> str:
    app = make_url(get_settings().app_database_url)
    return (
        make_url(url)
        .set(username=app.username, password=app.password)
        .render_as_string(hide_password=False)
    )


def test_t148_new_tables_force_rls_and_isolate_enquiries() -> None:
    url, name = provision_disposable_database_with("legal_dms_t148_rls", upgrade_target=HEAD)

    async def exercise() -> None:
        admin = create_async_engine(url)
        app = create_async_engine(_app_url(url))
        organization_id, other_organization_id, enquiry_id = (str(uuid4()) for _ in range(3))
        try:
            async with admin.begin() as connection:
                await connection.execute(
                    text("INSERT INTO organizations (id, name) VALUES (CAST(:id AS uuid), :name)"),
                    {"id": organization_id, "name": "T148 tenant"},
                )
                await connection.execute(
                    text("INSERT INTO organizations (id, name) VALUES (CAST(:id AS uuid), :name)"),
                    {"id": other_organization_id, "name": "T148 other tenant"},
                )
                await connection.execute(
                    text(
                        "INSERT INTO enquiries (id, organization_id, prospect_display_name) "
                        "VALUES (CAST(:id AS uuid), CAST(:organization_id AS uuid), "
                        "'T148 Prospect')"
                    ),
                    {"id": enquiry_id, "organization_id": organization_id},
                )
                flags = (
                    await connection.execute(
                        text(
                            "SELECT relname, relrowsecurity, relforcerowsecurity FROM pg_class "
                            "WHERE oid IN ('enquiries'::regclass, 'quotations'::regclass, "
                            "'quotation_revisions'::regclass, 'acceptances'::regclass) "
                            "ORDER BY relname"
                        )
                    )
                ).all()
                assert flags == [
                    ("acceptances", True, True),
                    ("enquiries", True, True),
                    ("quotation_revisions", True, True),
                    ("quotations", True, True),
                ]
            async with app.connect() as connection:
                assert (
                    await connection.execute(text("SELECT count(*) FROM enquiries"))
                ).scalar_one() == 0
            async with app.begin() as connection:
                await connection.execute(
                    text(
                        "SELECT set_config('app.current_organization_id', :organization_id, true)"
                    ),
                    {"organization_id": organization_id},
                )
                assert (
                    await connection.execute(text("SELECT count(*) FROM enquiries"))
                ).scalar_one() == 1
            async with app.begin() as connection:
                await connection.execute(
                    text(
                        "SELECT set_config('app.current_organization_id', :organization_id, true)"
                    ),
                    {"organization_id": other_organization_id},
                )
                assert (
                    await connection.execute(text("SELECT count(*) FROM enquiries"))
                ).scalar_one() == 0
        finally:
            await app.dispose()
            await admin.dispose()

    try:
        asyncio.run(exercise())
        assert alembic_current_branch(url) == HEAD
    finally:
        drop_disposable_database(name)
