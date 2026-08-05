"""Reusable shapes for filtering, sorting, and search — the parts of a "list
resources" request that are the same regardless of which resource is being
listed. A repository's list()/search() implementation is what interprets
these; this module only defines the shape, matching the "framework only, no
implementation yet" instruction for the search foundation specifically.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from app.application.common.pagination import PageRequest


class SortDirection(StrEnum):
    ASC = "asc"
    DESC = "desc"


@dataclass(frozen=True, slots=True)
class SortSpec:
    field: str
    direction: SortDirection = SortDirection.ASC


class FilterOperator(StrEnum):
    EQ = "eq"
    NEQ = "neq"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    CONTAINS = "contains"
    IN = "in"


@dataclass(frozen=True, slots=True)
class FilterSpec:
    field: str
    operator: FilterOperator
    value: object


@dataclass(frozen=True, slots=True)
class SearchQuery:
    """A full "list/search resources" request: free-text query, structured
    filters, sort order, and pagination — everything optional except paging.
    """

    page: PageRequest = field(default_factory=PageRequest)
    q: str | None = None
    filters: tuple[FilterSpec, ...] = ()
    sort: tuple[SortSpec, ...] = ()
