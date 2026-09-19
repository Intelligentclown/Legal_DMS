"""ADR-0037 operational-fresh installation classification port (T127).

Ordinary Party writes are eligible only for ``OPERATIONAL_FRESH``: the state
proven by T126's immutable birth and operational-transition evidence. Current
row counts still distinguish migration and legacy evidence, but cannot make an
empty upgraded installation fresh again.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum


class InstallationState(StrEnum):
    """The mechanical classification of a live installation (ADR-0037)."""

    OPERATIONAL_FRESH = "operational_fresh"
    UNPROVEN = "unproven"
    LEGACY_WITH_BUSINESS_DATA = "legacy_with_business_data"
    MIGRATED = "migrated"


class InstallationClassificationError(Exception):
    """Raised when installation provenance cannot be safely classified."""


class InstallationClassifier(ABC):
    """Port for deterministic provenance-aware runtime classification."""

    @abstractmethod
    async def classify(self) -> InstallationState:
        """Classify from database evidence only, never caller assertions."""
        ...
