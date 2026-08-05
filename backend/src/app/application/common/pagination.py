"""Pagination framework: a request shape and a generic result envelope,
independent of any specific repository or endpoint.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


@dataclass(frozen=True, slots=True)
class PageRequest:
    page: int = 1
    page_size: int = DEFAULT_PAGE_SIZE

    def __post_init__(self) -> None:
        if self.page < 1:
            raise ValueError("page must be >= 1")
        if not (1 <= self.page_size <= MAX_PAGE_SIZE):
            raise ValueError(f"page_size must be between 1 and {MAX_PAGE_SIZE}")

    @property
    def limit(self) -> int:
        return self.page_size

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


@dataclass(frozen=True, slots=True)
class PageResult[T]:
    items: list[T]
    total: int
    page: int
    page_size: int

    @property
    def total_pages(self) -> int:
        if self.page_size == 0:
            return 0
        return ceil(self.total / self.page_size)

    @classmethod
    def create(cls, items: list[T], total: int, request: PageRequest) -> PageResult[T]:
        return cls(items=items, total=total, page=request.page, page_size=request.page_size)
