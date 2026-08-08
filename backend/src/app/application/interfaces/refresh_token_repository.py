"""Refresh token repository port (T50/ADR-0018): `AbstractRepository[RefreshToken]`
plus "find by token hash" — the one lookup `AuthService.refresh()`/`.revoke()`
need that the generic port can't express (neither is a lookup by primary key).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.application.interfaces.repository import AbstractRepository
from app.infrastructure.persistence.models.identity import RefreshToken


class RefreshTokenRepository(AbstractRepository[RefreshToken], ABC):
    @abstractmethod
    async def get_by_token_hash(self, token_hash: str) -> RefreshToken | None: ...
