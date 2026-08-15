"""`POST /auth/login` (T58): email + password in, access + refresh tokens
out, or a structured 401.

`AuthService.authenticate()` returns a `Result`, not a raised exception, so
the failure branch here raises `result.error` (already an `AppError`
instance) directly -- the existing global `AppError` exception handler
turns it into the standard `{"error": {...}}` 401 response, no route-level
try/except needed.

Request/response schemas are co-located here, not in a separate schema
module -- no such convention exists elsewhere in this codebase to follow
instead. `LoginResponse` is returned bare, not wrapped in `ApiResponse[T]`
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
