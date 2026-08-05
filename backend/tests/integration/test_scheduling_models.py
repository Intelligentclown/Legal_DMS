"""Schema-level tests for tasks, appointments, tags, and matter_tags."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.models.client import Client
from app.infrastructure.persistence.models.matter import Matter, MatterStatus, MatterType
from app.infrastructure.persistence.models.scheduling import Appointment, MatterTag, Tag, Task


async def _make_matter(session: AsyncSession) -> Matter:
    matter_type = MatterType(code=f"TYPE-{uuid4()}", name="Sale")
    status = MatterStatus(code=f"STATUS-{uuid4()}", name="Open")
    client = Client(full_name="Client", primary_phone="9876543210")
    session.add_all([matter_type, status, client])
    await session.flush()

    matter = Matter(
        matter_number=f"M-{uuid4()}",
        matter_type_id=matter_type.id,
        matter_status_id=status.id,
        client_id=client.id,
        title="Test",
        opened_at=datetime.now(UTC),
    )
    session.add(matter)
    await session.flush()
    return matter


class TestTask:
    async def test_task_can_exist_without_a_matter(self, db_session: AsyncSession) -> None:
        task = Task(title="Follow up")
        db_session.add(task)

        await db_session.flush()

        assert task.id is not None
        assert task.status == "open"
        assert task.priority == "normal"


class TestAppointment:
    async def test_ends_at_must_be_after_starts_at(self, db_session: AsyncSession) -> None:
        start = datetime.now(UTC)
        db_session.add(
            Appointment(title="Meeting", starts_at=start, ends_at=start - timedelta(minutes=30))
        )

        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_valid_appointment_succeeds(self, db_session: AsyncSession) -> None:
        start = datetime.now(UTC)
        appointment = Appointment(
            title="Meeting", starts_at=start, ends_at=start + timedelta(hours=1)
        )
        db_session.add(appointment)

        await db_session.flush()

        assert appointment.id is not None
        assert appointment.status == "scheduled"


class TestTagsAndMatterTags:
    async def test_tag_name_must_be_unique(self, db_session: AsyncSession) -> None:
        db_session.add(Tag(name="urgent"))
        await db_session.flush()
        db_session.add(Tag(name="urgent"))

        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_same_matter_tag_pair_cannot_repeat(self, db_session: AsyncSession) -> None:
        matter = await _make_matter(db_session)
        tag = Tag(name="priority")
        db_session.add(tag)
        await db_session.flush()

        db_session.add(MatterTag(matter_id=matter.id, tag_id=tag.id))
        await db_session.flush()

        db_session.add(MatterTag(matter_id=matter.id, tag_id=tag.id))
        with pytest.raises(IntegrityError):
            await db_session.flush()
