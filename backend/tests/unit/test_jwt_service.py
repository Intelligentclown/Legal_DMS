"""Tests for T47's JWT encode/decode utility (D3/ADR-0018: PyJWT)."""

from __future__ import annotations

import jwt as pyjwt
import pytest

from app.infrastructure.config.settings import Settings
from app.infrastructure.security.jwt_service import (
    create_access_token,
    create_refresh_token,
    decode_token,
)


@pytest.fixture
def settings() -> Settings:
    return Settings(_env_file=None, jwt_secret_key="test-secret")


class TestCreateAccessToken:
    def test_round_trips_sub_and_roles(self, settings: Settings) -> None:
        token = create_access_token("user-123", ["matters:read", "clients:read"], settings)

        claims = decode_token(token, settings)

        assert claims is not None
        assert claims["sub"] == "user-123"
        assert claims["roles"] == ["matters:read", "clients:read"]

    def test_has_a_jti_claim_unique_per_token(self, settings: Settings) -> None:
        first = decode_token(create_access_token("user-123", [], settings), settings)
        second = decode_token(create_access_token("user-123", [], settings), settings)

        assert first is not None
        assert second is not None
        assert first["jti"]
        assert first["jti"] != second["jti"]


class TestCreateRefreshToken:
    def test_round_trips_sub(self, settings: Settings) -> None:
        token = create_refresh_token("user-123", settings)

        claims = decode_token(token, settings)

        assert claims is not None
        assert claims["sub"] == "user-123"
        assert claims["jti"]


class TestDecodeToken:
    def test_expired_access_token_is_rejected(self, settings: Settings) -> None:
        expired_settings = Settings(
            _env_file=None, jwt_secret_key="test-secret", access_token_ttl_minutes=-1
        )
        token = create_access_token("user-123", [], expired_settings)

        assert decode_token(token, settings) is None

    def test_expired_refresh_token_is_rejected(self, settings: Settings) -> None:
        expired_settings = Settings(
            _env_file=None, jwt_secret_key="test-secret", refresh_token_ttl_days=-1
        )
        token = create_refresh_token("user-123", expired_settings)

        assert decode_token(token, settings) is None

    def test_tampered_signature_is_rejected(self, settings: Settings) -> None:
        token = create_access_token("user-123", [], settings)
        header, payload, signature = token.split(".")
        flipped_first_char = "A" if signature[0] != "A" else "B"
        tampered = f"{header}.{payload}.{flipped_first_char}{signature[1:]}"

        assert decode_token(tampered, settings) is None

    def test_token_signed_with_a_different_secret_is_rejected(self, settings: Settings) -> None:
        other_settings = Settings(_env_file=None, jwt_secret_key="a-different-secret")
        token = create_access_token("user-123", [], other_settings)

        assert decode_token(token, settings) is None

    def test_malformed_token_is_rejected(self, settings: Settings) -> None:
        assert decode_token("not-a-real-token", settings) is None

    def test_does_not_leak_the_underlying_pyjwt_exception(self, settings: Settings) -> None:
        # decode_token()'s whole contract is "None on any failure" -- confirm no PyJWTError
        # subclass escapes for the malformed-input case specifically.
        try:
            result = decode_token("not-a-real-token", settings)
        except pyjwt.PyJWTError:
            pytest.fail("decode_token() must not raise PyJWTError -- it should return None")
        else:
            assert result is None
