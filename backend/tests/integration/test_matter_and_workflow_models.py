"""Schema-level tests for matters and the persisted workflow tables."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.models.client import Client
from app.infrastructure.persistence.models.matter import Matter, MatterStatus, MatterType
from app.infrastructure.persistence.models.workflow import (
    WorkflowDefinition,
    WorkflowHistory,
    WorkflowState,
)


async def _make_matter_type(session: AsyncSession) -> MatterType:
    matter_type = MatterType(code=f"TYPE-{uuid4()}", name="Sale Deed")
    session.add(matter_type)
    await session.flush()
    return matter_type


async def _make_matter_status(session: AsyncSession) -> MatterStatus:
    status = MatterStatus(code=f"STATUS-{uuid4()}", name="Open")
    session.add(status)
    await session.flush()
    return status


async def _make_client(session: AsyncSession) -> Client:
    client = Client(full_name="Client", primary_phone="9876543210")
    session.add(client)
    await session.flush()
    return client


async def _make_matter(session: AsyncSession, **overrides: object) -> Matter:
    matter_type = await _make_matter_type(session)
    status = await _make_matter_status(session)
    client = await _make_client(session)
    defaults = {
        "matter_number": f"M-{uuid4()}",
        "matter_type_id": matter_type.id,
        "matter_status_id": status.id,
        "client_id": client.id,
        "title": "Test matter",
        "opened_at": datetime.now(UTC),
    }
    matter = Matter(**{**defaults, **overrides})
    session.add(matter)
    await session.flush()
    return matter


class TestMatter:
    async def test_valid_matter_succeeds(self, db_session: AsyncSession) -> None:
        matter = await _make_matter(db_session)

        assert matter.id is not None
        assert matter.version == 1

    async def test_matter_number_must_be_unique(self, db_session: AsyncSession) -> None:
        matter = await _make_matter(db_session)

        with pytest.raises(IntegrityError):
            await _make_matter(db_session, matter_number=matter.matter_number)

    async def test_requires_a_valid_matter_type(self, db_session: AsyncSession) -> None:
        status = await _make_matter_status(db_session)
        client = await _make_client(db_session)
        db_session.add(
            Matter(
                matter_number=f"M-{uuid4()}",
                matter_type_id=uuid4(),
                matter_status_id=status.id,
                client_id=client.id,
                title="x",
                opened_at=datetime.now(UTC),
            )
        )

        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_closed_at_cannot_precede_opened_at(self, db_session: AsyncSession) -> None:
        opened = datetime.now(UTC)
        with pytest.raises(IntegrityError):
            await _make_matter(db_session, opened_at=opened, closed_at=opened - timedelta(days=1))

    async def test_optimistic_locking_is_enabled(self) -> None:
        assert Matter.__mapper__.version_id_col is Matter.__table__.c.version


class TestWorkflow:
    async def test_state_code_unique_within_definition_only(self, db_session: AsyncSession) -> None:
        definition = WorkflowDefinition(code=f"WF-{uuid4()}", name="Matter Lifecycle")
        db_session.add(definition)
        await db_session.flush()

        db_session.add(
            WorkflowState(workflow_definition_id=definition.id, code="draft", name="Draft")
        )
        await db_session.flush()

        db_session.add(
            WorkflowState(workflow_definition_id=definition.id, code="draft", name="Duplicate")
        )
        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_history_records_a_transition_for_any_entity_type(
        self, db_session: AsyncSession
    ) -> None:
        definition = WorkflowDefinition(code=f"WF-{uuid4()}", name="Matter Lifecycle")
        db_session.add(definition)
        await db_session.flush()

        draft = WorkflowState(workflow_definition_id=definition.id, code="draft", name="Draft")
        review = WorkflowState(workflow_definition_id=definition.id, code="review", name="Review")
        db_session.add_all([draft, review])
        await db_session.flush()

        entry = WorkflowHistory(
            workflow_definition_id=definition.id,
            entity_type="matter",
            entity_id=uuid4(),
            from_state_id=draft.id,
            to_state_id=review.id,
            event="submit_for_review",
        )
        db_session.add(entry)

        await db_session.flush()

        assert entry.id is not None

    async def test_history_requires_a_valid_workflow_definition(
        self, db_session: AsyncSession
    ) -> None:
        db_session.add(
            WorkflowHistory(
                workflow_definition_id=uuid4(),
                entity_type="matter",
                entity_id=uuid4(),
                to_state_id=uuid4(),
                event="x",
            )
        )

        with pytest.raises(IntegrityError):
            await db_session.flush()
