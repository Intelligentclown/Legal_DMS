"""Test-only static `InstallationClassifier` for forcing a chosen ADR-0036
state where a test needs determinism without touching a database (e.g. the
party HTTP suites, whose address-validation paths are otherwise unreachable
because a real address row itself flips the real classifier to legacy).
"""

from __future__ import annotations

from app.application.interfaces.install_classifier import (
    InstallationClassifier,
    InstallationState,
)


class StaticInstallationClassifier(InstallationClassifier):
    """Returns a fixed `InstallationState` from every `classify()` call."""

    def __init__(self, state: InstallationState) -> None:
        self._state = state

    async def classify(self) -> InstallationState:
        return self._state
