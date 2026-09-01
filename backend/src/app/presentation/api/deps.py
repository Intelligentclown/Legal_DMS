"""Shared FastAPI dependency declarations, reused across routers.

`SettingsDep` resolves through the DI container (see
`infrastructure/di/container.py`) rather than calling the concrete
implementation directly, so it's swappable in tests via
`container.override(...)` without touching any caller. `DBSessionDep`
intentionally stays on FastAPI's native generator `Depends()` pattern — a
request-scoped resource with teardown is exactly what that's for, and the
container doesn't try to replace it.

`CurrentUserDep`'s two upstream services (`AuthenticationProvider`/
`AuthorizationService`) follow the *same* request-scoped pattern as
`DBSessionDep`, not the container (T55) — `JwtAuthenticationProvider`/
`RbacAuthorizationService` both need a session-backed repository, and the
container has no mechanism to hand a factory the current request's session
(`resolve()` is synchronous, takes no arguments, and is usable outside a
request at all, e.g. from background jobs — it was never meant to be
request-aware). `get_authentication_provider()`/`get_authorization_service()`
below construct their service fresh per request instead, directly from
`DBSessionDep`, mirroring `DBSessionDep`'s own reasoning rather than
resolving through the container. See `ADR-0006` and
`docs/ImplementationLog/Stage3/Phase2.md`'s `T55` batch for the full
reasoning.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.auth_service import AuthService
from app.application.errors.exceptions import ForbiddenError, UnauthorizedError
from app.application.interfaces.audit import AuditLogger
from app.application.interfaces.auth import (
    AuthenticationProvider,
    AuthorizationService,
    CurrentUser,
)
from app.infrastructure.auth.jwt_authentication_provider import JwtAuthenticationProvider
from app.infrastructure.auth.rbac_authorization_service import RbacAuthorizationService
from app.infrastructure.config import Settings
from app.infrastructure.database.session import get_admin_db, get_db
from app.infrastructure.di.container import container
from app.infrastructure.persistence.sqlalchemy_refresh_token_repository import (
    SqlAlchemyRefreshTokenRepository,
)
from app.infrastructure.persistence.sqlalchemy_role_permission_repository import (
    SqlAlchemyRolePermissionRepository,
)
from app.infrastructure.persistence.sqlalchemy_user_repository import SqlAlchemyUserRepository


def get_settings_dependency() -> Settings:
    return container.resolve(Settings)


def get_audit_logger_dependency() -> AuditLogger:
    return container.resolve(AuditLogger)


SettingsDep = Annotated[Settings, Depends(get_settings_dependency)]
AuditLoggerDep = Annotated[AuditLogger, Depends(get_audit_logger_dependency)]
DBSessionDep = Annotated[AsyncSession, Depends(get_db)]
# T105: the admin/owning-role session -- see get_admin_db()'s own docstring
# for why AuthService specifically needs this instead of DBSessionDep.
AdminDBSessionDep = Annotated[AsyncSession, Depends(get_admin_db)]


async def get_authentication_provider(
    session: DBSessionDep, settings: SettingsDep
) -> AuthenticationProvider:
    """Built fresh per request (T55) — `SqlAlchemyUserRepository` needs
    *this* request's session, not a cached/shared one."""
    return JwtAuthenticationProvider(SqlAlchemyUserRepository(session), settings)


async def get_authorization_service(session: DBSessionDep) -> AuthorizationService:
    """Built fresh per request (T55): loads the role -> granted-permissions
    mapping from the database on every call, deliberately uncached — no
    existing, already-approved caching/invalidation policy covers this data,
    and `role_permissions`'s low write volume doesn't justify inventing one
    now (see `docs/ImplementationLog/Stage3/Phase2.md`'s `T55` batch)."""
    role_permission_repository = SqlAlchemyRolePermissionRepository(session)
    permission_codes_by_role_name = (
        await role_permission_repository.get_permission_codes_by_role_name()
    )
    return RbacAuthorizationService(permission_codes_by_role_name)


async def get_auth_service(
    session: AdminDBSessionDep, settings: SettingsDep, audit_logger: AuditLoggerDep
) -> AuthService:
    """Built fresh per request (T58, mirrors `get_authentication_provider()`/
    `get_authorization_service()`, T55) — `AuthService`'s two repositories
    both need *this* request's session, not a cached/shared one.
    `audit_logger` (T65) is the one dependency here that isn't session-bound
    -- resolved straight from the container via `AuditLoggerDep`, the same
    singleton `RequirePermission` below also reaches for.

    T105: `AdminDBSessionDep`, not `DBSessionDep` -- see `get_admin_db()`'s
    docstring. Login/refresh/logout look up a `User`/`RefreshToken` before
    any tenant context can exist, which the RLS-restricted `legal_dms_app`
    role (used by `DBSessionDep`/`get_db()`) would otherwise deny outright.
    `AuthService`'s own code is unchanged -- only which session constructs
    its repositories."""
    return AuthService(
        SqlAlchemyUserRepository(session),
        SqlAlchemyRefreshTokenRepository(session),
        settings,
        audit_logger,
    )


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


_bearer_scheme = HTTPBearer(auto_error=False)


async def get_bearer_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
) -> str | None:
    """`auto_error=False` so a missing/malformed `Authorization` header
    resolves to `None` instead of HTTPBearer raising 401 itself -- whether
    an anonymous caller is acceptable is `AuthorizationService`'s decision
    (T53/T54), not this dependency's."""
    return credentials.credentials if credentials is not None else None


async def get_current_user(
    auth_provider: Annotated[AuthenticationProvider, Depends(get_authentication_provider)],
    token: Annotated[str | None, Depends(get_bearer_token)],
) -> CurrentUser:
    return await auth_provider.get_current_user(token=token)


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]


def RequirePermission(*permissions: str) -> Callable[..., Awaitable[None]]:
    """Dependency factory (T54, closes Stage 2.5's F11; extended T63 to
    accept more than one permission code): use as
    `Depends(RequirePermission("matters:read"))` or, for an "any of these"
    check, `Depends(RequirePermission("users:manage", "roles:manage"))`,
    either as a route parameter or in a router's `dependencies=[...]` list.
    Raises `UnauthorizedError` (401) if the resolved `CurrentUser` isn't
    authenticated at all (T57 -- closes the 401/403 gap: no token,
    expired/malformed/tampered token all resolve to the same
    `is_authenticated=False`, and previously fell through to
    `AuthorizationService`'s anonymous-caller branch, which raises
    `ForbiddenError`/403 indistinguishably from an authenticated-but-
    unpermitted caller), checked once regardless of how many permission
    codes are supplied.

    Otherwise delegates to `AuthorizationService.require_permission()`
    (unmodified -- it still only ever checks one permission at a time) for
    each supplied code in turn, returning on the first one that doesn't
    raise. Every code except the last is tried inside a `try`/`except
    ForbiddenError` so a denial just moves on to the next candidate; the
    *last* code is called unguarded, so its own `ForbiddenError` propagates
    naturally if every permission was denied. For the single-permission
    case (every call site before T63), the loop body never runs and the one
    supplied code is checked exactly as before -- byte-for-byte the same
    call, same exception, same message, on the sole `AuthorizationService`
    call this factory ever risked skipping.

    T65: only the *final* denial -- the one that actually results in a 403
    reaching the caller -- is audited as `permission_denied`. A denial on an
    earlier candidate permission that a later one then grants is not an
    audit-worthy event; the caller was authorized. `AuditLogger` is resolved
    directly from the container (`container.resolve(AuditLogger)`), not
    added as a new parameter here -- this keeps `_require_permission`'s own
    signature (`user`, `authorization_service`) unchanged, since it's called
    directly with exactly those two positional arguments by this project's
    existing `TestRequirePermission` unit suite, bypassing FastAPI's own
    `Depends()` wiring entirely. `resource_id` is left `None`: no request/
    route object is available at this same signature without the identical
    problem. The 401 path above never reaches here, so it's never audited,
    per T65's own explicit exclusion."""

    async def _require_permission(
        user: CurrentUserDep,
        authorization_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    ) -> None:
        if not user.is_authenticated:
            raise UnauthorizedError("Authentication is required")

        for permission in permissions[:-1]:
            try:
                authorization_service.require_permission(user, permission)
                return
            except ForbiddenError:
                continue
        try:
            authorization_service.require_permission(user, permissions[-1])
        except ForbiddenError:
            await container.resolve(AuditLogger).record(
                actor=user,
                action="permission_denied",
                resource_type="endpoint",
                metadata={"required_permissions": list(permissions)},
            )
            raise

    return _require_permission
