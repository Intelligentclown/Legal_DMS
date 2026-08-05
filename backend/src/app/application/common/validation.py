"""Reusable validation framework: a `Validator[T]` protocol for business-rule
validation that goes beyond basic schema shape (which Pydantic already
handles at the presentation boundary), plus a helper that turns accumulated
failures into a single `ValidationError`.
"""

from __future__ import annotations

from typing import Protocol

from app.application.errors.exceptions import ValidationError


class Validator[T](Protocol):
    """A single business-rule check against a value of type T."""

    def validate(self, value: T) -> list[str]:
        """Return human-readable error messages; empty list means valid."""
        ...


def validate_all[T](value: T, validators: list[Validator[T]]) -> None:
    """Run every validator against `value`; raise ValidationError with all
    accumulated messages if any validator reported a problem.
    """
    errors: list[str] = []
    for validator in validators:
        errors.extend(validator.validate(value))

    if errors:
        raise ValidationError("; ".join(errors))
