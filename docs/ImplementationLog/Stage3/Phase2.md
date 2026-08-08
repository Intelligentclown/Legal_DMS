------------------------------------------------

# Stage 3 – Phase 2

Status: In Progress

Started: 2026-08-08

Completed:

Related Tasks: T52, T53

Related ADRs: ADR-0019

Git Commit: T52 — baed936 (merge; feature commit 003ab15). T53 — not yet committed.

Pull Request: T52 — #9. T53 — not yet opened.

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

None of the four items above reflects a defect in `T53`'s actual code or tests — the Design
Decisions, Tests Added, and Test Results recorded above for this batch are accurate and
unchanged by this note; nothing here rewrites what was technically built or how it was verified. All
four are process/governance gaps, parallel to (not identical to) `T52`'s own three. This pass does
not correct them — no branch/commit/PR is created, no retroactive in-repository approval record
predating implementation is inserted, and the QA Decision below stays unrendered pending an actual
QA Reviewer pass that will need to weigh all four.

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
  only when separately authorized).
- **A `TestRolePermission` class in `tests/integration/test_identity_models.py`** (schema-level:
  FK/uniqueness constraints on the `role_permissions` table itself, matching `TestUser`/`TestRole`/
  `TestPermission`/`TestUserRole`/`TestRefreshToken`'s existing sibling coverage) does not exist —
  noticed while reading that file for pattern reference, predates `T53`, and is out of this batch's
  scope (it would test the `T49`-era model, not anything `T53` added). Flagged, not filled in.

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
