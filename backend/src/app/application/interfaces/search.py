"""Search port: index documents and query them via the shared `SearchQuery`
shape (`application/common/query.py`). Concrete implementations live in
`infrastructure/search/`. The Stage 1 default is a naive in-memory
substring-match index proving the interface shape; real full-text/OCR/
metadata/smart search is deferred to a future stage.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from app.application.common.query import SearchQuery


@dataclass(frozen=True, slots=True)
class SearchHit:
    document_id: str
    score: float
    metadata: dict[str, Any]


@dataclass(frozen=True, slots=True)
class SearchResults:
    hits: list[SearchHit]
    total: int


class SearchIndex(ABC):
    @abstractmethod
    async def index(
        self, document_id: str, content: str, metadata: dict[str, Any] | None = None
    ) -> None: ...

    @abstractmethod
    async def remove(self, document_id: str) -> None: ...

    @abstractmethod
    async def search(self, query: SearchQuery) -> SearchResults: ...
