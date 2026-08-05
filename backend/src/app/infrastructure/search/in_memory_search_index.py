"""In-memory substring-match search index — proves the `SearchIndex`
interface shape. Real full-text/OCR/metadata/smart search implementations
(e.g. Postgres full-text search, Elasticsearch, ...) satisfy the same port
later without touching callers.

Supports `SearchQuery.q` (substring match against content) and
`SearchQuery.filters` (equality/comparison against metadata fields).
Deliberately does NOT apply `SearchQuery.sort` — a real index's sort
semantics depend on its backend; this naive default only proves the shape.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.application.common.query import FilterOperator, FilterSpec, SearchQuery
from app.application.interfaces.search import SearchHit, SearchIndex, SearchResults


@dataclass
class _IndexedDocument:
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


def _matches_filter(value: Any, filter_spec: FilterSpec) -> bool:
    target = filter_spec.value
    match filter_spec.operator:
        case FilterOperator.EQ:
            return value == target
        case FilterOperator.NEQ:
            return value != target
        case FilterOperator.CONTAINS:
            return value is not None and target in value
        case FilterOperator.IN:
            return value in target
        case FilterOperator.GT:
            return value is not None and value > target
        case FilterOperator.GTE:
            return value is not None and value >= target
        case FilterOperator.LT:
            return value is not None and value < target
        case FilterOperator.LTE:
            return value is not None and value <= target


class InMemorySearchIndex(SearchIndex):
    def __init__(self) -> None:
        self._documents: dict[str, _IndexedDocument] = {}

    async def index(
        self, document_id: str, content: str, metadata: dict[str, Any] | None = None
    ) -> None:
        self._documents[document_id] = _IndexedDocument(content=content, metadata=metadata or {})

    async def remove(self, document_id: str) -> None:
        self._documents.pop(document_id, None)

    async def search(self, query: SearchQuery) -> SearchResults:
        matches = list(self._documents.items())

        if query.q:
            needle = query.q.lower()
            matches = [(doc_id, doc) for doc_id, doc in matches if needle in doc.content.lower()]

        for filter_spec in query.filters:
            matches = [
                (doc_id, doc)
                for doc_id, doc in matches
                if _matches_filter(doc.metadata.get(filter_spec.field), filter_spec)
            ]

        total = len(matches)
        page = matches[query.page.offset : query.page.offset + query.page.limit]
        hits = [
            SearchHit(document_id=doc_id, score=1.0, metadata=doc.metadata) for doc_id, doc in page
        ]
        return SearchResults(hits=hits, total=total)
