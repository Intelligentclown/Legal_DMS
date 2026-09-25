"""SQLAlchemy repository for File-canonical Document metadata (T139)."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.interfaces.document_repository import DocumentRepository
from app.infrastructure.persistence.models.document import Document
from app.infrastructure.persistence.sqlalchemy_repository import SqlAlchemyRepository


class SqlAlchemyDocumentRepository(SqlAlchemyRepository[Document], DocumentRepository):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Document)

    async def get_in_file(
        self, document_id: UUID, organization_id: UUID, matter_id: UUID, file_id: UUID
    ) -> Document | None:
        result = await self._session.execute(
            select(Document).where(
                Document.id == document_id,
                Document.organization_id == organization_id,
                Document.matter_id == matter_id,
                Document.file_id == file_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_in_file(
        self, organization_id: UUID, matter_id: UUID, file_id: UUID, *, limit: int, offset: int
    ) -> Sequence[Document]:
        result = await self._session.execute(
            select(Document)
            .where(
                Document.organization_id == organization_id,
                Document.matter_id == matter_id,
                Document.file_id == file_id,
            )
            .order_by(Document.created_at, Document.id)
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    async def count_in_file(self, organization_id: UUID, matter_id: UUID, file_id: UUID) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(Document)
            .where(
                Document.organization_id == organization_id,
                Document.matter_id == matter_id,
                Document.file_id == file_id,
            )
        )
        return result.scalar_one()
