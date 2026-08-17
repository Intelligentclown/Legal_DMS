------------------------------------------------

# Stage 4 - Phase 0

Status: In Progress

Started: 2026-08-17

Completed:

Related Tasks: T66, T67

Related ADRs: ADR-0018 (D4)

Git Commit: T66 — `2edc23e`. T67 — pending (feature branch `feature/stage4-t67-first-admin-bootstrap`
pushed; no PR opened yet — Backend Developer role stops here per this batch's stop condition, QA
review happens in a separate session).

Pull Request: T66 - #44. T67 — not yet opened.

Release:

------------------------------------------------

**Correction (T67 batch, 2026-08-17):** the metadata block above previously read `Status: Done` /
`Completed: 2026-08-17` once T66 merged — accurate at the time, since T66 was this phase's only
task in flight. `Related Tasks` always included `T67`/`T68` in `IMPLEMENTATION_QUEUE.md`'s Phase 4
row, so the phase itself was never actually finished; `Status`/`Completed` are corrected back to
`In Progress`/blank here, not silently left wrong, now that `T67`'s implementation begins in this
same phase.

## T66 Batch: Seed Role Permissions

**Authorization / Scope:** The project owner explicitly authorized T66 (exact matrix sign-off: Administrator, Advocate, Paralegal, Clerk, Accountant, Read Only). Authorized in `IMPLEMENTATION_QUEUE.md` before implementation began.

## QA Decision — T66 batch

```
QA Decision (T66 batch)

☑ Approved
□ Approved with comments
□ Rework required
```

Rendered by the QA Reviewer role, independently, against PR #44 (`feature/stage4-t66-seed-role-permissions`). **PR #44 is not merged; this decision is recorded pre-merge.**

**Governance history, preserved not collapsed:**
- T66 authorization preceded implementation.
- Implementation: seeded `role_permissions` based on the approved matrix.
- QA findings/rework: initial QA review resulted in substantive findings which were resolved.
- Formatting correction: applied `black` and `ruff` to the migration and tests.
- Final QA approval: this decision follows the resolved findings and formatting pass.

**Verification Results:**
- **Authorization:** T66 authorization preceded implementation.
- **Scope:** Exact authorized scope is respected. T67 remains unauthorized and untouched.
- **Migration Graph:** The migration graph is valid. Exactly one Alembic head exists: `224b650e5235`.
- **Matrix Seeding:** The migration correctly seeds exactly 59 authorized `role_permission` associations. UUIDs are dynamically resolved from existing roles/permissions.
- **Downgrade Safety:** Downgrade removes only T66-created associations and preserves unrelated associations.
- **Validation Tests:** Exhaustive T66 matrix validation tests are present and effective. T63/T65 regression behavior is preserved.
- **Lint/Format:** `black` passes, `ruff` passes.

**No technical defects found in the PR scope.** This is an `Approved` disposition. PR #44 is approved for merge but was NOT merged at the time of this decision.

## Post-Merge Verification - T66 batch (2026-08-17)

**Verified directly on `main` at `2edc23e`:**
- `main` and `origin/main` are synchronized at `2edc23e`.
- T66's exact authorized 59-entry role-permission matrix is successfully seeded via migration `224b650e5235`.
- Exactly one Alembic head exists.
- Safe targeted downgrade holds.
- Exhaustive matrix validation tests are passing.
- Black is clean. Ruff is clean.
- T66 tests passing and relevant regression tests passing.
- T67 remains completely unauthorized and not started.

**T66 is now Done - merged.**
- Authorization commit: `66f94bf` (PR #43)
- Implementation commit: `533226d`
- QA rework commit: `b2b86b6`
- Formatting correction commit: `0239d80`
- QA-approval commit: `5ab88a5`
- Merge commit: `2edc23e` (PR #44)

## Objective — T67 batch

First-admin bootstrap: a one-time CLI command that checks whether any `User` row already exists
and, if none does, interactively prompts for an email and a password (via `getpass`, never
argv/env/a config file per approved D4), hashes the password with the existing `hash_password()`
(T46), and creates exactly one `User` assigned the seeded `Administrator` role (T66's matrix — this
batch only assigns the role, it does not touch `role_permissions`). Idempotent: a second run once a
user exists prints a clear message and exits cleanly, no error, no duplicate admin.

**Authorization / Scope (recorded before implementation, `PROJECT_STATE.json`/
`IMPLEMENTATION_QUEUE.md`, T67 row, merge `65b737a`/PR #46, 2026-08-17):** the project owner
explicitly authorized T67. Approved scope, verified directly against `git log`/`git show 65b737a`
before any implementation began, not assumed from prior conversation: a one-time CLI command,
registered via a new `backend/pyproject.toml` `[project.scripts]` entry (no such section existed
before this batch); placed wherever fits this codebase's existing layout; checks whether any `User`
row already exists; if none, interactively prompts for an email and a password via `getpass`; hashes
the password using the existing `hash_password()` (T46); creates exactly one `User` assigned the
`Administrator` role; idempotent on re-run; includes tests. `T68` (seed-count/bootstrap-idempotency
test coverage, depends on this task) is explicitly out of scope and unauthorized — not implemented
as part of this batch. No change to any existing route, schema, `deps.py`, `AuthService`, or any
`T52`–`T66` file beyond the new CLI module and `pyproject.toml`'s new `[project.scripts]` entry.

## Tasks Implemented — T67 batch

- `T67`: `infrastructure/cli/bootstrap.py` (new) — `run_bootstrap(session, *, email, password)`, the
  testable core: returns `None` (no-op) if any `User` row already exists, otherwise looks up the
  seeded `Administrator` role by name, creates the `User` with `hash_password()`'s output, assigns
  the role via `UserRole` (self-attributed, `assigned_by=user.id`, since no other actor exists at
  bootstrap time), flushes (never commits — the caller owns the transaction boundary, mirroring
  `SqlAlchemyUserRepository`'s existing convention). `main()`/`_async_main()` — the actual process
  entry point: opens its own session via the existing `get_session_factory()`, checks for an
  existing user before prompting (so it never asks for credentials it's about to discard), prompts
  for email via `input()` and password via `getpass.getpass()`, calls `run_bootstrap()`, commits on
  success, and prints a one-line outcome message either way.
- `backend/pyproject.toml`: added `[project.scripts]` with `bootstrap-admin =
  "app.infrastructure.cli.bootstrap:main"` — the section did not exist before this batch, exactly as
  the approved scope anticipated.

## Files Modified — T67 batch

- `backend/src/app/infrastructure/cli/__init__.py` (new, empty — package marker, matching every
  other `infrastructure/*` subpackage's convention)
- `backend/src/app/infrastructure/cli/bootstrap.py` (new)
- `backend/pyproject.toml` (modified — new `[project.scripts]` table only)
- `backend/tests/integration/test_bootstrap_admin.py` (new)
- `docs/ImplementationLog/Stage4/Phase0.md` (this file)

No other file touched — confirmed via `git status`/`git diff --stat` against `main` before writing
this section, not reconstructed from memory. In particular: no route, no schema/migration, no
`deps.py`, no `AuthService`, no `T52`–`T66` file.

## Tests Added — T67 batch

All in `backend/tests/integration/test_bootstrap_admin.py`, against the real migrated schema via the
shared `db_session` fixture (`tests/conftest.py`) — everything rolled back in teardown:

- `TestRunBootstrapNoExistingUser::test_creates_admin_with_hashed_password` — with zero existing
  users, `run_bootstrap()` creates a `User` whose `password_hash` is neither the plaintext password
  nor equal to it, and `verify_password()` confirms it actually matches.
- `TestRunBootstrapNoExistingUser::test_assigns_administrator_role` — the created user's roles
  (queried via the same `Role`/`UserRole` join `get_role_names()` uses elsewhere) are exactly
  `["Administrator"]`.
- `TestRunBootstrapNoExistingUser::test_creates_exactly_one_user` — exactly one `User` row exists in
  the database afterward.
- `TestRunBootstrapExistingUser::test_returns_none_without_creating_duplicate` — with one existing
  user already in the database, `run_bootstrap()` returns `None` and the `User` count stays at
  exactly one (no second admin created, no exception raised).
- `TestRunBootstrapExistingUser::test_does_not_touch_existing_user` — the pre-existing user's row is
  unmodified after a `run_bootstrap()` call that no-ops.

Directly satisfies both of the approved scope's named test requirements: "no existing user -> admin
created correctly with hashed password and Administrator role" and "an existing user -> command
exits cleanly without creating a duplicate."

## Test Results — T67 batch

- `uv run pytest tests/integration/test_bootstrap_admin.py -v` — 5/5 passing, personally run against
  live Postgres this session (`legal_dms_postgres` container, confirmed healthy via `docker ps`
  before running).
- `uv run pytest` (full suite) — **487/487 passing** (0 failed, 0 skipped). Baseline immediately
  before this batch's test file: 482/482 (confirmed by re-running with
  `--ignore=tests/integration/test_bootstrap_admin.py`) — one higher than `PROJECT_STATE.json`'s
  last recorded full-suite count of 481; this pre-existing one-test drift predates this batch (not
  introduced by it) and is disclosed here rather than silently reconciled, since reconciling
  `PROJECT_STATE.json` is the Documentation Manager's role, not this one's.
- `uv run ruff check src tests alembic` — clean (one `F401` unused-import finding in the new test
  file was caught and fixed during this batch, not left for QA).
- `uv run black --check src tests alembic` — clean, 204 files unchanged.
- **Disclosed, not verified in this environment:** an actual interactive run of `uv run
  bootstrap-admin` via piped stdin (`printf 'email\npassword\n' | uv run bootstrap-admin`) was
  attempted as a manual smoke test against the local dev database (`legal_dms_dev`, confirmed empty
  — 0 users — beforehand). The process hung at the `input()` prompt rather than consuming the piped
  input, which this session's tooling then had to terminate by process id; the dev database was
  re-verified empty (0 users) afterward, so no partial/malformed row was left behind. This reads as
  a limitation of piping stdin through this sandboxed session's background-process plumbing on
  Windows, not a defect in `main()`/`_async_main()` itself — `input()`/`getpass.getpass()` are
  unmodified stdlib calls, and the logic they feed (`run_bootstrap()`) is independently proven by
  the 5 passing integration tests above. Recorded here per this project's "disclose what couldn't be
  verified, don't present it as passing" testing rule; a real interactive terminal run is the
  natural follow-up the next session (or the project owner) can do directly.

## Design Decisions — T67 batch

- **`run_bootstrap()`/`main()` split.** The approved scope's two testable requirements ("no existing
  user -> admin created correctly," "existing user -> exits cleanly, no duplicate") are both pure
  database logic with no dependency on an actual terminal. Splitting them from the `input()`/
  `getpass()`/session-factory/commit/print concerns lets the tests exercise the real logic against
  live Postgres without mocking stdin — the same "core logic is a plain function, the entry point is
  a thin wrapper" shape already established by this project's routes (e.g. `users.py`'s handlers
  delegate to `BaseService`/the repository rather than embedding logic inline).
- **`full_name` default.** `User.full_name` is a required, non-nullable column, but the approved
  scope only authorizes prompting for email and password — no third interactive prompt was added
  (would exceed the literal "prompts for an email and a password" scope). `full_name` is set to the
  literal string `"Administrator"`, a reasonable placeholder for a bootstrap-created account; nothing
  prevents it being edited later via `T62`'s existing `PUT /api/v1/users/{id}`.
- **`flush()`, not `commit()`, inside `run_bootstrap()`.** The caller owns the transaction boundary —
  mirrors `SqlAlchemyUserRepository.assign_role()`/`remove_role()`, which also only `flush()`;
  `get_db()`/`main()` are what actually commit, exactly as ADR-0020 already establishes for the
  request-scoped case.
- **Role lookup by name, not a new repository method.** `run_bootstrap()` queries
  `Role.name == "Administrator"` directly via the session it's given, the same way
  `users.py`'s `get_role_repository()` already reaches for the existing generic
  `SqlAlchemyRepository[Role]` rather than inventing a `Role`-specific repository for one lookup —
  no new repository class or port method was added for this single, CLI-only query.
- **`assigned_by=user.id` (self-assignment).** `UserRole.assigned_by` is nullable, but at bootstrap
  time no other user/admin exists to attribute the assignment to; self-attribution is the only
  option consistent with the column's existing FK-to-`users` shape without adding a new nullable
  case the column doesn't already support.
- **Missing-role guard raises, doesn't silently create a `Role`.** If no `Administrator` role is
  found (e.g. `T66`'s/the earlier seed migration hasn't run), `run_bootstrap()` raises `RuntimeError`
  with a message pointing at `alembic upgrade head`, rather than creating an ad hoc role row — this
  CLI's job is to bootstrap the first *user*, not to seed roles (that's the seed migrations'
  territory), so failing loudly and directing the operator to run migrations first is the correct
  failure mode, not a silent workaround.

## Problems Encountered — T67 batch

- A manual interactive smoke test of `uv run bootstrap-admin` (piped stdin) hung and had to be
  terminated by process id — see Test Results above for the full account and why this doesn't
  indicate a code defect.
- `ruff` initially flagged an unused `pytest` import in the new test file (a leftover from an earlier
  draft that used `@pytest.fixture`/`pytest.mark` before the tests were simplified to plain `async
  def` functions under `asyncio_mode = auto`) — caught and fixed before this batch's checks were
  reported clean, not left for QA to find.

## Deferred Work — T67 batch

- `T68` (seed-row-count and bootstrap-idempotency test coverage as its own task) — explicitly out of
  scope per this batch's authorization; trigger: `T68`'s own authorization, once granted.
- A real interactive terminal verification of `uv run bootstrap-admin` (see Test Results' disclosed
  limitation above) — trigger: next session with direct terminal access, or the project owner running
  it themselves once this branch is reviewed.

## Future Considerations — T67 batch

- Once this CLI is actually run against a real deployment, `T62`'s `PUT /api/v1/users/{id}` is the
  existing route for correcting the bootstrap admin's `full_name`/`email`/`phone` afterward — no new
  route is needed for that.
- This batch does not address what happens if `bootstrap-admin` is run before migrations (no `users`/
  `roles` tables yet) — the resulting `ProgrammingError`/connection failure is an unhandled stdlib/
  SQLAlchemy exception, not a friendly message. Not raised as a defect (the approved scope doesn't
  ask for it, and every other one-time operational script in this project — e.g. `alembic` itself —
  has the same expectation that migrations run first), but worth a friendlier error message if this
  CLI ever becomes a documented part of a deployment runbook.

## Reviewer Checklist — T67 batch

```
Reviewer Checklist (T67 batch)

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

- **Architecture preserved:** no port/contract changed; no Clean Architecture layering violated —
  `infrastructure/cli/bootstrap.py` sits in the infrastructure layer alongside `infrastructure/auth/`,
  `infrastructure/persistence/`, etc., and depends only on existing ports/concrete infrastructure
  (`get_session_factory()`, `hash_password()`, the `User`/`Role`/`UserRole` models) the same way
  `presentation/api/v1/users.py` already does.
- **Existing design patterns followed:** password hashing via the existing plain-function
  `hash_password()` (T46, unmodified); role/user creation shape mirrors `users.py`'s `create_user()`/
  `assign_role()` (construct the model, `session.add()`, `flush()`); repository-layer transaction
  discipline (`flush()`, not `commit()`) mirrors `SqlAlchemyUserRepository`.
- **Tests added:** 5 new tests, both approved-scope requirements directly covered — see Tests Added
  above.
- **Existing tests pass:** full suite 487/487 (482 prior + 5 new), personally re-run against live
  Postgres this session — see Test Results above.
- **Documentation updated:** this phase log entry. `AI_BOOTSTRAP.md`/`PROJECT_STATE.json` are left to
  the Documentation Manager per this role's ownership boundary (see the two unchecked boxes below) —
  not out of oversight.
- **ADR updated (if required): □** — no new architectural decision; this batch implements ADR-0018's
  already-approved D4 exactly as designed, it doesn't decide anything new.
- **AI_BOOTSTRAP updated (if required): □** — no non-negotiable rule, required-reading order, or
  standing convention changed; out of this role's ownership boundary regardless (Documentation
  Manager, per `PROJECT_WORKFLOW.md` §8).
- **PROJECT_STATE updated (if required): □** — T67's status/test counts/completion percentage belong
  to `PROJECT_STATE.json`, owned by the Documentation Manager, only after a QA Decision exists — not
  touched by this role, per `docs/prompts/BackendDeveloper.md` §5/§8's explicit "never synchronize
  project-wide documentation" boundary.
- **No unrelated refactoring:** no `T52`–`T66` file touched; no existing route/schema/`deps.py`/
  `AuthService` file touched, exactly as the approved scope requires.
- **No scope creep:** `T68` not implemented, as explicitly instructed; no password-confirmation
  second prompt, no reactivation/deletion/search, no additional interactive prompts beyond email and
  password.
- **Ready for QA:** this log entry plus `git diff main...feature/stage4-t67-first-admin-bootstrap`
  should let a QA Reviewer verify the batch without needing clarifying questions.

## QA Decision — T67 batch

```
QA Decision (T67 batch)

□ Approved
□ Approved with comments
□ Rework required
```

Not yet rendered — left for the QA Reviewer role in a separate session, per this batch's own stop
condition (Backend Developer role stops after implementation and self-assessment; does not render
the QA Decision, open a PR, or proceed further).
