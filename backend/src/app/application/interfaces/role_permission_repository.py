"""Role-permission lookup port (T53): the one query `RbacAuthorizationService`
needs. `AuthorizationService.require_permission()` is synchronous (an
existing, approved port signature -- not changed here), so it cannot run an
async DB query per call; instead, a role-name -> granted-permission-codes
snapshot is loaded once (async, ahead of time) and handed to
`RbacAuthorizationService` to check synchronously against.

Not an `AbstractRepository[RolePermission]`: nothing needs CRUD on
individual `role_permissions` join rows (nothing in this stage writes to
that table yet -- seeding it is `T66`), only this one aggregate read.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping


class RolePermissionRepository(ABC):
    @abstractmethod
    async def get_permission_codes_by_role_name(self) -> Mapping[str, frozenset[str]]:
        """Every role name (`Role.name`) mapped to the set of permission
        codes (`Permission.code`) granted to it via `role_permissions`. A
        role with no granted permissions is simply absent from the mapping,
        not mapped to an empty set."""
        ...
