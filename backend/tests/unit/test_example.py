"""Example unit tests demonstrating the testing pattern for pure
application/domain logic — no FastAPI app, no database, no I/O.
"""

import pytest

from app.application.errors import AppError, NotFoundError, ValidationError
from app.infrastructure.config.settings import Settings


class TestAppErrorHierarchy:
    def test_not_found_error_carries_its_status_and_code(self) -> None:
        error = NotFoundError("matter not found")

        assert isinstance(error, AppError)
        assert error.status_code == 404
        assert error.error_code == "not_found"
        assert error.message == "matter not found"

    def test_error_code_can_be_overridden(self) -> None:
        error = ValidationError("bad input", error_code="custom_code")

        assert error.error_code == "custom_code"
        assert error.status_code == 422


class TestSettingsCorsOriginsParsing:
    """Regression test: cors_origins is a list[str] field sourced from a
    comma-separated env value. Without NoDecode, pydantic-settings tries to
    JSON-decode the raw string before validation runs and crashes on
    startup — this caught that bug against a real .env file.
    """

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("http://localhost:5173", ["http://localhost:5173"]),
            (
                "http://localhost:5173,http://localhost:5174",
                ["http://localhost:5173", "http://localhost:5174"],
            ),
            (
                "http://localhost:5173, http://localhost:5174 ,",
                ["http://localhost:5173", "http://localhost:5174"],
            ),
        ],
    )
    def test_parses_comma_separated_origins(self, raw: str, expected: list[str]) -> None:
        settings = Settings(_env_file=None, jwt_secret_key="test-secret", cors_origins=raw)

        assert settings.cors_origins == expected

    def test_accepts_a_list_directly(self) -> None:
        settings = Settings(
            _env_file=None, jwt_secret_key="test-secret", cors_origins=["http://localhost:5173"]
        )

        assert settings.cors_origins == ["http://localhost:5173"]
