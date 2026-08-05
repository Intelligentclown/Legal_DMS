"""Centralized exception handling.

Registers FastAPI exception handlers so every error the API returns —
deliberate (`AppError`), validation, or truly unexpected — has the same
JSON shape: `{"error": {"code": ..., "message": ...}}`. Unexpected
exceptions are logged with full detail server-side but never leak
implementation details to the client.
"""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.application.errors import AppError
from app.infrastructure.logging import get_logger

logger = get_logger("error_handler")


def _error_response(status_code: int, error_code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": error_code, "message": message}},
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        logger.warning(
            "Application error: %s",
            exc.message,
            extra={
                "error_code": exc.error_code,
                "path": request.url.path,
                "request_id": getattr(request.state, "request_id", None),
            },
        )
        return _error_response(exc.status_code, exc.error_code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        logger.info(
            "Request validation failed",
            extra={"errors": exc.errors(), "path": request.url.path},
        )
        return _error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "validation_error",
            "Request validation failed.",
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "Unhandled exception on %s",
            request.url.path,
            exc_info=exc,
            extra={
                "path": request.url.path,
                "request_id": getattr(request.state, "request_id", None),
            },
        )
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "internal_error",
            "An unexpected error occurred.",
        )
