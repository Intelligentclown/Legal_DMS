"""Tests for the validation framework."""

import pytest

from app.application.common.validation import validate_all
from app.application.errors.exceptions import ValidationError


class _MinLength:
    def __init__(self, minimum: int) -> None:
        self._minimum = minimum

    def validate(self, value: str) -> list[str]:
        if len(value) < self._minimum:
            return [f"must be at least {self._minimum} characters"]
        return []


class _NoWhitespace:
    def validate(self, value: str) -> list[str]:
        if " " in value:
            return ["must not contain whitespace"]
        return []


class TestValidateAll:
    def test_passes_silently_when_all_validators_pass(self) -> None:
        validate_all("hello", [_MinLength(3), _NoWhitespace()])

    def test_raises_validation_error_with_single_failure(self) -> None:
        with pytest.raises(ValidationError, match="at least 10 characters"):
            validate_all("short", [_MinLength(10)])

    def test_raises_validation_error_accumulating_multiple_failures(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            validate_all("a b", [_MinLength(10), _NoWhitespace()])

        message = exc_info.value.message
        assert "at least 10 characters" in message
        assert "must not contain whitespace" in message
