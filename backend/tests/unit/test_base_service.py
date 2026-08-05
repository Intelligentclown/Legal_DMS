"""Tests for BaseService using a simple in-memory fake repository — no
database needed, this is pure application-layer logic.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from uuid import UUID, uuid4

import pytest

from app.application.common.base_service import BaseService
from app.application.errors.exceptions import NotFoundError
from app.application.interfaces.repository import AbstractRepository


@dataclass
class _Widget:
    id: UUID = field(default_factory=uuid4)
    name: str = ""


class _InMemoryWidgetRepository(AbstractRepository[_Widget]):
    def __init__(self) -> None:
        self._items: dict[UUID, _Widget] = {}

    async def get_by_id(self, id_: UUID) -> _Widget | None:
        return self._items.get(id_)

    async def list(self, *, limit: int = 100, offset: int = 0) -> Sequence[_Widget]:
        return list(self._items.values())[offset : offset + limit]

    async def add(self, entity: _Widget) -> _Widget:
        self._items[entity.id] = entity
        return entity

    async def update(self, entity: _Widget) -> _Widget:
        self._items[entity.id] = entity
        return entity

    async def delete(self, id_: UUID) -> None:
        self._items.pop(id_, None)


class WidgetService(BaseService[_Widget]):
    pass


class TestBaseService:
    async def test_get_by_id_or_raise_returns_entity_when_found(self) -> None:
        repo = _InMemoryWidgetRepository()
        widget = _Widget(name="thing")
        await repo.add(widget)
        service = WidgetService(repo)

        found = await service.get_by_id_or_raise(widget.id)

        assert found is widget

    async def test_get_by_id_or_raise_raises_not_found_when_missing(self) -> None:
        service = WidgetService(_InMemoryWidgetRepository())

        with pytest.raises(NotFoundError, match="Widget"):
            await service.get_by_id_or_raise(uuid4())

    async def test_not_found_message_uses_overridden_resource_name(self) -> None:
        service = WidgetService(_InMemoryWidgetRepository(), resource_name="Gadget")

        with pytest.raises(NotFoundError, match="Gadget"):
            await service.get_by_id_or_raise(uuid4())
