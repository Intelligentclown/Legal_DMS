"""Integration test for the generic CRUD router factory, proving the
mechanism works end-to-end via a throwaway FastAPI app — never mounted into
the real shipped app (`main.py` only ever mounts `/health` and `/version`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.application.common.base_service import BaseService
from app.presentation.common.crud_router_factory import build_crud_router
from app.presentation.middleware.error_handler import register_exception_handlers
from tests.support.in_memory_repository import InMemoryRepository


@dataclass
class _Note:
    id: UUID = field(default_factory=uuid4)
    text: str = ""


class _NoteRead(BaseModel):
    id: UUID
    text: str


class _NoteCreate(BaseModel):
    text: str


class _NoteUpdate(BaseModel):
    text: str


def _build_note(payload: _NoteCreate) -> _Note:
    return _Note(text=payload.text)


def _apply_note_update(entity: _Note, payload: _NoteUpdate) -> _Note:
    entity.text = payload.text
    return entity


@pytest.fixture
def client() -> TestClient:
    repository = InMemoryRepository[_Note]()
    service = BaseService[_Note](repository, resource_name="Note")

    def get_service() -> BaseService[_Note]:
        return service

    test_app = FastAPI()
    register_exception_handlers(test_app)
    test_app.include_router(
        build_crud_router(
            prefix="/notes",
            tags=["notes"],
            get_service=get_service,
            read_schema=_NoteRead,
            create_schema=_NoteCreate,
            update_schema=_NoteUpdate,
            build_entity=_build_note,
            apply_update=_apply_note_update,
        )
    )
    return TestClient(test_app)


class TestCrudRouterFactory:
    def test_create_then_get_round_trips(self, client: TestClient) -> None:
        create_response = client.post("/notes", json={"text": "hello"})
        assert create_response.status_code == 201
        note_id = create_response.json()["data"]["id"]

        get_response = client.get(f"/notes/{note_id}")

        assert get_response.status_code == 200
        assert get_response.json()["data"]["text"] == "hello"

    def test_get_missing_item_returns_404_with_consistent_error_shape(
        self, client: TestClient
    ) -> None:
        response = client.get(f"/notes/{uuid4()}")

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"

    def test_list_returns_paginated_items(self, client: TestClient) -> None:
        for i in range(3):
            client.post("/notes", json={"text": f"note-{i}"})

        response = client.get("/notes", params={"page": 1, "page_size": 2})

        assert response.status_code == 200
        body = response.json()
        assert len(body["data"]) == 2
        assert body["meta"]["pagination"]["total"] == 3

    def test_update_changes_the_item(self, client: TestClient) -> None:
        create_response = client.post("/notes", json={"text": "before"})
        note_id = create_response.json()["data"]["id"]

        update_response = client.put(f"/notes/{note_id}", json={"text": "after"})

        assert update_response.status_code == 200
        assert update_response.json()["data"]["text"] == "after"

    def test_delete_removes_the_item(self, client: TestClient) -> None:
        create_response = client.post("/notes", json={"text": "temp"})
        note_id = create_response.json()["data"]["id"]

        delete_response = client.delete(f"/notes/{note_id}")
        assert delete_response.status_code == 204

        get_response = client.get(f"/notes/{note_id}")
        assert get_response.status_code == 404
