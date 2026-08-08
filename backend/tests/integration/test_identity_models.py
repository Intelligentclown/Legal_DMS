"""Schema-level tests for the identity & access models: constraints, FKs,
and audit-column defaults. No business logic exists yet to test — these
verify the schema itself, against the real migrated tables.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.models.identity import (
    Permission,
    RefreshToken,
    Role,
    User,
    UserRole,
)


async def _make_user(session: AsyncSession, **overrides: object) -> User:
    defaults = {"email": f"{uuid4()}@example.com", "full_name": "Test User"}
    user = User(**{**defaults, **overrides})
    session.add(user)
    await session.flush()
    return user


class TestUser:
    async def test_create_user_succeeds_with_audit_defaults(self, db_session: AsyncSession) -> None:
        user = await _make_user(db_session)

        assert user.id is not None
        assert user.created_at is not None
        assert user.updated_at is not None
        assert user.deleted_at is None
        assert user.version == 1
        assert user.is_active is True

    async def test_email_must_be_unique(self, db_session: AsyncSession) -> None:
        await _make_user(db_session, email="dup@example.com")

        with pytest.raises(IntegrityError):
            await _make_user(db_session, email="dup@example.com")

    async def test_full_name_is_required(self, db_session: AsyncSession) -> None:
        user = User(email="norname@example.com", full_name=None)
        db_session.add(user)

        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_soft_delete_sets_deleted_at(self, db_session: AsyncSession) -> None:
        user = await _make_user(db_session)

        user.deleted_at = datetime.now(UTC)
        await db_session.flush()
        await db_session.refresh(user)

        assert user.deleted_at is not None


class TestRole:
    async def test_name_must_be_unique(self, db_session: AsyncSession) -> None:
        db_session.add(Role(name="paralegal"))
        await db_session.flush()
        db_session.add(Role(name="paralegal"))

        with pytest.raises(IntegrityError):
            await db_session.flush()


class TestPermission:
    async def test_code_must_be_unique(self, db_session: AsyncSession) -> None:
        code = f"test:{uuid4()}"
        db_session.add(Permission(code=code, category="matters"))
        await db_session.flush()
        db_session.add(Permission(code=code, category="matters"))

        with pytest.raises(IntegrityError):
            await db_session.flush()


class TestUserRole:
    async def test_requires_existing_user_and_role(self, db_session: AsyncSession) -> None:
        db_session.add(UserRole(user_id=uuid4(), role_id=uuid4()))

        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_same_user_role_pair_cannot_repeat(self, db_session: AsyncSession) -> None:
        user = await _make_user(db_session)
        role = Role(name="admin")
        db_session.add(role)
        await db_session.flush()

        db_session.add(UserRole(user_id=user.id, role_id=role.id))
        await db_session.flush()
        db_session.add(UserRole(user_id=user.id, role_id=role.id))

        with pytest.raises(IntegrityError):
            await db_session.flush()


class TestRefreshToken:
    async def test_requires_existing_user(self, db_session: AsyncSession) -> None:
        db_session.add(
            RefreshToken(
                user_id=uuid4(),
                token_hash=f"hash-{uuid4()}",
                expires_at=datetime.now(UTC),
            )
        )

        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_create_succeeds_with_expected_defaults(self, db_session: AsyncSession) -> None:
        user = await _make_user(db_session)
        expires_at = datetime.now(UTC)

        token = RefreshToken(user_id=user.id, token_hash=f"hash-{uuid4()}", expires_at=expires_at)
        db_session.add(token)
        await db_session.flush()

        assert token.id is not None
        assert token.issued_at is not None
        assert token.revoked_at is None

    async def test_token_hash_must_be_unique(self, db_session: AsyncSession) -> None:
        user = await _make_user(db_session)
        shared_hash = f"hash-{uuid4()}"
        db_session.add(
            RefreshToken(user_id=user.id, token_hash=shared_hash, expires_at=datetime.now(UTC))
        )
        await db_session.flush()

        db_session.add(
            RefreshToken(user_id=user.id, token_hash=shared_hash, expires_at=datetime.now(UTC))
        )

        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_revoked_at_can_be_set(self, db_session: AsyncSession) -> None:
        user = await _make_user(db_session)
        token = RefreshToken(
            user_id=user.id, token_hash=f"hash-{uuid4()}", expires_at=datetime.now(UTC)
        )
        db_session.add(token)
        await db_session.flush()

        token.revoked_at = datetime.now(UTC)
        await db_session.flush()
        await db_session.refresh(token)

        assert token.revoked_at is not None
