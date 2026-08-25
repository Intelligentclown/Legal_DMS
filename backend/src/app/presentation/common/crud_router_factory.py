"""Generic CRUD router factory — the "Base Controller" pattern for Stage 1's
core architecture. Ties together `BaseService`, pagination, and the
`ApiResponse` envelope into a standard list/get/create/update/delete set of
routes for any entity, with no business logic living in the router itself
(that stays in the service).

Not mounted into the real app in Stage 1 — proven with a test-only in-memory
entity in `tests/integration/test_crud_router_factory.py`. A future feature
wires its real router with this once a real entity/schema exists.

Deliberately does NOT use `from __future__ import annotations`: FastAPI
needs the *actual* Pydantic model classes for its request-body and
response-model introspection. This function's own PEP 695 type parameters
(`ReadSchema`, `CreateSchema`, ...) are `TypeVar` placeholders at runtime,
not the concrete classes — using them as nested-function parameter
annotations would make FastAPI treat the request body as an unresolvable
query parameter. The fix is to annotate with the actual runtime arguments
(`read_schema`, `create_schema`, ...) instead, which requires eager
(non-postponed) annotation evaluation so the closure variable's current
value is captured directly rather than deferred to a string.
"""

from collections.abc import Callable
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel

from app.application.common.base_service import BaseService
from app.application.common.pagination import DEFAULT_PAGE_SIZE, PageRequest
from app.application.common.query import (
    FilterOperator,
    FilterSpec,
    SearchQuery,
    SortDirection,
    SortSpec,
)
from app.application.interfaces.repository import SupportsId
from app.presentation.common.response import ApiResponse, paginated_response


def _parse_sort_param(raw: str) -> SortSpec:
    field, _, direction = raw.partition(":")
    if direction:
        return SortSpec(field=field, direction=SortDirection(direction))
    return SortSpec(field=field)


def _parse_filter_param(raw: str) -> FilterSpec:
    field, operator, value = raw.split(":", 2)
    parsed_operator = FilterOperator(operator)
    parsed_value: object = value.split(",") if parsed_operator is FilterOperator.IN else value
    return FilterSpec(field=field, operator=parsed_operator, value=parsed_value)


def _build_search_query(sort: list[str] | None, filters: list[str] | None) -> SearchQuery | None:
    if not sort and not filters:
        return None
    return SearchQuery(
        sort=tuple(_parse_sort_param(item) for item in sort or []),
        filters=tuple(_parse_filter_param(item) for item in filters or []),
    )


def build_crud_router[
    T: SupportsId, ReadSchema: BaseModel, CreateSchema: BaseModel, UpdateSchema: BaseModel
](
    *,
    prefix: str,
    tags: list[str],
    get_service: Callable[..., BaseService[T]],
    read_schema: type[ReadSchema],
    create_schema: type[CreateSchema],
    update_schema: type[UpdateSchema],
    build_entity: Callable[[CreateSchema], T],
    apply_update: Callable[[T, UpdateSchema], T],
) -> APIRouter:
    """Build a standard CRUD router for entity type `T`.

    `build_entity` and `apply_update` are the two pieces of mapping the
    factory can't do generically — turning a validated create/update payload
    into (or onto) an entity is specific to what `T` actually needs.
    """
    router = APIRouter(prefix=prefix, tags=tags)

    def _to_read(entity: T) -> ReadSchema:
        return read_schema.model_validate(entity, from_attributes=True)

    @router.get("", response_model=ApiResponse[list[read_schema]])
    async def list_items(
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
        sort: list[str] | None = Query(default=None),
        filters: list[str] | None = Query(default=None, alias="filter"),
        service: BaseService = Depends(get_service),
    ) -> ApiResponse[list[ReadSchema]]:
        request = PageRequest(page=page, page_size=page_size)
        search_query = _build_search_query(sort=sort, filters=filters)
        if search_query is not None:
            page_result = await service.list_page(request, query=search_query)
        else:
            page_result = await service.list_page(request)
        entity_response = paginated_response(page_result)
        return ApiResponse(
            data=[_to_read(item) for item in entity_response.data],
            meta=entity_response.meta,
        )

    @router.get("/{item_id}", response_model=ApiResponse[read_schema])
    async def get_item(
        item_id: UUID, service: BaseService = Depends(get_service)
    ) -> ApiResponse[ReadSchema]:
        entity = await service.get_by_id_or_raise(item_id)
        return ApiResponse(data=_to_read(entity))

    @router.post("", status_code=status.HTTP_201_CREATED, response_model=ApiResponse[read_schema])
    async def create_item(
        payload: create_schema, service: BaseService = Depends(get_service)
    ) -> ApiResponse[ReadSchema]:
        created = await service.create(build_entity(payload))
        return ApiResponse(data=_to_read(created))

    @router.put("/{item_id}", response_model=ApiResponse[read_schema])
    async def update_item(
        item_id: UUID,
        payload: update_schema,
        service: BaseService = Depends(get_service),
    ) -> ApiResponse[ReadSchema]:
        entity = await service.get_by_id_or_raise(item_id)
        updated = await service.update(apply_update(entity, payload))
        return ApiResponse(data=_to_read(updated))

    @router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_item(item_id: UUID, service: BaseService = Depends(get_service)) -> None:
        await service.delete(item_id)

    return router
