"""Base building blocks for the domain layer.

No framework imports belong here — domain code must stay usable regardless of
what web framework, ORM, or delivery mechanism the outer layers use.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID


class Entity:
    """Base class for domain entities: identity-based equality via `id`."""

    id: UUID

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Entity):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)


@dataclass(frozen=True, slots=True)
class ValueObject:
    """Base marker for immutable, value-based-equality domain objects."""
