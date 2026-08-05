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
    app_version: str = "0.1.0"

    database_url: str = "postgresql+asyncpg://legal_dms:legal_dms@localhost:5432/legal_dms_dev"

    log_level: str = "INFO"
    log_dir: str = "logs"
    storage_root: str = "storage"

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
