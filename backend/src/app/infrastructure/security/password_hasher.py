"""Password hashing (D2/ADR-0018): Argon2id via `argon2-cffi`. Plain
functions, not a port -- no caller needs to swap the algorithm behind an
interface, and `argon2-cffi` is already fully encapsulated here (only this
module imports `argon2`).
"""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHash, VerificationError, VerifyMismatchError

_hasher = PasswordHasher()


def hash_password(plain: str) -> str:
    return _hasher.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        _hasher.verify(hashed, plain)
    except (VerifyMismatchError, VerificationError, InvalidHash):
        return False
    return True
