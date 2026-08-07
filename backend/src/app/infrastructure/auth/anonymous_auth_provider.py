"""Stage 1 default AuthenticationProvider: no login mechanism exists yet, so
every request resolves to an anonymous user. A real provider
(`JwtAuthenticationProvider`, Stage 3 Phase 2) satisfies the same port once
login actually exists.
"""

from __future__ import annotations

from app.application.interfaces.auth import AuthenticationProvider, CurrentUser


class AnonymousAuthenticationProvider(AuthenticationProvider):
    async def get_current_user(self, token: str | None) -> CurrentUser:
        # Deliberately ignores `token` -- this provider predates real login
        # (D7/ADR-0019 only changed the port's shape, not this stub's
        # behavior). Accepting-but-ignoring keeps it a valid
        # AuthenticationProvider without pretending to validate anything.
        return CurrentUser()
