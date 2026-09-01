"""Integration tests for T67's `infrastructure/cli/bootstrap.py`, extended
by T105/ADR-0031 SS6.2/SS6.3 for atomic Organization creation.

`run_bootstrap()` -- the in-memory core -- is covered against the real
migrated schema via the shared `db_session` fixture (`tests/conftest.py`),
same as every other integration test in this suite: everything rolled back
in teardown.

`T68` extends this file to also cover `_async_main()` -- the actual process
entry point `run_bootstrap()`'s own tests deliberately didn't exercise (see
T67's QA Decision, `docs/ImplementationLog/Stage4/Phase0.md`'s T67 batch,
non-blocking comment naming this exact gap). `_async_main()` (not `main()`)
is what's driven directly: `main()`'s only additional behavior is
`asyncio.run(_async_main())`, and `asyncio.run()` cannot be called from
inside a already-running event loop -- which every `asyncio_mode = auto`
async test function here runs inside. `_async_main()` is the coroutine that
actually contains this entry point's logic; `main()` is a synchronous shim
around it with no logic of its own to verify.

Two things `_async_main()`'s tests need that `run_bootstrap()`'s didn't:

- `input()`/`getpass()` mocked -- `input()` is patched at `builtins.input`
  (the module calls the builtin directly, no import to intercept);
  `getpass()` is patched at `app.infrastructure.cli.bootstrap.getpass`
  (matching `from getpass import getpass`'s binding into that module's own
  namespace). T105: `_async_main()` now calls `input()` three times (email,
  then Organization name, then Organization legal name) -- `input_mock`
  below is a `side_effect` list, not a single `return_value`, for exactly
  this reason.
- `get_session_factory()` mocked to hand back the test's own `db_session`,
  via `_FakeSessionFactory` below -- the CLI-level mirror of this codebase's
  `get_db` dependency-override pattern (`test_users.py`'s `client` fixture:
  yield the test's session, don't open a new one).

One thing the "creates the admin" test needs that no other test in this
suite has needed: `_async_main()` actually calls `session.commit()` (not
just `flush()`), so proving that requires reading the row back through a
*second*, independent engine/connection, not `db_session` itself -- Postgres
lets a session see its own uncommitted writes, so a same-session read can't
tell "committed" apart from "merely flushed." Because that commit is real
(this is the one test in the suite that deliberately leaves `db_session`'s
usual rollback-only safety net), the test cleans up the row it creates
through that same second connection once it's done asserting.
"""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.infrastructure.cli.bootstrap import _async_main, run_bootstrap
from app.infrastructure.config import get_settings
from app.infrastructure.persistence.models.identity import Role, RolePermission, User, UserRole
from app.infrastructure.persistence.models.organization import Organization
from app.infrastructure.security.password_hasher import verify_password

_ORG_NAME = "Acme Legal"
_ORG_LEGAL_NAME = "Acme Legal Services LLP"


async def _make_user(db_session: AsyncSession, **overrides: object) -> User:
    defaults: dict[str, object] = {
        "email": f"{uuid4()}@example.com",
        "full_name": "Existing User",
        "password_hash": "irrelevant-for-this-test",
        "is_active": True,
    }
    user = User(**{**defaults, **overrides})
    db_session.add(user)
    await db_session.flush()
    return user


class TestRunBootstrapNoExistingUser:
    async def test_creates_admin_with_hashed_password(self, db_session: AsyncSession) -> None:
        email = f"{uuid4()}@example.com"
        password = "correct horse battery staple"

        created = await run_bootstrap(
            db_session, email=email, password=password, organization_name=_ORG_NAME
        )

        assert created is not None
        assert created.email == email
        assert created.password_hash != password
        assert verify_password(password, created.password_hash or "") is True

    async def test_assigns_administrator_role(self, db_session: AsyncSession) -> None:
        created = await run_bootstrap(
            db_session,
            email=f"{uuid4()}@example.com",
            password="correct horse battery staple",
            organization_name=_ORG_NAME,
        )
        assert created is not None

        result = await db_session.execute(
            select(Role.name)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == created.id)
        )
        assert list(result.scalars().all()) == ["Administrator"]

    async def test_creates_exactly_one_user(self, db_session: AsyncSession) -> None:
        await run_bootstrap(
            db_session,
            email=f"{uuid4()}@example.com",
            password="correct horse battery staple",
            organization_name=_ORG_NAME,
        )

        result = await db_session.execute(select(User))
        assert len(result.scalars().all()) == 1

    async def test_creates_exactly_one_organization_and_links_it(
        self, db_session: AsyncSession
    ) -> None:
        created = await run_bootstrap(
            db_session,
            email=f"{uuid4()}@example.com",
            password="correct horse battery staple",
            organization_name=_ORG_NAME,
            organization_legal_name=_ORG_LEGAL_NAME,
        )
        assert created is not None
        assert created.organization_id is not None

        result = await db_session.execute(select(Organization))
        organizations = result.scalars().all()
        assert len(organizations) == 1
        organization = organizations[0]
        assert organization.id == created.organization_id
        assert organization.name == _ORG_NAME
        assert organization.legal_name == _ORG_LEGAL_NAME

    async def test_organization_audit_columns_attributed_to_the_new_user(
        self, db_session: AsyncSession
    ) -> None:
        """Verifies the self-attribution ordering (create User, flush, THEN
        create Organization with created_by=user.id) -- mirrors the
        pre-existing `UserRole.assigned_by=user.id` precedent exactly."""
        created = await run_bootstrap(
            db_session,
            email=f"{uuid4()}@example.com",
            password="correct horse battery staple",
            organization_name=_ORG_NAME,
        )
        assert created is not None

        result = await db_session.execute(select(Organization))
        organization = result.scalar_one()
        assert organization.created_by == created.id
        assert organization.updated_by == created.id

    async def test_no_partial_state_when_admin_role_is_missing(
        self, db_session: AsyncSession
    ) -> None:
        """ADR/0031 SS16's bootstrap-atomicity acceptance criterion: a
        failure partway through (here, the pre-existing
        "no Administrator role" RuntimeError guard) leaves no partial
        state -- not a User with no Organization, not an Organization with
        no User."""
        admin_role = (
            await db_session.execute(select(Role).where(Role.name == "Administrator"))
        ).scalar_one()
        await db_session.execute(
            delete(RolePermission).where(RolePermission.role_id == admin_role.id)
        )
        await db_session.execute(delete(Role).where(Role.id == admin_role.id))
        await db_session.flush()

        with pytest.raises(RuntimeError):
            await run_bootstrap(
                db_session,
                email=f"{uuid4()}@example.com",
                password="correct horse battery staple",
                organization_name=_ORG_NAME,
            )

        # The RuntimeError guard fires before any User/Organization is even
        # constructed -- nothing to roll back at the ORM level, but confirms
        # the invariant directly: no orphaned row of either kind exists.
        assert (await db_session.execute(select(User))).scalars().all() == []
        assert (await db_session.execute(select(Organization))).scalars().all() == []


class TestRunBootstrapExistingUser:
    async def test_returns_none_without_creating_duplicate(self, db_session: AsyncSession) -> None:
        await _make_user(db_session)

        result = await run_bootstrap(
            db_session,
            email=f"{uuid4()}@example.com",
            password="correct horse battery staple",
            organization_name=_ORG_NAME,
        )

        assert result is None
        remaining = await db_session.execute(select(User))
        assert len(remaining.scalars().all()) == 1
        assert (await db_session.execute(select(Organization))).scalars().all() == []

    async def test_does_not_touch_existing_user(self, db_session: AsyncSession) -> None:
        existing = await _make_user(db_session)

        await run_bootstrap(
            db_session,
            email=f"{uuid4()}@example.com",
            password="correct horse battery staple",
            organization_name=_ORG_NAME,
        )

        refreshed = await db_session.get(User, existing.id)
        assert refreshed is not None
        assert refreshed.email == existing.email


class _FakeSessionFactory:
    """Stands in for `get_session_factory()`'s return value: `_async_main()`
    does `session_factory = get_session_factory()` then
    `async with session_factory() as session`, so this needs to be callable
    (returning something async-context-manageable) rather than itself an
    async context manager. Always hands back the same session -- this test's
    own `db_session` -- and does nothing on exit, so `db_session`'s
    lifecycle stays entirely owned by the `db_session` fixture, exactly the
    same non-ownership `get_db` overrides elsewhere in this codebase already
    establish for FastAPI's DI.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def __call__(self) -> _FakeSessionFactory:
        return self

    async def __aenter__(self) -> AsyncSession:
        return self._session

    async def __aexit__(self, *exc_info: object) -> None:
        return None


def _install_fake_session_factory(monkeypatch: pytest.MonkeyPatch, session: AsyncSession) -> None:
    factory = _FakeSessionFactory(session)
    monkeypatch.setattr("app.infrastructure.cli.bootstrap.get_session_factory", lambda: factory)


async def _fetch_and_delete_committed_user(email: str) -> User | None:
    """Reads (and, if found, deletes) a user by email through a brand-new
    engine/connection -- independent of `db_session`'s -- used both to prove
    a real commit happened (a separate connection can't see another
    connection's merely-flushed, uncommitted writes) and, since that commit
    is real and `db_session`'s own rollback can't undo it, to clean the row
    back up afterward regardless of whether the test's assertions passed.
    Also deletes the Organization the same commit created (T105).
    """
    engine = create_async_engine(get_settings().database_url)
    try:
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            result = await session.execute(select(User).where(User.email == email))
            found = result.scalar_one_or_none()
            if found is not None:
                organization_id = found.organization_id
                # Genuine circular FK between these two T105 tables:
                # organizations.created_by/updated_by -> users.id (self-
                # attribution, per bootstrap.py's ordering) AND
                # users.organization_id -> organizations.id. Neither table
                # can be deleted first while both edges still point at each
                # other -- break the cycle by nulling users.organization_id
                # before deleting either row. Raw text() (not the ORM-aware
                # update(User) construct) deliberately -- the latter's
                # session-synchronization would mutate `found`'s already-
                # loaded organization_id in place, before the caller below
                # gets to assert on it.
                await session.execute(delete(UserRole).where(UserRole.user_id == found.id))
                if organization_id is not None:
                    await session.execute(
                        text(
                            "UPDATE users SET organization_id = NULL WHERE id = CAST(:id AS uuid)"
                        ).bindparams(id=str(found.id))
                    )
                    await session.execute(
                        delete(Organization).where(Organization.id == organization_id)
                    )
                await session.execute(delete(User).where(User.id == found.id))
                await session.commit()
            return found
    finally:
        await engine.dispose()


class TestAsyncMainNoExistingUser:
    async def test_creates_admin_and_actually_commits(
        self, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        email = f"{uuid4()}@example.com"
        password = "correct horse battery staple"

        _install_fake_session_factory(monkeypatch, db_session)
        input_mock = MagicMock(side_effect=[email, _ORG_NAME, _ORG_LEGAL_NAME])
        getpass_mock = MagicMock(return_value=password)
        monkeypatch.setattr("builtins.input", input_mock)
        monkeypatch.setattr("app.infrastructure.cli.bootstrap.getpass", getpass_mock)

        try:
            await _async_main()

            assert input_mock.call_count == 3
            getpass_mock.assert_called_once_with("Administrator password: ")

            # A second, independent connection -- not db_session -- is what
            # actually proves session.commit() ran rather than just flush():
            # Postgres would let db_session itself see its own uncommitted
            # writes, which would make this assertion pass even if the
            # production code's commit() call were deleted.
            persisted = await _fetch_and_delete_committed_user(email)
            assert persisted is not None, (
                "admin row was not visible via an independent connection -- "
                "_async_main() did not actually commit it"
            )
            assert verify_password(password, persisted.password_hash or "") is True
            assert persisted.organization_id is not None
        finally:
            # Belt-and-suspenders: if the assertions above already deleted
            # the row, this is a no-op: unconditional cleanup keeps the dev
            # database empty even if a prior assertion failed first.
            await _fetch_and_delete_committed_user(email)

    async def test_assigns_administrator_role_and_actually_commits(
        self, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        email = f"{uuid4()}@example.com"
        password = "correct horse battery staple"

        _install_fake_session_factory(monkeypatch, db_session)
        monkeypatch.setattr(
            "builtins.input", MagicMock(side_effect=[email, _ORG_NAME, _ORG_LEGAL_NAME])
        )
        monkeypatch.setattr(
            "app.infrastructure.cli.bootstrap.getpass", MagicMock(return_value=password)
        )

        try:
            await _async_main()

            engine = create_async_engine(get_settings().database_url)
            try:
                session_factory = async_sessionmaker(engine, expire_on_commit=False)
                async with session_factory() as verify_session:
                    result = await verify_session.execute(
                        select(Role.name)
                        .join(UserRole, UserRole.role_id == Role.id)
                        .join(User, User.id == UserRole.user_id)
                        .where(User.email == email)
                    )
                    assert list(result.scalars().all()) == ["Administrator"]
            finally:
                await engine.dispose()
        finally:
            await _fetch_and_delete_committed_user(email)

    async def test_organization_legal_name_is_optional(
        self, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        email = f"{uuid4()}@example.com"
        password = "correct horse battery staple"

        _install_fake_session_factory(monkeypatch, db_session)
        # A blank legal-name prompt response -> organization_legal_name=None.
        monkeypatch.setattr("builtins.input", MagicMock(side_effect=[email, _ORG_NAME, ""]))
        monkeypatch.setattr(
            "app.infrastructure.cli.bootstrap.getpass", MagicMock(return_value=password)
        )

        try:
            await _async_main()

            engine = create_async_engine(get_settings().database_url)
            try:
                session_factory = async_sessionmaker(engine, expire_on_commit=False)
                async with session_factory() as verify_session:
                    result = await verify_session.execute(
                        select(Organization.legal_name)
                        .join(User, User.organization_id == Organization.id)
                        .where(User.email == email)
                    )
                    assert result.scalar_one() is None
            finally:
                await engine.dispose()
        finally:
            await _fetch_and_delete_committed_user(email)


class TestAsyncMainExistingUser:
    async def test_prints_message_and_skips_without_prompting(
        self,
        db_session: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        await _make_user(db_session)

        _install_fake_session_factory(monkeypatch, db_session)
        input_mock = MagicMock()
        getpass_mock = MagicMock()
        monkeypatch.setattr("builtins.input", input_mock)
        monkeypatch.setattr("app.infrastructure.cli.bootstrap.getpass", getpass_mock)

        await _async_main()

        input_mock.assert_not_called()
        getpass_mock.assert_not_called()

        captured = capsys.readouterr()
        assert "already exists" in captured.out

        remaining = await db_session.execute(select(User))
        assert len(remaining.scalars().all()) == 1
