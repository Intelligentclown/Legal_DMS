"""Real-PostgreSQL migration evidence for T141's bounded schema foundation."""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine

from app.infrastructure.config import get_settings
from tests.integration.test_t137_file_document_tenant_foundation import _seed_legacy_document
from tests.integration.test_t138_file_migration_and_allocator import _alembic
from tests.support.synthetic_migration import (
    alembic_current_branch,
    drop_disposable_database,
    provision_disposable_database_with,
)

PARENT = "be439c0d6fdb"
HEAD = "cdcfd7df5fde"

_INSERT_STORAGE = text(
    "INSERT INTO file_storage_records "
    "(id, storage_provider, file_path, original_filename, size_bytes, checksum_sha256) "
    "VALUES (CAST(:id AS uuid), 'local', :path, :filename, 1, :hash)"
)
_INSERT_VERSION = text(
    "INSERT INTO document_versions (id, document_id, version_number, file_storage_record_id) "
    "VALUES (CAST(:id AS uuid), CAST(:document AS uuid), 1, CAST(:storage AS uuid))"
)
_INSERT_TEMPLATE = text(
    "INSERT INTO document_templates (id, document_type_id, name, file_storage_record_id) "
    "VALUES (CAST(:id AS uuid), CAST(:type AS uuid), 'T', CAST(:storage AS uuid))"
)


def _app_url(url: str) -> str:
    app_database_url = make_url(get_settings().app_database_url)
    return (
        make_url(url)
        .set(username=app_database_url.username, password=app_database_url.password)
        .render_as_string(hide_password=False)
    )


async def _seed_version_storage(url: str, ids: dict[str, str]) -> tuple[str, str]:
    storage_id, version_id = str(uuid4()), str(uuid4())
    engine = create_async_engine(url)
    try:
        async with engine.begin() as connection:
            await connection.execute(
                _INSERT_STORAGE,
                {"id": storage_id, "path": "v", "filename": "v", "hash": "a" * 64},
            )
            await connection.execute(
                _INSERT_VERSION,
                {"id": version_id, "document": ids["document"], "storage": storage_id},
            )
    finally:
        await engine.dispose()
    return storage_id, version_id


async def _seed_non_version_storage(url: str, ids: dict[str, str], consumer_table: str) -> str:
    storage_id = str(uuid4())
    engine = create_async_engine(url)
    try:
        async with engine.begin() as connection:
            await connection.execute(
                _INSERT_STORAGE,
                {"id": storage_id, "path": "n", "filename": "n", "hash": "b" * 64},
            )
            if consumer_table == "document_templates":
                statement = _INSERT_TEMPLATE
                values = {"id": str(uuid4()), "type": ids["doc_type"], "storage": storage_id}
            elif consumer_table == "qr_code_records":
                statement = text(
                    "INSERT INTO qr_code_records "
                    "(id, entity_type, entity_id, code_value, qr_image_file_storage_record_id) "
                    "VALUES (CAST(:id AS uuid), 'x', CAST(:entity AS uuid), :code, "
                    "CAST(:storage AS uuid))"
                )
                values = {
                    "id": str(uuid4()),
                    "entity": str(uuid4()),
                    "code": str(uuid4()),
                    "storage": storage_id,
                }
            else:
                payment_method_id, payment_id = str(uuid4()), str(uuid4())
                await connection.execute(
                    text(
                        "INSERT INTO payment_methods (id, code, name) "
                        "VALUES (CAST(:id AS uuid), :code, 'T141')"
                    ),
                    {"id": payment_method_id, "code": f"T141-{uuid4()}"},
                )
                await connection.execute(
                    text(
                        "INSERT INTO payments "
                        "(id, organization_id, matter_id, client_id, payment_method_id, amount, "
                        "status, paid_at) VALUES (CAST(:id AS uuid), CAST(:org AS uuid), "
                        "CAST(:matter AS uuid), CAST(:client AS uuid), CAST(:method AS uuid), "
                        "1, 'completed', now())"
                    ),
                    {
                        "id": payment_id,
                        "org": ids["org"],
                        "matter": ids["matter"],
                        "client": ids["client"],
                        "method": payment_method_id,
                    },
                )
                statement = text(
                    "INSERT INTO receipts "
                    "(id, payment_id, receipt_number, issued_at, file_storage_record_id) "
                    "VALUES (CAST(:id AS uuid), CAST(:payment AS uuid), :number, now(), "
                    "CAST(:storage AS uuid))"
                )
                values = {
                    "id": str(uuid4()),
                    "payment": payment_id,
                    "number": f"R-{uuid4()}",
                    "storage": storage_id,
                }
            await connection.execute(statement, values)
    finally:
        await engine.dispose()
    return storage_id


def test_fresh_install_reaches_t141_sole_head() -> None:
    url, name = provision_disposable_database_with("legal_dms_t141_fresh", upgrade_target=HEAD)
    try:
        assert alembic_current_branch(url) == HEAD
    finally:
        drop_disposable_database(name)


def test_upgrade_backfills_version_storage_and_preserves_non_version_storage() -> None:
    url, name = provision_disposable_database_with("legal_dms_t141", upgrade_target=PARENT)
    try:
        ids = asyncio.run(_seed_legacy_document(url, at_head=True))

        async def exercise() -> None:
            engine = create_async_engine(url)
            try:
                async with engine.begin() as connection:
                    storage_id, template_id, version_id, template_row_id = map(
                        str, (uuid4(), uuid4(), uuid4(), uuid4())
                    )
                    await connection.execute(
                        _INSERT_STORAGE,
                        {"id": storage_id, "path": "v", "filename": "v", "hash": "a" * 64},
                    )
                    await connection.execute(
                        _INSERT_STORAGE,
                        {"id": template_id, "path": "t", "filename": "t", "hash": "b" * 64},
                    )
                    await connection.execute(
                        _INSERT_VERSION,
                        {"id": version_id, "document": ids["document"], "storage": storage_id},
                    )
                    await connection.execute(
                        _INSERT_TEMPLATE,
                        {"id": template_row_id, "type": ids["doc_type"], "storage": template_id},
                    )
            finally:
                await engine.dispose()

        asyncio.run(exercise())
        result = _alembic(url, "upgrade", HEAD)
        assert result.returncode == 0, result.stdout + result.stderr

        async def verify() -> None:
            engine = create_async_engine(url)
            try:
                async with engine.connect() as connection:
                    assert (
                        await connection.execute(
                            text("SELECT organization_id::text FROM document_versions LIMIT 1")
                        )
                    ).scalar_one() == ids["org"]
                    assert (
                        await connection.execute(
                            text(
                                "SELECT count(*) FROM file_storage_records "
                                "WHERE organization_id IS NULL"
                            )
                        )
                    ).scalar_one() == 1
            finally:
                await engine.dispose()

        asyncio.run(verify())
        assert alembic_current_branch(url) == HEAD
    finally:
        drop_disposable_database(name)


@pytest.mark.parametrize(
    "consumer_table",
    [
        "document_templates",
        "qr_code_records",
        "receipts",
    ],
)
def test_upgrade_rejects_version_storage_shared_with_other_consumer(
    consumer_table: str,
) -> None:
    url, name = provision_disposable_database_with("legal_dms_t141_shared", upgrade_target=PARENT)
    try:
        ids = asyncio.run(_seed_legacy_document(url, at_head=True))

        async def seed() -> None:
            engine = create_async_engine(url)
            try:
                async with engine.begin() as connection:
                    storage_id, version_id = str(uuid4()), str(uuid4())
                    await connection.execute(
                        _INSERT_STORAGE,
                        {"id": storage_id, "path": "v", "filename": "v", "hash": "a" * 64},
                    )
                    await connection.execute(
                        _INSERT_VERSION,
                        {"id": version_id, "document": ids["document"], "storage": storage_id},
                    )
                    if consumer_table == "document_templates":
                        statement = _INSERT_TEMPLATE
                        values = {
                            "id": str(uuid4()),
                            "type": ids["doc_type"],
                            "storage": storage_id,
                        }
                    elif consumer_table == "qr_code_records":
                        statement = text(
                            "INSERT INTO qr_code_records (id, entity_type, entity_id, code_value, "
                            "qr_image_file_storage_record_id) VALUES (CAST(:id AS uuid), 'x', "
                            "CAST(:entity AS uuid), :code, CAST(:storage AS uuid))"
                        )
                        values = {
                            "id": str(uuid4()),
                            "entity": str(uuid4()),
                            "code": str(uuid4()),
                            "storage": storage_id,
                        }
                    else:
                        payment_method_id, payment_id = str(uuid4()), str(uuid4())
                        await connection.execute(
                            text(
                                "INSERT INTO payment_methods (id, code, name) "
                                "VALUES (CAST(:id AS uuid), :code, 'T141')"
                            ),
                            {"id": payment_method_id, "code": f"T141-{uuid4()}"},
                        )
                        await connection.execute(
                            text(
                                "INSERT INTO payments (id, organization_id, matter_id, client_id, "
                                "payment_method_id, amount, status, paid_at) VALUES "
                                "(CAST(:id AS uuid), "
                                "CAST(:org AS uuid), CAST(:matter AS uuid), CAST(:client AS uuid), "
                                "CAST(:method AS uuid), 1, 'completed', now())"
                            ),
                            {
                                "id": payment_id,
                                "org": ids["org"],
                                "matter": ids["matter"],
                                "client": ids["client"],
                                "method": payment_method_id,
                            },
                        )
                        statement = text(
                            "INSERT INTO receipts (id, payment_id, receipt_number, issued_at, "
                            "file_storage_record_id) VALUES (CAST(:id AS uuid), "
                            "CAST(:payment AS uuid), "
                            ":number, now(), CAST(:storage AS uuid))"
                        )
                        values = {
                            "id": str(uuid4()),
                            "payment": payment_id,
                            "number": f"R-{uuid4()}",
                            "storage": storage_id,
                        }
                    await connection.execute(statement, values)
            finally:
                await engine.dispose()

        asyncio.run(seed())
        result = _alembic(url, "upgrade", HEAD)
        assert result.returncode != 0
        assert alembic_current_branch(url) == PARENT
    finally:
        drop_disposable_database(name)


@pytest.mark.parametrize("consumer_table", ["document_templates", "qr_code_records", "receipts"])
def test_upgrade_preserves_non_version_storage_without_tenant_inference(
    consumer_table: str,
) -> None:
    url, name = provision_disposable_database_with(
        "legal_dms_t141_non_version", upgrade_target=PARENT
    )
    try:
        ids = asyncio.run(_seed_legacy_document(url, at_head=True))
        storage_id = asyncio.run(_seed_non_version_storage(url, ids, consumer_table))
        result = _alembic(url, "upgrade", HEAD)
        assert result.returncode == 0, result.stdout + result.stderr

        async def verify() -> None:
            engine = create_async_engine(url)
            try:
                async with engine.connect() as connection:
                    assert (
                        await connection.execute(
                            text(
                                "SELECT organization_id FROM file_storage_records "
                                "WHERE id = CAST(:id AS uuid)"
                            ),
                            {"id": storage_id},
                        )
                    ).scalar_one() is None
                    if consumer_table == "document_templates":
                        column = "file_storage_record_id"
                    elif consumer_table == "qr_code_records":
                        column = "qr_image_file_storage_record_id"
                    else:
                        column = "file_storage_record_id"
                    assert (
                        await connection.execute(
                            text(
                                f"SELECT count(*) FROM {consumer_table} "
                                f"WHERE {column} = CAST(:id AS uuid)"
                            ),
                            {"id": storage_id},
                        )
                    ).scalar_one() == 1
            finally:
                await engine.dispose()

        asyncio.run(verify())
    finally:
        drop_disposable_database(name)


def test_t141_idempotency_constraints_and_forced_rls() -> None:
    url, name = provision_disposable_database_with("legal_dms_t141_security", upgrade_target=PARENT)
    try:
        ids = asyncio.run(_seed_legacy_document(url, at_head=True))
        storage_id, version_id = asyncio.run(_seed_version_storage(url, ids))
        result = _alembic(url, "upgrade", HEAD)
        assert result.returncode == 0, result.stdout + result.stderr

        async def exercise() -> None:
            admin = create_async_engine(url)
            app = create_async_engine(_app_url(url))
            try:
                async with admin.connect() as connection:
                    flags = (
                        await connection.execute(
                            text(
                                "SELECT relname, relrowsecurity, relforcerowsecurity "
                                "FROM pg_class WHERE oid IN ("
                                "'document_versions'::regclass, "
                                "'file_storage_records'::regclass, "
                                "'document_version_idempotency_keys'::regclass) "
                                "ORDER BY relname"
                            )
                        )
                    ).all()
                    assert flags == [
                        ("document_version_idempotency_keys", True, True),
                        ("document_versions", True, True),
                        ("file_storage_records", True, True),
                    ]
                    owner, rolsuper, rolbypassrls = (
                        await connection.execute(
                            text(
                                "SELECT t.tableowner, r.rolsuper, r.rolbypassrls "
                                "FROM pg_tables t JOIN pg_roles r "
                                "ON r.rolname = 'legal_dms_app' "
                                "WHERE t.tablename = 'document_versions'"
                            )
                        )
                    ).one()
                    assert owner != "legal_dms_app"
                    assert rolsuper is False
                    assert rolbypassrls is False
                async with app.connect() as connection:
                    assert (
                        await connection.execute(text("SELECT count(*) FROM document_versions"))
                    ).scalar_one() == 0
                    assert (
                        await connection.execute(text("SELECT count(*) FROM file_storage_records"))
                    ).scalar_one() == 0
                async with app.connect() as connection, connection.begin():
                    await connection.execute(
                        text("SELECT set_config('app.current_organization_id', :org, true)"),
                        {"org": ids["other"]},
                    )
                    assert (
                        await connection.execute(text("SELECT count(*) FROM document_versions"))
                    ).scalar_one() == 0
                idempotency_id = str(uuid4())
                async with app.begin() as connection:
                    await connection.execute(
                        text("SELECT set_config('app.current_organization_id', :org, true)"),
                        {"org": ids["org"]},
                    )
                    assert (
                        await connection.execute(text("SELECT count(*) FROM document_versions"))
                    ).scalar_one() == 1
                    await connection.execute(
                        text(
                            "INSERT INTO document_version_idempotency_keys "
                            "(id, organization_id, document_id, idempotency_key, "
                            "payload_fingerprint, document_version_id) VALUES "
                            "(CAST(:id AS uuid), CAST(:org AS uuid), CAST(:document AS uuid), "
                            ":key, :fingerprint, CAST(:version AS uuid))"
                        ),
                        {
                            "id": idempotency_id,
                            "org": ids["org"],
                            "document": ids["document"],
                            "key": "retry-key",
                            "fingerprint": "c" * 64,
                            "version": version_id,
                        },
                    )
                async with app.begin() as connection:
                    await connection.execute(
                        text("SELECT set_config('app.current_organization_id', :org, true)"),
                        {"org": ids["org"]},
                    )
                    with pytest.raises(IntegrityError):
                        await connection.execute(
                            text(
                                "INSERT INTO document_version_idempotency_keys "
                                "(id, organization_id, document_id, idempotency_key, "
                                "payload_fingerprint, document_version_id) VALUES "
                                "(CAST(:id AS uuid), CAST(:org AS uuid), CAST(:document AS uuid), "
                                ":key, :fingerprint, CAST(:version AS uuid))"
                            ),
                            {
                                "id": str(uuid4()),
                                "org": ids["org"],
                                "document": ids["document"],
                                "key": "retry-key",
                                "fingerprint": "d" * 64,
                                "version": version_id,
                            },
                        )
                async with app.begin() as connection:
                    await connection.execute(
                        text("SELECT set_config('app.current_organization_id', :org, true)"),
                        {"org": ids["other"]},
                    )
                    with pytest.raises(IntegrityError):
                        await connection.execute(
                            text(
                                "INSERT INTO document_versions "
                                "(id, organization_id, document_id, version_number, "
                                "file_storage_record_id) VALUES "
                                "(CAST(:id AS uuid), CAST(:org AS uuid), "
                                "CAST(:document AS uuid), 2, CAST(:storage AS uuid))"
                            ),
                            {
                                "id": str(uuid4()),
                                "org": ids["other"],
                                "document": ids["document"],
                                "storage": storage_id,
                            },
                        )
                async with app.begin() as connection:
                    await connection.execute(
                        text("SELECT set_config('app.current_organization_id', :org, true)"),
                        {"org": ids["org"]},
                    )
                    with pytest.raises(IntegrityError):
                        await connection.execute(
                            text(
                                "INSERT INTO document_versions "
                                "(id, organization_id, document_id, version_number, "
                                "file_storage_record_id) VALUES "
                                "(CAST(:id AS uuid), CAST(:org AS uuid), "
                                "CAST(:document AS uuid), 2, CAST(:storage AS uuid))"
                            ),
                            {
                                "id": str(uuid4()),
                                "org": ids["org"],
                                "document": ids["document"],
                                "storage": storage_id,
                            },
                        )
                async with app.begin() as connection:
                    await connection.execute(
                        text("SELECT set_config('app.current_organization_id', :org, true)"),
                        {"org": ids["other"]},
                    )
                    with pytest.raises(IntegrityError):
                        await connection.execute(
                            text(
                                "INSERT INTO document_version_idempotency_keys "
                                "(id, organization_id, document_id, idempotency_key, "
                                "payload_fingerprint, document_version_id) VALUES "
                                "(CAST(:id AS uuid), CAST(:org AS uuid), "
                                "CAST(:document AS uuid), :key, :fingerprint, "
                                "CAST(:version AS uuid))"
                            ),
                            {
                                "id": str(uuid4()),
                                "org": ids["other"],
                                "document": ids["document"],
                                "key": "wrong-tenant",
                                "fingerprint": "e" * 64,
                                "version": version_id,
                            },
                        )
            finally:
                await app.dispose()
                await admin.dispose()

        asyncio.run(exercise())
    finally:
        drop_disposable_database(name)


def test_t141_downgrade_allows_empty_foundation_and_refuses_tenant_evidence() -> None:
    url, name = provision_disposable_database_with(
        "legal_dms_t141_downgrade", upgrade_target=PARENT
    )
    try:
        assert _alembic(url, "upgrade", HEAD).returncode == 0
        result = _alembic(url, "downgrade", PARENT)
        assert result.returncode == 0, result.stdout + result.stderr
        assert alembic_current_branch(url) == PARENT

        ids = asyncio.run(_seed_legacy_document(url, at_head=True))
        asyncio.run(_seed_version_storage(url, ids))
        assert _alembic(url, "upgrade", HEAD).returncode == 0
        result = _alembic(url, "downgrade", PARENT)
        assert result.returncode != 0
        assert "cannot downgrade T141" in (result.stdout + result.stderr)
        assert alembic_current_branch(url) == HEAD
    finally:
        drop_disposable_database(name)
