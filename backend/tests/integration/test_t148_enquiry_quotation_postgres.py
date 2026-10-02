"""T148 PostgreSQL migration and tenant-RLS coverage on disposable databases."""

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
from sqlalchemy.ext.asyncio import create_async_engine

from app.infrastructure.config import get_settings
from tests.support.synthetic_migration import (
    alembic_current_branch,
    drop_disposable_database,
    provision_disposable_database_with,
)

HEAD = "8d77007b9d7f"
PARENT = "e148c0f5a8b2"
BACKEND_DIR = Path(__file__).resolve().parents[2]


def _app_url(url: str) -> str:
    app = make_url(get_settings().app_database_url)
    return (
        make_url(url)
        .set(username=app.username, password=app.password)
        .render_as_string(hide_password=False)
    )


def _alembic(url: str, command: str, target: str) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    environment["DATABASE_URL"] = url
    environment["PYTHONPATH"] = str(BACKEND_DIR / "src")
    return subprocess.run(
        [sys.executable, "-m", "alembic", command, target],
        cwd=BACKEND_DIR,
        env=environment,
        capture_output=True,
        text=True,
    )


async def _seed_t150_revision(url: str) -> dict[str, str]:
    """Create only the existing T148 hierarchy needed to exercise persistence."""
    ids = {
        name: str(uuid4())
        for name in ("organization", "user", "party", "enquiry", "quotation", "revision", "matter")
    }
    engine = create_async_engine(url)
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text("INSERT INTO organizations (id, name) VALUES (CAST(:id AS uuid), :name)"),
                {"id": ids["organization"], "name": f"T150 {ids['organization']}"},
            )
            await connection.execute(
                text(
                    "INSERT INTO users (id, email, full_name, is_active, organization_id) VALUES "
                    "(CAST(:id AS uuid), :email, 'T150 issuer', true, CAST(:organization AS uuid))"
                ),
                {
                    "id": ids["user"],
                    "email": f"t150-{ids['user']}@example.test",
                    "organization": ids["organization"],
                },
            )
            await connection.execute(
                text(
                    "INSERT INTO parties (id, organization_id, party_type, display_name, primary_phone) "
                    "VALUES (CAST(:id AS uuid), CAST(:organization AS uuid), 'individual', 'T150 party', '9876543210')"
                ),
                {"id": ids["party"], "organization": ids["organization"]},
            )
            await connection.execute(
                text(
                    "INSERT INTO enquiries (id, organization_id, party_id) VALUES "
                    "(CAST(:id AS uuid), CAST(:organization AS uuid), CAST(:party AS uuid))"
                ),
                {"id": ids["enquiry"], "organization": ids["organization"], "party": ids["party"]},
            )
            await connection.execute(
                text(
                    "INSERT INTO quotations (id, organization_id, enquiry_id) VALUES "
                    "(CAST(:id AS uuid), CAST(:organization AS uuid), CAST(:enquiry AS uuid))"
                ),
                {
                    "id": ids["quotation"],
                    "organization": ids["organization"],
                    "enquiry": ids["enquiry"],
                },
            )
            await connection.execute(
                text(
                    "INSERT INTO quotation_revisions (id, organization_id, quotation_id, ordinal, proposal_snapshot) "
                    'VALUES (CAST(:id AS uuid), CAST(:organization AS uuid), CAST(:quotation AS uuid), 1, \'{"scope": "T150"}\'::jsonb)'
                ),
                {
                    "id": ids["revision"],
                    "organization": ids["organization"],
                    "quotation": ids["quotation"],
                },
            )
            await connection.execute(
                text(
                    "INSERT INTO matters (id, organization_id, matter_number, matter_type_id, matter_status_id, "
                    "title, opened_at) VALUES (CAST(:id AS uuid), CAST(:organization AS uuid), :number, "
                    "(SELECT id FROM matter_types ORDER BY code LIMIT 1), "
                    "(SELECT id FROM matter_statuses ORDER BY code LIMIT 1), 'T150 matter', now())"
                ),
                {
                    "id": ids["matter"],
                    "organization": ids["organization"],
                    "number": f"T150-{ids['matter']}",
                },
            )
    finally:
        await engine.dispose()
    return ids


async def _reject(url: str, statement: str, values: dict[str, str]) -> None:
    engine = create_async_engine(url)
    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            with pytest.raises(Exception, match=r"QuotationRevision|immutable"):
                await connection.execute(text(statement), values)
            await transaction.rollback()
    finally:
        await engine.dispose()


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


def test_t150_upgrade_from_populated_t148_permits_only_one_issuance_transition() -> None:
    url, name = provision_disposable_database_with("legal_dms_t150_upgrade", upgrade_target=PARENT)
    try:
        ids = asyncio.run(_seed_t150_revision(url))
        result = _alembic(url, "upgrade", HEAD)
        assert result.returncode == 0, result.stdout + result.stderr
        ids.update(
            partial_revision=str(uuid4()),
            content_revision=str(uuid4()),
            provenance_revision=str(uuid4()),
        )

        async def exercise() -> None:
            engine = create_async_engine(url)
            try:
                async with engine.begin() as connection:
                    for revision_id, ordinal in (
                        (ids["partial_revision"], 2),
                        (ids["content_revision"], 3),
                        (ids["provenance_revision"], 4),
                    ):
                        await connection.execute(
                            text(
                                "INSERT INTO quotation_revisions "
                                "(id, organization_id, quotation_id, ordinal, proposal_snapshot) VALUES "
                                "(CAST(:id AS uuid), CAST(:organization AS uuid), "
                                'CAST(:quotation AS uuid), :ordinal, \'{"scope": "T150"}\'::jsonb)'
                            ),
                            {
                                "id": revision_id,
                                "organization": ids["organization"],
                                "quotation": ids["quotation"],
                                "ordinal": ordinal,
                            },
                        )
                    await connection.execute(
                        text(
                            "UPDATE quotation_revisions SET issued_at = now(), issued_by = CAST(:user AS uuid) "
                            "WHERE id = CAST(:revision AS uuid)"
                        ),
                        {"user": ids["user"], "revision": ids["revision"]},
                    )
                    issued = (
                        await connection.execute(
                            text(
                                "SELECT issued_at IS NOT NULL, issued_by::text FROM quotation_revisions WHERE id = CAST(:revision AS uuid)"
                            ),
                            {"revision": ids["revision"]},
                        )
                    ).one()
                    assert issued == (True, ids["user"])
                    await connection.execute(
                        text(
                            "INSERT INTO acceptances (id, organization_id, enquiry_id, quotation_id, quotation_revision_id, "
                            "matter_id, accepted_by, idempotency_key, request_fingerprint) VALUES "
                            "(CAST(:id AS uuid), CAST(:organization AS uuid), CAST(:enquiry AS uuid), CAST(:quotation AS uuid), "
                            "CAST(:revision AS uuid), CAST(:matter AS uuid), CAST(:user AS uuid), 't150', :fingerprint)"
                        ),
                        {**ids, "id": str(uuid4()), "fingerprint": "a" * 64},
                    )
            finally:
                await engine.dispose()

        asyncio.run(exercise())
        asyncio.run(
            _reject(
                url,
                "UPDATE quotation_revisions SET issued_at = now() WHERE id = CAST(:partial_revision AS uuid)",
                ids,
            )
        )
        asyncio.run(
            _reject(
                url,
                "UPDATE quotation_revisions SET issued_by = CAST(:user AS uuid) WHERE id = CAST(:partial_revision AS uuid)",
                ids,
            )
        )
        asyncio.run(
            _reject(
                url,
                'UPDATE quotation_revisions SET proposal_snapshot = \'{"scope": "changed"}\'::jsonb, '
                "issued_at = now(), issued_by = CAST(:user AS uuid) "
                "WHERE id = CAST(:content_revision AS uuid)",
                ids,
            )
        )
        asyncio.run(
            _reject(
                url,
                "UPDATE quotation_revisions SET ordinal = 5 WHERE id = CAST(:partial_revision AS uuid)",
                ids,
            )
        )
        asyncio.run(
            _reject(
                url,
                "UPDATE quotation_revisions SET created_by = CAST(:user AS uuid), issued_at = now(), "
                "issued_by = CAST(:user AS uuid) WHERE id = CAST(:provenance_revision AS uuid)",
                ids,
            )
        )
        asyncio.run(
            _reject(url, "DELETE FROM quotation_revisions WHERE id = CAST(:revision AS uuid)", ids)
        )
        asyncio.run(
            _reject(
                url,
                "UPDATE quotation_revisions SET issued_at = NULL, issued_by = NULL WHERE id = CAST(:revision AS uuid)",
                ids,
            )
        )
        asyncio.run(
            _reject(
                url,
                "UPDATE quotation_revisions SET issued_at = now() WHERE id = CAST(:revision AS uuid)",
                ids,
            )
        )
        asyncio.run(
            _reject(
                url,
                "UPDATE quotation_revisions SET issued_by = CAST(:user AS uuid) WHERE id = CAST(:revision AS uuid)",
                ids,
            )
        )

        async def acceptance_is_immutable() -> None:
            engine = create_async_engine(url)
            try:
                async with engine.connect() as connection:
                    acceptance_id = (
                        await connection.execute(text("SELECT id FROM acceptances LIMIT 1"))
                    ).scalar_one()
                    await connection.commit()
                    for statement in (
                        "UPDATE acceptances SET idempotency_key = 'changed' WHERE id = :id",
                        "DELETE FROM acceptances WHERE id = :id",
                    ):
                        transaction = await connection.begin()
                        with pytest.raises(
                            Exception, match="T148 quotation/acceptance evidence is immutable"
                        ):
                            await connection.execute(text(statement), {"id": acceptance_id})
                        await transaction.rollback()
            finally:
                await engine.dispose()

        asyncio.run(acceptance_is_immutable())
        assert alembic_current_branch(url) == HEAD
    finally:
        drop_disposable_database(name)


def test_t150_fresh_chain_and_empty_downgrade_restore_t148_trigger() -> None:
    url, name = provision_disposable_database_with("legal_dms_t150_chain", upgrade_target=HEAD)
    try:
        assert alembic_current_branch(url) == HEAD
        result = _alembic(url, "downgrade", PARENT)
        assert result.returncode == 0, result.stdout + result.stderr
        assert alembic_current_branch(url) == PARENT
    finally:
        drop_disposable_database(name)
