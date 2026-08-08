"""Real `AuthorizationService` (T53): checks `require_permission()` against
the caller's roles -> `role_permissions`, via a pre-loaded role-name ->
permission-codes snapshot (`RolePermissionRepository`, T53's own narrow
port). `require_permission()` stays synchronous -- the port's existing,
approved signature -- so the snapshot is loaded once, ahead of time
(async), not queried per call; constructing that snapshot per request is
`T55`'s wiring job, same deferred-construction pattern already established
for `AuthService`/`JwtAuthenticationProvider`.

Reuses `PermissiveAuthorizationService`'s "an anonymous caller is denied
every permission check" rule verbatim, then -- unlike that stub -- actually
checks an authenticated caller's roles against real granted permissions
instead of permitting everyone once authenticated.
"""

from __future__ import annotations

from collections.abc import Mapping

from app.application.errors.exceptions import ForbiddenError
from app.application.interfaces.auth import AuthorizationService, CurrentUser


class RbacAuthorizationService(AuthorizationService):
    def __init__(self, permission_codes_by_role_name: Mapping[str, frozenset[str]]) -> None:
        self._permission_codes_by_role_name = permission_codes_by_role_name

    def require_permission(self, user: CurrentUser, permission: str) -> None:
        if not user.is_authenticated:
            raise ForbiddenError(f"Authentication is required for '{permission}'")

        for role in user.roles:
            if permission in self._permission_codes_by_role_name.get(role, frozenset()):
                return

        raise ForbiddenError(f"'{user.display_name}' lacks permission '{permission}'")
