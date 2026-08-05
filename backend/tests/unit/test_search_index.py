"""Tests for the search foundation: SearchIndex port + InMemorySearchIndex."""

from __future__ import annotations

from app.application.common.pagination import PageRequest
from app.application.common.query import FilterOperator, FilterSpec, SearchQuery
from app.application.interfaces.search import SearchIndex
from app.infrastructure.di.container import configure_container, container
from app.infrastructure.search.in_memory_search_index import InMemorySearchIndex


class TestInMemorySearchIndex:
    async def test_search_with_no_query_returns_everything(self) -> None:
        index = InMemorySearchIndex()
        await index.index("1", "First document")
        await index.index("2", "Second document")

        results = await index.search(SearchQuery())

        assert results.total == 2
        assert {hit.document_id for hit in results.hits} == {"1", "2"}

    async def test_free_text_query_matches_substring_case_insensitively(self) -> None:
        index = InMemorySearchIndex()
        await index.index("1", "The quick Brown fox")
        await index.index("2", "A lazy dog")

        results = await index.search(SearchQuery(q="brown"))

        assert results.total == 1
        assert results.hits[0].document_id == "1"

    async def test_remove_excludes_the_document_from_future_searches(self) -> None:
        index = InMemorySearchIndex()
        await index.index("1", "hello")

        await index.remove("1")

        results = await index.search(SearchQuery())
        assert results.total == 0

    async def test_filter_eq_matches_metadata_field(self) -> None:
        index = InMemorySearchIndex()
        await index.index("1", "doc", metadata={"status": "active"})
        await index.index("2", "doc", metadata={"status": "archived"})

        results = await index.search(
            SearchQuery(
                filters=(FilterSpec(field="status", operator=FilterOperator.EQ, value="active"),)
            )
        )

        assert results.total == 1
        assert results.hits[0].document_id == "1"

    async def test_filter_gte_matches_numeric_metadata(self) -> None:
        index = InMemorySearchIndex()
        await index.index("1", "doc", metadata={"priority": 1})
        await index.index("2", "doc", metadata={"priority": 5})

        results = await index.search(
            SearchQuery(
                filters=(FilterSpec(field="priority", operator=FilterOperator.GTE, value=3),)
            )
        )

        assert [hit.document_id for hit in results.hits] == ["2"]

    async def test_pagination_via_search_query_page(self) -> None:
        index = InMemorySearchIndex()
        for i in range(5):
            await index.index(str(i), "doc")

        results = await index.search(SearchQuery(page=PageRequest(page=2, page_size=2)))

        assert results.total == 5
        assert len(results.hits) == 2


class TestConfigureContainer:
    def test_registers_search_index_as_in_memory_implementation(self) -> None:
        configure_container()

        assert isinstance(container.resolve(SearchIndex), InMemorySearchIndex)
