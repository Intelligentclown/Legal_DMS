"""SQLAlchemy implementation of `UserRepository` (T50) — `SqlAlchemyRepository[User]`
plus the two lookups the port adds.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
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
