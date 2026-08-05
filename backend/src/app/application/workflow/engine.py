"""Generic workflow engine: define states and the transitions allowed
between them, then drive an instance through them one event at a time.
Pure state machine — no persistence of workflow instances, no framework
imports. A future feature persists "what state is this Matter/Document in"
itself; the engine only decides whether a transition is valid.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Transition:
    event: str
    target: str
    guard: Callable[[], bool] | None = None


@dataclass(frozen=True, slots=True)
class WorkflowDefinition:
    """A named state machine: states, and the transitions allowed from each."""

    name: str
    initial_state: str
    states: frozenset[str]
    transitions: dict[str, tuple[Transition, ...]]

    def __post_init__(self) -> None:
        if self.initial_state not in self.states:
            raise ValueError(f"initial_state {self.initial_state!r} is not in states")
        for state, transitions in self.transitions.items():
            if state not in self.states:
                raise ValueError(f"transition source state {state!r} is not in states")
            for transition in transitions:
                if transition.target not in self.states:
                    raise ValueError(
                        f"transition target state {transition.target!r} is not in states"
                    )


class WorkflowError(Exception):
    """Raised when an event has no valid transition from the current state."""


class WorkflowEngine:
    """Drives a single `WorkflowDefinition`: given a current state and an
    event, determines (or applies) the next state.
    """

    def __init__(self, definition: WorkflowDefinition) -> None:
        self._definition = definition

    def _matching_transition(self, current_state: str, event: str) -> Transition | None:
        for transition in self._definition.transitions.get(current_state, ()):
            if transition.event == event and (transition.guard is None or transition.guard()):
                return transition
        return None

    def can_transition(self, current_state: str, event: str) -> bool:
        return self._matching_transition(current_state, event) is not None

    def transition(self, current_state: str, event: str) -> str:
        matched = self._matching_transition(current_state, event)
        if matched is None:
            raise WorkflowError(
                f"No valid transition for event {event!r} from state {current_state!r} "
                f"in workflow {self._definition.name!r}"
            )
        return matched.target
