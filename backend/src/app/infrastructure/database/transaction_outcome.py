"""Request-local external-side-effect compensation (ADR-0042)."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from enum import StrEnum


class TransactionOutcome(StrEnum):
    CONFIRMED_COMMIT = "confirmed_commit"
    DEFINITIVE_NON_COMMIT = "definitive_non_commit"
    COMMIT_OUTCOME_UNCERTAIN = "commit_outcome_uncertain"


Compensation = Callable[[], Awaitable[None]]
logger = logging.getLogger(__name__)


class TransactionOutcomeUncertainError(Exception):
    """The server cannot safely say whether the final database commit happened."""


class TransactionOutcomeContext:
    """Domain-neutral, single-use registry finalized only by ``get_db``."""

    def __init__(self) -> None:
        self._actions: list[Compensation] = []
        self._outcome: TransactionOutcome | None = None

    def register(self, action: Compensation) -> None:
        if self._outcome is not None:
            raise RuntimeError("Cannot register compensation after transaction finalization")
        self._actions.append(action)

    @property
    def outcome(self) -> TransactionOutcome | None:
        return self._outcome

    async def finalize(self, outcome: TransactionOutcome) -> None:
        if self._outcome is not None:
            raise RuntimeError("Transaction outcome already finalized")
        self._outcome = outcome
        actions, self._actions = self._actions, []
        if outcome is not TransactionOutcome.DEFINITIVE_NON_COMMIT:
            return
        for action in reversed(actions):
            try:
                await action()
            except Exception:
                logger.exception("transaction compensation failed")
