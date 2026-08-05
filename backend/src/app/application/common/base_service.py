"""Base class for application services.

A service orchestrates one or more repositories (and other ports) to
implement a use case. This base standardizes construction (a repository + a
named logger) and provides the CRUD convenience methods almost every service
needs — `get_by_id_or_raise`, `list_page`, `create`, `update`, `delete` —
each a thin, overridable wrapper around the repository. A feature's real
service overrides whichever of these need actual business rules; the ones
it doesn't override still work correctly via the repository directly.
"""

from __future__ import annotations

from uuid import UUID

from app.application.common.pagination import PageRequest, PageResult
from app.application.errors.exceptions import NotFoundError
from app.application.interfaces.repository import AbstractRepository, SupportsId
from app.infrastructure.logging.logger import get_logger


class BaseService[T: SupportsId]:
    def __init__(
        self, repository: AbstractRepository[T], *, resource_name: str | None = None
    ) -> None:
        self._repository = repository
        self._resource_name = resource_name or type(self).__name__.removesuffix("Service")
        self._logger = get_logger(f"service.{self._resource_name.lower()}")

    async def get_by_id_or_raise(self, id_: UUID) -> T:
        entity = await self._repository.get_by_id(id_)
        if entity is None:
            raise NotFoundError(f"{self._resource_name} with id {id_} was not found")
        return entity

    async def list_page(self, request: PageRequest) -> PageResult[T]:
        items = await self._repository.list(limit=request.limit, offset=request.offset)
        total = await self._repository.count()
        return PageResult.create(list(items), total=total, request=request)

    async def create(self, entity: T) -> T:
        return await self._repository.add(entity)

    async def update(self, entity: T) -> T:
        return await self._repository.update(entity)

    async def delete(self, id_: UUID) -> None:
        await self.get_by_id_or_raise(id_)
        await self._repository.delete(id_)
