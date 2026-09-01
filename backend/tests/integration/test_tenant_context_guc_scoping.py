"""T105/ADR-0021: regression tests for the `app.current_user_id`/
`app.current_organization_id` Postgres session GUCs' transaction-local
scoping -- the "connection-pool behavior... becomes correctness-relevant"
obligation ADR/0021's Operational Implications names explicitly, verified
directly against a real connection pool rather than assumed from Postgres's
own `set_config(..., true)` documentation alone.

Runs against `get_app_engine()`/`app_database_url` (the restricted
`legal_dms_app` role) -- skips gracefully, mirroring
`test_get_db_transaction_policy.py`'s pattern, if that role isn't
reachable/provisioned yet (`uv run provision-app-role` then
`uv run alembic upgrade head`).
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.infrastructure.database.session import get_app_engine


@pytest.fixture
async def app_engine() -> AsyncGenerator[AsyncEngine, None]:
    get_app_engine.cache_clear()
    engine = get_app_engine()
    try:
        async with engine.connect():
            pass
    except Exception:
        await engine.dispose()
        get_app_engine.cache_clear()
        pytest.skip(
            "legal_dms_app is not reachable/provisioned — run `uv run provision-app-role` "
            "then `uv run alembic upgrade head`."
        )
        return

    yield engine

    await engine.dispose()
    get_app_engine.cache_clear()


class TestSetConfigVisibleWithinItsOwnTransaction:
    async def test_current_setting_reflects_the_value_just_set(
        self, app_engine: AsyncEngine
    ) -> None:
        async with app_engine.connect() as conn, conn.begin():
            await conn.execute(
                text("SELECT set_config('app.current_organization_id', :val, true)").bindparams(
                    val="11111111-1111-1111-1111-111111111111"
                )
            )
            result = await conn.execute(
                text("SELECT current_setting('app.current_organization_id', true)")
            )
            assert result.scalar_one() == "11111111-1111-1111-1111-111111111111"


class TestGucDoesNotLeakAcrossTransactionsOnTheSamePooledConnection:
    async def test_a_new_transaction_sees_the_guc_unset(self, app_engine: AsyncEngine) -> None:
        async with app_engine.connect() as conn:
            async with conn.begin():
                await conn.execute(
                    text("SELECT set_config('app.current_organization_id', :val, true)").bindparams(
                        val="22222222-2222-2222-2222-222222222222"
                    )
                )
                result = await conn.execute(
                    text("SELECT current_setting('app.current_organization_id', true)")
                )
                assert result.scalar_one() == "22222222-2222-2222-2222-222222222222"

            # First transaction committed -- is_local=true means the GUC
            # resets at that boundary, per PostgreSQL's own documented
            # set_config() semantics. A second transaction on the *same*
            # underlying connection object must see it unset again.
            async with conn.begin():
                result = await conn.execute(
                    text("SELECT current_setting('app.current_organization_id', true)")
                )
                assert result.scalar_one() in (None, "")

    async def test_a_rolled_back_transaction_also_does_not_leak_the_guc(
        self, app_engine: AsyncEngine
    ) -> None:
        async with app_engine.connect() as conn:
            trans = await conn.begin()
            await conn.execute(
                text("SELECT set_config('app.current_organization_id', :val, true)").bindparams(
                    val="33333333-3333-3333-3333-333333333333"
                )
            )
            await trans.rollback()

            async with conn.begin():
                result = await conn.execute(
                    text("SELECT current_setting('app.current_organization_id', true)")
                )
                assert result.scalar_one() in (None, "")


class TestNeverSetReturnsNullNotAnError:
    async def test_current_setting_on_a_fresh_session_is_null(
        self, app_engine: AsyncEngine
    ) -> None:
        async with app_engine.connect() as conn, conn.begin():
            result = await conn.execute(
                text("SELECT current_setting('app.current_organization_id', true)")
            )
            assert result.scalar_one() in (None, "")


class TestNoneBoundOrgIdNeverProducesACastException:
    """The Decision-2 regression case, corrected against real Postgres
    behavior (verified directly, not assumed from documentation): an earlier
    draft of this design believed `set_config(name, NULL, true)` makes
    `current_setting(name, true)` read back as true SQL `NULL`. Empirically,
    for a *custom* (unregistered) GUC that has already been `set_config()`-ed
    at least once on the current session/connection, a subsequent
    `set_config(name, NULL, true)` leaves `current_setting(name, true)`
    returning an **empty string**, not `NULL` -- which matters directly
    under connection pooling, where the same physical connection serves many
    requests across many transactions. The actual fix lives in the RLS
    policy expressions themselves (migration `7192e84e9a2f`): every
    `current_setting(...)` is wrapped in `NULLIF(..., '')` *before* the
    `::uuid` cast, which is safe regardless of which of the two behaviors
    Postgres exhibits.
    """

    async def test_raw_current_setting_cast_does_raise_after_a_null_set_config(
        self, app_engine: AsyncEngine
    ) -> None:
        """Documents the actual failure mode this fix addresses -- without
        NULLIF, this exact sequence raises, proving the bug is real, not
        theoretical."""
        async with app_engine.connect() as conn, conn.begin():
            await conn.execute(
                text("SELECT set_config('app.current_organization_id', :val, true)").bindparams(
                    val="44444444-4444-4444-4444-444444444444"
                )
            )
            await conn.execute(
                text("SELECT set_config('app.current_organization_id', :val, true)").bindparams(
                    val=None
                )
            )

            with pytest.raises(Exception, match=r"invalid input syntax for type uuid"):
                await conn.execute(
                    text("SELECT current_setting('app.current_organization_id', true)::uuid")
                )

    async def test_the_nullif_wrapped_expression_never_raises(
        self, app_engine: AsyncEngine
    ) -> None:
        """The actual expression every RLS policy uses (migration
        `7192e84e9a2f`) -- must not raise, and must correctly evaluate to
        NULL (never a match) after a None-bound reset."""
        async with app_engine.connect() as conn, conn.begin():
            await conn.execute(
                text("SELECT set_config('app.current_organization_id', :val, true)").bindparams(
                    val="44444444-4444-4444-4444-444444444444"
                )
            )
            await conn.execute(
                text("SELECT set_config('app.current_organization_id', :val, true)").bindparams(
                    val=None
                )
            )

            result = await conn.execute(
                text(
                    "SELECT (NULLIF(current_setting('app.current_organization_id', true), '')"
                    "::uuid IS NULL)"
                )
            )
            assert result.scalar_one() is True

    async def test_the_nullif_wrapped_expression_is_also_safe_on_a_never_set_guc(
        self, app_engine: AsyncEngine
    ) -> None:
        async with app_engine.connect() as conn, conn.begin():
            result = await conn.execute(
                text(
                    "SELECT (NULLIF(current_setting('app.current_organization_id', true), '')"
                    "::uuid IS NULL)"
                )
            )
            assert result.scalar_one() is True
