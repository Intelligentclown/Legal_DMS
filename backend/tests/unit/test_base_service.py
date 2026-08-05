"""Tests for BaseService using a simple in-memory fake repository — no
database needed, this is pure application-layer logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

import pytest

from app.application.common.base_service import BaseService
from app.application.common.pagination import PageRequest
from app.application.errors.exceptions import NotFoundError
from tests.support.in_memory_repository import InMemoryRepository


@dataclass
class _Widget:
    id: UUID = field(default_factory=uuid4)
    name: str = ""


class WidgetService(BaseService[_Widget]):
    pass


class TestBaseService:
    async def test_get_by_id_or_raise_returns_entity_when_found(self) -> None:
        repo = InMemoryRepository[_Widget]()
        widget = _Widget(name="thing")
        await repo.add(widget)
        service = WidgetService(repo)

        found = await service.get_by_id_or_raise(widget.id)

        assert found is widget

    async def test_get_by_id_or_raise_raises_not_found_when_missing(self) -> None:
        service = WidgetService(InMemoryRepository[_Widget]())

        with pytest.raises(NotFoundError, match="Widget"):
            await service.get_by_id_or_raise(uuid4())

    async def test_not_found_message_uses_overridden_resource_name(self) -> None:
        service = WidgetService(InMemoryRepository[_Widget](), resource_name="Gadget")

        with pytest.raises(NotFoundError, match="Gadget"):
            await service.get_by_id_or_raise(uuid4())

    async def test_create_adds_and_returns_the_entity(self) -> None:
        service = WidgetService(InMemoryRepository[_Widget]())
        widget = _Widget(name="new")

        created = await service.create(widget)

        assert created is widget
        assert await service.get_by_id_or_raise(widget.id) is widget

    async def test_update_persists_changes(self) -> None:
        repo = InMemoryRepository[_Widget]()
        widget = _Widget(name="original")
        await repo.add(widget)
        service = WidgetService(repo)

        widget.name = "renamed"
        await service.update(widget)

        found = await service.get_by_id_or_raise(widget.id)
        assert found.name == "renamed"

    async def test_delete_removes_the_entity(self) -> None:
        repo = InMemoryRepository[_Widget]()
        widget = _Widget(name="doomed")
        await repo.add(widget)
        service = WidgetService(repo)

        await service.delete(widget.id)

        with pytest.raises(NotFoundError):
            await service.get_by_id_or_raise(widget.id)

    async def test_delete_raises_not_found_when_missing(self) -> None:
        service = WidgetService(InMemoryRepository[_Widget]())

        with pytest.raises(NotFoundError):
            await service.delete(uuid4())

    async def test_list_page_returns_items_and_total(self) -> None:
        repo = InMemoryRepository[_Widget]()
        for i in range(5):
            await repo.add(_Widget(name=f"item-{i}"))
        service = WidgetService(repo)

        page = await service.list_page(PageRequest(page=1, page_size=2))

        assert len(page.items) == 2
        assert page.total == 5
        assert page.total_pages == 3
