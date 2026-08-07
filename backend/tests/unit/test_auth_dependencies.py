"""T44: verifies the approved authentication dependencies (`argon2-cffi`,
`PyJWT`) are actually installed and importable, per
`docs/Stage3_Backend_Handoff.md` D2/D3.

Deliberately does not hash a password or encode/decode a token -- that's
`T46`/`T47` (Phase 1), explicitly out of scope for Stage 3 Phase 0. This
only proves the dependency addition itself (`backend/pyproject.toml` +
`uv.lock`) is real and usable, closing the gap that nothing previously
tested it beyond "the install command didn't fail."
"""

from __future__ import annotations


class TestArgon2CffiIsInstalled:
    def test_password_hasher_class_is_importable(self) -> None:
        from argon2 import PasswordHasher

        assert PasswordHasher is not None

    def test_verify_mismatch_error_is_importable(self) -> None:
        # The exception T46's verify_password() will need to catch --
        # confirming it exists now avoids a surprise when T46 is written.
        from argon2.exceptions import VerifyMismatchError

        assert VerifyMismatchError is not None


class TestPyJWTIsInstalled:
    def test_encode_and_decode_functions_are_importable(self) -> None:
        import jwt

        assert callable(jwt.encode)
        assert callable(jwt.decode)

    def test_expected_exceptions_are_importable(self) -> None:
        # The exceptions T47's decode utility will need to catch --
        # confirming they exist now avoids a surprise when T47 is written.
        from jwt import ExpiredSignatureError, InvalidSignatureError

        assert ExpiredSignatureError is not None
        assert InvalidSignatureError is not None
