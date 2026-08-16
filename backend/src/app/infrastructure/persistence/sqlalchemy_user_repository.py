"""SQLAlchemy implementation of `UserRepository` (T50) — `SqlAlchemyRepository[User]`
plus the lookups/mutations the port adds.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
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
