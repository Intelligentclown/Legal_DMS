"""Bounded T138 File use cases: org-scoped, Matter-scoped and immutable numbering."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any
from uuid import UUID, uuid4

from app.application.errors.exceptions import NotFoundError, ValidationError
from app.application.interfaces.file_repository import FileRepository
from app.application.interfaces.matter_repository import MatterRepository
from app.infrastructure.persistence.models.file import File


class FileService:
    def __init__(self, repository: FileRepository, matter_repository: MatterRepository) -> None:
        self._repository = repository
        self._matter_repository = matter_repository

    async def _matter(self, organization_id: UUID, matter_id: UUID) -> None:
        if (
            await self._matter_repository.get_by_id_in_organization(matter_id, organization_id)
            is None
        ):
            raise NotFoundError(f"Matter with id {matter_id} was not found")

    async def list_in_matter(
        self, organization_id: UUID, matter_id: UUID, *, limit: int, offset: int
    ) -> Sequence[File]:
        await self._matter(organization_id, matter_id)
        return await self._repository.list_in_matter(
            organization_id, matter_id, limit=limit, offset=offset
        )

    async def count_in_matter(self, organization_id: UUID, matter_id: UUID) -> int:
        await self._matter(organization_id, matter_id)
        return await self._repository.count_in_matter(organization_id, matter_id)

    async def get_in_matter(self, file_id: UUID, organization_id: UUID, matter_id: UUID) -> File:
        await self._matter(organization_id, matter_id)
        file = await self._repository.get_in_matter(file_id, organization_id, matter_id)
        if file is None:
            raise NotFoundError(f"File with id {file_id} was not found")
        return file

    async def create_in_matter(
        self, organization_id: UUID, matter_id: UUID, title: str, *, actor_id: UUID | None = None
    ) -> File:
        await self._matter(organization_id, matter_id)
        if not title.strip():
            raise ValidationError("title is required")
        file = File(
            id=uuid4(),
            organization_id=organization_id,
            matter_id=matter_id,
            file_number=0,
            title=title,
            created_by=actor_id,
            updated_by=actor_id,
        )
        return await self._repository.allocate_and_add(file)

    async def update_title_in_matter(
        self,
        file_id: UUID,
        organization_id: UUID,
        matter_id: UUID,
        fields: Mapping[str, Any],
        *,
        actor_id: UUID | None = None,
    ) -> File:
        file = await self.get_in_matter(file_id, organization_id, matter_id)
        if "title" in fields:
            title = fields["title"]
            if not isinstance(title, str) or not title.strip():
                raise ValidationError("title is required")
            file.title = title
            file.updated_by = actor_id
        return await self._repository.update(file)
