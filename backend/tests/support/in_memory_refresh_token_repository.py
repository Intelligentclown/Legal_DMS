"""In-memory fake satisfying `RefreshTokenRepository` (T50), for tests
that need refresh-token persistence/lookup without a real database.
"""

from __future__ import annotations

from app.application.interfaces.refresh_token_repository import RefreshTokenRepository
from app.infrastructure.persistence.models.identity import RefreshToken
from tests.support.in_memory_repository import InMemoryRepository


class InMemoryRefreshTokenRepository(InMemoryRepository[RefreshToken], RefreshTokenRepository):
    async def get_by_token_hash(self, token_hash: str) -> RefreshToken | None:
        return next((row for row in self._items.values() if row.token_hash == token_hash), None)
