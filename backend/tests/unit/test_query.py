"""Tests for the filter/sort/search query shapes."""

from app.application.common.pagination import PageRequest
from app.application.common.query import (
    FilterOperator,
    FilterSpec,
    SearchQuery,
    SortDirection,
    SortSpec,
)


class TestSearchQuery:
    def test_defaults_to_empty_filters_and_sort_with_first_page(self) -> None:
        query = SearchQuery()

        assert query.q is None
        assert query.filters == ()
        assert query.sort == ()
        assert query.page == PageRequest()

    def test_carries_filters_sort_and_free_text_query(self) -> None:
        query = SearchQuery(
            q="acme",
            filters=(FilterSpec(field="status", operator=FilterOperator.EQ, value="active"),),
            sort=(SortSpec(field="created_at", direction=SortDirection.DESC),),
        )

        assert query.q == "acme"
        assert query.filters[0].operator is FilterOperator.EQ
        assert query.sort[0].direction is SortDirection.DESC
