"""T126 PostgreSQL integration coverage for ADR-0037 provenance bootstrap."""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine

from app.infrastructure.cli.fresh_install_provenance import (
    FreshInstallError,
    establish_fresh_installation,
)
from app.infrastructure.cli.operational_fresh_bootstrap import run_bootstrap
from app.infrastructure.config import get_settings
from tests.support.synthetic_migration import (
    drop_disposable_database,
    provision_disposable_database_with,
    provision_empty_disposable_database,
)

HEAD = "5d8a3f2e9c6b"
EVENTS = "legal_dms_provenance.installation_events"

pytestmark = pytest.mark.asyncio


@pytest.fixture
def blank_database() -> Iterator[tuple[str, str]]:
    url, name = provision_empty_disposable_database("legal_dms_t126_blank")
    try:
        yield url, name
    finally:
        drop_disposable_database(name)


@pytest.fixture
def upgraded_database() -> Iterator[tuple[str, str]]:
    url, name = provision_disposable_database_with("legal_dms_t126_upgrade", upgrade_target=HEAD)
    try:
        yield url, name
    finally:
        drop_disposable_database(name)


async def _event_rows(url: str) -> list[tuple[str, int, str]]:
    engine = create_async_engine(url)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text(f"SELECT event_kind, event_sequence, observed_schema_revision FROM {EVENTS}")
            )
            return [
                (str(kind), int(sequence), str(revision)) for kind, sequence, revision in result
            ]
    finally:
        await engine.dispose()


async def test_fresh_install_binds_birth_to_blank_target(blank_database) -> None:
    url, _name = blank_database
    installation_id = await establish_fresh_installation(url)
    assert installation_id
    assert await _event_rows(url) == [("FRESH_BIRTH", 1, HEAD)]


async def test_existing_empty_upgrade_never_receives_birth(upgraded_database) -> None:
    url, _name = upgraded_database
    assert await _event_rows(url) == []
    with pytest.raises(FreshInstallError):
        await establish_fresh_installation(url)


async def test_bootstrap_is_idempotent_and_rejects_business_rows(blank_database) -> None:
    url, _name = blank_database
    await establish_fresh_installation(url)
    event_id = await run_bootstrap(url)
    assert event_id
    assert await run_bootstrap(url) == event_id
    assert await _event_rows(url) == [
        ("FRESH_BIRTH", 1, HEAD),
        ("OPERATIONAL_FRESH_ENTERED", 2, HEAD),
    ]


async def test_bootstrap_rolls_back_when_parties_make_predicate_nonempty(blank_database) -> None:
    url, _name = blank_database
    await establish_fresh_installation(url)
    engine = create_async_engine(url)
    try:
        organization_id = uuid4()
        async with engine.begin() as conn:
            await conn.execute(
                text("INSERT INTO organizations (id, name) VALUES (:id, :name)"),
                {"id": organization_id, "name": f"T126-{uuid4()}"},
            )
            await conn.execute(
                text(
                    "INSERT INTO parties "
                    "(id, organization_id, party_type, display_name, primary_phone, version) "
                    "VALUES (:id, :organization_id, 'individual', 'T126 Party', '7000000001', 1)"
                ),
                {"id": uuid4(), "organization_id": organization_id},
            )
        with pytest.raises(DBAPIError):
            await run_bootstrap(url)
        assert await _event_rows(url) == [("FRESH_BIRTH", 1, HEAD)]
    finally:
        await engine.dispose()


async def test_provenance_is_append_only(blank_database) -> None:
    url, _name = blank_database
    await establish_fresh_installation(url)
    engine = create_async_engine(url)
    try:
        async with engine.begin() as conn:
            with pytest.raises(DBAPIError):
                await conn.execute(text(f"DELETE FROM {EVENTS}"))
    finally:
        await engine.dispose()


async def test_concurrent_bootstraps_append_only_one_transition(blank_database) -> None:
    url, _name = blank_database
    await establish_fresh_installation(url)
    first, second = await asyncio.gather(run_bootstrap(url), run_bootstrap(url))
    assert first == second
    assert await _event_rows(url) == [
        ("FRESH_BIRTH", 1, HEAD),
        ("OPERATIONAL_FRESH_ENTERED", 2, HEAD),
    ]


async def test_runtime_role_cannot_mutate_or_execute_bootstrap(blank_database) -> None:
    url, _name = blank_database
    await establish_fresh_installation(url)
    app = make_url(get_settings().app_database_url)
    runtime_url = (
        make_url(url)
        .set(
            username=app.username,
            password=app.password,
        )
        .render_as_string(hide_password=False)
    )
    engine = create_async_engine(runtime_url)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT has_table_privilege(current_user, "
                    "'legal_dms_provenance.installation_events', 'INSERT, UPDATE, DELETE'), "
                    "has_function_privilege(current_user, "
                    "'legal_dms_provenance.enter_operational_fresh(uuid)', 'EXECUTE')"
                )
            )
            assert result.one() == (False, False)
    finally:
        await engine.dispose()
