"""`POST /auth/login` (T58), `POST /auth/refresh` (T59), `POST /auth/logout`
(T60), and `GET /auth/me` (T61): email + password, or a refresh token, in;
access + refresh tokens out, or a structured 401 -- except logout, which
has nothing to fail on.

`AuthService.authenticate()`/`.refresh()` both return a `Result`, not a
raised exception, so the failure branch in each route raises `result.error`
(already an `AppError` instance) directly -- the existing global `AppError`
exception handler turns it into the standard `{"error": {...}}` 401
response, no route-level try/except needed. `.refresh()`'s single generic
message covers an invalid, expired, revoked, or unknown token identically
-- same no-enumeration reasoning as login's identical wrong-password/
unknown-email message -- so `/refresh` doesn't need to (and can't)
distinguish those cases in its response either.

`AuthService.revoke()` (logout) is different in kind, not just outcome: it
returns `None`, never a `Result` -- an unknown or already-revoked token is
silently a no-op, not a failure, so there is no error branch to raise here.
`/logout` returns `204 No Content` with no body, mirroring
`presentation/common/crud_router_factory.py`'s `delete_item` -- the only
existing precedent in this codebase for "the action succeeded, there's
nothing to return."

Request/response schemas are co-located here, not in a separate schema
module -- no such convention exists elsewhere in this codebase to follow
instead. Both token responses are returned bare, not wrapped in
`ApiResponse[T]` (`presentation/common/response.py`) -- that envelope is
for resource-returning endpoints; a token pair isn't a fetchable resource.

`GET /auth/me` (T61) is the first route in this module that *does* fetch a
resource -- the caller's own profile -- so its response is wrapped in
`ApiResponse[MeResponse]`, matching `crud_router_factory.py`'s `GET
/{item_id}` -> `ApiResponse[ReadSchema]` precedent instead of `login`/
`refresh`/`logout`'s bare convention. It reuses `CurrentUserDep` (T52-T57)
rather than `AuthServiceDep` -- resolving "who is the caller" from the
bearer token is exactly what that dependency already does. `CurrentUserDep`
never raises (an anonymous caller just resolves to `is_authenticated=False`
per T52), so the route itself raises `UnauthorizedError` when unauthenticated
-- the same check `RequirePermission` (T54) already makes -- rather than
requiring a specific permission code: any authenticated user may view their
own profile.
"""

from __future__ import annotations

from fastapi import APIRouter, status
from pydantic import BaseModel

from app.application.errors.exceptions import UnauthorizedError
from app.presentation.api.deps import AuthServiceDep, CurrentUserDep
from app.presentation.common.response import ApiResponse

router = APIRouter(prefix="/auth")


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


@router.post("/login", summary="Log in with email and password")
async def login(payload: LoginRequest, auth_service: AuthServiceDep) -> LoginResponse:
    result = await auth_service.authenticate(payload.email, payload.password)
    if result.is_failure:
        raise result.error

    access_token, refresh_token = await auth_service.issue_tokens(result.value)
    return LoginResponse(access_token=access_token, refresh_token=refresh_token)


class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


@router.post("/refresh", summary="Exchange a refresh token for a new token pair")
async def refresh(payload: RefreshRequest, auth_service: AuthServiceDep) -> RefreshResponse:
    result = await auth_service.refresh(payload.refresh_token)
    if result.is_failure:
        raise result.error

    access_token, refresh_token = result.value
    return RefreshResponse(access_token=access_token, refresh_token=refresh_token)


class LogoutRequest(BaseModel):
    refresh_token: str


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Revoke a refresh token")
async def logout(payload: LogoutRequest, auth_service: AuthServiceDep) -> None:
    await auth_service.revoke(payload.refresh_token)


class MeResponse(BaseModel):
    id: str
    display_name: str
    roles: list[str]


@router.get("/me", summary="Get the current authenticated user's profile")
async def me(user: CurrentUserDep) -> ApiResponse[MeResponse]:
    if not user.is_authenticated:
        raise UnauthorizedError("Authentication is required")

    return ApiResponse(
        data=MeResponse(id=user.id, display_name=user.display_name, roles=sorted(user.roles))
    )
