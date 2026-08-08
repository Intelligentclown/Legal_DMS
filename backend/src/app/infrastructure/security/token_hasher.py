"""Refresh-token hashing (T50/D1/ADR-0018): SHA-256, deliberately not
Argon2. `refresh_tokens.token_hash` is looked up by exact match
(`WHERE token_hash = ?`), which requires a deterministic hash -- Argon2's
per-call random salt makes that structurally impossible (the same input
never hashes to the same output twice). A refresh token is also already
high-entropy (a signed JWT with a random `jti`), unlike a human-chosen
password, so Argon2's slow, memory-hard design buys nothing here beyond
unnecessary CPU cost. `password_hasher.py`'s Argon2 choice and this
module's SHA-256 choice are both correct for what each is hashing --
neither is a weaker version of the other.
"""

from __future__ import annotations

import hashlib


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
