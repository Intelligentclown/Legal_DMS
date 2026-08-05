"""Stage 1 default AuthenticationProvider: no login mechanism exists yet, so
every request resolves to an anonymous user. A real provider (session, JWT,
...) satisfies the same port once a future auth stage implements login.
"""

from __future__ import annotations

from app.application.interfaces.auth import AuthenticationProvider, CurrentUser


class AnonymousAuthenticationProvider(AuthenticationProvider):
    async def get_current_user(self) -> CurrentUser:
        return CurrentUser()
