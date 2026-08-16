"""`GET /users`, `GET /users/{id}`, `POST /users`, `PUT /users/{id}`, and
`POST /users/{id}/deactivate` (T62): admin-only user management, gated by a
single router-level `RequirePermission("users:manage")` (T54) rather than
repeating it on every route -- all five routes require the exact same
permission, so there is nothing route-specific for a per-route dependency to
express.

Hand-written, not `crud_router_factory.py` (T62's own authorized scope keeps
that factory unmodified and unused here) -- but the list/get routes still
mirror its `ApiResponse`/pagination/`_to_read` shape exactly, since nothing
about *this* feature's needs differs from that established convention.

Two local, per-request dependencies (`get_user_repository`/`get_user_service`)
are declared here rather than added to `presentation/api/deps.py` -- T62's
authorized scope leaves `deps.py` unmodified, and both dependencies are only
ever needed by this module, the same reasoning `AuthServiceDep` (T58) doesn't
apply here since `SqlAlchemyUserRepository`/`BaseService[User]` are the only
two pieces `users.py` needs, not a use-case-specific application service.
`get_user_service()` wraps `get_user_repository()`'s result in the existing,
generic `BaseService[User]` (T55's "framework layer" -- `get_by_id_or_raise()`/
`list_page()`/`update()` already do exactly what `get_user()`/`list_users()`/
`deactivate_user()` need); `create_user()`/`update_user()` also reach for the
repository directly, since only `UserRepository.get_by_email()` -- not
anything `BaseService` exposes -- can answer "does this email already belong
to someone else."

`UserRead` deliberately omits `password_hash` (and every other field not
listed in T62's approved contract, e.g. no `roles` -- role assignment is
T63's, out of scope here) -- `_to_read()`'s `model_validate(..., from_attributes=True)`
only ever populates the fields `UserRead` itself declares, so there is no
value in trying to explicitly filter `password_hash` out of a response that
was never going to contain it.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from app.application.common.base_service import BaseService
from app.application.common.pagination import DEFAULT_PAGE_SIZE, PageRequest
from app.application.errors.exceptions import ConflictError
from app.infrastructure.persistence.models.identity import User
from app.infrastructure.persistence.sqlalchemy_user_repository import SqlAlchemyUserRepository
from app.infrastructure.security.password_hasher import hash_password
from app.presentation.api.deps import DBSessionDep, RequirePermission
from app.presentation.common.response import ApiResponse, paginated_response

router = APIRouter(prefix="/users", dependencies=[Depends(RequirePermission("users:manage"))])


async def get_user_repository(session: DBSessionDep) -> SqlAlchemyUserRepository:
    """Built fresh per request (mirrors `deps.py`'s own `get_auth_service()`/
    `get_authentication_provider()` reasoning, T55/T58): needs *this*
    request's session, not a cached/shared one."""
    return SqlAlchemyUserRepository(session)


UserRepositoryDep = Annotated[SqlAlchemyUserRepository, Depends(get_user_repository)]


async def get_user_service(repository: UserRepositoryDep) -> BaseService[User]:
    return BaseService(repository, resource_name="User")


UserServiceDep = Annotated[BaseService[User], Depends(get_user_service)]


class UserRead(BaseModel):
    id: UUID
    email: str
    full_name: str
    phone: str | None
    is_active: bool
    last_login_at: datetime | None


def _to_read(user: User) -> UserRead:
    return UserRead.model_validate(user, from_attributes=True)


@router.get("", summary="List users")
async def list_users(
    service: UserServiceDep, page: int = 1, page_size: int = DEFAULT_PAGE_SIZE
) -> ApiResponse[list[UserRead]]:
    page_result = await service.list_page(PageRequest(page=page, page_size=page_size))
    entity_response = paginated_response(page_result)
    return ApiResponse(
        data=[_to_read(user) for user in entity_response.data], meta=entity_response.meta
    )


@router.get("/{user_id}", summary="Get a user by id")
async def get_user(user_id: UUID, service: UserServiceDep) -> ApiResponse[UserRead]:
    user = await service.get_by_id_or_raise(user_id)
    return ApiResponse(data=_to_read(user))


class UserCreate(BaseModel):
    email: str
    full_name: str
    phone: str | None = None
    password: str


@router.post(
    "", status_code=status.HTTP_201_CREATED, summary="Create a user with a hashed password"
)
async def create_user(payload: UserCreate, repository: UserRepositoryDep) -> ApiResponse[UserRead]:
    if await repository.get_by_email(payload.email) is not None:
        raise ConflictError(f"A user with email {payload.email} already exists")

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        phone=payload.phone,
        password_hash=hash_password(payload.password),
    )
    created = await repository.add(user)
    return ApiResponse(data=_to_read(created))


class UserUpdate(BaseModel):
    email: str
    full_name: str
    phone: str | None


@router.put("/{user_id}", summary="Replace a user's email/full_name/phone")
async def update_user(
    user_id: UUID, payload: UserUpdate, service: UserServiceDep, repository: UserRepositoryDep
) -> ApiResponse[UserRead]:
    user = await service.get_by_id_or_raise(user_id)

    existing = await repository.get_by_email(payload.email)
    if existing is not None and existing.id != user.id:
        raise ConflictError(f"A user with email {payload.email} already exists")

    user.email = payload.email
    user.full_name = payload.full_name
    user.phone = payload.phone
    updated = await service.update(user)
    return ApiResponse(data=_to_read(updated))


@router.post("/{user_id}/deactivate", summary="Deactivate a user")
async def deactivate_user(user_id: UUID, service: UserServiceDep) -> ApiResponse[UserRead]:
    user = await service.get_by_id_or_raise(user_id)
    user.is_active = False
    updated = await service.update(user)
    return ApiResponse(data=_to_read(updated))
