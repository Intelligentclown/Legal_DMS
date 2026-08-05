"""Schema-level tests for activity logs, audit logs, and notifications."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.models.activity import ActivityLog, AuditLog, Notification
from app.infrastructure.persistence.models.identity import User


async def _make_user(session: AsyncSession) -> User:
    user = User(email=f"{uuid4()}@example.com", full_name="Actor")
    session.add(user)
    await session.flush()
    return user


class TestActivityLog:
    async def test_can_be_recorded_without_an_actor(self, db_session: AsyncSession) -> None:
        entry = ActivityLog(entity_type="matter", entity_id=uuid4(), action="created")
        db_session.add(entry)

        await db_session.flush()

        assert entry.id is not None
        assert entry.actor_id is None

    async def test_details_is_stored_as_json(self, db_session: AsyncSession) -> None:
        entry = ActivityLog(
            entity_type="matter",
            entity_id=uuid4(),
            action="updated",
            details={"field": "status", "old": "draft", "new": "open"},
        )
        db_session.add(entry)
        await db_session.flush()
        await db_session.refresh(entry)

        assert entry.details == {"field": "status", "old": "draft", "new": "open"}


class TestAuditLog:
    async def test_mirrors_the_audit_logger_port_shape(self, db_session: AsyncSession) -> None:
        actor = await _make_user(db_session)

        entry = AuditLog(
            actor_id=actor.id,
            action="matter.created",
            resource_type="Matter",
            resource_id="123",
            audit_metadata={"title": "New matter"},
        )
        db_session.add(entry)
        await db_session.flush()
        await db_session.refresh(entry)

        assert entry.audit_metadata == {"title": "New matter"}
        assert entry.created_at is not None

    async def test_can_be_recorded_for_an_anonymous_actor(self, db_session: AsyncSession) -> None:
        entry = AuditLog(action="health.checked", resource_type="System")
        db_session.add(entry)

        await db_session.flush()

        assert entry.actor_id is None


class TestNotification:
    async def test_requires_an_existing_recipient(self, db_session: AsyncSession) -> None:
        db_session.add(Notification(recipient_id=uuid4(), title="Hi", body="Hello"))

        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_defaults_to_unread_in_app(self, db_session: AsyncSession) -> None:
        user = await _make_user(db_session)
        notification = Notification(recipient_id=user.id, title="Hi", body="Hello")
        db_session.add(notification)

        await db_session.flush()

        assert notification.is_read is False
        assert notification.channel == "in_app"
        assert notification.read_at is None
