"""Verifies the seed data migration (9963e15f2752) populated lookup
tables with the expected shape. Row-count/spot-check style, not
exhaustive content checks -- exact seed values may evolve.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.models.document import DocumentType
from app.infrastructure.persistence.models.financial import PaymentMethod
from app.infrastructure.persistence.models.geography import Country, District, State
from app.infrastructure.persistence.models.identity import Permission, Role
from app.infrastructure.persistence.models.matter import MatterStatus, MatterType
from app.infrastructure.persistence.models.system import ApplicationSetting, FeatureFlag
from app.infrastructure.persistence.models.workflow import WorkflowDefinition, WorkflowState


async def _count(session: AsyncSession, model: type) -> int:
    return (await session.execute(select(func.count()).select_from(model))).scalar_one()


class TestGeographySeed:
    async def test_india_and_states_and_gujarat_districts_exist(
        self, db_session: AsyncSession
    ) -> None:
        assert await _count(db_session, Country) == 1
        assert await _count(db_session, State) == 36
        assert await _count(db_session, District) == 33

        india = (
            await db_session.execute(select(Country).where(Country.iso_code == "IND"))
        ).scalar_one()
        gujarat = (
            await db_session.execute(
                select(State).where(State.name == "Gujarat", State.country_id == india.id)
            )
        ).scalar_one()
        district_names = (
            (await db_session.execute(select(District.name).where(District.state_id == gujarat.id)))
            .scalars()
            .all()
        )
        assert "Ahmedabad" in district_names
        assert "Vadodara" in district_names


class TestIdentitySeed:
    async def test_roles_and_permissions_exist(self, db_session: AsyncSession) -> None:
        assert await _count(db_session, Role) == 6
        assert await _count(db_session, Permission) == 18

        admin = (
            await db_session.execute(select(Role).where(Role.name == "Administrator"))
        ).scalar_one()
        assert admin.is_system_role is True

        codes = (await db_session.execute(select(Permission.code))).scalars().all()
        assert "matters:read" in codes
        assert "settings:manage" in codes


class TestMatterAndWorkflowSeed:
    async def test_matter_lookups_and_starter_workflow_exist(
        self, db_session: AsyncSession
    ) -> None:
        assert await _count(db_session, MatterType) == 8
        assert await _count(db_session, MatterStatus) == 6
        assert await _count(db_session, WorkflowDefinition) == 1
        assert await _count(db_session, WorkflowState) == 6

        definition = (
            await db_session.execute(
                select(WorkflowDefinition).where(WorkflowDefinition.code == "matter_lifecycle")
            )
        ).scalar_one()
        states = (
            (
                await db_session.execute(
                    select(WorkflowState).where(
                        WorkflowState.workflow_definition_id == definition.id
                    )
                )
            )
            .scalars()
            .all()
        )
        assert sum(1 for s in states if s.is_initial) == 1
        assert sum(1 for s in states if s.is_final) == 2


class TestDocumentAndFinancialSeed:
    async def test_document_types_and_payment_methods_exist(self, db_session: AsyncSession) -> None:
        assert await _count(db_session, DocumentType) == 10
        assert await _count(db_session, PaymentMethod) == 6


class TestSystemConfigSeed:
    async def test_application_settings_and_feature_flags_exist(
        self, db_session: AsyncSession
    ) -> None:
        assert await _count(db_session, ApplicationSetting) == 6
        assert await _count(db_session, FeatureFlag) == 5

        timezone_setting = (
            await db_session.execute(
                select(ApplicationSetting).where(ApplicationSetting.key == "app.timezone")
            )
        ).scalar_one()
        assert timezone_setting.value == {"value": "Asia/Kolkata"}

        flags = (await db_session.execute(select(FeatureFlag))).scalars().all()
        assert all(flag.is_enabled is False for flag in flags)
