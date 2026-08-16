"""`GET /users`, `GET /users/{id}`, `POST /users`, `PUT /users/{id}`, and
`POST /users/{id}/deactivate` (T62); `POST /users/{id}/roles` and `DELETE
/users/{id}/roles/{role_id}` (T63): admin-only user management, gated by a
single router-level `RequirePermission("users:manage", "roles:manage")` --
T63 extends `RequirePermission` (`deps.py`) to accept more than one
permission code, authorizing on *any* one of them, so the two new role-
assignment routes can share the router-level dependency with T62's five
user-management routes rather than needing a second, route-specific one
alongside it. `roles:manage` alone doesn't grant anything on T62's own five
routes beyond what this shared dependency already checks -- there's no
narrower way to say "either permission, on every route in this router"
than one router-level dependency covering all seven.

Hand-written, not `crud_router_factory.py` (T62's own authorized scope keeps
that factory unmodified and unused here) -- but the list/get routes still
mirror its `ApiResponse`/pagination/`_to_read` shape exactly, since nothing
about *this* feature's needs differs from that established convention.

Three local, per-request dependencies (`get_user_repository`/
`get_user_service`/`get_role_repository`) are declared here rather than
added to `presentation/api/deps.py` -- T62/T63's authorized scope leaves
`deps.py` unmodified beyond `RequirePermission` itself, and all three are
only ever needed by this module, the same reasoning `AuthServiceDep` (T58)
doesn't apply here since `SqlAlchemyUserRepository`/`BaseService[User]`/the
generic `SqlAlchemyRepository[Role]` are the only pieces `users.py` needs,
not a use-case-specific application service. `get_user_service()` wraps
`get_user_repository()`'s result in the existing, generic `BaseService[User]`
(T55's "framework layer" -- `get_by_id_or_raise()`/`list_page()`/`update()`
already do exactly what `get_user()`/`list_users()`/`deactivate_user()`
need); `create_user()`/`update_user()`/`assign_role()`/`remove_role()` also
reach for the repository directly, since only `UserRepository`'s own narrow
methods (`get_by_email()`, and T63's `assign_role()`/`remove_role()`) --
not anything `BaseService` exposes -- can answer those questions.
`get_role_repository()` returns the existing *generic* `SqlAlchemyRepository
[Role]` directly (T63: no `RoleRepository` port/class exists or is created
here) -- `get_by_id()` is all role-assignment needs to validate a `role_id`
exists, and inventing a `Role`-specific repository for one lookup this
generic one already provides would duplicate, not extend, existing
machinery.

`UserRead` deliberately omits `password_hash` (and every other field not
listed in T62's approved contract, e.g. no `roles` -- role assignment is
T63's, exposed instead as its own `RoleAssignmentRead`, not folded into
`UserRead`) -- `_to_read()`'s `model_validate(..., from_attributes=True)`
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
from app.application.errors.exceptions import ConflictError, NotFoundError
from app.infrastructure.persistence.models.identity import Role, User
from app.infrastructure.persistence.sqlalchemy_repository import SqlAlchemyRepository
from app.infrastructure.persistence.sqlalchemy_user_repository import SqlAlchemyUserRepository
from app.infrastructure.security.password_hasher import hash_password
from app.presentation.api.deps import CurrentUserDep, DBSessionDep, RequirePermission
from app.presentation.common.response import ApiResponse, paginated_response

router = APIRouter(
    prefix="/users",
    dependencies=[Depends(RequirePermission("users:manage", "roles:manage"))],
)


async def get_user_repository(session: DBSessionDep) -> SqlAlchemyUserRepository:
    """Built fresh per request (mirrors `deps.py`'s own `get_auth_service()`/
    `get_authentication_provider()` reasoning, T55/T58): needs *this*
    request's session, not a cached/shared one."""
    return SqlAlchemyUserRepository(session)


UserRepositoryDep = Annotated[SqlAlchemyUserRepository, Depends(get_user_repository)]


async def get_user_service(repository: UserRepositoryDep) -> BaseService[User]:
    return BaseService(repository, resource_name="User")


UserServiceDep = Annotated[BaseService[User], Depends(get_user_service)]


async def get_role_repository(session: DBSessionDep) -> SqlAlchemyRepository[Role]:
    """The existing *generic* repository (T50's framework layer), not a new
    `Role`-specific class -- `get_by_id()` is all role-assignment needs to
    validate a `role_id` exists."""
    return SqlAlchemyRepository(session, Role)


RoleRepositoryDep = Annotated[SqlAlchemyRepository[Role], Depends(get_role_repository)]


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


class RoleAssignmentCreate(BaseModel):
    role_id: UUID


class RoleAssignmentRead(BaseModel):
    user_id: UUID
    role_id: UUID
    assigned_at: datetime
    assigned_by: UUID | None


@router.post(
    "/{user_id}/roles",
    status_code=status.HTTP_201_CREATED,
    summary="Assign an existing role to a user",
)
async def assign_role(
    user_id: UUID,
    payload: RoleAssignmentCreate,
    current_user: CurrentUserDep,
    service: UserServiceDep,
    repository: UserRepositoryDep,
    role_repository: RoleRepositoryDep,
) -> ApiResponse[RoleAssignmentRead]:
    await service.get_by_id_or_raise(user_id)
    if await role_repository.get_by_id(payload.role_id) is None:
        raise NotFoundError(f"Role with id {payload.role_id} was not found")

    # `current_user.id` is guaranteed non-None here: the router-level
    # RequirePermission dependency already enforced is_authenticated=True
    # before this handler runs (T57's 401-before-403 order).
    created = await repository.assign_role(
        user_id, payload.role_id, assigned_by=UUID(current_user.id)
    )
    if created is None:
        raise ConflictError(f"User {user_id} already has role {payload.role_id}")

    return ApiResponse(data=RoleAssignmentRead.model_validate(created, from_attributes=True))


@router.delete(
    "/{user_id}/roles/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a role from a user",
)
async def remove_role(
    user_id: UUID,
    role_id: UUID,
    service: UserServiceDep,
    repository: UserRepositoryDep,
    role_repository: RoleRepositoryDep,
) -> None:
    await service.get_by_id_or_raise(user_id)
    if await role_repository.get_by_id(role_id) is None:
        raise NotFoundError(f"Role with id {role_id} was not found")

    if not await repository.remove_role(user_id, role_id):
        raise NotFoundError(f"User {user_id} does not have role {role_id}")
