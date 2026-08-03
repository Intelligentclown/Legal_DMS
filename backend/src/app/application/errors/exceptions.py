"""Application-wide exception hierarchy.

All errors the application deliberately raises inherit from `AppError`, so a
single exception handler (see `presentation/middleware/error_handler.py`) can
translate any of them into a consistent JSON error response using
`status_code` and `error_code`. Anything that is *not* an `AppError` is an
unexpected/programming error and is handled separately, never leaked to the
client with implementation details.
"""

from __future__ import annotations


class AppError(Exception):
    """Base class for all deliberately-raised application errors."""

    status_code: int = 500
    error_code: str = "internal_error"

    def __init__(self, message: str, *, error_code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        if error_code is not None:
            self.error_code = error_code


class ValidationError(AppError):
    """Input failed validation rules beyond basic schema parsing."""

    status_code = 422
    error_code = "validation_error"


class NotFoundError(AppError):
    """A requested resource does not exist."""

    status_code = 404
    error_code = "not_found"


class ConflictError(AppError):
    """The request conflicts with the current state of the resource."""

    status_code = 409
    error_code = "conflict"


class UnauthorizedError(AppError):
    """The caller is not authenticated."""

    status_code = 401
    error_code = "unauthorized"


class ForbiddenError(AppError):
    """The caller is authenticated but not permitted to perform this action."""

    status_code = 403
    error_code = "forbidden"


class UnexpectedError(AppError):
    """A known failure mode that doesn't warrant its own exception type.

    Prefer a specific `AppError` subclass where one fits; use this only for
    genuinely miscellaneous, deliberately-raised failures.
    """

    status_code = 500
    error_code = "unexpected_error"
