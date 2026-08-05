"""Stage 1 default AuthorizationService: no real permission data model
exists yet, so every permission check passes *for an authenticated user*.
The one rule that's actually meaningful before real permission rules
exist: an anonymous caller (nobody can log in yet — see
AnonymousAuthenticationProvider) is denied every permission check. Real,
granular permission rules arrive once a User/Role model exists.
"""

from __future__ import annotations

from app.application.errors.exceptions import ForbiddenError
from app.application.interfaces.auth import AuthorizationService, CurrentUser


class PermissiveAuthorizationService(AuthorizationService):
    def require_permission(self, user: CurrentUser, permission: str) -> None:
        if not user.is_authenticated:
            raise ForbiddenError(f"Authentication is required for '{permission}'")
