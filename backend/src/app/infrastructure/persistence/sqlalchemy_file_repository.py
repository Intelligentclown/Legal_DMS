"""PostgreSQL File repository with ADR-0027 atomic Matter counters."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.interfaces.file_repository import FileRepository
from app.infrastructure.persistence.models.file import File
from app.infrastructure.persistence.sqlalchemy_repository import SqlAlchemyRepository


class SqlAlchemyFileRepository(SqlAlchemyRepository[File], FileRepository):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, File)

    async def get_in_matter(
        self, file_id: UUID, organization_id: UUID, matter_id: UUID
    ) -> File | None:
        result = await self._session.execute(
            select(File).where(
                File.id == file_id,
                File.organization_id == organization_id,
                File.matter_id == matter_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_in_matter(
        self, organization_id: UUID, matter_id: UUID, *, limit: int, offset: int
    ) -> Sequence[File]:
        result = await self._session.execute(
            select(File)
            .where(File.organization_id == organization_id, File.matter_id == matter_id)
            .order_by(File.file_number)
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    async def count_in_matter(self, organization_id: UUID, matter_id: UUID) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(File)
            .where(File.organization_id == organization_id, File.matter_id == matter_id)
        )
        return result.scalar_one()

    async def allocate_and_add(self, file: File) -> File:
        # PostgreSQL's conflict update locks only this Matter's counter row.
        # The enclosing request transaction commits/rolls back both statements.
        async with self._session.begin_nested():
            result = await self._session.execute(
                text("""
                INSERT INTO file_number_sequences (matter_id, organization_id, next_number)
                VALUES (:matter_id, :organization_id, 2)
                ON CONFLICT ON CONSTRAINT uq_file_number_sequences_organization_id_matter_id
                DO UPDATE
                SET next_number = file_number_sequences.next_number + 1
                WHERE file_number_sequences.organization_id = EXCLUDED.organization_id
                RETURNING next_number - 1
            """),
                {"matter_id": file.matter_id, "organization_id": file.organization_id},
            )
            file.file_number = int(result.scalar_one())
            self._session.add(file)
            await self._session.flush()
        return file
