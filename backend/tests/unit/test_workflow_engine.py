"""Tests for the generic workflow engine, using a toy A -> B -> C graph —
deliberately not the charter's real-world example workflow, since only the
engine ships in Stage 1, not any business workflow definition.
"""

from __future__ import annotations

import pytest

from app.application.workflow.engine import (
    Transition,
    WorkflowDefinition,
    WorkflowEngine,
    WorkflowError,
)


def _toy_definition(*, guard: bool = True) -> WorkflowDefinition:
    return WorkflowDefinition(
        name="toy",
        initial_state="A",
        states=frozenset({"A", "B", "C"}),
        transitions={
            "A": (Transition(event="advance", target="B"),),
            "B": (
                Transition(event="advance", target="C", guard=lambda: guard),
                Transition(event="retreat", target="A"),
            ),
        },
    )


class TestWorkflowDefinitionValidation:
    def test_rejects_initial_state_not_in_states(self) -> None:
        with pytest.raises(ValueError, match="initial_state"):
            WorkflowDefinition(
                name="bad", initial_state="Z", states=frozenset({"A"}), transitions={}
            )

    def test_rejects_transition_source_not_in_states(self) -> None:
        with pytest.raises(ValueError, match="source state"):
            WorkflowDefinition(
                name="bad",
                initial_state="A",
                states=frozenset({"A"}),
                transitions={"Z": (Transition(event="go", target="A"),)},
            )

    def test_rejects_transition_target_not_in_states(self) -> None:
        with pytest.raises(ValueError, match="target state"):
            WorkflowDefinition(
                name="bad",
                initial_state="A",
                states=frozenset({"A"}),
                transitions={"A": (Transition(event="go", target="Z"),)},
            )


class TestWorkflowEngine:
    def test_valid_transition_moves_to_target_state(self) -> None:
        engine = WorkflowEngine(_toy_definition())

        assert engine.transition("A", "advance") == "B"
        assert engine.transition("B", "advance") == "C"

    def test_can_transition_reflects_validity_without_applying(self) -> None:
        engine = WorkflowEngine(_toy_definition())

        assert engine.can_transition("A", "advance") is True
        assert engine.can_transition("A", "retreat") is False

    def test_invalid_event_raises_workflow_error(self) -> None:
        engine = WorkflowEngine(_toy_definition())

        with pytest.raises(WorkflowError, match="No valid transition"):
            engine.transition("A", "teleport")

    def test_event_valid_elsewhere_but_not_from_this_state_raises(self) -> None:
        engine = WorkflowEngine(_toy_definition())

        with pytest.raises(WorkflowError):
            engine.transition("C", "advance")

    def test_transition_can_move_backward(self) -> None:
        engine = WorkflowEngine(_toy_definition())

        assert engine.transition("B", "retreat") == "A"

    def test_guard_blocks_the_transition_when_false(self) -> None:
        engine = WorkflowEngine(_toy_definition(guard=False))

        assert engine.can_transition("B", "advance") is False
        with pytest.raises(WorkflowError):
            engine.transition("B", "advance")

    def test_guard_allows_the_transition_when_true(self) -> None:
        engine = WorkflowEngine(_toy_definition(guard=True))

        assert engine.transition("B", "advance") == "C"
