------------------------------------------------

# Stage 3 – Phase 2

Status: In Progress

Started: 2026-08-08

Completed: 2026-08-10

Related Tasks: T52, T53, T54, T55

Related ADRs: ADR-0019

Git Commit: T52 — baed936 (merge; feature commit 003ab15). T53 — a103dca (merge; feature commit dd754f5). T54 — 6396f6b (merge; feature commit dbd6724). T55 — b094436 (merge; feature commit 86a3d5d; governance-reconciliation commit f070e28).

Pull Request: T52 — #9. T53 — #10. T54 — #12. T55 — #15.

Release:

------------------------------------------------

## Objective

Begin Stage 3 Phase 2 (wiring auth into the request pipeline) with `T52` only: a real
`JwtAuthenticationProvider` implementing `AuthenticationProvider`'s approved D7 signature
(`async def get_current_user(self, token: str | None) -> CurrentUser`, `ADR-0019`). No
`RbacAuthorizationService`, `RequirePermission` dependency, `configure_container()` wiring, or
`deps.py` changes — those are `T53`–`T57`, not started this batch.

**Provenance note (recorded by the Documentation Manager role, not the implementer):** this section
of the log is being written after the fact, reconstructing what the repository actually shows
(`git status`, the files themselves, a fresh test run) rather than from a Backend Developer's own
self-authored account, because no such account exists anywhere in the repository — see Problems
Encountered for why. Every fact below was independently verified against the repository, not copied
from a claim.

**T54 batch (2026-08-08):** the `RequirePermission(...)` FastAPI dependency factory (closes Stage
2.5's flagged-not-scheduled finding F11, now explicitly in scope) — the first real caller of `T53`'s
`AuthorizationService.require_permission()` anywhere in the app. No `RbacAuthorizationService`
changes, no `configure_container()` wiring, no route changes; `T55`–`T57` explicitly not started
this batch.

**Authorization / Scope:** `T54` was authorized by the project owner in a Project Manager
conversation — the same authorization channel `T52`/`T53` used. Unlike `T53`, the Backend Developer
role's `docs/prompts/BackendDeveloper.md` §5 approval checkpoint (reconstruct state, summarize
understanding — task, acceptance criteria, dependencies — then wait for explicit approval of *that
summary* before implementing) **was performed and explicitly approved before implementation began**
— this is reported directly, not independently reconstructible from repository state alone (a
conversation leaves no repository artifact either way), but it is not disputed here and is recorded
as fact per the instruction under which this section is written; see Problems Encountered for why
this distinction from `T53` matters enough to state plainly. What was **not** done before
implementation began is the same gap `T52`/`T53` already demonstrated: the authorization itself was
never written into `IMPLEMENTATION_QUEUE.md`/`PROJECT_STATE.json` beforehand, and this phase log had
no `T54` batch entry until this pass.

## Tasks Implemented

- **T52 — `JwtAuthenticationProvider`.** `infrastructure/auth/jwt_authentication_provider.py`: decodes
  the presented bearer token via `T47`'s `decode_token()`, then re-derives the caller's identity and
  roles live from the database via `T50`'s `UserRepository` (`get_by_id`, `get_role_names`) — the
  token's own `roles` claim is never trusted as the source of truth, matching the defense-in-depth
  pattern `AuthService.refresh()` already established. `token=None`, a `None` decode result (expired/
  malformed/tampered/wrong-secret token — all of which `decode_token()` already collapses to `None`
  per `T47`), a non-UUID/missing `sub` claim, an unknown user id, or an inactive user all resolve to
  the same anonymous default (`CurrentUser()`) — the method never raises.

**T53 batch (this update, 2026-08-08):** real `RbacAuthorizationService` implementing
`AuthorizationService` — checks `require_permission()` against the caller's roles → `role_permissions`.
Approved strictly scoped to `T53` and its own tests; `T54`–`T57` explicitly not authorized this
batch (no `RequirePermission` dependency, no `configure_container()` wiring, no `deps.py` changes).

**T54 batch:** `RequirePermission(permission: str) -> Callable[..., Awaitable[None]]` in
`presentation/api/deps.py` — a dependency *factory*: called with a permission code
(`RequirePermission("matters:read")`), it returns an async dependency function that resolves the
request's `CurrentUser` (via the existing `CurrentUserDep`) and the registered `AuthorizationService`
(via a new `get_authorization_service()` resolver, mirroring `get_authentication_provider()`'s
existing shape), then calls `authorization_service.require_permission(user, permission)`. Raises
`ForbiddenError` on denial — the project's existing exception handler already turns that into the
standard 403 response shape, so no route needs to catch it itself. Intended usage:
`Depends(RequirePermission("matters:read"))`, either as a single route's dependency or in a router's
`dependencies=[...]` list.

## Files Modified

- `backend/src/app/infrastructure/auth/jwt_authentication_provider.py` *(new)*.
- `backend/tests/unit/test_jwt_authentication_provider.py` *(new)*.

Both files are **untracked** in the working tree as of this log entry (confirmed via `git status`) —
not merely "on a branch instead of main," but not committed anywhere at all yet. See Problems
Encountered.

**T53 batch:**
- `backend/src/app/application/interfaces/role_permission_repository.py` *(new)* — narrow port,
  one method: `get_permission_codes_by_role_name() -> Mapping[str, frozenset[str]]`.
- `backend/src/app/infrastructure/persistence/sqlalchemy_role_permission_repository.py` *(new)* —
  the port's SQLAlchemy implementation (one join query, `roles` → `role_permissions` → `permissions`).
- `backend/src/app/infrastructure/auth/rbac_authorization_service.py` *(new)* — real
  `AuthorizationService`.
- `backend/tests/unit/test_rbac_authorization_service.py` *(new)*.
- `backend/tests/integration/test_sqlalchemy_role_permission_repository.py` *(new)*.
- `docs/ImplementationLog/Stage3/Phase2.md` — this file.

No dependency file touched. No existing file modified — all five are new files; `container.py`,
`deps.py`, and `infrastructure/auth/__init__.py` are untouched (matches `T52`'s own precedent of not
updating `infrastructure/auth/__init__.py`'s re-exports, since nothing consumes it yet either way).
All five files are **untracked** as of this log entry — same as `T52`'s files were before its own
branch/commit/PR closed that gap; not yet branched, committed, or pushed this batch.

**T54 batch:**
- `backend/src/app/presentation/api/deps.py` — **modified** (not new): added
  `get_authorization_service()` and `RequirePermission(...)`.
- `backend/tests/unit/test_auth.py` — **modified**: added `_RecordingAuthorizationService` (a fake
  recording every `require_permission()` call) and `TestRequirePermission` (5 tests); updated the
  `from app.presentation.api.deps import ...` line to also import `RequirePermission`.
- `docs/ImplementationLog/Stage3/Phase2.md` — this file.

Unlike `T52`/`T53`, this batch touches two **existing, already-tracked** files rather than adding new
ones — `git status` shows both as `M` (modified), not `??` (untracked). No dependency file touched;
no other source file changed — `container.py`, `main.py`, and `presentation/api/v1/` (confirmed by
direct grep) are all untouched. Both modified files remain **uncommitted directly on `main`** as of
this log entry — see Problems Encountered.

## Tests Added

11 in `backend/tests/unit/test_jwt_authentication_provider.py`:

`TestNoOrInvalidToken` (6): `token=None` returns anonymous; a malformed (non-JWT) token returns
anonymous; an expired token returns anonymous; a tampered-signature token returns anonymous; a token
signed with a different secret returns anonymous; a token with a non-UUID `sub` claim returns
anonymous rather than raising.

`TestDatabaseResolution` (5): a well-formed token for an unknown user id returns anonymous; a token
for a since-deactivated user returns anonymous; a valid token for an active, known user returns a
populated, authenticated `CurrentUser` with the correct id/display name/roles; roles are re-derived
from the database rather than trusted from the token's own `roles` claim (a token carrying a stale
role, checked against a database role that has since changed, reflects the database's current value);
a user deactivated *after* token issuance returns anonymous on the next call, not just at next login.

**T53 batch:** 13 total.

8 in `backend/tests/unit/test_rbac_authorization_service.py` (pure logic, an in-memory
role → permission-codes mapping, no DB):

`TestAnonymousCallers` (2): an anonymous caller is denied regardless of what the mapping contains;
a caller with non-empty `roles` but `is_authenticated=False` is still denied — `is_authenticated` is
the deciding flag, not whether `roles` happens to be non-empty.

`TestAuthenticatedCallers` (6): an authenticated user with a granting role is permitted; without one,
denied; with no roles at all, denied; a permission granted by only one of several roles the user
holds is permitted; a role the caller has that's simply absent from the mapping (e.g. genuinely
unseeded, `T66`) fails the check cleanly rather than raising a lookup error; permission codes must
match exactly (`matters:read` granted does not satisfy a `matters:write` check).

5 in `backend/tests/integration/test_sqlalchemy_role_permission_repository.py` (against the real
migrated schema, live Postgres): an empty `role_permissions` table yields an empty mapping; a single
grant is reflected under the correct role name; a role with multiple granted permissions returns all
of them; a role with zero grants is absent from the mapping entirely (not present with an empty set);
two different roles sharing the same permission each get their own independent entry.

**T54 batch:** 5 in `backend/tests/unit/test_auth.py`'s new `TestRequirePermission` class, calling
the dependency function `RequirePermission(...)` returns directly (bypassing FastAPI's own
`Depends()` wiring — matching `TestGetCurrentUserDependency`'s existing pattern in the same file,
since proving `Depends()` itself works is FastAPI's job, not this project's):

1. `test_allows_when_the_authorization_service_permits` — an authenticated user against a permitting
   fake `AuthorizationService` does not raise.
2. `test_raises_forbidden_when_the_authorization_service_denies` — a denying fake raises
   `ForbiddenError`.
3. `test_passes_the_configured_permission_and_user_through_unchanged` — the exact `(user,
   permission)` pair reaches `AuthorizationService.require_permission()` unmodified, verified via a
   recording fake (`_RecordingAuthorizationService`).
4. `test_denies_anonymous_via_a_real_authorization_service` — against the real
   `PermissiveAuthorizationService` (not a fake), an anonymous `CurrentUser()` raises `ForbiddenError`
   matching "Authentication is required".
5. `test_allows_authenticated_via_a_real_authorization_service` — the same real service permits an
   authenticated user.

Matches `T54`'s own scope exactly (verify the dependency forwards to `AuthorizationService`
correctly and raises the right exception on denial) plus one earned test (a real service, not just a
fake, to prove the wiring isn't only correct against a test double) — the same "close real coverage
gaps, not just the letter of the spec" approach every prior Stage 3 batch has used.

## Test Results

- New tests: `pytest tests/unit/test_jwt_authentication_provider.py -v` — **11/11 passing**.
- Full backend suite: `pytest -q` — **356 passed** (345 prior + 11 new), 0 failed, 0 skipped. Re-run
  directly by the Documentation Manager role during this synchronization pass, not assumed from a
  prior claim.
- **Lint:** `ruff check src tests alembic` and `black --check src tests alembic` — both clean,
  re-verified directly.
- **Import/boot smoke test:** `python -c "from app.main import app"` — succeeds. `JwtAuthenticationProvider`
  is not wired into `main.py`/`configure_container()` this batch (that's `T55`), so this only confirms
  the new modules don't break import resolution.

**T53 batch:**
- New tests: `pytest tests/unit/test_rbac_authorization_service.py tests/integration/test_sqlalchemy_role_permission_repository.py -v`
  — **13/13 passing**, first run. (One fix needed before that first green run — see Problems
  Encountered: two integration tests initially used real seeded permission codes like `matters:read`
  and collided with Stage 2's seed data; switched to per-test unique codes.)
- Full backend suite: `pytest -q` (Postgres reachable this session — `legal_dms_postgres` healthy) —
  **369 passed** (356 prior + 13 new), 0 failed, 0 skipped.
- **Lint:** `ruff check src tests alembic` and `black --check src tests alembic` — both clean, no
  fixes needed.
- **Import/boot smoke test:** `python -c "from app.main import app"` — succeeds.
  `RbacAuthorizationService` is not wired into `configure_container()` this batch (that's `T55`), so
  this only confirms the new modules don't break import resolution.

**T54 batch:**
- New tests: `uv run pytest tests/unit/test_auth.py -v -k RequirePermission` — **5/5 passing**,
  independently re-run by the Documentation Manager role during this reconciliation pass, not
  assumed from a prior claim.
- Full backend suite: `uv run pytest -q` — **374 passed** (369 prior + 5 new), 0 failed, 0 skipped —
  matches the count QA independently reported; re-confirmed directly, not merely transcribed.
- **Lint:** `uv run ruff check src tests alembic` and `uv run black --check src tests alembic` —
  both clean, re-verified directly.
- **Import/boot smoke test:** `uv run python -c "from app.main import app"` — succeeds.
  `RequirePermission` is a plain dependency factory, not registered anywhere itself (nothing to wire
  into `configure_container()` — it resolves `AuthorizationService` at call time via the existing
  container, the same as `get_authentication_provider()` already does), so this only confirms the
  modified modules don't break import resolution.
- **Scope check:** direct `grep` of `container.py`, `main.py`, and `presentation/api/v1/` confirms no
  route, no `configure_container()` entry, and no `T53`/`T55`/`T56` file was touched this batch.

## Design Decisions

- **Never raises, always resolves to a `CurrentUser`.** Every failure mode (no token, expired,
  malformed, tampered, wrong secret, unparseable `sub`, unknown user, inactive user) collapses to the
  same anonymous default rather than distinct exceptions — matches the port's own documented contract
  (`application/interfaces/auth.py`: "must resolve the same as an invalid/expired token would — the
  anonymous default — never raise") and keeps "is this caller authenticated" a decision entirely
  local to whatever reads `CurrentUser.is_authenticated`, not scattered across a catch-every-exception
  block at each call site.
- **Roles re-derived from the database on every call, not read from the token's `roles` claim.**
  Consistent with `T50`'s `AuthService.refresh()`, which already re-derives current role names rather
  than trusting a token's claims — a role granted or revoked after token issuance takes effect
  immediately on the next request, not only after the access token naturally expires. Covered
  explicitly by `test_roles_are_re_derived_from_the_database_not_the_token_claims`.
- **No `configure_container()` registration this batch.** Same reasoning `T50`/`Phase1.md` already
  recorded for `AuthService`: `JwtAuthenticationProvider` needs a per-request `UserRepository` (backed
  by a per-request `AsyncSession`), which the container doesn't hold. That wiring is `T55`'s job.

**T53 batch:**
- **A new narrow port (`RolePermissionRepository`), not an `AbstractRepository[RolePermission]`.**
  `AbstractRepository[T]` is keyed to CRUD on one entity type by `id`; what `RbacAuthorizationService`
  actually needs is a read-only aggregate — every role name mapped to its granted permission codes,
  joined across three tables. Forcing that shape into `AbstractRepository[RolePermission]` would mean
  either a meaningless `get_by_id`/`add`/`update`/`delete` surface on join rows nothing writes yet, or
  a "generic filter" capability this project has already deferred as out-of-scope speculative work
  (Stage 2.5's F2/`SearchQuery`). One purpose-built method, sized to exactly what `T53`'s one real
  caller needs — the same "narrow port, not a general-purpose query interface" precedent `T50`'s
  `UserRepository`/`RefreshTokenRepository` already established.
- **The permission snapshot is loaded once and handed to `RbacAuthorizationService` at construction,
  not queried per `require_permission()` call.** `AuthorizationService.require_permission()` is
  synchronous — an existing, approved port signature (Stage 1) that this batch does not touch or
  propose changing — so an async DB query cannot run inside it. Constructing
  `RbacAuthorizationService(mapping)` with an already-resolved `Mapping[str, frozenset[str]]` keeps
  the port's signature untouched and keeps the service itself trivially testable with a plain dict, at
  the cost of deferring "how is that mapping actually built and refreshed per request" to `T55`'s
  wiring — the same deferred-construction trade-off `T50`/`T52` already made for their own per-request
  dependencies.
- **`require_permission()` reuses `PermissiveAuthorizationService`'s exact "anonymous is always
  denied" check** (`if not user.is_authenticated: raise ForbiddenError(...)`) before consulting the
  mapping at all — matching an existing pattern in the same file's sibling class rather than
  reinventing the anonymous-caller rule.
- **A role present on `CurrentUser.roles` but absent from the snapshot (e.g. genuinely unseeded,
  `T66`) is treated as "grants nothing," not an error.** `dict.get(role, frozenset())` rather than
  indexing — the caller's role assignment is not this service's concern to validate; it only answers
  "does any role this caller holds grant this permission," and an unmapped role simply contributes no
  permissions to that answer.

**T54 batch:**
- **A dependency *factory* (`RequirePermission(permission) -> a dependency`), not a dependency
  itself.** FastAPI's `Depends()` needs a zero/param-injected callable at the point it's declared,
  but `require_permission()` needs a specific *permission code* baked in per route/router — the
  factory shape is the standard FastAPI pattern for exactly this ("parameterized dependency"), not an
  invention specific to this project. Matches `docs/Stage3_Backend_Handoff.md`'s own description of
  `T54` as a "dependency factory," not a dependency.
- **A new `get_authorization_service()` resolver, mirroring `get_authentication_provider()`'s
  existing shape exactly** (`container.resolve(AuthorizationService)`), rather than inlining
  `container.resolve(...)` directly inside `RequirePermission`'s nested function. Keeps `deps.py`'s
  existing one-resolver-per-port convention intact; `RequirePermission` composes it via `Depends(...)`
  like any other dependency, not a special case.
- **No new exception handling in `RequirePermission` itself** — `AuthorizationService.require_permission()`
  already raises `ForbiddenError` on denial (Stage 1's own contract, exercised again unchanged by
  `T53`), and this project's existing global exception handler already turns `ForbiddenError` into
  the standard 403 shape. Adding a `try`/`except` here would just re-raise the same thing, or worse,
  risk swallowing it — the minimal-code path is also the correct one.
- **Tests call the returned dependency function directly, not through a real FastAPI route.** Matches
  `TestGetCurrentUserDependency`'s existing precedent in the same file — proving `Depends()`'s own
  resolution machinery works is FastAPI's responsibility, verified by FastAPI's own test suite, not
  something this project needs to re-prove for every dependency it defines.

## Problems Encountered

**The core issue this log entry exists to resolve, stated plainly and without inventing anything not
actually true:**

- **Authorization occurred, but not inside the repository.** The project owner explicitly authorized
  `T52` in a separate Project Manager conversation. That authorization is real — it is not being
  fabricated or backdated here — but it was never written into `IMPLEMENTATION_QUEUE.md` or
  `PROJECT_STATE.json` before implementation began, so both documents still read "not authorized yet"
  as of this session's start, directly contradicting what had actually been approved. This violates
  this project's own Repository-First Rule in spirit (the repository is supposed to be able to answer
  "was this authorized" on its own, without relying on a conversation elsewhere) even though the
  underlying decision was legitimate. This log does not retroactively insert a fake in-repository
  approval record predating implementation — it records, honestly, that the approval happened
  out-of-band and the repository is only catching up to that fact now.
- **No `docs/ImplementationLog/Stage3/Phase2.md` existed until this pass.** Per
  `docs/ImplementationLog/README.md`, a phase log is supposed to be created "the moment Phase 0
  [here, Phase 2] implementation actually starts," not after the fact. It wasn't. This file is that
  missing entry, created now rather than left permanently absent.
- **`T52` was implemented directly on `main`, and is currently uncommitted.** `git status` shows
  `jwt_authentication_provider.py` and its test file as **untracked** — no `feature/stage3-t52-*`
  branch was ever created, unlike every completed Stage 3 batch before it (`T46`, `T47`, `T49`,
  `T50`/`T51` all went through a feature branch + PR). This is a real deviation from
  `PROJECT_WORKFLOW.md` §4's branch strategy, not a formality — flagged here, not corrected, since
  creating a branch, committing, and pushing are git actions outside this role's scope (§8: "Never
  implement or modify source code" extends in spirit to not taking git actions on someone else's
  behalf without separate authorization) and none of those was authorized as part of this
  documentation-synchronization pass.
  **Update (2026-08-08, Documentation Manager, T52 administrative closeout):** this gap has since
  closed independently of any action taken from this log — `git log` now shows
  `feature/stage3-t52-jwt-authentication` branched, committed (`003ab15`), opened as PR #9, and
  merged (`baed936`). Confirmed directly via `git show --stat baed936`, not assumed. Recorded as a
  correction, not a silent edit to the paragraph above — the deviation was real at the time it was
  written and is described accurately here for how it was actually resolved.

None of the three items above reflects a defect in `T52`'s actual code or tests — QA's independent
review found both technically correct (see this log's QA Decision section once rendered). All three
are process/documentation gaps, and this pass closes the first two directly; the third remains open
and is recorded as such rather than silently implied to be resolved.

**T53 batch:** One technical issue and four process/governance deviations, all disclosed rather than
left implicit or silently absorbed into a clean narrative.

**Technical (not a defect in the shipped code):** the first run of
`test_sqlalchemy_role_permission_repository.py` failed two tests with a Postgres `UniqueViolationError`
on `permissions.code` — the tests had used literal codes (`"matters:read"`, `"matters:write"`) that
collide with Stage 2's already-committed seed data (18 real permissions, including those exact
codes). Fixed by generating a unique code per test (`f"{prefix}:{uuid4()}"`) instead of reusing real
permission strings — the same lesson `T49`'s/`T50`'s integration tests already had to apply for
`token_hash`/email uniqueness against a shared schema. No production code was affected; this was a
test-authoring mistake, not a bug in `SqlAlchemyRolePermissionRepository` itself.

**Process/governance (recorded 2026-08-08, Documentation Manager, T53 correction pass — not
technical defects, and not corrected retroactively into a cleaner-looking history):**

- **`T53` was authorized by the project owner in conversation.** That authorization is real, the
  same as `T52`'s was — it is not being disputed or treated as invalid here.
- **That authorization was never written into `IMPLEMENTATION_QUEUE.md` or `PROJECT_STATE.json`
  before implementation began.** Both documents read "not started"/"not authorized" for `T53` right
  up until this correction pass, which contradicted what had actually been approved — the same
  failure mode `T52`'s own QA Decision already named explicitly as worth avoiding going forward
  (see "QA Decision — T52 batch" above: "whoever authorizes a task should ensure
  `IMPLEMENTATION_QUEUE.md`/`PROJECT_STATE.json` reflect that authorization *before* implementation
  begins"). It recurred here anyway.
- **The Backend Developer role's required approval checkpoint (`docs/prompts/BackendDeveloper.md`
  §5, steps 3–4: reconstruct state, summarize understanding — task, acceptance criteria,
  dependencies — then wait for explicit approval of *that summary* before implementing) was
  skipped.** Project-owner authorization of the task in conversation is not the same thing as this
  checkpoint; §5 requires both. No record of that summarize-and-wait step exists anywhere in this
  batch's own account above.
- **`T53` was implemented directly on `main`.** Already visible above (Files Modified: all five new
  files are untracked; Deferred Work: no feature branch/commit/PR yet) — restated here explicitly as
  a governance deviation in its own right, the same class of deviation `T52`'s Problems Encountered
  recorded (subsequently closed for `T52` via PR #9/`baed936`; still open for `T53`).
  **Update (2026-08-08, Documentation Manager, T53 final closeout):** this gap has since closed —
  `git log` confirms `feature/stage3-t53-rbac-authorization` was branched, committed (`dd754f5`),
  opened as PR #10, and merged (`a103dca`); `main` and `origin/main` both verified at `a103dca`,
  working tree clean. Confirmed directly via `git show --stat a103dca`, not assumed. Recorded as a
  correction, not a silent edit to the paragraph above — the deviation was real at the time it was
  written and is described accurately here for how it was actually resolved, the same convention
  `T52`'s own Problems Encountered already used for its analogous branch/commit gap.

None of the four items above reflects a defect in `T53`'s actual code or tests — the Design
Decisions, Tests Added, and Test Results recorded above for this batch are accurate and
unchanged by this note; nothing here rewrites what was technically built or how it was verified. All
four are process/governance gaps, parallel to (not identical to) `T52`'s own three. **Items 1
(authorization not pre-recorded) and 2 (Backend Developer approval checkpoint skipped) remain
exactly as they happened — governance history, not erased by the branch/commit resolution above,
which only ever addressed item 3/4 (the git-action gap).** The QA Decision below was subsequently
rendered by the QA Reviewer role (**Approved with comments**) — preserved as written, not altered by
this update.

**T54 batch (2026-08-08, Documentation Manager reconciliation — repository-first, nothing rewritten,
nothing assumed):** three process/governance deviations and one important non-deviation, all stated
plainly.

1. **Project Manager authorization exists in conversation, not (yet, at the time implementation
   began) written into `IMPLEMENTATION_QUEUE.md`/`PROJECT_STATE.json`.** Real, not disputed — the
   third consecutive Stage 3 Phase 2 batch with this exact recording gap (`T52`, `T53`, now `T54`),
   despite two prior QA Decisions naming it explicitly as worth fixing. This pass corrects the
   *documentation*, not the underlying process; it is documented here after the fact, not backdated
   to claim otherwise.
2. **No `T54` batch entry existed in this phase log until this pass.** `T53`'s closeout had already
   moved this file's own `Status` to `Done`, `Completed: 2026-08-08` — this batch reopens it (see the
   metadata block) rather than starting a new file, per this project's own "one file per phase,
   appended to as it progresses" convention.
3. **`T54`'s two modified files (`deps.py`, `test_auth.py`) are uncommitted, directly on `main`.** No
   `feature/stage3-t54-*` branch exists. Same class of deviation `T52`/`T53` each carried and each
   eventually closed via a real branch → commit → PR → merge sequence — still open for `T54`.

**Not a deviation — stated explicitly because getting this wrong would misrepresent the record, not
because it's remarkable in itself:** **the Backend Developer role's `docs/prompts/BackendDeveloper.md`
§5 approval checkpoint (reconstruct state, summarize understanding, wait for explicit approval of
that summary before implementing) was performed for `T54` and received explicit approval before
implementation began.** This is the first Stage 3 Phase 2 batch where that checkpoint was actually
exercised — `T53`'s own QA Decision named its absence as "the most serious" of its four deviations
and called it "overdue for an actual fix rather than a third repetition." `T54` is that fix, on this
one item specifically. This fact rests on what was reported for this reconciliation, since a
conversation — like the authorization itself — leaves no independently-inspectable repository
artifact either way; it is recorded as given, not fabricated, and not silently omitted either.

Items 1 and 3 are process/governance gaps, not technical defects — the code and tests above are
unaffected by any of this, independently re-verified in Test Results, not merely transcribed. Item 2
is closed by this pass creating the batch entry itself. Items 1 and 3 remain open; this pass does not
correct them — no retroactive in-repository approval record predating implementation is inserted, and
no branch/commit/PR is created as part of a documentation reconciliation.

## Deferred Work

- **`T53`–`T57`** (`RbacAuthorizationService`, `RequirePermission` dependency, `configure_container()`
  wiring, `deps.py` update, Phase 2 tests) — not started, per `T52`'s own scope.
- **A feature branch, commit, and PR for `T52`'s existing code** — not created this pass. `T52`'s
  files remain untracked, uncommitted, directly on `main`. Trigger: the next session with explicit
  authorization to take git actions should branch, commit, and push this already-implemented, already
  independently QA-verified code before continuing to `T53`, so the deviation doesn't compound further.
  **Resolved (2026-08-08):** no longer deferred — see the corresponding update under Problems
  Encountered. `feature/stage3-t52-jwt-authentication` was branched, committed, opened as PR #9, and
  merged as `baed936`.

**T53 batch:**
- **`T54`–`T57`** (`RequirePermission` FastAPI dependency, `configure_container()` wiring for both
  `JwtAuthenticationProvider` and `RbacAuthorizationService`, `deps.py` update, Phase 2 tests
  exercising the full pipeline) — explicitly not started, per instruction to scope strictly to `T53`
  and its own tests.
- **A feature branch, commit, and PR for `T53`'s new code** — not created this batch (a git action;
  same posture as `T52`'s own log entries — implementation and self-assessment first, git actions
  only when separately authorized). **Resolved (2026-08-08):** no longer deferred —
  `feature/stage3-t53-rbac-authorization` was branched, committed (`dd754f5`), opened as PR #10, and
  merged (`a103dca`); see the corresponding update under Problems Encountered.
- **A `TestRolePermission` class in `tests/integration/test_identity_models.py`** (schema-level:
  FK/uniqueness constraints on the `role_permissions` table itself, matching `TestUser`/`TestRole`/
  `TestPermission`/`TestUserRole`/`TestRefreshToken`'s existing sibling coverage) does not exist —
  noticed while reading that file for pattern reference, predates `T53`, and is out of this batch's
  scope (it would test the `T49`-era model, not anything `T53` added). Flagged, not filled in.

**T54 batch:**
- **`T55`–`T57`** (`configure_container()` wiring for `JwtAuthenticationProvider`/
  `RbacAuthorizationService`, `deps.py`'s `CurrentUserDep` update for the new provider signature,
  Phase 2 tests exercising the full pipeline) — explicitly not started, per instruction to scope
  strictly to `T54`.
- **A feature branch, commit, and PR for `T54`'s changes** — not created this pass (a git action; the
  instruction under which this pass runs explicitly excludes it). Trigger: the next session with
  explicit authorization to take git actions should branch, commit, and push `deps.py`/`test_auth.py`'s
  changes, mirroring exactly how `T52` and `T53` each eventually closed this same gap.
- **No route anywhere in the app calls `RequirePermission(...)` yet.** Expected — no route exists to
  call it from (Stage 3 Phase 3, `T58`+); `RequirePermission` itself is proven correct in isolation
  (Test Results above), not integration-tested against a real endpoint, since no endpoint exists yet.

## Future Considerations

- Whoever picks up `T53` should also resolve the standing branch/commit gap for `T52` first (or
  alongside), rather than adding a second uncommitted batch on top of the first — see Deferred Work.
- `T55`'s `configure_container()` wiring is the first point at which `JwtAuthenticationProvider` needs
  a concrete resolution strategy for its per-request `UserRepository` dependency — the same
  request-scoped-construction question `Phase1.md` already flagged for `AuthService`.

**T53 batch:**
- `T55` is also the first point at which `RbacAuthorizationService` needs a real construction
  strategy: something must call `SqlAlchemyRolePermissionRepository(session).get_permission_codes_by_role_name()`
  and pass the result into `RbacAuthorizationService.__init__()`, per request (or on some caching/
  refresh policy — a real design question `T55` should answer deliberately, not inherit by default;
  `role_permissions` changes rarely relative to request volume, so an unconditional per-request reload
  may be wasteful, but that's a `T55`-scoped judgment call, not pre-decided here).
- `T54`'s `RequirePermission(...)` FastAPI dependency is the first real caller of
  `AuthorizationService.require_permission()` anywhere in the app — worth re-reading this batch's
  tests before building it, since they document the exact contract (`ForbiddenError` on both
  "unauthenticated" and "authenticated but unpermitted," never any other exception).
- `T66`'s `role_permissions` seed data (still gated on its own sign-off) is what will make
  `RbacAuthorizationService` meaningful end-to-end in the live app; until then, `T53`'s tests are the
  only thing exercising real grants.

**T54 batch:**
- Whoever picks up `T55` should also resolve the standing branch/commit gap for `T54` first (or
  alongside) — the same recommendation `T53`'s own Future Considerations made for `T52`, repeating
  because the underlying gap has now recurred a third time.
- `T58`+ (Phase 3 routes, e.g. `T62`'s user-management routes) are the first real callers of
  `RequirePermission(...)` in a router's `dependencies=[...]` list or a single route's own
  `Depends(...)` — worth re-reading this batch's tests before wiring it in, since they document the
  exact contract (forwards `(user, permission)` unchanged, raises `ForbiddenError` on denial, no
  other exception).
- The recurring authorization-recording gap (three consecutive batches: `T52`, `T53`, `T54`) is a
  process problem this project's own documentation keeps naming and re-naming rather than fixing.
  Whoever authorizes `T55` should write that authorization into
  `IMPLEMENTATION_QUEUE.md`/`PROJECT_STATE.json` *before* implementation begins — not because this
  reconciliation pass can enforce it, but because a fourth recurrence would no longer read as an
  isolated incident in any of these documents' own words.

**Authorization note, originally added 2026-08-10 by the Documentation Manager role — corrected the
same day, below, after QA review found its central provenance claim unprovable.** The paragraph this
replaces stated that `T55`'s authorization (and its subsequent architectural-clarification/expanded
scope) was "recorded in `IMPLEMENTATION_QUEUE.md`/`PROJECT_STATE.json` before any implementation
began." **That claim is corrected here, not silently removed — it cannot be substantiated and must
not stand as a repository fact:** the committed `HEAD` immediately before this correction still read
`T55` as "not started, not authorized"; the authorization/clarification text existed only in an
uncommitted working tree, alongside `T55`'s own implementation, with no commit-based evidence of
which came first. A documentation pass asserting "before implementation began" without a commit to
point to was an overclaim, not a verified fact — repeated here as its own governance lesson, not
just `T55`'s.

**The accurate account:** the project owner authorized `T55` — and, separately, the architectural
clarification and expanded scope described below — **conversationally**. Neither was recorded in a
**committed** repository state before implementation began. This is the **fourth** consecutive Stage
3 Phase 2 batch with this exact governance gap (`T52`, `T53`, `T54`, now `T55`) — the "fourth
recurrence" every one of the prior three batches' own QA Decisions warned about, materializing
despite the warning. It is historical and cannot be retroactively fixed by rewording it — only
disclosed accurately, the same way `T52`/`T53`/`T54`'s own authorization gaps are recorded above, not
erased.

**Original scope (as conversationally authorized):** the two `container.register(...)` replacements
in `configure_container()`. **Architectural clarification (also conversational, per the Backend
Developer's `docs/prompts/BackendDeveloper.md` §5 checkpoint):** that literal approach is technically
unworkable — `container.resolve()` is synchronous and zero-argument, but `JwtAuthenticationProvider`
needs a request-scoped `UserRepository` and `RbacAuthorizationService` needs an asynchronously-loaded
permission mapping, both backed by the current request's `AsyncSession` (`DBSessionDep`), which the
container has no mechanism to inject into a synchronous factory — confirming exactly the open
question this section's own T52/T53-batch bullets above already anticipated. **Expanded scope (also
conversational):** request-scoped `Depends()` construction in `presentation/api/deps.py`
(`DBSessionDep` → `SqlAlchemyUserRepository`/`SqlAlchemyRolePermissionRepository` → the real
provider/service), a fresh-per-request RBAC permission mapping with no caching/invalidation policy,
and conditional removal of the existing `Anonymous`/`Permissive` container registrations (confirmed
unused elsewhere by direct repository inspection during implementation — see Design Decisions below
— so removed, not merely preserved-and-documented). `T52`/`T53`/`T54`'s own implementation files,
`T56`, `T57`, and any route remain explicitly out of scope, and no scope creep into any of them was
found. See the `T55` batch immediately below for what was actually built against this scope.

## Tasks Implemented — T55 batch

- **T55 — request-scoped `AuthenticationProvider`/`AuthorizationService` construction.**
  `presentation/api/deps.py`'s `get_authentication_provider()`/`get_authorization_service()` now
  build `JwtAuthenticationProvider`/`RbacAuthorizationService` fresh per request, directly from
  `DBSessionDep`, instead of resolving them from the DI container. `infrastructure/di/container.py`'s
  two `container.register(AuthenticationProvider, ...)`/`container.register(AuthorizationService,
  ...)` lines are removed — confirmed unused anywhere else by direct repository inspection (see
  Design Decisions). No route, no `T52`/`T53`/`T54` file, no `T56`/`T57` content touched.

## Files Modified — T55 batch

- `backend/src/app/presentation/api/deps.py` — modified: `get_authentication_provider()` now
  `async`, takes `DBSessionDep`/`SettingsDep`, constructs `JwtAuthenticationProvider(
  SqlAlchemyUserRepository(session), settings)`; new `get_authorization_service()` constructs
  `SqlAlchemyRolePermissionRepository(session)`, awaits
  `get_permission_codes_by_role_name()`, and builds `RbacAuthorizationService` from the result.
- `backend/src/app/infrastructure/di/container.py` — modified: the two auth-port registrations
  removed, replaced with a docstring note explaining why (request-scoped construction can't go
  through a synchronous, zero-argument `resolve()`).
- `backend/tests/unit/test_auth.py` — modified: `TestConfigureContainer`'s test renamed/rewritten
  from asserting the container resolves the Stage 1 stub defaults to asserting the container no
  longer registers either port at all.
- `backend/tests/integration/test_auth_dependency_wiring.py` *(new)* — 6 tests against the real
  migrated schema, live Postgres.
- `docs/ImplementationLog/Stage3/Phase2.md` — this file.

No new dependency; no route file touched.

## Tests Added — T55 batch

6 in `backend/tests/integration/test_auth_dependency_wiring.py`:

`TestGetAuthenticationProvider` (3): resolves a real, active user through the full chain (token →
`JwtAuthenticationProvider` → `SqlAlchemyUserRepository` → DB) to a populated `CurrentUser`; **uses
the exact session it was given** — the specific property `T55` couldn't be a container registration
without losing; an unknown user id resolves to anonymous.

`TestGetAuthorizationService` (3): `require_permission()` reflects real `role_permissions` data
loaded through the real chain; denies a permission not granted to the caller's roles; **uses the
exact session it was given**, mirroring the authentication side's equivalent test.

Plus one existing unit test rewritten (not counted as new): `TestConfigureContainer`'s single test
now asserts `AuthenticationProvider`/`AuthorizationService` are *not* container-registered, replacing
an assertion that stopped being true the moment `T55` removed those registrations.

## Test Results — T55 batch

- New tests: `pytest tests/integration/test_auth_dependency_wiring.py -v` — 6/6 passing.
- Full backend suite: `uv run pytest -q` (Postgres reachable — `legal_dms_postgres` healthy) —
  **380 passed** (374 prior + 6 new), 0 failed, 0 skipped. Independently re-run by the Documentation
  Manager role during this reconciliation, not transcribed from QA's report alone.
- **Lint:** `uv run ruff check src tests alembic` — clean, re-verified directly.
- **Format:** `uv run black --check src tests alembic` — clean (192 files unchanged), re-verified
  directly.
- **Boot smoke test:** `python -c "from app.main import app"` — succeeds, re-verified directly.
- **Request-scoped session usage** — independently verified via
  `test_uses_the_exact_session_it_was_given` on both the authentication and authorization sides, the
  specific property that made a container registration architecturally wrong for this task.
- **Scope check:** direct `grep`/inspection of `container.py`, `deps.py`, and every `T52`/`T53`/`T54`
  file confirms no route, no unrelated file, and none of `T52`/`T53`/`T54`'s own implementation files
  were touched.

## Design Decisions — T55 batch

- **Request-scoped `Depends()` construction, not container registration** — the entire reason this
  batch needed an architectural clarification in the first place; see the corrected authorization
  note above for the full technical reasoning (`container.resolve()` is synchronous/zero-argument;
  both real providers need a request-scoped `AsyncSession`).
- **The obsolete `Anonymous`/`Permissive` container registrations were removed, not merely
  preserved-and-flagged** — the expanded authorization made removal conditional on confirming they're
  unused elsewhere; direct `grep` across `backend/src/` and `backend/tests/` found no remaining
  reference to either registration (the stub classes themselves are still imported and used directly,
  unregistered, by tests that construct them explicitly — only the container's registration of them
  is gone), so the condition was met and they were removed, documented in `container.py`'s own
  docstring rather than silently.
- **No caching/invalidation policy for the RBAC permission mapping** — exactly as the expanded
  authorization specified: loaded fresh on every request via
  `get_permission_codes_by_role_name()`. Not built now, not deferred as a promise — simply out of
  this batch's authorized scope.

## Problems Encountered — T55 batch

**The governance finding this reconciliation pass exists to record, stated plainly:** `T55`'s
authorization, its architectural clarification, and its expanded scope all originated in
conversation. **None of the three was recorded in a committed repository state before implementation
began.** This is the fourth consecutive Stage 3 Phase 2 batch to demonstrate this exact gap — `T52`,
`T53`, and `T54` each demonstrated it before, and each of their own QA Decisions explicitly warned
that a further recurrence would no longer read as an isolated incident. It didn't stay isolated. This
is not a technical defect — `T55`'s implementation is correct on the merits (see Test Results) — it
is a process/governance gap, the same category as `T52`/`T53`/`T54`'s own, and it is recorded here
the same way theirs were: honestly, without erasing the finding or claiming it was resolved
retroactively. A prior version of this section additionally overclaimed that the authorization *had*
been recorded before implementation began — that overclaim is itself corrected above, not repeated
here.

## Deferred Work — T55 batch

- **`T56`–`T57`** (`CurrentUserDep` update for the new provider signature; integration tests
  exercising valid/expired/malformed/tampered tokens end-to-end and 401/403 responses) — not started,
  per `T55`'s own scope.
- **A feature branch, commit, and PR for `T55`'s changes** — not created by this documentation
  reconciliation pass. **Resolved since:** `feature/stage3-t55-auth-wiring` → `86a3d5d`/`f070e28` →
  PR #15 → merged `b094436`; see the QA Decision (follow-up) section below.
- **A structural fix for the recurring authorization-recording gap** — named four times now
  (`T52`, `T53`, `T54`, `T55`) without ever being fixed as a process, only re-disclosed each time.
  Trigger: whoever owns this project's process definition should decide whether to add an actual gate
  (e.g., a phase log cannot exist without a linked, committed authorization commit) rather than
  relying on each batch's own documentation pass to remember to flag it.

## Future Considerations — T55 batch

- `T56`'s `CurrentUserDep` update is the next real consumer of this batch's
  `get_authentication_provider()` — already fully wired, so `T56` should be a small, mechanical
  change if the signature question it's scoped to answer stays narrow.
- `T57`'s integration tests are the first point the full pipeline (token → `CurrentUser` →
  `RequirePermission` → 403) gets exercised end-to-end; `test_auth_dependency_wiring.py`'s tests
  prove the two halves independently but not yet chained together through a real route, since no
  route exists yet.

## Reviewer Checklist — T55 batch

Self-assessed by the Documentation Manager role against the repository's actual current state, since
no separate Backend Developer self-assessment exists in the repository for this batch (the same
situation `T52`'s own Reviewer Checklist notes).

```
Reviewer Checklist

☑ Architecture preserved
☑ Existing design patterns followed
☑ Tests added
☑ Existing tests pass
☑ Documentation updated
□ ADR updated (if required)
□ AI_BOOTSTRAP updated (if required)
☑ PROJECT_STATE updated (if required)
☑ No unrelated refactoring
□ No scope creep
☑ Ready for QA
```

Notes on the less-obvious ones:

- **No scope creep:** `□` — left honestly unchecked. The *code* stayed exactly within the expanded
  authorization's boundary (verified above). What did not stay within any committed boundary is the
  authorization-recording process itself — the fourth recurrence recorded in Problems Encountered.
  Marking this `☑` would understate that.
- **Ready for QA:** `☑` — this log states every fact a reviewer would need: the technical scope, the
  test evidence, and the governance finding, all in one place.

## QA Decision — T55 batch

```
QA Decision (T55 batch)

□ Approved
□ Approved with comments
☑ Rework required
```

Rendered by the QA Reviewer role. **Technical review: no issues.** `T55`'s implementation is
technically correct — 380/380 full suite, 6/6 new integration tests, `ruff`/`black` clean, boot
succeeds, request-scoped session usage independently verified, no `T52`/`T53`/`T54`/`T56`/`T57`/route
scope creep. **`Rework required` is rendered on governance/process grounds only:** the working-tree
documentation, as it stood before this correction, claimed the expanded authorization was "recorded
here … before any implementation began" — a claim the committed repository state cannot support, since
`HEAD` immediately prior still read `T55` as unauthorized and nothing about the authorization was ever
committed. That claim must not stand as a repository fact and has been corrected (see the authorization
note and Problems Encountered above) to state plainly: authorization existed conversationally, but the
repository record was created/reconciled after implementation had already begun — the fourth
consecutive occurrence of this exact gap (`T52`, `T53`, `T54`, `T55`).

**This QA Decision belongs to the QA Reviewer role and is not altered by this Documentation Manager
pass** — it is transcribed here exactly as rendered, not re-judged, and is preserved unedited below
as the historical record of the process gate's first pass.

## QA Decision — T55 batch (follow-up, 2026-08-10)

```
QA Decision (T55 batch, follow-up)

□ Approved
☑ Approved with comments
□ Rework required
```

**Supersedes the `Rework required` decision above for the purpose of closeout** (that original
decision is preserved unedited above as the historical record — this is a new, separate, dated
entry, not a retroactive rewrite, the same convention `T52`'s and `T54`'s own follow-up decisions
already used). The branch/commit/PR gap has since closed:
`feature/stage3-t55-auth-wiring` → implementation commit `86a3d5d` → governance-reconciliation
commit `f070e28` → PR #15 → merged `b094436`; `main`/`origin/main` both verified at `b094436`.
Technical re-confirmation: 380/380 full suite, `ruff`/`black` clean, boot succeeds — unchanged since
the original decision, because nothing about the code changed between the two reviews.

**The authorization-not-pre-recorded governance finding is NOT resolved by this follow-up and is not
claimed to be.** It cannot be — the repository cannot retroactively acquire a commit that predates
`T55`'s implementation. It remains on permanent record as the **fourth** consecutive Stage 3 Phase 2
batch to demonstrate this exact gap (`T52`, `T53`, `T54`, `T55`), exactly as the original decision
above states. This follow-up closes the *git-provenance* gap (branch/commit/PR now exist) the same
way `T52`'s and `T53`'s follow-ups did — it does not, and could not, close the *authorization-timing*
gap, which is history, not a pending item.

**`T55` is now marked `Done`** — code, both QA decisions (original preserved, follow-up as final
disposition), and documentation are all reconciled. `T56`/`T57` remain untouched, unauthorized, not
started by this decision or this closeout.

## Reviewer Checklist — T52 batch

Self-assessed by the Documentation Manager role against the repository's actual current state, since
no separate Backend Developer self-assessment exists in the repository for this batch (see Problems
Encountered — this is itself part of the process gap being closed, not a new omission introduced
here).

```
Reviewer Checklist

☑ Architecture preserved
☑ Existing design patterns followed
☑ Tests added
☑ Existing tests pass
☑ Documentation updated
□ ADR updated (if required)
□ AI_BOOTSTRAP updated (if required)
☑ PROJECT_STATE updated (if required)
☑ No unrelated refactoring
☑ No scope creep
□ Ready for QA
```

Notes on the less-obvious ones:

- **Architecture preserved:** `JwtAuthenticationProvider` lives in `infrastructure/auth/`, implements
  `application/interfaces/auth.py`'s `AuthenticationProvider` port with no changes to the port itself,
  imports `UserRepository` (a port) rather than a concrete SQLAlchemy class directly — no layering
  violation found on direct inspection.
- **Existing design patterns followed:** matches `AnonymousAuthenticationProvider`'s shape (one class,
  one method, same port) and reuses `T50`/`AuthService`'s "never trust token claims for anything the
  database can answer fresher" pattern rather than inventing a different one.
- **Documentation updated:** *this* pass (`Phase2.md` created; `IMPLEMENTATION_QUEUE.md`,
  `PROJECT_STATE.json`, `docs/AI_HANDOVER.md`, `docs/SessionReport.md` synchronized) is what makes
  this box honestly checkable — it was not true before this session.
- **ADR updated (if required):** `□` — correctly not required. `ADR-0019` already records D7; this
  batch implements what's already decided.
- **AI_BOOTSTRAP updated (if required):** `□` — no non-negotiable rule or standing convention changed.
- **No scope creep:** `☑` for the *code* (exactly `T52`, nothing from `T53`+ touched) — but see
  Problems Encountered for the two process gaps (authorization-recording, phase-log timing) that are
  a different kind of deviation, not scope creep in the technical sense.
- **Ready for QA:** `□` — left unchecked deliberately. This checklist covers the documentation
  synchronization itself; whether the *process gate* (the three items QA originally found) is now
  satisfied is QA's independent judgment to render, not this role's to presume. The branch/commit
  deviation also remains genuinely open, not resolved — a reviewer should weigh that explicitly
  rather than see a checked box implying otherwise.

## QA Decision — T52 batch

```
QA Decision

□ Approved
☑ Approved with comments
□ Rework required
```

Rendered by the QA Reviewer role, 2026-08-08, re-reviewing the process gate specifically (not
`T52`'s underlying code/tests, which an earlier pass already independently confirmed technically
correct: 356/356 full suite, 11/11 new tests, ruff/black clean — see Test Results). The three
process findings that originally justified this log's now-superseded **Rework required** stand
individually as follows:

1. **Stale "not authorized" text in `IMPLEMENTATION_QUEUE.md`/`PROJECT_STATE.json`** — closed by
   this log's own creation and the documentation-synchronization pass that produced it.
2. **Missing `docs/ImplementationLog/Stage3/Phase2.md`** — closed; this file now exists, created
   during that same pass rather than left permanently absent.
3. **Undocumented direct-to-`main` implementation (no feature branch)** — accepted as
   disclosed-but-open at the time of this decision, per the precedent already established for the
   same class of deviation on the `T50`/`T51` batch (no revert, no rework, recorded and tracked
   instead). **Independently closed since**, not by any action this decision required: `git log`
   now shows `feature/stage3-t52-jwt-authentication` merged via PR #9 (`baed936`) — see the dated
   update under Problems Encountered/Deferred Work above.

**Comment (the reason this is "with comments," not a plain Approved):** the underlying failure mode
— an authorization or decision made in conversation, not written into the repository before or
during implementation — is worth naming explicitly so it doesn't recur for `T53`+: whoever
authorizes a task should ensure `IMPLEMENTATION_QUEUE.md`/`PROJECT_STATE.json` reflect that
authorization *before* implementation begins, the same discipline this project already applies to
QA Decisions themselves ("an honest unchecked box beats a falsely checked one").

No implementation rework required. `T53` remains unauthorized by this decision — this closes `T52`
only. Proceeding to the Documentation Manager's final closeout (`PROJECT_STATE.json`,
`docs/AI_HANDOVER.md`, `docs/Roadmap.md`, `IMPLEMENTATION_QUEUE.md`'s task table).

## Reviewer Checklist — T53 batch

Self-assessed by the Backend Developer role only, per `docs/prompts/BackendDeveloper.md` — this role
renders the Reviewer Checklist, never the QA Decision (see below).

```
Reviewer Checklist

☑ Architecture preserved
☑ Existing design patterns followed
☑ Tests added
☑ Existing tests pass
☑ Documentation updated
□ ADR updated (if required)
□ AI_BOOTSTRAP updated (if required)
□ PROJECT_STATE updated (if required)
☑ No unrelated refactoring
☑ No scope creep
☑ Ready for QA
```

Notes on the less-obvious ones:

- **Architecture preserved:** `RolePermissionRepository` lives in `application/interfaces/`
  (no SQLAlchemy import), `SqlAlchemyRolePermissionRepository` in `infrastructure/persistence/`,
  `RbacAuthorizationService` in `infrastructure/auth/` implementing `application/interfaces/auth.py`'s
  `AuthorizationService` port with **no change to the port itself** — its `require_permission()`
  signature is exactly as Stage 1 defined it. No layering violation found on direct inspection.
- **Existing design patterns followed:** narrow port + one concrete lookup method mirrors
  `UserRepository`/`RefreshTokenRepository`'s established shape (see Design Decisions for why this
  one isn't an `AbstractRepository[RolePermission]`); `RbacAuthorizationService` reuses
  `PermissiveAuthorizationService`'s exact anonymous-caller check rather than inventing a new one.
- **Tests added:** 13 new tests, first run required one fix (permission-code collision with seed
  data, not a design flaw — see Problems Encountered), then 13/13 passing.
- **Existing tests pass:** full suite re-run this batch — 369/369, 0 failed, 0 skipped.
- **Documentation updated:** this phase log, extended in place for the `T53` batch across all eleven
  sections (not just a summary appended at the end) — matches `Phase1.md`'s established multi-batch
  convention. `IMPLEMENTATION_QUEUE.md`/`PROJECT_STATE.json`/`docs/AI_HANDOVER.md` are explicitly
  **not** touched by this role this batch — per `docs/prompts/BackendDeveloper.md`'s documentation-
  ownership rules, those belong to the Project Manager/Documentation Manager roles, after a QA
  Decision exists for this batch.
- **ADR updated (if required):** `□` — correctly not required. No new architectural decision was
  made; `RolePermissionRepository` is a narrow port sized to one caller, the same category of
  addition `T50`'s two new ports already were without needing their own ADR.
- **AI_BOOTSTRAP updated (if required):** `□` — no non-negotiable rule or standing convention changed.
- **PROJECT_STATE updated (if required):** `□` — deliberately not this role's job this batch; belongs
  to the Documentation Manager, after QA.
- **No scope creep:** `☑` — exactly `T53` and its own tests, as explicitly approved; `T54`–`T57`
  (the `RequirePermission` dependency, `configure_container()` wiring, `deps.py`, Phase 2 integration
  tests) were not touched, matching the approval's explicit boundary.
- **Ready for QA:** `☑` — this log's Design Decisions section states every judgment call made (the
  narrow-port choice, the pre-loaded-snapshot-not-per-call-query choice, the reused anonymous-check,
  the absent-role-means-no-permissions choice) with reasoning, so a reviewer shouldn't need to ask
  why anything here looks the way it does.

## QA Decision — T53 batch

```
QA Decision

□ Approved
☑ Approved with comments
□ Rework required
```

Rendered by the QA Reviewer role, 2026-08-08, independently reconstructing repository state rather
than trusting the Backend Developer's or Documentation Manager's accounts (`git status`/`git log`
checked directly; `test_rbac_authorization_service.py` and
`test_sqlalchemy_role_permission_repository.py` re-run in isolation — 13/13; full suite re-run —
369/369, 0 failed, 0 skipped; `ruff`/`black` re-run clean; app boot re-verified; `container.py`,
`deps.py`, `main.py`, and `presentation/api/v1/` re-grepped directly to confirm `T54`–`T57` remain
untouched).

**Technical review (on the merits, independent of the process findings below):** `RolePermissionRepository`
is correctly narrow — one aggregate read method, not a misfitted `AbstractRepository[RolePermission]`
— for exactly the reason given in Design Decisions (nothing writes to `role_permissions` yet; `T66`
does). `SqlAlchemyRolePermissionRepository`'s join query and its five integration tests (re-run
directly against live Postgres) correctly prove role→permission-code grouping, including the
"ungranted role is absent, not mapped to an empty set" and "two roles sharing a permission each get
independent entries" cases. `RbacAuthorizationService` correctly reuses
`PermissiveAuthorizationService`'s anonymous-denial check verbatim (confirmed by reading both files
side by side) rather than reinventing it, and its 8 unit tests correctly separate
"`is_authenticated=False` is decisive regardless of `roles`" from "authenticated but no granting
role" from "role present but absent from the snapshot fails clean, not via `KeyError`" — the last one
independently verified by reading `RbacAuthorizationService.require_permission()`'s
`self._permission_codes_by_role_name.get(role, frozenset())` directly. The pre-loaded-snapshot
design (not a per-call query) is correctly justified by `AuthorizationService.require_permission()`
being a pre-existing synchronous port this batch doesn't touch. No layering violation, no scope
creep into `T54`–`T57`, no change to any existing port signature.

**Process/governance review — the four deviations named in this review's own instructions, taken in
turn, none hidden or softened:**

1. **Project-owner authorization existed only in conversation, not recorded in the repository before
   implementation.** Real, not disputed — same failure mode `T52`'s own QA Decision already named
   explicitly as worth avoiding going forward, and it recurred anyway one batch later. This is now
   the second consecutive batch with this exact gap, which matters more than either instance alone:
   a one-off is a slip, a repeat is a pattern that needs an actual process fix, not just another
   retrospective note. **Comment, not a blocker for this batch specifically** (the retrospective
   correction in `IMPLEMENTATION_QUEUE.md`/`PROJECT_STATE.json` is accurate and now in place) — but
   see the standing recommendation below.
2. **The Backend Developer approval checkpoint (`docs/prompts/BackendDeveloper.md` §5, steps 3–4)
   was skipped — new this batch, not present in `T52`'s set of deviations.** This is a materially
   different, and more concerning, gap than item 1: item 1 is a recording failure after a real
   authorization; this is the absence of the specific in-repository step whose entire purpose is to
   catch a scope misunderstanding *before* code is written, independent of whether the task itself
   was authorized. Verified directly against `docs/prompts/BackendDeveloper.md`: no
   summarize-understanding-and-wait-for-approval record exists anywhere in this batch's own account.
   That it happened to cause no harm this time (the implementation is precisely scoped to `T53`, per
   the technical review above) does not retroactively justify skipping the safeguard — a checkpoint
   whose absence is only ever discovered to be harmless after the fact isn't doing its job.
   **Flagged as the most serious of the four** — not because it changed this batch's outcome, but
   because unlike items 1/3/4 (which have a direct precedent of being accepted-then-resolved on the
   `T52` batch), this specific checkpoint has no such precedent of being waived, and letting it pass
   without comment here would make two skips look like an emerging norm.
3. **Implemented directly on `main`, no feature branch.** Same class of deviation as `T52`'s
   (accepted-as-disclosed-but-open there, subsequently closed independently via
   `feature/stage3-t52-jwt-authentication`/PR #9). Confirmed via `git status` — still open for `T53`.
4. **Currently uncommitted/untracked.** Direct consequence of item 3, confirmed the same way.

**Comment (why "with comments," not a plain `Approved`, and not `Rework required`):** the
implementation itself needs no changes — reverting or redoing working, correctly-scoped, thoroughly
tested code over a documentation/process gap would be pure churn, the same reasoning this project
already applied to `T52`. But items 3–4 are not yet resolved the way `T52`'s eventually were, so
**this batch is not yet cleared for the Documentation Manager's final closeout** — a real feature
branch, commit, and PR must exist first, mirroring exactly how `T52` actually closed (branch → commit
→ PR #9 → merge → *then* Phase2.md's `T52` section updated to `Status: Done`). Until that happens,
`T53` stays in its current state: technically approved, administratively open.

**Standing recommendation (repeated from `T52`'s own QA Decision, now overdue for an actual fix
rather than a third repetition):** whoever authorizes a task in conversation must write that
authorization into `IMPLEMENTATION_QUEUE.md`/`PROJECT_STATE.json` *before* implementation begins, and
the Backend Developer role must actually perform its §5 approval checkpoint rather than proceeding on
the task-level go-ahead alone. Two consecutive batches have now demonstrated the same class of gap;
a third should not happen.

No implementation rework required. `T53`'s code and tests stand as reviewed and approved on their
technical merits. Branch/commit/PR remain outstanding before this batch can be marked `Done` or
handed to the Documentation Manager — tracked here, not resolved by this decision, consistent with
this role's own git-action boundary.

## Reviewer Checklist — T54 batch

Self-assessed by the Documentation Manager role against the repository's actual current state, since
no separate Backend Developer self-assessment exists in the repository for this batch (see Problems
Encountered — the approval checkpoint was performed and approved, but no written self-assessment
artifact was left in the repository either way).

```
Reviewer Checklist

☑ Architecture preserved
☑ Existing design patterns followed
☑ Tests added
☑ Existing tests pass
☑ Documentation updated
□ ADR updated (if required)
□ AI_BOOTSTRAP updated (if required)
☑ PROJECT_STATE updated (if required)
☑ No unrelated refactoring
☑ No scope creep
□ Ready for QA
```

Notes on the less-obvious ones:

- **Architecture preserved:** `RequirePermission`/`get_authorization_service` live in
  `presentation/api/deps.py` alongside every other dependency resolver, calling `AuthorizationService`
  (a `T53` port) with no change to its `require_permission()` signature. No layering violation on
  direct inspection.
- **Existing design patterns followed:** a FastAPI parameterized-dependency factory, mirroring
  `get_authentication_provider()`'s existing resolver shape exactly rather than inventing a new one.
- **Tests added:** 5 new tests, independently re-run 5/5 passing — see Tests Added/Test Results.
- **Existing tests pass:** full suite independently re-run this pass — 374/374, 0 failed, 0 skipped.
- **Documentation updated:** this phase log (this T54 batch, across all eleven standard sections plus
  an Authorization/Scope note folded into Objective — see that section's note on why a twelfth
  heading wasn't added), `IMPLEMENTATION_QUEUE.md`, `PROJECT_STATE.json`, `docs/AI_HANDOVER.md`,
  `docs/Roadmap.md`, `docs/SessionReport.md` — all part of this same reconciliation pass.
- **ADR updated (if required):** `□` — correctly not required. No new architectural decision; `T54`
  implements what Stage 2.5's F11 and `docs/Stage3_Backend_Handoff.md` already specified.
- **AI_BOOTSTRAP updated (if required):** `□` — no non-negotiable rule or standing convention changed.
- **No scope creep:** `☑` — exactly `T54`; direct `grep` of `container.py`, `main.py`, and
  `presentation/api/v1/` confirms no `T53`/`T55`/`T56` file and no route was touched.
- **Ready for QA:** `□` — left unchecked deliberately, the same convention `T52`'s original entry
  used. QA has, in fact, already reviewed this batch (see QA Decision below) — but the checklist
  reflects this log's own documentation state at the point it's written, and the branch/commit gap
  remains genuinely open, not resolved by writing this checklist.

## QA Decision — T54 batch

```
QA Decision (T54 batch)

□ Approved
□ Approved with comments
☑ Rework required
```

Rendered by the QA Reviewer role, 2026-08-08 (reported for this reconciliation pass, transcribed
into the repository, not invented here — this Documentation Manager pass renders no new technical
QA decision, per its own instructions).

**Technical review: no issues.** `RequirePermission`'s implementation and its 5 tests are confirmed
correct — 5/5 new tests passing, 374/374 full suite, `ruff`/`black` clean, application boot succeeds,
no `T53`/`T55`/`T56`/route file touched. **No code changes are required.**

**Rework required is rendered on process grounds only — three findings, one explicit non-finding:**

1. **Authorization exists in the Project Manager conversation, not recorded in
   `IMPLEMENTATION_QUEUE.md`/`PROJECT_STATE.json` before implementation began.** The third
   consecutive Stage 3 Phase 2 batch with this exact gap (`T52`, `T53`, `T54`) — a pattern, not a
   one-off, as `T53`'s own QA Decision already warned.
2. **`docs/ImplementationLog/Stage3/Phase2.md` had no `T54` batch entry.** Unlike `T52` (where the
   whole file was missing) this file already existed, but nothing in it recorded `T54`'s
   implementation, tests, or design decisions until this reconciliation pass.
3. **`T54`'s changes exist directly on `main`, uncommitted, unbranched.** Same class of deviation
   `T52`/`T53` each carried and each eventually closed via a real branch → commit → PR → merge.
4. **Explicitly not a finding:** the Backend Developer role's `docs/prompts/BackendDeveloper.md` §5
   approval checkpoint **was performed and explicitly approved before implementation began** for this
   batch — confirmed distinct from `T53`, where it was skipped. This is the fix `T53`'s own QA
   Decision called "overdue," and it worked; recorded here so this batch isn't mistakenly assumed to
   carry the same deviation `T53` did.

**Comment:** this batch corrects finding 2 by existing (this log entry). Findings 1 and 3 remain open
— the same pattern `T52`/`T53` each went through: `Rework required` (or, for `T52`/`T53`,
"Approved with comments" once the phase log existed) until the branch/commit/PR gap actually closes,
at which point a final closeout pass can re-render the decision, mirroring exactly how `T52` and `T53`
each closed. **Until then, `T54` stays in its current state: technically correct, administratively
open, NOT marked `Done`.**

No implementation rework required — `T54`'s code and tests stand as reviewed and confirmed correct.

---

**Follow-up re-review (2026-08-10, QA Reviewer role) — the decision above is preserved verbatim, not
erased or rewritten.** The original `Rework required` was correct at the time it was rendered
(2026-08-08): findings 1–3 were real and open. This note records what has changed since, based on
independent re-verification of the repository, not on the remediation report alone.

**Independently re-verified this pass:**
- `git branch --show-current` — `main`; `git status` — clean.
- `git log` — `dbd6724` ("feat(auth): add RequirePermission dependency") exists as a real commit on
  `feature/stage3-t54-require-permission`, merged via PR #12 (`6396f6b`, "Merge pull request #12
  from Intelligentclown/feature/stage3-t54-require-permission"). Both `main` and `origin/main`
  independently confirmed at `6396f6b` via `git log`/`git rev-parse` — not assumed from the report.
- `git show --stat dbd6724` — confirms the commit contains exactly `T54`'s implementation
  (`presentation/api/deps.py`, `tests/unit/test_auth.py`) plus the expected documentation
  reconciliation files; no `T53`/`T55`/`T56` source file, no route file.
- Full suite re-run post-merge: **374/374 passing**, 0 failed, 0 skipped. `ruff`/`black` re-run
  clean. Direct grep of `container.py`/`main.py`/`presentation/api/v1/*.py` confirms
  `RequirePermission`/`get_authorization_service`/`RbacAuthorizationService`/`JwtAuthenticationProvider`
  are still absent from all of them — **`T55` has not started.**

**Disposition of the three original findings:**

1. **Authorization not recorded before implementation began.** Not something a later commit can
   retroactively fix — the recording either happened before implementation or it didn't, and for
   `T54` (as for `T52`/`T53` before it) it didn't. This remains true and is **not** being marked
   resolved; it stays on the record as governance history, exactly as findings 1/2 on the `T52` and
   `T53` QA Decisions above were preserved rather than erased once those batches closed out. It is
   not, on its own, a reason to withhold approval now that the git-provenance gap (finding 3, below)
   has closed for real — the same judgment already applied twice in this same log.
2. **`Phase2.md` had no `T54` batch entry.** Resolved — this file now contains the full `T54` batch
   (Objective, Tasks Implemented, Files Modified, Tests Added, Test Results, Design Decisions,
   Problems Encountered, Reviewer Checklist, and this QA Decision itself).
3. **`T54`'s changes existed directly on `main`, uncommitted, unbranched.** Resolved, and verified
   independently rather than accepted on the strength of the report:
   `feature/stage3-t54-require-permission` → `dbd6724` → PR #12 → merged `6396f6b`, confirmed by
   direct `git log`/`git rev-parse`/`git show`, matching exactly how `T52`'s and `T53`'s equivalent
   findings closed.

**Distinguishing what was and wasn't a code defect, since the two are easy to conflate after a
process rework:** at no point across the original review or this follow-up did any test fail, any
lint check fail, or any technical/architectural defect surface. `Rework required` was rendered, and
is now being superseded, entirely on process/governance grounds — the implementation itself was never
in question and required no changes at either point.

## QA Decision — T54 batch (follow-up, 2026-08-10)

```
QA Decision (T54 batch, follow-up)

□ Approved
☑ Approved with comments
□ Rework required
```

**Supersedes the `Rework required` decision above for the purpose of closeout** (that original
decision is preserved unedited above as the historical record — this is a new, separate, dated
entry, not a retroactive rewrite). Findings 2 and 3 are resolved and independently confirmed; finding
1 remains open as permanent governance history, consistent with how the identical class of finding
was handled on `T52`'s and `T53`'s own QA Decisions. `T54`'s code and tests were correct throughout
and required no changes at any point in this process. **`T54` is now cleared for the Documentation
Manager's closeout** (marking it `Done` in `IMPLEMENTATION_QUEUE.md`, updating this file's metadata
block's `Git Commit`/`Pull Request`/`Status`/`Completed` fields) — not performed by this QA pass,
consistent with this role's own boundary against project-management-document/git actions.

**Standing comment, carried forward unchanged from `T52`/`T53`:** authorization given in conversation
must be written into the repository before implementation begins, not reconstructed afterward. `T54`
is the third consecutive batch to demonstrate the recording half of this gap — but it is also the
first to demonstrate the fix already called for on the Backend Developer checkpoint half (`§5` was
actually performed and approved this time). Progress, not full resolution: the recording gap itself
still needs an actual process fix, not a fourth acknowledgment.

`T55` was not started, authorized, or touched by this review. No implementation code, test, or
project-management document (`IMPLEMENTATION_QUEUE.md`, `PROJECT_STATE.json`) was modified as part of
rendering this follow-up decision — only this phase log's own QA Decision section, which is this
role's to render per `docs/ImplementationLog/README.md`.

*The sentence immediately below is the closing line of the original (2026-08-08) `Rework required`
decision above, preserved verbatim as part of that historical record — not deleted, not edited. It
describes the state as of that original decision, before the branch/commit/PR gap closed. It is
**superseded** by the follow-up decision's own disposition of finding 3 (resolved, independently
verified) immediately above this note. Flagged here rather than silently left to read as if it still
described the current state.*

Branch/commit/PR remain outstanding before this batch can be marked `Done` or proceed past this
reconciliation — tracked here, not resolved by this decision, consistent with the Documentation
Manager role's own git-action boundary (no branch, commit, or push performed as part of this pass).

**Documentation Manager closeout (2026-08-10):** the follow-up decision above clears `T54` for
closeout. This phase log's metadata block (`Status`, `Completed`, `Git Commit`, `Pull Request`) has
been updated accordingly — see the top of this file. `T54` is now marked `Done` in
`IMPLEMENTATION_QUEUE.md`/`PROJECT_STATE.json`, per the Developer/QA record here, mirroring exactly
how `T52`/`T53` each closed. `T55` remains unauthorized and unstarted.
