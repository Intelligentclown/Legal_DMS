"""Identity & access schema: Users, Roles, Permissions, and their
many-to-many join tables.

Pure persistence models — no authentication is wired to these. Stage 1's
`AnonymousAuthenticationProvider` is unchanged; a real
`AuthenticationProvider`/`AuthorizationService` implementation reading from
these tables is future work. `permissions.code` matches the string
convention `AuthorizationService.require_permission()` already expects
(e.g. `"matters:read"`), so that future implementation can read this table
directly without changing the port.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base
from app.infrastructure.persistence.models.mixins import AuditMixin


class User(Base, AuditMixin):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(20))
    # Nullable: no login mechanism exists yet (Stage 1's AnonymousAuthenticationProvider
    # is the only auth in effect). Schema is ready for a future real auth stage.
    password_hash: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Role(Base, AuditMixin):
    __tablename__ = "roles"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str | None] = mapped_column(String(500))
    is_system_role: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")


class Permission(Base, AuditMixin):
    __tablename__ = "permissions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str | None] = mapped_column(String(500))
    category: Mapped[str] = mapped_column(String(100))


class UserRole(Base):
    __tablename__ = "user_roles"
    __table_args__ = (UniqueConstraint("user_id", "role_id"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    role_id: Mapped[UUID] = mapped_column(ForeignKey("roles.id"), index=True)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    assigned_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))


class RolePermission(Base):
    __tablename__ = "role_permissions"
    __table_args__ = (UniqueConstraint("role_id", "permission_id"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    role_id: Mapped[UUID] = mapped_column(ForeignKey("roles.id"), index=True)
    permission_id: Mapped[UUID] = mapped_column(ForeignKey("permissions.id"), index=True)


class RefreshToken(Base):
    """D1/ADR-0018: the DB-backed, revocable half of Stage 3's token design.
    Never stores the raw token, only a hash of it (same principle as
    `User.password_hash`) -- `T50`'s `AuthService` is what will actually
    write/read/revoke these rows. No `AuditMixin`: this is a system-issued,
    high-volume security record, not a human-edited business entity (same
    reasoning already applied to `UserRole`/`RolePermission` above);
    `revoked_at` already covers this table's one lifecycle transition, so
    `AuditMixin`'s `deleted_at`/`created_by`/`updated_by` would be dead
    columns, not a soft-delete/attribution trail anything here needs.
    """

    __tablename__ = "refresh_tokens"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
