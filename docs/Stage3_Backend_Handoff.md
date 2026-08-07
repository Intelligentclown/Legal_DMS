# Stage 3 — Backend Implementation Handoff

**Audience:** whoever implements Stage 3's backend work (Phases 0–4, tasks T41–T68 in
[`IMPLEMENTATION_QUEUE.md`](../IMPLEMENTATION_QUEUE.md)). Written to be read on its own — the
source-of-truth task list, decisions, and acceptance criteria all live in
`IMPLEMENTATION_QUEUE.md`'s "Stage 3" section; this document exists to save you re-deriving the
codebase context that section assumes.

**Status:** Architecture approved. Phase 0 (T41–T45) is done, QA Decision Approved — see
`IMPLEMENTATION_QUEUE.md`'s Stage 3 status header and
`docs/ImplementationLog/Stage3/Phase0.md` for the current, authoritative account. **Correction:**
this line originally read "Architecture approved (`ADR-0018`/`0019`/`0020`, once written per
T45/T43)," written before a later direct instruction redefined T44/T45 to cover different work.
`ADR-0019` (D7) and `ADR-0020` (session commit/rollback) were written as part of that redefined
work; **`ADR-0018` (D1–D6) was not written under either T45 or any other task ID at the time —
it was subsequently written 2026-08-07**, outside this handoff's own scope, closing that specific
gap. The `docs/templates/PreStageChecklist.md` sign-off (the other original T44/T45 item) is also
now complete and approved (`docs/reviews/PreStageChecklist_Stage3_2026-08-07.md`) — nothing from
the original T44/T45 content remains open. See
[docs/reviews/Documentation_Migration_Note_T44_T45_2026-08-06.md](reviews/Documentation_Migration_Note_T44_T45_2026-08-06.md)
for the full disambiguation. **This handoff's Phase 0 section is historical context; its Phase
1–4 file-by-file map is what remains live. Phase 1 is under way — `T46` and `T47` are done
(`docs/ImplementationLog/Stage3/Phase1.md`); `T48` onward has not been authorized.** Do not write
any code for `T48` or later below until you have an explicit go-ahead separate from this document
existing.

**Scope of this handoff:** backend only — Phase 0 through Phase 4 (`T41`–`T68`). It does **not**
cover Phase 5 (frontend, `T69`–`T76`) or Phase 6 (hardening/close-out, `T77`–`T80`) — those get
their own handoff once this phase is done and verified. Do not build frontend code, Electron IPC,
or touch `/docs`/CORS settings as part of this handoff.

---

## 1. Required reading before writing anything

In this order:

1. [`IMPLEMENTATION_QUEUE.md`](../IMPLEMENTATION_QUEUE.md)'s "Stage 3 — Authentication &
   Authorization" section — the actual task list, approved decisions table, and acceptance
   criteria this handoff summarizes. **That section is authoritative; if this document and it ever
   disagree, trust `IMPLEMENTATION_QUEUE.md`.**
2. [`docs/Architecture.md`](Architecture.md) — Clean Architecture layering this stage must follow
   exactly (domain → application → infrastructure ← presentation).
3. [`ADR/0004-security-foundation-placeholders.md`](../ADR/0004-security-foundation-placeholders.md)
   — what Stage 0 already prepared for this moment (`RequestIDMiddleware`, `UnauthorizedError`/
   `ForbiddenError`, env-driven config discipline) and explicitly did not.
4. `backend/src/app/application/interfaces/auth.py` — the exact `CurrentUser`/
   `AuthenticationProvider`/`AuthorizationService` shapes you're extending, not replacing.
5. `backend/src/app/infrastructure/auth/anonymous_auth_provider.py` and
   `permissive_authorization_service.py` — the two stub implementations you're adding real
   siblings for (don't delete the stubs; they may still be useful as test fakes).
6. `backend/src/app/infrastructure/persistence/models/identity.py` — the exact `User`/`Role`/
   `Permission`/`UserRole`/`RolePermission` columns already in the schema (see §3 below for the
   summary).
7. `backend/alembic/versions/9963e15f2752_seed_lookup_data.py` — read its own docstring and the
   `roles`/`permissions` `op.bulk_insert()` blocks; this is what T66's migration adds to.
8. One existing post-Stage-2 addition end-to-end as your pattern template — **Command Bus is the
   best fit** (`application/interfaces/command_bus.py` → `infrastructure/commands/
   in_memory_command_bus.py` → registered in `infrastructure/di/container.py`'s
   `configure_container()` → `tests/unit/test_command_bus.py`). Every new port/implementation you
   add this stage should look like that shape: an ABC in `application/interfaces/`, a concrete
   class in `infrastructure/<area>/`, one `container.register(...)` line, and a test file that
   exercises both directly and through DI resolution.

---

## 2. Finalized decisions (full detail in `IMPLEMENTATION_QUEUE.md`)

| # | Decision | Locked-in answer |
|---|---|---|
| D1 | Token mechanism | JWT access token (short-lived, ~15–30 min) + DB-backed, revocable refresh token. New `refresh_tokens` table (T49). |
| D2 | Password hashing | Argon2id via `argon2-cffi`. |
| D3 | JWT library | `PyJWT`. |
| D4 | First-admin bootstrap | One-time CLI command, **interactive** password prompt (`getpass` — never argv, env, or a file). |
| D5 | Self-registration | None. Only admin-created users via a `users:manage`-protected endpoint. |
| D6 | Frontend token storage | Out of scope for this handoff (Phase 5) — noted here only so backend token design doesn't accidentally assume `localStorage` semantics (e.g. don't make the refresh token something a browser-style client would silently auto-attach as a cookie). |
| D7 | `AuthenticationProvider` signature | **`async def get_current_user(self, token: str \| None) -> CurrentUser`** — this exact signature. Passing `None` (no token presented) must return the same anonymous `CurrentUser()` default `AnonymousAuthenticationProvider` returns today, not raise. |

---

## 3. What's already in place — don't rebuild, extend

**Schema (Stage 2, already migrated, do not re-create):**

```python
class User(Base, AuditMixin):
    __tablename__ = "users"
    id: Mapped[UUID]
    email: Mapped[str]              # unique, indexed
    full_name: Mapped[str]
    phone: Mapped[str | None]
    password_hash: Mapped[str | None]   # nullable today — every row you create must set it
    is_active: Mapped[bool]             # default True
    last_login_at: Mapped[datetime | None]

class Role(Base, AuditMixin):
    __tablename__ = "roles"
    id, name (unique), description, is_system_role

class Permission(Base, AuditMixin):
    __tablename__ = "permissions"
    id, code (unique, e.g. "matters:read"), description, category

class UserRole(Base):        # user_id + role_id, unique together, assigned_at/assigned_by
class RolePermission(Base):  # role_id + permission_id, unique together
```

**Seed data already present** (from `9963e15f2752_seed_lookup_data.py`): 6 roles (Administrator,
Advocate, Paralegal, Clerk, Accountant, Read Only) and 18 permissions across `matters:*`,
`clients:*`, `properties:*`, `documents:*`, `financial:*`, plus `users:manage`, `roles:manage`,
`settings:manage`, `reports:read`. **`role_permissions` and `users` are both empty** — populating
them is T66/T67's job, not something to assume already exists.

**Ports already defined** (`application/interfaces/auth.py`) — you are implementing these, and
(per D7) making one signature change to one of them, not designing new ones:

```python
@dataclass(frozen=True, slots=True)
class CurrentUser:
    id: str | None = None
    display_name: str = "Anonymous"
    roles: frozenset[str] = field(default_factory=frozenset)
    is_authenticated: bool = False

class AuthenticationProvider(ABC):
    @abstractmethod
    async def get_current_user(self, token: str | None) -> CurrentUser: ...  # ← D7 change goes here

class AuthorizationService(ABC):
    @abstractmethod
    def require_permission(self, user: CurrentUser, permission: str) -> None: ...
```

**Errors already defined** (`application/errors/exceptions.py`), unused so far — raise these, don't
invent new ones: `UnauthorizedError` (401, "the caller is not authenticated"), `ForbiddenError`
(403, "authenticated but not permitted"). Both already flow through the existing
`presentation/middleware/error_handler.py` into the standard `{"error":{"code","message"}}` shape —
you don't need to touch the error handler.

**Repository already generic:** `SqlAlchemyRepository[User]` (and `[Role]`, etc.) work today with
zero new repository code — Stage 1's repository pattern is entity-agnostic. Don't write a
`UserRepository` class unless `AuthService`/user-management routes genuinely need a query the
generic repository can't express (e.g. "find by email" — `get_by_id` only takes a UUID; you'll need
either a small custom method or a direct `select()` in the service, consistent with how this
project has handled entity-specific lookups so far — check for precedent before inventing a new
pattern).

**What's genuinely missing (this stage builds it):** password hashing, JWT encode/decode, the
`refresh_tokens` table, `AuthService`, real `AuthenticationProvider`/`AuthorizationService`
implementations, `RequirePermission(...)`, every auth/user-management route, the `role_permissions`
seed, and the bootstrap CLI.

---

## 4. Hard prerequisite — do this literally first

**`get_db()` currently never commits.** `backend/src/app/infrastructure/database/session.py`:

```python
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    session_factory = get_session_factory()
    async with session_factory() as session:
        yield session
```

`SqlAlchemyRepository.add()`/`update()`/`delete()` only call `session.flush()`, never `commit()`.
The session closes at the end of every request without persisting anything — a write looks like it
succeeded (flush makes it visible within the same transaction) and then vanishes. **Every write
this stage makes — creating the bootstrap admin, hashing a password, recording `last_login_at`,
assigning a role — would silently fail without fixing this first.**

**Fix (T42):**

```python
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

Then (T43): add a regression test that writes through `get_db()` in one session and reads it back
from a **second, independent** session/connection (the existing `tests/conftest.py` `db_session`
fixture deliberately rolls back for test isolation, so it can't prove this — you need a fixture that
doesn't roll back, or two separate engine/session instances). Write `ADR-0020` recording this as a
deliberate policy ("every session commits on success, rolls back on exception") — see
`ADR/template.md` for the shape, and any of `ADR/0010`–`0017` for length/tone precedent.

**Do not start Phase 1 until T42/T43 are done, tested, and committed separately** — this project's
"small, reviewed sections" discipline applies here more than anywhere else in this stage, since
everything downstream depends on writes actually persisting.

---

## 5. New dependencies

Add to `backend/pyproject.toml`'s `[project.dependencies]` (not `dependency-groups.dev` — these are
runtime deps):

- `argon2-cffi` (D2)
- `PyJWT` (D3)

Run `uv lock` after adding, don't hand-edit `uv.lock`.

## 6. New `Settings` fields

Extend `backend/src/app/infrastructure/config/settings.py`'s `Settings` class — follow the existing
pattern exactly (env-driven, a sensible non-secret default only where genuinely safe, no default at
all for the actual signing secret):

- `jwt_secret_key: str` — **no default**; must come from `.env`/env var. Add it to
  `backend/.env.example` with a placeholder, never a real value.
- `jwt_algorithm: str = "HS256"`
- `access_token_ttl_minutes: int = 20` (or your judgment within the ~15–30 min range D1 specifies)
- `refresh_token_ttl_days: int = 14` (pick a concrete number; not specified more precisely by D1 —
  use your judgment, document the choice in `ADR-0018`)

---

## 7. File-by-file implementation map

Organized by phase, matching this project's existing folder conventions (see
`docs/FolderStructure.md`). Paths relative to `backend/src/app/` unless noted.

### Phase 1 — credentials & token foundation (T46–T51)

| File | What |
|---|---|
| `infrastructure/security/password_hasher.py` *(new)* | `hash_password(plain: str) -> str`, `verify_password(plain: str, hashed: str) -> bool`, using `argon2.PasswordHasher`. |
| `infrastructure/security/jwt_service.py` *(new)* | Encode/decode functions or a small class — access & refresh token creation (claims: `sub` = user id, `roles`, `exp`, `jti`), and a decode function that raises (or returns `None`/a `Result`) on expired/invalid/tampered tokens. Reads `Settings.jwt_secret_key`/`jwt_algorithm`/TTLs — don't hardcode. |
| `alembic/versions/<rev>_refresh_tokens.py` *(new, backend/)* | `refresh_tokens` table: `id` (UUID PK), `user_id` (FK → `users.id`), `token_hash` (store a hash of the token, never the raw token — same principle as passwords), `issued_at`, `expires_at`, `revoked_at` (nullable). Follow `DatabaseMigrationTemplate.md` for documenting it in `docs/Database.md`/`docs/ERD.md`. |
| `application/auth_service.py` *(new — or `application/services/auth_service.py`, match whichever convention `application/` settles into; there's no `services/` subfolder yet, so top-level `application/auth_service.py` is the more consistent choice today)* | `AuthService`: `authenticate(email, password) -> Result[User, AppError]`, `issue_tokens(user) -> tuple[str, str]` (access, refresh), `refresh(refresh_token) -> Result[tuple[str, str], AppError]` (validates + rotates — old refresh token revoked, new one issued), `revoke(refresh_token) -> None`. Depends on `AbstractRepository[User]`, the password hasher, the JWT service, and a repository/port for `refresh_tokens` (either a `SqlAlchemyRepository[RefreshToken]` or a small dedicated interface if `AbstractRepository`'s shape doesn't fit token lookup-by-hash cleanly — your call, document it). |
| `tests/unit/test_auth_service.py` *(new)* | Every case in T51's acceptance criteria — see `IMPLEMENTATION_QUEUE.md`. |

### Phase 2 — wiring into the request pipeline (T52–T57)

| File | What |
|---|---|
| `infrastructure/auth/jwt_authentication_provider.py` *(new)* | `JwtAuthenticationProvider(AuthenticationProvider)` — `get_current_user(self, token: str | None)` decodes the token via the JWT service, loads the `User` (and their roles, via `user_roles`) if valid, returns a populated `CurrentUser`; returns the anonymous default for `None`/invalid/expired (don't raise here — let the caller/dependency decide whether anonymous is acceptable, matching how `AnonymousAuthenticationProvider` already behaves). |
| `infrastructure/auth/rbac_authorization_service.py` *(new)* | `RbacAuthorizationService(AuthorizationService)` — `require_permission(user, permission)` raises `ForbiddenError` if the user is anonymous (same first check `PermissiveAuthorizationService` already does) or if `permission` isn't in the set of permissions their roles grant (via `role_permissions`). Needs a way to look up a user's effective permission set — either query it fresh each call or have `JwtAuthenticationProvider` attach it to `CurrentUser` at login time (note: `CurrentUser.roles` exists but there's no `permissions` field today — decide whether `RbacAuthorizationService` re-derives permissions from `roles` each call (simpler, one extra query) or whether `CurrentUser` needs a new field for permissions (touches the dataclass, a smaller version of D7's kind of change — flag it if you go this route rather than doing it silently). |
| `presentation/api/deps.py` *(modify)* | `CurrentUserDep` needs to extract the bearer token from the request (FastAPI's `HTTPBearer`/`OAuth2PasswordBearer` security scheme, or manual header parsing — match whatever's idiomatic for the FastAPI version pinned in `pyproject.toml`) and pass it to `get_current_user(token)`. Add a new `RequirePermission(permission: str)` dependency factory here (or a new `presentation/api/security.py` if `deps.py` gets crowded) — closes F11. |
| `infrastructure/di/container.py` *(modify)* | In `configure_container()`, replace the `AuthenticationProvider -> AnonymousAuthenticationProvider` and `AuthorizationService -> PermissiveAuthorizationService` registrations with the real implementations. **Do not delete the stub classes** — they're still useful as test fakes and as the pattern reference for "what does the permissive/anonymous baseline look like." |
| `tests/unit/test_jwt_authentication_provider.py`, `test_rbac_authorization_service.py` *(new)* | Per T57's acceptance criteria. |

### Phase 3 — routes (T58–T65)

| File | What |
|---|---|
| `presentation/api/v1/auth.py` *(new)* | `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`, `GET /auth/me`. Request/response Pydantic schemas alongside (match the existing `presentation/api/v1/version.py`'s inline-schema style, or a `presentation/api/v1/schemas/auth.py` if it grows — check what precedent exists before choosing). Use `ApiResponse[T]` for responses, consistent with every other endpoint shape in this codebase. |
| `presentation/api/v1/users.py` *(new)* | List/get/create/update/deactivate users, each behind `RequirePermission("users:manage")`. Creating a user hashes the password via `password_hasher`, never stores plaintext even transiently in a log. Consider whether `build_crud_router` (`presentation/common/crud_router_factory.py`) fits here — it was designed for exactly this ("a future feature wires its real router with this once a real entity/schema exists") but its `build_entity`/`apply_update` hooks need to handle password hashing specially; read that file's docstring (it has a documented PEP 695/runtime-annotation gotcha) before deciding to use it vs. hand-writing the router. |
| `presentation/api/v1/router.py` *(modify)* | Mount the two new routers. **This is the moment the real app's route surface changes for the first time since Stage 0** — every prior addition explicitly verified it stayed at `/api/v1/health`+`/api/v1/version` only; this stage is where that invariant is expected to change, deliberately. |
| `infrastructure/audit/audit_logger.py` or wherever login events get recorded *(modify or extend)* | Log login success/failure and permission-denied events via the existing `AuditLogger` port — don't build a new logging path. |
| `tests/integration/test_auth_routes.py`, `test_user_routes.py` *(new)* | Per T64's acceptance criteria — every route, happy path + every failure mode, asserting exact status codes. |

### Phase 4 — seed & bootstrap (T66–T68)

| File | What |
|---|---|
| `alembic/versions/<rev>_seed_role_permissions.py` *(new)* | Populate `role_permissions` per the approved matrix — **get explicit sign-off on the exact matrix before writing this migration**, it's flagged as still-open in `IMPLEMENTATION_QUEUE.md` separately from D1–D7. Follow `9963e15f2752`'s `sa.table()` shadow-definition pattern, not ORM imports (Alembic's own recommendation, already established in this codebase). |
| `cli.py` or `infrastructure/cli/bootstrap.py` *(new — check if a `backend/src/app/cli.py` entry point convention makes more sense given `pyproject.toml`'s `[project.scripts]`, currently unused)* | The D4 bootstrap command: checks if any user exists, if not prompts for email + `getpass`-style password, creates the first user with the `Administrator` role. Idempotent: running it again when a user already exists should say so and exit cleanly, not error or create a duplicate. |
| `tests/integration/test_seed_role_permissions.py`, `tests/unit/test_bootstrap_admin.py` *(new)* | Per T68's acceptance criteria. |

---

## 8. Testing conventions to follow

- `tests/unit/` for anything with no I/O (password hashing, JWT encode/decode, pure `AuthService`
  logic against a fake repository).
- `tests/integration/` for anything exercising the real FastAPI app via `TestClient`, or touching a
  real Postgres connection (route tests, the `refresh_tokens`/`role_permissions` migrations,
  end-to-end login flows).
- Fixtures go in `tests/conftest.py` (extend it, don't duplicate) — see the existing `client`
  fixture (`TestClient`) and `db_session` fixture (real migrated schema, rolls back per test)
  patterns.
- Match this project's existing assertion style: specific status codes, specific error codes from
  the `{"error":{"code","message"}}` shape — not just "it raised something."
- Run the **full** suite before considering any phase done, not just the new tests — `uv run
  pytest` from `backend/`, confirm the existing 282 still pass alongside whatever you've added.

## 9. Explicit boundaries — do not do these as part of this handoff

- No frontend code, no Electron IPC, no `frontend/src/` changes at all (Phase 5, separate handoff).
- No `/docs`/`/redoc` gating, no CORS changes (Phase 6, separate handoff — even though they're
  security-adjacent, they're scoped to a later phase deliberately).
- No password reset/forgot-password flow, no MFA, no OAuth/SSO, no rate limiting or account
  lockout, no session-management UI, no row/column-level access control — all explicitly deferred,
  see `IMPLEMENTATION_QUEUE.md`'s "Explicitly out of scope" list for Stage 3.
- No touching Matter/Client/Property/Document/Financial schema or routes — this stage is Identity &
  Access only.
- No writing the `role_permissions` seed migration (T66) until the exact matrix is signed off
  separately — implementing the rest of Phase 4 (T67/T68's non-seed parts) doesn't need to wait for
  that, but T66 itself does.
- Don't start any of this until you have an explicit go-ahead beyond this document — it is
  preparation, not authorization.

## 10. Definition of done for this handoff's scope (T41–T68)

Mirrors `IMPLEMENTATION_QUEUE.md`'s per-phase acceptance criteria for Stage 3 — reproduced in full
there; the short version: `get_db()` provably commits/rolls back correctly; a wrong password never
verifies and a tampered/expired JWT is always rejected; every `RequirePermission`-guarded route
returns 401/403 correctly and never 500 for an auth failure; `POST /auth/login` →
`POST /auth/refresh` → `POST /auth/logout` works end-to-end against the bootstrap admin with correct
token rotation and revocation; `role_permissions` matches the approved matrix exactly; the bootstrap
CLI creates exactly one admin and is idempotent; the full backend test suite (existing 282 + every
new test) passes; ruff/black are clean; `ADR-0018`/`0019`/`0020` exist; `IMPLEMENTATION_QUEUE.md`
reflects T41–T68 as done.

At that point, stop and report — Phase 5 (frontend) and Phase 6 (hardening) each get their own
handoff, not an automatic continuation.
