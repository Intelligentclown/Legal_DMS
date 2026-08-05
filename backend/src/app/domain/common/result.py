"""Result[T, E]: an explicit success/failure return type for operations whose
failure is an expected, handleable outcome — not a raised exception.

Prefer raising an `AppError` subclass (see `application/errors/exceptions.py`)
for failures that should abort the request/operation. Prefer `Result` when
the caller is expected to branch on success/failure as part of normal control
flow (e.g. a validation step that collects errors rather than aborting).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Result[T, E]:
    _value: T | None
    _error: E | None
    is_success: bool

    @classmethod
    def ok(cls, value: T) -> Result[T, E]:
        return cls(_value=value, _error=None, is_success=True)

    @classmethod
    def fail(cls, error: E) -> Result[T, E]:
        return cls(_value=None, _error=error, is_success=False)

    @property
    def is_failure(self) -> bool:
        return not self.is_success

    @property
    def value(self) -> T:
        if not self.is_success:
            raise ValueError("Cannot access .value on a failed Result")
        return self._value  # type: ignore[return-value]

    @property
    def error(self) -> E:
        if self.is_success:
            raise ValueError("Cannot access .error on a successful Result")
        return self._error  # type: ignore[return-value]
