"""Centralized, type-validated application configuration.

All configuration is read from environment variables (optionally via a local
`.env` file) — nothing is ever hardcoded. `get_settings()` is cached so the
same validated instance is reused everywhere via FastAPI's `Depends`.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

Environment = Literal["development", "testing", "production"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Environment = "development"

    app_name: str = "Legal Document & Matter Management System"
    api_v1_prefix: str = "/api/v1"
    app_version: str = "0.2.0"

    database_url: str = "postgresql+asyncpg://legal_dms:legal_dms@localhost:5432/legal_dms_dev"

    # T105/ADR-0021: the live app's request-serving get_db() connects through this
    # distinct, non-table-owning role instead of database_url's admin/owning role,
    # so FORCE'd RLS on organizations/users is a genuine backstop rather than a
    # no-op for the table owner. Alembic, bootstrap-admin, the reconciliation CLI,
    # and the test suite's db_session fixture all keep using database_url unchanged
    # -- see infrastructure/cli/provision_app_role.py for how this role is created.
    app_database_url: str = (
        "postgresql+asyncpg://legal_dms_app:legal_dms_app@localhost:5432/legal_dms_dev"
    )

    log_level: str = "INFO"
    log_dir: str = "logs"
    storage_root: str = "storage"

    # No default, deliberately (Stage 3, ADR/0019/0020's sibling decision D3) -- a JWT signing
    # secret must never have a code-level fallback that a misconfigured deployment could silently
    # run with. Must come from .env/an env var; see backend/.env.example. Nothing in this Stage 3
    # Phase 0 batch signs a real token yet -- this field exists so Settings() has the shape T47's
    # token utility will read from, without that utility existing yet.
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 20
    refresh_token_ttl_days: int = 14

    # NoDecode: env values are comma-separated, not JSON — parsed by the validator below.
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]

    # NoDecode: env value is "name:true,other:false", not JSON.
    feature_flags: Annotated[dict[str, bool], NoDecode] = {}

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("feature_flags", mode="before")
    @classmethod
    def _parse_feature_flags(cls, value: str | dict[str, bool]) -> dict[str, bool]:
        if isinstance(value, str):
            flags: dict[str, bool] = {}
            for pair in value.split(","):
                name, _, raw_value = pair.strip().partition(":")
                if not name:
                    continue
                flags[name] = raw_value.strip().lower() in ("1", "true", "yes", "on")
            return flags
        return value

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def is_testing(self) -> bool:
        return self.environment == "testing"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
