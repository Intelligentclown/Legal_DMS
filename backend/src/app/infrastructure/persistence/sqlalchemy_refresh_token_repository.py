"""SQLAlchemy implementation of `RefreshTokenRepository` (T50) —
`SqlAlchemyRepository[RefreshToken]` plus the one lookup the port adds.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.interfaces.refresh_token_repository import RefreshTokenRepository
from app.infrastructure.persistence.models.identity import RefreshToken
from app.infrastructure.persistence.sqlalchemy_repository import SqlAlchemyRepository


class SqlAlchemyRefreshTokenRepository(SqlAlchemyRepository[RefreshToken], RefreshTokenRepository):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, RefreshToken)

    async def get_by_token_hash(self, token_hash: str) -> RefreshToken | None:
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
