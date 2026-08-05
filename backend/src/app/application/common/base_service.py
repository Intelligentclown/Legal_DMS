"""Base class for application services.

A service orchestrates one or more repositories (and other ports) to
implement a use case. This base doesn't do much on its own — it standardizes
construction (a repository + a named logger) and provides one genuinely
reusable convenience — `get_by_id_or_raise` — since "fetch or 404" is
something almost every service needs and would otherwise reimplement
identically.
"""

from __future__ import annotations

from uuid import UUID

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
