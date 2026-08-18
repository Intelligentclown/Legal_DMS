# T61 Implementation Handoff — `GET /api/v1/auth/me`

Created by: Project Manager role, 2026-08-15, following explicit Project Owner authorization.
Recipient: Backend Developer role.

---

## 1. Authorization

- **Approved by:** Project Owner, explicitly, in this Project Manager conversation, 2026-08-15.
- **Recorded in repository (verified, not assumed):** commit `520026f` ("docs(project): record
  T61 authorization before implementation"), branch `docs/t61-authorization`, opened as
  [PR #29](https://github.com/Intelligentclown/Legal_DMS/pull/29), merged to `main` as `cca1077`
  ("Merge pull request #29 from Intelligentclown/docs/t61-authorization"). `git rev-parse HEAD
  origin/main` both confirm `cca1077` at the time this handoff was written.
- **Authorization precedes implementation:** confirmed — no implementation, test, or migration
  file for T61 exists anywhere in the tree as of `cca1077`.
- **Scope basis:** the two contract decisions the Project Owner approved explicitly in this
  conversation (response fields; no RBAC permission requirement), as already recorded verbatim in
  `IMPLEMENTATION_QUEUE.md`'s T61 row and `PROJECT_STATE.json`'s `currentStage.note`. No separate
  "Implementation Understanding Summary" document exists in this repository or this conversation —
  this handoff and the two governance files above are the authoritative scope record.
- Per this project's governance discipline (five-for-five on T56–T60, now six-for-six): authorization
  was committed and merged into `main` **before** this handoff was written, and before any
  implementation exists.

## 2. Exact Scope

Implement one new route: **`GET /api/v1/auth/me`**.

- Requires an authenticated caller, via the existing `CurrentUserDep` (`presentation/api/deps.py`).
- **No specific RBAC permission is required.** Any authenticated user (`CurrentUser.is_authenticated
  is True`) may access this route. Do **not** use `RequirePermission(...)` — none of the 18 seeded
  permission codes represents "view own profile," and inventing one is explicitly out of scope.
- Returns exactly three fields, taken directly from the resolved `CurrentUser`, with no
  transformation: `id`, `display_name`, `roles`.
- **No additional profile fields are in scope** — `email`, `phone`, `is_active`, `last_login_at`
  (all present on the `User` persistence model but not on `CurrentUser`) must **not** be added to
  the response, and `CurrentUser`'s dataclass must **not** be extended to carry them.
- No request body. No query parameters. No path parameters.
- **Response envelope:** wrap the response in `ApiResponse[MeResponse]`
  (`presentation/common/response.py`), matching `crud_router_factory.py`'s `GET /{item_id}` →
  `ApiResponse[ReadSchema]` pattern — **not** `login`/`refresh`/`logout`'s bare-response convention.
  Those three routes are explicitly bare because a token pair "isn't a fetchable resource"
  (`response.py`'s own docstring: `ApiResponse` is "for future resource-returning endpoints"); `/me`
  fetches the current user's own resource, which is exactly the case `ApiResponse` exists for. This
  is a deliberate instruction from this handoff, not a discretionary choice — do not default to
  `login`/`refresh`/`logout`'s bare-schema pattern here.
- **Success status:** `200 OK` (FastAPI's default for a `GET`; no precedent in this codebase for a
  non-default status on a plain resource fetch).

## 3. Allowed Files

- `backend/src/app/presentation/api/v1/auth.py` — extend with a new `MeResponse` schema
  (co-located, matching the existing `LoginRequest`/`LoginResponse`/etc. convention — no separate
  schema module exists in this codebase) and a `me()` route handler.
- `backend/tests/integration/test_auth_me.py` — new file, following `test_auth_login.py` /
  `test_auth_refresh.py` / `test_auth_logout.py`'s established pattern (`httpx.AsyncClient` +
  `ASGITransport`, `get_db` dependency override, real Postgres, local `client` fixture / `_make_user()`
  / `_login()` helpers reused verbatim where applicable).

No other file should need to change. `router.py` already mounts `auth.router`; no new registration
is needed.

## 4. Forbidden Files / Scope

Do **not** modify:

- `backend/src/app/application/auth_service.py` (`AuthService`) — `/me` needs no service-layer call
  beyond what `CurrentUserDep` already resolves.
- `backend/src/app/presentation/api/deps.py` — `CurrentUserDep`, `get_authentication_provider()`,
  `get_bearer_token()`, `get_current_user()`, `RequirePermission(...)` are all reused exactly as they
  exist today. No new dependency needs to be added here.
- `backend/src/app/presentation/api/v1/router.py` — already mounts `auth.router`; no change needed.
- `backend/src/app/application/interfaces/auth.py` (`CurrentUser` dataclass) — must stay exactly as
  it is (`id`, `display_name`, `roles`, `is_authenticated`); do not add fields.
- `backend/src/app/infrastructure/auth/jwt_authentication_provider.py`,
  `backend/src/app/infrastructure/auth/rbac_authorization_service.py`,
  `backend/src/app/infrastructure/auth/permissive_authorization_service.py` — unmodified.
- Any file under `backend/alembic/` (no migration is needed or authorized).
- Any file related to T62 (user management), T63 (role assignment), T64 (cross-route integration
  tests beyond `/me`'s own), T65 (audit-log wiring), or anything in Phase 4/5/6.
- Any frontend file.
- Any governance file (`IMPLEMENTATION_QUEUE.md`, `PROJECT_STATE.json`, `PROJECT_CHECKPOINT.md`) —
  those are Project Manager / Documentation Manager owned; the Backend Developer's own required
  documentation update is scoped to `docs/ImplementationLog/Stage3/Phase3.md` only (see §9).

## 5. Acceptance Criteria

1. `GET /api/v1/auth/me` with a valid access token for an active user → `200`, body
   `{"data": {"id": "<uuid-string>", "display_name": "<full_name>", "roles": [...]}, "meta": null}`.
2. `GET /api/v1/auth/me` with no `Authorization` header → `401`.
3. `GET /api/v1/auth/me` with a malformed/invalid token string → `401`.
4. `GET /api/v1/auth/me` with an expired token → `401`.
5. `GET /api/v1/auth/me` with a token for a now-inactive user → `401`.
6. A user with multiple assigned roles gets all of them back in `roles`.
7. No route added, removed, or changed besides `/me`. `app.openapi()["paths"]` must show exactly
   `/api/v1/auth/login`, `/api/v1/auth/refresh`, `/api/v1/auth/logout`, `/api/v1/auth/me`,
   `/api/v1/health`, `/api/v1/version` — nothing else.
8. Full backend suite still green (403 prior + new `/me` tests), `ruff`/`black` clean, boot smoke
   test (`python -c "from app.main import app"`) still passes.

## 6. Required Tests

New file `backend/tests/integration/test_auth_me.py`, minimum set (mirroring T58–T60's per-batch
test list):

- `test_valid_token_returns_profile_and_roles` — 200, correct `id`/`display_name`/`roles` for that
  specific user, wrapped in `ApiResponse`'s `{"data": ...}` shape.
- `test_missing_token_returns_401`
- `test_malformed_token_returns_401`
- `test_expired_token_returns_401`
- `test_inactive_user_token_returns_401`
- `test_multiple_roles_all_returned` — a user with 2+ roles gets all of them back, not just one.

Do not add a "revoked token" case for `/me` — access tokens are not DB-revocable by design (D1);
that concern belongs to `/refresh`, not `/me`.

## 7. Stop Conditions

Stop and escalate to the Project Manager (do not improvise a fix) if any of the following occurs:

- The approved response shape (`id`/`display_name`/`roles` only, wrapped in `ApiResponse`) turns out
  to be insufficient for some reason not anticipated here.
- Implementing `/me` seems to require any change to `CurrentUser`, `deps.py`, `AuthService`, or any
  file listed in §4.
- `RequirePermission(...)` or any permission code appears to be necessary after all.
- Any existing test (outside the new `test_auth_me.py`) starts failing because of this change.
- Anything about the existing `CurrentUserDep`/`JwtAuthenticationProvider` chain does not behave as
  documented in §2 of the T61 Assessment (e.g., an inactive user's token does *not* resolve to
  anonymous as expected).

## 8. Implementation Constraints

- Follow the Backend Developer role's required checkpoint
  (`docs/prompts/BackendDeveloper.md` §5): reconstruct understanding of this handoff, summarize it,
  and wait for explicit approval of that summary before writing code.
- One feature branch for this task (`feature/stage3-t61-auth-me` or equivalent), not a direct commit
  to `main`.
- No unrelated refactoring, no touching any file not listed in §3.
- Reuse existing test fixtures/helpers (`client`, `_make_user()`, `_login()`) rather than
  reinventing them, per every prior Phase 3 batch's own documented convention.

## 9. QA Requirements

QA Reviewer must independently verify, not merely transcribe the Backend Developer's own report:

- Code/tests match §5's acceptance criteria exactly.
- `git show --stat <implementation commit>` confirms only the files listed in §3 changed (plus the
  implementation log — see §10).
- No file listed in §4 was touched.
- Full suite passes, `ruff`/`black` clean, boot smoke test passes, `app.openapi()["paths"]` contains
  exactly the six routes listed in §5, item 7.
- Render an explicit QA Decision: `Approved` / `Approved with comments` / `Rework required` — never
  pre-filled by the implementer.

## 10. Documentation Requirements

Backend Developer, immediately after implementation (per this project's established Phase 3
pattern):

- Append a new **T61 batch** section to `docs/ImplementationLog/Stage3/Phase3.md` (Objective, Tasks
  Implemented, Files Modified, Tests Added, Test Results, Design Decisions, Problems Encountered,
  Deferred Work, Reviewer Checklist) — matching the existing T58/T59/T60 batch sections' structure
  exactly.

Do **not** update `IMPLEMENTATION_QUEUE.md`, `PROJECT_STATE.json`, or `PROJECT_CHECKPOINT.md` as
part of implementation — those are updated by the Project Manager / Documentation Manager roles
after a QA Decision exists, per this project's Documentation Ownership rules
(`docs/ImplementationLog/README.md`).

---

**T62–T67 remain explicitly out of scope and unauthorized.** This handoff authorizes T61 only.
