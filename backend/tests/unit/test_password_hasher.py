"""Tests for T46's password hashing utility (D2/ADR-0018: Argon2id via
argon2-cffi).
"""

from __future__ import annotations

from app.infrastructure.security.password_hasher import hash_password, verify_password


class TestHashPassword:
    def test_hash_is_never_plaintext_equal_to_input(self) -> None:
        hashed = hash_password("correct horse battery staple")

        assert hashed != "correct horse battery staple"

    def test_hash_uses_argon2id(self) -> None:
        hashed = hash_password("correct horse battery staple")

        assert hashed.startswith("$argon2id$")

    def test_hashing_the_same_password_twice_yields_different_hashes(self) -> None:
        first = hash_password("correct horse battery staple")
        second = hash_password("correct horse battery staple")

        assert first != second


class TestVerifyPassword:
    def test_correct_password_verifies(self) -> None:
        hashed = hash_password("correct horse battery staple")

        assert verify_password("correct horse battery staple", hashed) is True

    def test_wrong_password_fails(self) -> None:
        hashed = hash_password("correct horse battery staple")

        assert verify_password("wrong password", hashed) is False

    def test_malformed_hash_fails_rather_than_raising(self) -> None:
        assert verify_password("correct horse battery staple", "not-a-real-hash") is False
