"""`POST /auth/login` (T58) and `POST /auth/refresh` (T59): email + password,
or a refresh token, in; access + refresh tokens out; or a structured 401.

`AuthService.authenticate()`/`.refresh()` both return a `Result`, not a
raised exception, so the failure branch in each route raises `result.error`
(already an `AppError` instance) directly -- the existing global `AppError`
exception handler turns it into the standard `{"error": {...}}` 401
response, no route-level try/except needed. `.refresh()`'s single generic
message covers an invalid, expired, revoked, or unknown token identically
-- same no-enumeration reasoning as login's identical wrong-password/
unknown-email message -- so `/refresh` doesn't need to (and can't)
distinguish those cases in its response either.

Request/response schemas are co-located here, not in a separate schema
module -- no such convention exists elsewhere in this codebase to follow
instead. Both responses are returned bare, not wrapped in `ApiResponse[T]`
(`presentation/common/response.py`) -- that envelope is for
resource-returning endpoints; a token pair isn't a fetchable resource.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.presentation.api.deps import AuthServiceDep

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
