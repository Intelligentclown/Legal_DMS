"""Tests for T50's refresh-token hashing utility (D1/ADR-0018: SHA-256,
deliberately not Argon2 -- see token_hasher.py's docstring for why).
"""

from __future__ import annotations

from app.infrastructure.security.token_hasher import hash_token


class TestHashToken:
    def test_hash_is_never_equal_to_input(self) -> None:
        assert hash_token("some.jwt.token") != "some.jwt.token"

    def test_is_deterministic(self) -> None:
        assert hash_token("some.jwt.token") == hash_token("some.jwt.token")

    def test_different_inputs_hash_differently(self) -> None:
        assert hash_token("token-a") != hash_token("token-b")

    def test_produces_a_hex_sha256_digest(self) -> None:
        hashed = hash_token("some.jwt.token")

        assert len(hashed) == 64
        assert all(char in "0123456789abcdef" for char in hashed)
