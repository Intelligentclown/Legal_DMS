"""FastAPI application factory and entrypoint.

Run with: `uv run uvicorn app.main:app --reload` (from `backend/`).
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.infrastructure.config import get_settings
from app.infrastructure.logging import configure_logging, get_logger
from app.presentation.api.v1.router import router as v1_router
from app.presentation.middleware.error_handler import register_exception_handlers
from app.presentation.middleware.logging_middleware import LoggingMiddleware
from app.presentation.middleware.request_id import RequestIDMiddleware

logger = get_logger("main")


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(LoggingMiddleware)
    # Added last so it becomes the outermost middleware, running before
    # LoggingMiddleware/CORS on the way in — every downstream handler and
    # log line can then rely on request.state.request_id being set.
    app.add_middleware(RequestIDMiddleware)

    register_exception_handlers(app)

    app.include_router(v1_router, prefix=settings.api_v1_prefix)

    logger.info("Application startup complete", extra={"environment": settings.environment})

    return app


app = create_app()
