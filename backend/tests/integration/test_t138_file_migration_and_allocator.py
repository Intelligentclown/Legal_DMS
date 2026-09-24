"""Real-PostgreSQL T138 migration and ADR-0027 allocator evidence."""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.infrastructure.persistence.models.file import File
from app.infrastructure.persistence.sqlalchemy_file_repository import SqlAlchemyFileRepository
from tests.integration.test_t137_file_document_tenant_foundation import _seed_legacy_document
from tests.support.synthetic_migration import (
    alembic_current_branch,
    drop_disposable_database,
    provision_disposable_database_with,
)

PARENT = "b8c4d2e1f7a9"
HEAD = "be439c0d6fdb"
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


def test_file_permission_upgrade_and_downgrade_are_exact() -> None:
    url, name = provision_disposable_database_with("legal_dms_t138_rbac", upgrade_target=PARENT)
    try:
        result = _alembic(url, "upgrade", HEAD)
        assert result.returncode == 0, result.stdout + result.stderr
        assert alembic_current_branch(url) == HEAD

        async def verify() -> None:
            engine = create_async_engine(url)
            try:
                async with engine.connect() as conn:
                    permissions = (
                        await conn.execute(
                            text(
                                "SELECT code, description, category FROM permissions "
                                "WHERE code LIKE 'files:%' ORDER BY code"
                            )
                        )
                    ).all()
                    assert permissions == [
                        ("files:read", "View files", "files"),
                        ("files:write", "Create and edit files", "files"),
                    ]
                    grants = (
                        await conn.execute(
                            text(
                                "SELECT r.name, p.code FROM role_permissions rp "
                                "JOIN roles r ON r.id=rp.role_id "
                                "JOIN permissions p ON p.id=rp.permission_id "
                                "WHERE p.code LIKE 'files:%' ORDER BY r.name, p.code"
                            )
                        )
                    ).all()
                    assert grants == [
                        ("Accountant", "files:read"),
                        ("Administrator", "files:read"),
                        ("Administrator", "files:write"),
                        ("Advocate", "files:read"),
                        ("Advocate", "files:write"),
                        ("Clerk", "files:read"),
                        ("Clerk", "files:write"),
                        ("Paralegal", "files:read"),
                        ("Paralegal", "files:write"),
                        ("Read Only", "files:read"),
                    ]
            finally:
                await engine.dispose()

        asyncio.run(verify())
        result = _alembic(url, "downgrade", PARENT)
        assert result.returncode == 0, result.stdout + result.stderr
        assert alembic_current_branch(url) == PARENT
    finally:
        drop_disposable_database(name)


def test_same_matter_concurrent_allocation_is_unique_and_rollback_reuses_number() -> None:
    url, name = provision_disposable_database_with("legal_dms_t138_allocator", upgrade_target=HEAD)
    try:
        ids = asyncio.run(_seed_legacy_document(url, at_head=True))

        async def exercise() -> None:
            engine = create_async_engine(url)
            factory = async_sessionmaker(engine, expire_on_commit=False)

            async def create(title: str) -> int:
                async with factory() as session:
                    repository = SqlAlchemyFileRepository(session)
                    file = File(
                        id=uuid4(),
                        organization_id=ids["org"],
                        matter_id=ids["matter"],
                        file_number=0,
                        title=title,
                    )
                    await repository.allocate_and_add(file)
                    await session.commit()
                    return file.file_number

            try:
                numbers = await asyncio.gather(
                    *(create(f"concurrent-{index}") for index in range(12))
                )
                assert sorted(numbers) == list(range(1, 13))
                async with factory() as session:
                    repository = SqlAlchemyFileRepository(session)
                    transient = File(
                        id=uuid4(),
                        organization_id=ids["org"],
                        matter_id=ids["matter"],
                        file_number=0,
                        title="rollback",
                    )
                    await repository.allocate_and_add(transient)
                    assert transient.file_number == 13
                    await session.rollback()
                assert await create("reused") == 13
            finally:
                await engine.dispose()

        asyncio.run(exercise())
    finally:
        drop_disposable_database(name)
