"""Consistent success-response envelope for future endpoints.

`/health` and `/version` intentionally stay unwrapped — simple, framework-
agnostic liveness/version probes by convention. `ApiResponse` is for future
resource-returning endpoints so every one of them has the same
`{"data": ..., "meta": ...}` shape.
"""

from __future__ import annotations

from pydantic import BaseModel

from app.application.common.pagination import PageResult


class ApiResponse[T](BaseModel):
    data: T
    meta: dict[str, object] | None = None


class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


def paginated_response[T](page_result: PageResult[T]) -> ApiResponse[list[T]]:
    meta = PaginationMeta(
        page=page_result.page,
        page_size=page_result.page_size,
        total=page_result.total,
        total_pages=page_result.total_pages,
    )
    return ApiResponse(data=page_result.items, meta={"pagination": meta.model_dump()})
