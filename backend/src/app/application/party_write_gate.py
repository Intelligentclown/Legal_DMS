"""ADR-0036 enablement gate for ordinary Party writes (T124).

`PartyWriteGate` is the application-layer fail-closed gate between the
authorized Party permission surface (`parties:write` / `parties:delete`, the
presentation layer) and database writes: before any normal create/update/delete
of a `Party` row, `ensure_writable()` consults `InstallationClassifier` and
only a `FRESH` classification proceeds. Every other state — and any failure to
observe the database — raises `ForbiddenError` so a Party write is never
reachable in a legacy or ambiguous installation.

This applies to ORDINARY Party writes only. The T118 migration executor's
own owning-path writes are a governed transfer path and are intentionally
not routed through this gate (ADR-0036's migration window); the classifier and
gate are also deliberately never consulted for reads, which are already
protected by Party RLS (T123) plus Organization scoping and the permission
surface.
"""

from __future__ import annotations

from app.application.errors.exceptions import ForbiddenError
from app.application.interfaces.install_classifier import (
    InstallationClassifier,
    InstallationState,
)


class PartyWriteGate:
    """Fail-closed enablement gate over an `InstallationClassifier`."""

    def __init__(self, classifier: InstallationClassifier) -> None:
        self._classifier = classifier

    async def ensure_writable(self) -> None:
        state = await self._classifier.classify()
        if state is not InstallationState.FRESH:
            raise ForbiddenError(
                "Party writes are not available in this installation: it is "
                f"classified as {state.value!r}, not the ADR-0036 fresh-install "
                "state. Ordinary Party writes are gated until the governed "
                "migration window (T108-T118) has cut over."
            )
