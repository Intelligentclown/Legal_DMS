"""T137 migration, integrity, downgrade, and RLS coverage on disposable PostgreSQL."""

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

PARENT = "9e6a4b2c8d1f"
HEAD = "b8c4d2e1f7a9"
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


async def _seed_legacy_document(url: str, *, at_head: bool = False) -> dict[str, str]:
    ids = {
        name: str(uuid4())
        for name in ("org", "other", "client", "type", "status", "matter", "doc_type", "document")
    }
    engine = create_async_engine(url)
    try:
        async with engine.begin() as conn:
            for name in ("org", "other"):
                await conn.execute(
                    text("INSERT INTO organizations (id, name) VALUES (CAST(:id AS uuid), :name)"),
                    {"id": ids[name], "name": name},
                )
            await conn.execute(
                text(
                    "INSERT INTO clients (id, organization_id, client_type, full_name, primary_phone) VALUES (CAST(:id AS uuid), CAST(:org AS uuid), 'individual', 'T137 Client', '9876543210')"
                ),
                {"id": ids["client"], "org": ids["org"]},
            )
            await conn.execute(
                text(
                    "INSERT INTO matter_types (id, code, name) VALUES (CAST(:id AS uuid), 'T137', 'T137')"
                ),
                {"id": ids["type"]},
            )
            await conn.execute(
                text(
                    "INSERT INTO matter_statuses (id, code, name) VALUES (CAST(:id AS uuid), 'T137', 'T137')"
                ),
                {"id": ids["status"]},
            )
            await conn.execute(
                text(
                    "INSERT INTO matters (id, organization_id, matter_number, matter_type_id, matter_status_id, client_id, title, opened_at) VALUES (CAST(:id AS uuid), CAST(:org AS uuid), 'T137-M', CAST(:type AS uuid), CAST(:status AS uuid), CAST(:client AS uuid), 'T137 Matter', now())"
                ),
                {
                    "id": ids["matter"],
                    "org": ids["org"],
                    "type": ids["type"],
                    "status": ids["status"],
                    "client": ids["client"],
                },
            )
            await conn.execute(
                text(
                    "INSERT INTO document_types (id, code, name) VALUES (CAST(:id AS uuid), 'T137', 'T137')"
                ),
                {"id": ids["doc_type"]},
            )
            document_sql = (
                "INSERT INTO documents (id, organization_id, matter_id, document_type_id, title, status) "
                "VALUES (CAST(:id AS uuid), CAST(:org AS uuid), CAST(:matter AS uuid), CAST(:type AS uuid), 'Legacy', 'draft')"
                if at_head
                else "INSERT INTO documents (id, matter_id, document_type_id, title, status) VALUES (CAST(:id AS uuid), CAST(:matter AS uuid), CAST(:type AS uuid), 'Legacy', 'draft')"
            )
            await conn.execute(
                text(document_sql),
                {
                    "id": ids["document"],
                    "org": ids["org"],
                    "matter": ids["matter"],
                    "type": ids["doc_type"],
                },
            )
    finally:
        await engine.dispose()
    return ids


def test_upgrade_backfills_only_matter_organization_and_creates_no_files() -> None:
    url, name = provision_disposable_database_with("legal_dms_t137_upgrade", upgrade_target=PARENT)
    try:
        ids = asyncio.run(_seed_legacy_document(url))
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
                                "SELECT organization_id::text FROM documents WHERE id = CAST(:id AS uuid)"
                            ),
                            {"id": ids["document"]},
                        )
                    ).scalar_one() == ids["org"]
                    assert (
                        await conn.execute(
                            text("SELECT file_id FROM documents WHERE id = CAST(:id AS uuid)"),
                            {"id": ids["document"]},
                        )
                    ).scalar_one() is None
                    assert (
                        await conn.execute(text("SELECT count(*) FROM files"))
                    ).scalar_one() == 0
                    assert (
                        await conn.execute(text("SELECT count(*) FROM file_number_sequences"))
                    ).scalar_one() == 0
            finally:
                await engine.dispose()

        asyncio.run(verify())
    finally:
        drop_disposable_database(name)


def test_file_document_composite_tenant_and_matter_constraints() -> None:
    url, name = provision_disposable_database_with("legal_dms_t137_integrity", upgrade_target=HEAD)
    try:
        ids = asyncio.run(_seed_legacy_document(url, at_head=True))

        async def exercise() -> None:
            engine = create_async_engine(url)
            file_id, other_file_id = str(uuid4()), str(uuid4())
            try:
                async with engine.begin() as conn:
                    await conn.execute(
                        text(
                            "INSERT INTO files (id, organization_id, matter_id, file_number, title) VALUES (CAST(:id AS uuid), CAST(:org AS uuid), CAST(:matter AS uuid), 1, 'File')"
                        ),
                        {"id": file_id, "org": ids["org"], "matter": ids["matter"]},
                    )
                async with engine.begin() as conn:
                    with pytest.raises(IntegrityError):
                        await conn.execute(
                            text(
                                "INSERT INTO files (id, organization_id, matter_id, file_number, title) VALUES (CAST(:id AS uuid), CAST(:org AS uuid), CAST(:matter AS uuid), 2, 'Bad')"
                            ),
                            {"id": other_file_id, "org": ids["other"], "matter": ids["matter"]},
                        )
                async with engine.begin() as conn:
                    await conn.execute(
                        text(
                            "UPDATE documents SET file_id = CAST(:file AS uuid) WHERE id = CAST(:doc AS uuid)"
                        ),
                        {"file": file_id, "doc": ids["document"]},
                    )
                async with engine.begin() as conn:
                    with pytest.raises(IntegrityError):
                        await conn.execute(
                            text(
                                "UPDATE documents SET organization_id = CAST(:org AS uuid) WHERE id = CAST(:doc AS uuid)"
                            ),
                            {"org": ids["other"], "doc": ids["document"]},
                        )
            finally:
                await engine.dispose()

        asyncio.run(exercise())
    finally:
        drop_disposable_database(name)


def test_downgrade_refuses_file_state_and_allows_empty_foundation() -> None:
    url, name = provision_disposable_database_with("legal_dms_t137_downgrade", upgrade_target=HEAD)
    try:
        assert _alembic(url, "downgrade", PARENT).returncode == 0
        assert alembic_current_branch(url) == PARENT
        assert _alembic(url, "upgrade", HEAD).returncode == 0
        ids = asyncio.run(_seed_legacy_document(url, at_head=True))

        async def add_file() -> None:
            engine = create_async_engine(url)
            try:
                async with engine.begin() as conn:
                    await conn.execute(
                        text(
                            "INSERT INTO files (id, organization_id, matter_id, file_number, title) VALUES (CAST(:id AS uuid), CAST(:org AS uuid), CAST(:matter AS uuid), 1, 'Persisted')"
                        ),
                        {"id": str(uuid4()), "org": ids["org"], "matter": ids["matter"]},
                    )
            finally:
                await engine.dispose()

        asyncio.run(add_file())
        result = _alembic(url, "downgrade", PARENT)
        assert result.returncode != 0
        assert "cannot downgrade T137" in (result.stdout + result.stderr)
    finally:
        drop_disposable_database(name)


def test_file_and_document_rls_are_forced_and_default_deny() -> None:
    url, name = provision_disposable_database_with("legal_dms_t137_rls", upgrade_target=HEAD)
    try:
        ids = asyncio.run(_seed_legacy_document(url, at_head=True))

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
                        text(
                            "INSERT INTO files (id, organization_id, matter_id, file_number, title) VALUES (CAST(:id AS uuid), CAST(:org AS uuid), CAST(:matter AS uuid), 1, 'Secured')"
                        ),
                        {"id": str(uuid4()), "org": ids["org"], "matter": ids["matter"]},
                    )
                    flags = (
                        await conn.execute(
                            text(
                                "SELECT relname, relrowsecurity, relforcerowsecurity FROM pg_class WHERE oid IN ('files'::regclass, 'documents'::regclass) ORDER BY relname"
                            )
                        )
                    ).all()
                    assert flags == [("documents", True, True), ("files", True, True)]
                async with app.connect() as conn:
                    assert (
                        await conn.execute(text("SELECT count(*) FROM files"))
                    ).scalar_one() == 0
                    assert (
                        await conn.execute(text("SELECT count(*) FROM documents"))
                    ).scalar_one() == 0
                async with app.connect() as conn, conn.begin():
                    await conn.execute(
                        text("SELECT set_config('app.current_organization_id', :org, true)"),
                        {"org": ids["org"]},
                    )
                    assert (
                        await conn.execute(text("SELECT count(*) FROM files"))
                    ).scalar_one() == 1
                    assert (
                        await conn.execute(text("SELECT count(*) FROM documents"))
                    ).scalar_one() == 1
            finally:
                await app.dispose()
                await admin.dispose()

        asyncio.run(exercise())
    finally:
        drop_disposable_database(name)
