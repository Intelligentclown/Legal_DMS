"""Schema-level tests for system, config, AI, and plugin models."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.models.system import (
    AiRequest,
    AiResponse,
    ApplicationSetting,
    BackgroundJobRecord,
    FeatureFlag,
    PluginRegistryEntry,
    SystemEvent,
)


class TestApplicationSetting:
    async def test_key_must_be_unique(self, db_session: AsyncSession) -> None:
        db_session.add(ApplicationSetting(key="theme", value={"mode": "dark"}))
        await db_session.flush()

        db_session.add(ApplicationSetting(key="theme", value={"mode": "light"}))
        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_valid_setting_succeeds(self, db_session: AsyncSession) -> None:
        setting = ApplicationSetting(key="max_upload_mb", value={"limit": 50})
        db_session.add(setting)

        await db_session.flush()

        assert setting.id is not None
        assert setting.value == {"limit": 50}


class TestFeatureFlag:
    async def test_name_must_be_unique(self, db_session: AsyncSession) -> None:
        name = f"test-flag-{uuid4()}"
        db_session.add(FeatureFlag(name=name))
        await db_session.flush()

        db_session.add(FeatureFlag(name=name))
        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_defaults_to_disabled(self, db_session: AsyncSession) -> None:
        flag = FeatureFlag(name=f"test-flag-{uuid4()}")
        db_session.add(flag)

        await db_session.flush()

        assert flag.is_enabled is False


class TestAiRequestAndResponse:
    async def test_response_requires_a_valid_request(self, db_session: AsyncSession) -> None:
        db_session.add(AiResponse(ai_request_id=uuid4(), response_text="n/a"))

        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_request_and_response_link_correctly(self, db_session: AsyncSession) -> None:
        request = AiRequest(request_type="draft_summary", prompt="Summarize this matter.")
        db_session.add(request)
        await db_session.flush()

        response = AiResponse(
            ai_request_id=request.id, response_text="Summary text.", model_used="test-model"
        )
        db_session.add(response)

        await db_session.flush()

        assert response.ai_request_id == request.id
        assert request.status == "pending"


class TestPluginRegistryEntry:
    async def test_name_must_be_unique(self, db_session: AsyncSession) -> None:
        db_session.add(PluginRegistryEntry(name="pdf-exporter", version="1.0.0"))
        await db_session.flush()

        db_session.add(PluginRegistryEntry(name="pdf-exporter", version="1.0.1"))
        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_valid_entry_succeeds(self, db_session: AsyncSession) -> None:
        entry = PluginRegistryEntry(name="qr-generator", version="0.1.0")
        db_session.add(entry)

        await db_session.flush()

        assert entry.is_enabled is True


class TestBackgroundJobRecord:
    async def test_valid_job_succeeds(self, db_session: AsyncSession) -> None:
        job = BackgroundJobRecord(job_name="send_notifications", payload={"batch": 1})
        db_session.add(job)

        await db_session.flush()

        assert job.id is not None
        assert job.status == "pending"


class TestSystemEvent:
    async def test_valid_event_succeeds(self, db_session: AsyncSession) -> None:
        event = SystemEvent(event_type="matter.opened", payload={"matter_id": str(uuid4())})
        db_session.add(event)

        await db_session.flush()

        assert event.id is not None
