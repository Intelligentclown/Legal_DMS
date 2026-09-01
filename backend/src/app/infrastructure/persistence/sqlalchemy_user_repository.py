"""SQLAlchemy implementation of `UserRepository` (T50) — `SqlAlchemyRepository[User]`
plus the lookups/mutations the port adds.
"""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.interfaces.user_repository import UserRepository
from app.infrastructure.persistence.models.identity import Role, User, UserRole
from app.infrastructure.persistence.sqlalchemy_repository import SqlAlchemyRepository


class SqlAlchemyUserRepository(SqlAlchemyRepository[User], UserRepository):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, User)

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_role_names(self, user_id: UUID) -> frozenset[str]:
        stmt = (
            select(Role.name)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
        )
        result = await self._session.execute(stmt)
        return frozenset(result.scalars().all())

    async def assign_role(self, user_id: UUID, role_id: UUID, assigned_by: UUID) -> UserRole | None:
        stmt = select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role_id)
        result = await self._session.execute(stmt)
        if result.scalar_one_or_none() is not None:
            return None

        user_role = UserRole(user_id=user_id, role_id=role_id, assigned_by=assigned_by)
        self._session.add(user_role)
        try:
            await self._session.flush()
        except IntegrityError:
            # The pre-check above is a courtesy, not a guarantee -- a
            # concurrent request can still win the race and insert the same
            # (user_id, role_id) row first. The database's own
            # UniqueConstraint(user_id, role_id) is what's actually
            # authoritative; this just translates its rejection into the
            # same "already exists" signal the pre-check gives, rather than
            # letting an unhandled IntegrityError surface as a 500.
            return None
        return user_role

    async def remove_role(self, user_id: UUID, role_id: UUID) -> bool:
        stmt = select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role_id)
        result = await self._session.execute(stmt)
        user_role = result.scalar_one_or_none()
        if user_role is None:
            return False

        await self._session.delete(user_role)
        await self._session.flush()
        return True

    async def set_current_user_context(self, user_id: UUID) -> None:
        # set_config(..., true) is transaction-local (PostgreSQL docs) --
        # bound parameter, never string-interpolated, so this can never
        # produce an empty-string-cast error and never a SQL-injection
        # surface.
        await self._session.execute(
            text("SELECT set_config('app.current_user_id', :user_id, true)").bindparams(
                user_id=str(user_id)
            )
        )

    async def set_current_organization_context(self, organization_id: UUID | None) -> None:
        # A None value binds SQL NULL as set_config()'s new_value. Verified
        # directly against Postgres (not merely assumed from docs): for a
        # custom/unregistered GUC that has already been set at least once on
        # this session/connection, set_config(name, NULL, true) leaves
        # current_setting(name, true) returning an *empty string*, not a
        # true-NULL reset -- so the RLS policies themselves wrap every
        # current_setting(...) in NULLIF(..., '') before casting to ::uuid
        # (see migration 7192e84e9a2f), which is what actually prevents the
        # empty-string cast error, not this call's NULL argument alone.
        await self._session.execute(
            text("SELECT set_config('app.current_organization_id', :org_id, true)").bindparams(
                org_id=str(organization_id) if organization_id is not None else None
            )
        )

    async def get_by_id_in_organization(self, user_id: UUID, organization_id: UUID) -> User | None:
        stmt = select(User).where(User.id == user_id, User.organization_id == organization_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_in_organization(
        self, organization_id: UUID, *, limit: int = 100, offset: int = 0
    ) -> Sequence[User]:
        stmt = (
            select(User).where(User.organization_id == organization_id).limit(limit).offset(offset)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def count_in_organization(self, organization_id: UUID) -> int:
        stmt = select(func.count()).select_from(User).where(User.organization_id == organization_id)
        result = await self._session.execute(stmt)
        return result.scalar_one()
