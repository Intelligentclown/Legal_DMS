------------------------------------------------

# Stage 4 - Phase 0

Status: In Progress

Started: 2026-08-17

Completed:

Related Tasks: T66, T67, T68

Related ADRs: ADR-0018 (D4)

Git Commit: T66 — `2edc23e`. T67 — `fc0b142` (merge; feature commit `b409f78`; QA-approval commit
`790b778`; authorization commit `119d612`). T68 — pending (feature branch
`feature/stage4-t68-bootstrap-entrypoint-tests` pushed; no PR opened yet — Backend Developer role
stops here per this batch's stop condition, QA review happens in a separate session).

Pull Request: T66 - #44. T67 — #47 (merged `fc0b142`, 2026-08-18; post-merge closeout #48, merge
`f0c9b34`). T68 — not yet opened.

Release:

------------------------------------------------

**Correction (T67 batch, 2026-08-17):** the metadata block above previously read `Status: Done` /
`Completed: 2026-08-17` once T66 merged — accurate at the time, since T66 was this phase's only
task in flight. `Related Tasks` always included `T67`/`T68` in `IMPLEMENTATION_QUEUE.md`'s Phase 4
row, so the phase itself was never actually finished; `Status`/`Completed` are corrected back to
`In Progress`/blank here, not silently left wrong, now that `T67`'s implementation begins in this
same phase.

**Correction (T68 batch, 2026-08-18):** the metadata block's `Git Commit`/`Pull Request` fields for
`T67` still read "pending" going into this batch, even though `T67` merged (`PR #47`, `fc0b142`,
2026-08-18) and was closed out (`PR #48`, `f0c9b34`) before this session began — that closeout
updated `PROJECT_STATE.json`/`IMPLEMENTATION_QUEUE.md`/the changelogs but never came back to fill in
this file's own metadata block or add a `T67` Post-Merge Verification section. Corrected here, not
silently left stale, per this project's "trust the code, report the discrepancy" discipline —
verified directly via `git log`/`git show fc0b142`, not assumed. `Related Tasks` now also includes
`T68`.

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
☑ Approved with comments
□ Rework required
```

Rendered by the QA Reviewer role, independently, against feature commit `b409f78`
(`feature/stage4-t67-first-admin-bootstrap`) — no PR opened yet; this decision is recorded
pre-PR, per this project's practice of committing the QA Decision to the branch before any PR is
opened or merged.

**Verification Results (all checked directly against the repository and a live run, not taken from
the Developer's self-assessment):**

- **Authorization:** T67 authorization (`IMPLEMENTATION_QUEUE.md` row, `PROJECT_STATE.json`) is
  recorded before the implementation commit — confirmed by commit order (`119d612` precedes
  `b409f78`).
- **Scope:** `git diff main...feature/stage4-t67-first-admin-bootstrap --stat` independently
  confirms exactly five files changed: `backend/pyproject.toml` (new `[project.scripts]` table
  only), `backend/src/app/infrastructure/cli/__init__.py` (new, empty), `backend/src/app/
  infrastructure/cli/bootstrap.py` (new), `backend/tests/integration/test_bootstrap_admin.py`
  (new), and this phase log. No route, schema/migration, `deps.py`, `AuthService`, or any
  `T52`–`T66` file touched. `T68` is not implemented. Matches the approved scope in
  `IMPLEMENTATION_QUEUE.md`'s T67 row and `ADR-0018`'s D4 exactly — no scope creep, no
  untouched-file violation.
- **D4 compliance (password never via argv/env/file):** verified by reading
  `infrastructure/cli/bootstrap.py` directly, not by trusting the docstring's claim. The password is
  read exclusively via `getpass.getpass()`; the file contains no `sys.argv`, `os.environ`, or config
  file access anywhere. Genuinely satisfies D4, not merely asserted.
- **Idempotency:** genuinely proven, at the `run_bootstrap()` level, by two non-vacuous tests —
  `test_returns_none_without_creating_duplicate` (existing user present → returns `None`, user count
  stays at exactly 1) and `test_does_not_touch_existing_user` (existing row unmodified) — both would
  fail if the no-op guard were removed or broken. **Gap, disclosed not hidden:** these tests exercise
  `run_bootstrap()` only; the full CLI-level second-invocation behavior (`main()` prints a message
  and exits cleanly with no error) is not exercised by any automated test. The phase log's own Test
  Results/Deferred Work sections already disclose this — a manual interactive smoke test hung under
  piped stdin and had to be killed. Not hidden or presented as passing; noted here as a real,
  disclosed verification gap, not a defect.
- **Tests — independently re-run this session:** `uv run pytest tests/integration/
  test_bootstrap_admin.py -v` → 5/5 passing. `uv run pytest` (full suite) → 487/487 passing.
  `uv run ruff check src tests alembic` → clean. `uv run black --check src tests alembic` → clean,
  204 files unchanged. All four independently reproduced against the live `legal_dms_postgres`
  container, not taken on the Developer's word.
- **Architecture:** `infrastructure/cli/bootstrap.py` sits in the infrastructure layer alongside
  `infrastructure/auth/`, `infrastructure/persistence/`; no port/contract changed; no layering
  violation.
- **Edge cases the tests miss (non-blocking, recorded as comments):**
  1. `run_bootstrap()` re-implements user creation and role assignment by hand
     (`session.add()`/`flush()`) instead of reusing `AbstractRepository[User].add()` and, notably,
     `UserRepository.assign_role()` — both already exist on `SqlAlchemyUserRepository` and do the
     identical job. `assign_role()` additionally catches `IntegrityError` from a concurrent
     duplicate-assignment race, a safety net the hand-rolled version lacks. Functionally immaterial
     here (bootstrap always operates on a brand-new `user_id`, so the `(user_id, role_id)` pair
     cannot collide), but a real, minor divergence from this codebase's established repository-layer
     convention for user/role mutations — not what the Design Decisions section's "mirrors
     `SqlAlchemyUserRepository`'s existing convention" claim would suggest to a reader expecting
     actual reuse.
  2. The `RuntimeError` guard for "no `Administrator` role found" (migrations not yet run) has zero
     test coverage. Not required by the approved scope's two named test requirements, and the
     Future Considerations section already flags the adjacent pre-migration failure mode as a known
     gap — but this specific guard clause is untested code, worth closing if this file is touched
     again.
- **Out of scope for this review:** the working tree also carries an unrelated modified
  `docs/prompts/README.md` and untracked `docs/HANDOFF/`/`docs/prompts/GitCI_PR_Manager.md` — none
  of these are part of feature commit `b409f78` (`git show --stat b409f78` confirms only the five
  files listed under Scope above), so they don't affect this decision.

**Disposition:** no technical defect blocks this batch — scope is exact, D4 is genuinely satisfied,
tests are real and non-vacuous, and the full suite/lint/format are independently clean. The two
items above are recorded as comments (pattern-consistency and an untested guard clause), not
rework — both are the kind of finding this project's `Approved with comments` disposition exists
for.

## Objective — T68 batch

Close the one gap T67's own QA Decision named as a non-blocking comment: `test_bootstrap_admin.py`
covered `run_bootstrap()`, the in-memory core, but nothing exercised `infrastructure/cli/
bootstrap.py`'s actual entry point (`main()`/`_async_main()`) — the `input()`/`getpass()` prompting,
the `get_session_factory()`-backed session, and, most importantly, the real `session.commit()` call
`run_bootstrap()`'s own tests never touch (they only ever `flush()`).

**Authorization / Scope (recorded before implementation, `IMPLEMENTATION_QUEUE.md`'s T68 row /
`PROJECT_STATE.json`, commit `d6b6b45`, PR #49, merge `5bca735`, 2026-08-18):** the project owner
explicitly authorized T68, narrowed by a direct pre-authorization check to only the genuinely
missing half of the task's one-line description. **Already satisfied, not re-authorized:** the
seed-row-count/matrix-match half — `test_t66_role_permissions.py::
test_t66_role_permissions_matrix_exact_match` already covers this, confirmed by direct read before
this batch began; no new test written for it, per the authorization's own explicit instruction not
to duplicate it. **Genuinely missing, authorized:** a new test mocking `input()`/`getpass()`
(patched at `app.infrastructure.cli.bootstrap.getpass`, matching how the module imports it) and
`get_session_factory()` (patched to yield the test's own `db_session`, mirroring this codebase's
`get_db`-override pattern) to invoke `_async_main()`/`main()` directly, covering: (1) a first
invocation with no existing user creates the admin and actually commits, not just flushes; (2) a
second invocation, or one run when a user already exists, prints the "already exists" message, does
not prompt for credentials it would discard, and does not create a duplicate user. Test-file-only —
`bootstrap.py`, `run_bootstrap()`, and every other `T52`–`T67` file explicitly remain unmodified; no
migration, route, or schema change.

## Tasks Implemented — T68 batch

- `T68` (genuinely-missing half only): `backend/tests/integration/test_bootstrap_admin.py` extended
  with two new test classes exercising `_async_main()` directly (not `main()` — `main()`'s only
  addition beyond `_async_main()` is `asyncio.run(...)`, which cannot be called from inside an
  already-running event loop, and every `asyncio_mode = auto` async test function here runs inside
  one; `_async_main()` is the coroutine that actually holds this entry point's logic, so it's what's
  driven directly, documented as a design decision below rather than silently substituted without
  comment).
  - `TestAsyncMainNoExistingUser` (2 tests): with zero existing users, `_async_main()` is invoked
    with `input()`/`getpass()` mocked to supply an email/password; the created row's existence and
    its `Administrator` role assignment are each verified through a **second, independent**
    engine/connection — not `db_session` — proving `session.commit()` genuinely ran (a same-session
    read can't distinguish "committed" from "merely flushed," since a session always sees its own
    uncommitted writes).
  - `TestAsyncMainExistingUser` (1 test): with one existing user already present (via `db_session`,
    flush-only, no real commit needed since nothing should be created), `_async_main()` is invoked
    with `input()`/`getpass()` mocked as plain (uncalled) `MagicMock`s; asserts both mocks were never
    called, the "already exists" message was printed (`capsys`), and the user count stays at exactly
    one.
  - `_FakeSessionFactory` (new, test-file-local helper class) and `_install_fake_session_factory()`
    (new, test-file-local helper function): the CLI-level mirror of `get_db`-override, handing
    `_async_main()` the test's own `db_session` instead of a freshly-opened one.
  - `_fetch_and_delete_committed_user()` (new, test-file-local helper function): opens a throwaway
    second engine/connection to read back (and, if found, delete) a user by email — used both to
    prove a real commit happened and, since that commit is real and `db_session`'s own rollback can't
    undo it, to clean the row back up afterward regardless of whether the test's own assertions
    passed.
- No change to `bootstrap.py`, `run_bootstrap()`, or any other `T52`–`T67` file — confirmed via
  `git status`/`git diff --stat` before writing this section (see Files Modified below), not
  reconstructed from memory.

## Files Modified — T68 batch

- `backend/tests/integration/test_bootstrap_admin.py` (modified — module docstring extended to
  describe the new coverage; two new test classes and three new helpers added; the five existing
  `T67` tests/helpers (`_make_user`, `TestRunBootstrapNoExistingUser`,
  `TestRunBootstrapExistingUser`) left untouched)
- `docs/ImplementationLog/Stage4/Phase0.md` (this file — the `T68` batch section, plus the metadata
  block correction noted above)

No other file touched. In particular: `backend/src/app/infrastructure/cli/bootstrap.py` is
byte-for-byte unchanged (`git diff --stat` against `main` for that path returns nothing), and no
route, schema/migration, `deps.py`, `AuthService`, or any other `T52`–`T67` file was touched.

## Tests Added — T68 batch

All in `backend/tests/integration/test_bootstrap_admin.py`, against the real migrated schema — the
existing `db_session` fixture for the session `_async_main()` operates on, plus a second,
independent `create_async_engine()`/`async_sessionmaker()` pair (created directly in the test/helper,
not from any fixture) for the two tests that need to prove a real commit happened:

- `TestAsyncMainNoExistingUser::test_creates_admin_and_actually_commits` — with zero existing users,
  `_async_main()` (session, `input()`, and `getpass()` all mocked) creates the admin; the row is read
  back through a second, independent connection (proving a real `commit()`, not just a `flush()`) and
  its password hash is verified against the mocked plaintext; `input()`/`getpass()` are asserted
  called exactly once each, with the exact prompt strings `_async_main()` actually uses.
- `TestAsyncMainNoExistingUser::test_assigns_administrator_role_and_actually_commits` — same setup;
  the `Administrator` role assignment (joined all the way from `User.email`, not just `UserRole`) is
  read back through a second, independent connection and found to be exactly `["Administrator"]`.
- `TestAsyncMainExistingUser::test_prints_message_and_skips_without_prompting` — with one existing
  user pre-seeded (flush-only), `_async_main()` is invoked with `input()`/`getpass()` mocked as
  plain, uncalled `MagicMock`s; asserts both are never called, `"already exists"` appears in captured
  stdout, and the user count remains exactly one.

Directly satisfies both of T68's authorized named requirements: "a first invocation with no existing
user creates the admin and actually commits (not just flushes)" and "a second invocation, or one run
when a user already exists, prints the message, does not prompt, does not create a duplicate."

## Test Results — T68 batch

- `uv run pytest tests/integration/test_bootstrap_admin.py -v` — **8/8 passing** (the 5 existing `T67`
  tests, unmodified and still green, plus 3 new), personally run against live Postgres this session
  (`legal_dms_postgres` container, confirmed healthy via `docker ps` before running).
- `uv run pytest` (full suite) — **490/490 passing** (0 failed, 0 skipped) — 487 immediately prior to
  this batch (the count `T67`'s own closeout recorded) + 3 new.
- `uv run ruff check src tests alembic` — clean (one `UP037` "remove quotes from type annotation"
  finding, from an initially-quoted forward reference to `_FakeSessionFactory` inside its own class
  body — unnecessary given this file's `from __future__ import annotations` — was caught and fixed
  during this batch, not left for QA).
- `uv run black --check src tests alembic` — clean, 204 files unchanged (one reformat, a single
  helper function signature `black` wanted collapsed onto one line, applied and re-verified during
  this batch).
- **Database hygiene, independently verified, not assumed:** `docker exec legal_dms_postgres psql -U
  legal_dms -d legal_dms_dev -tAc "SELECT count(*) FROM users;"` returned `0` both before this
  batch's tests ran and again after the full suite ran — the two tests that call a real
  `session.commit()` clean up the row they create (via `_fetch_and_delete_committed_user()`, in a
  `finally` block so cleanup runs even if an assertion above it fails), so this batch leaves the dev
  database exactly as it found it, despite deliberately not relying on `db_session`'s usual
  rollback-only safety net for those two tests.
- **Not independently re-derived via mutation, disclosed rather than asserted:** this batch did not
  temporarily strip `bootstrap.py`'s `session.commit()` call and re-run the new tests to directly
  observe them fail (which would have proven the "actually commits" tests aren't vacuous by
  construction, not just by reasoning about them) — the sandboxed session this batch ran in declined
  to permit editing `bootstrap.py`, even transiently and for verification purposes only, given `T68`'s
  own explicit "no changes to bootstrap.py" scope boundary. The soundness argument instead rests on
  well-established Postgres transaction-isolation semantics (a separate connection cannot see another
  connection's uncommitted writes, so a same-session read genuinely cannot substitute for this),
  documented directly in the test file's own module docstring and reasoned through in Design
  Decisions below — recorded here as a real, disclosed limitation on how this batch's own claim was
  verified, not silently presented as if a mutation test had actually been run.

## Design Decisions — T68 batch

- **`_async_main()`, not `main()`, is what's driven directly.** `main()`'s only behavior beyond
  `_async_main()` is `asyncio.run(_async_main())`; `asyncio.run()` raises if called from inside an
  already-running event loop, which every `asyncio_mode = auto` async test function in this suite
  runs inside. `_async_main()` is the coroutine holding all of this entry point's actual logic —
  testing it directly, `await`ed like any other coroutine in this suite, covers everything `main()`
  would add nothing further to prove.
- **A second, independent engine/connection is what actually proves a commit happened.** Reading the
  created row back through `db_session` itself would pass regardless of whether `run_bootstrap()`
  only flushed or actually committed — a session always sees its own uncommitted writes within the
  same transaction (Postgres's normal read-your-own-writes behavior). Only a genuinely separate
  connection can distinguish the two, which is exactly what T68's "actually commits, not just
  flushes" requirement is asking to be proven, not merely asserted.
- **The two commit-verifying tests clean up after themselves, deliberately outside `db_session`'s own
  safety net.** Every other test in this file (and this codebase's integration suite generally) relies
  entirely on `db_session`'s teardown-time `rollback()` for cleanup — safe, because nothing in those
  tests ever really commits. These two tests are the deliberate exception: since `_async_main()`
  really does call `session.commit()`, `db_session`'s later `rollback()` has nothing left to undo.
  Explicit, `finally`-guarded deletion through the same second connection keeps the dev database
  exactly as clean after this batch's tests as before them, and keeps the suite re-runnable (a
  leftover row from a prior run would otherwise make the "zero existing users" precondition false on
  the next run).
- **`_FakeSessionFactory` mirrors `get_db`-override, not a new pattern.** `get_session_factory()`'s
  real return value is an `async_sessionmaker`, itself callable, whose call returns a fresh
  `AsyncSession` usable as an async context manager. `_FakeSessionFactory` reproduces exactly that
  shape (callable, returns an async-context-manageable value) while always handing back the test's
  own `db_session` and doing nothing on exit — the same "yield the test's session, don't open or
  close a new one" contract `test_users.py`'s `client` fixture already establishes for `get_db`,
  applied here to a plain function instead of FastAPI's dependency-injection system.
- **`input()` patched at `builtins.input`; `getpass()` patched at the module's own imported name.**
  `bootstrap.py` calls the `input` builtin directly (nothing to intercept except the builtin itself),
  but does `from getpass import getpass`, binding `getpass` into its own module namespace — patching
  `app.infrastructure.cli.bootstrap.getpass` (not `getpass.getpass`) is what actually affects the
  name `_async_main()` resolves at call time, exactly as T68's authorization explicitly specified.

## Problems Encountered — T68 batch

- `ruff` initially flagged a `UP037` finding (quoted forward reference to `_FakeSessionFactory`
  inside its own `__call__` return-type annotation, unnecessary given this file's existing
  `from __future__ import annotations`) — caught and fixed before this batch's checks were reported
  clean.
- `black` wanted one helper function signature (`_install_fake_session_factory`) collapsed onto a
  single line — applied and re-verified, no manual formatting decisions overridden.
- This session's sandboxing declined a transient, self-reverting edit to `bootstrap.py` that would
  have let this batch directly observe the "actually commits" tests fail when the real `commit()`
  call is removed (a mutation-style soundness check) — see Test Results above for the full account
  and why the tests are still trusted as non-vacuous by construction, not by having watched them fail.

## Deferred Work — T68 batch

- The mutation-style soundness verification described above (temporarily stripping `bootstrap.py`'s
  `commit()` call to directly observe the new tests fail) — trigger: a session whose sandboxing
  permits transient edits to production files for verification purposes, or the project owner running
  it themselves.
- T67's QA Decision named two non-blocking comments neither this batch nor its authorization asked it
  to address: `run_bootstrap()` hand-rolling user/role persistence instead of reusing
  `SqlAlchemyUserRepository.assign_role()`, and the missing-`Administrator`-role `RuntimeError` guard
  having zero test coverage. Both remain exactly as `T67` left them — untouched, since `T68`'s
  authorization is test-file-only and explicitly does not touch `bootstrap.py`. Trigger: a future task
  that's actually authorized to modify `bootstrap.py`.

## Future Considerations — T68 batch

- `_FakeSessionFactory`/`_install_fake_session_factory()`/`_fetch_and_delete_committed_user()` are
  currently local to `test_bootstrap_admin.py`. If a future CLI script needs the same
  "mock `get_session_factory()` at the entry point" pattern, these are the natural candidates to
  extract into a shared test-support module (mirroring `tests/support/in_memory_user_repository.py`'s
  existing precedent) rather than re-implementing the same shape — not done here, since this is the
  only file that currently needs it and inventing a shared module for a single caller would be
  speculative.

## Reviewer Checklist — T68 batch

```
Reviewer Checklist (T68 batch)

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

- **Architecture preserved:** no production code touched at all — test-file-only, exactly as
  authorized; no port/contract/layering change possible from this batch's diff.
- **Existing design patterns followed:** the new mocking helpers mirror `get_db`-override
  (`test_users.py`'s `client` fixture) applied to a plain function instead of FastAPI DI; test
  class naming (`TestAsyncMainNoExistingUser`/`TestAsyncMainExistingUser`) mirrors the existing
  `TestRunBootstrapNoExistingUser`/`TestRunBootstrapExistingUser` convention already in this same
  file; `monkeypatch` (not a mocking library import beyond `unittest.mock.MagicMock` for call-tracking)
  matches this codebase's existing `test_auth.py` precedent.
- **Tests added:** 3 new tests, both of T68's authorized named requirements directly covered — see
  Tests Added above.
- **Existing tests pass:** full suite 490/490 (487 prior + 3 new), personally re-run against live
  Postgres this session — see Test Results above. The 5 pre-existing `T67` tests in this same file
  are unmodified and still pass.
- **Documentation updated:** this phase log entry, plus the T67 metadata-block correction noted
  above (a genuine discrepancy found while rebuilding context, corrected per this project's
  "trust the code, report the discrepancy" rule, not left stale). `AI_BOOTSTRAP.md`/
  `PROJECT_STATE.json` are left to the Documentation Manager, per this role's ownership boundary —
  see the two unchecked boxes below.
- **ADR updated (if required): □** — no architectural decision made or needed; this batch adds test
  coverage for already-approved `T67`/`ADR-0018` behavior, it doesn't decide anything new.
- **AI_BOOTSTRAP updated (if required): □** — no non-negotiable rule, required-reading order, or
  standing convention changed; out of this role's ownership boundary regardless.
- **PROJECT_STATE updated (if required): □** — `T68`'s status/test counts belong to
  `PROJECT_STATE.json`, owned by the Documentation Manager, only after a QA Decision exists — not
  touched by this role, per `docs/prompts/BackendDeveloper.md` §5/§8.
- **No unrelated refactoring:** the 5 pre-existing `T67` tests/helpers in this file are untouched;
  no other file's content changed beyond this phase log.
- **No scope creep:** the seed-row-count/matrix-match half of T68's original one-line description was
  deliberately *not* re-tested, per the authorization's explicit instruction that
  `test_t66_role_permissions.py` already covers it; `bootstrap.py` itself was not touched even
  though two of this batch's own findings (see Deferred Work) would be easy to act on from here.
- **Ready for QA:** this log entry plus `git diff main...feature/stage4-t68-bootstrap-entrypoint-tests`
  should let a QA Reviewer verify the batch without needing clarifying questions.

## QA Decision — T68 batch

```
QA Decision (T68 batch)

☑ Approved
□ Approved with comments
□ Rework required
```

Rendered by the QA Reviewer role, independently, against feature commit `33c728b`
(`feature/stage4-t68-bootstrap-entrypoint-tests`) — no PR opened yet; this decision is recorded
pre-PR, per this project's practice of committing the QA Decision to the branch before any PR is
opened or merged.

**Verification Results (checked directly against the repository and live runs, not taken from the
Developer's self-assessment):**

- **Authorization:** T68's narrowed scope (`IMPLEMENTATION_QUEUE.md` row, commit `d6b6b45`, PR #49,
  merge `5bca735`) precedes the implementation commit — confirmed by commit order (`5bca735`/
  `d6b6b45` precede `33c728b`). The "already satisfied" half (seed-row-count matrix match) was
  independently re-read in `test_t66_role_permissions.py` and genuinely already covers that ground;
  no duplicate test was added for it, exactly as the narrowed authorization required.
- **Scope — test-file-only, verified, not assumed:** `git diff main...feature/stage4-t68-bootstrap-entrypoint-tests --stat`
  confirms exactly two files changed: `backend/tests/integration/test_bootstrap_admin.py` and this
  phase log. `git diff main...feature/stage4-t68-bootstrap-entrypoint-tests -- backend/src/` returns
  **nothing** — `bootstrap.py` is byte-for-byte unchanged. No migration, route, or schema file
  touched. Matches the authorized scope exactly.
- **Does this genuinely prove a real commit happened?** Yes — verified two ways, not just by reading
  the test. (1) The tests read the created row back through a second, independent
  engine/connection (`_fetch_and_delete_committed_user`, a fresh `create_async_engine()` against the
  same `get_settings().database_url` the `db_session` fixture itself uses — confirmed by reading
  `tests/conftest.py` directly), which cannot see another connection's merely-flushed, uncommitted
  writes under Postgres's normal transaction isolation. (2) **This QA review went further and ran a
  mutation test the Developer's own log disclosed being unable to perform:** `session.commit()` was
  temporarily removed from `bootstrap.py`'s `_async_main()`, the two "actually commits" tests were
  re-run, and both failed exactly as expected (`AssertionError: assert [] == ['Administrator']` /
  the equivalent for the row-existence assertion) — proving they are genuinely non-vacuous, not
  merely plausible by construction. The change was reverted immediately
  (`git diff --stat` on `bootstrap.py` confirms zero diff afterward) and the full suite (490/490) and
  a direct `psql` user count (0) were re-verified clean post-revert.
- **Are "no duplicate created" and "no prompt shown" actually asserted?** Yes, explicitly, not
  implied: `TestAsyncMainExistingUser::test_prints_message_and_skips_without_prompting` asserts
  `input_mock.assert_not_called()`, `getpass_mock.assert_not_called()`, `"already exists" in
  captured.out`, and `len(remaining.scalars().all()) == 1` (post-existing count unchanged) — all four
  are real, would-fail-if-broken assertions, not inferred from the absence of an error.
- **Do the new tests clean up correctly without rollback-based isolation?** Verified directly, not
  assumed: ran `docker exec legal_dms_postgres psql ... "SELECT count(*) FROM users;"` before and
  after the full suite — **0 both times**, including after this review's own mutation-test run (whose
  failed assertions never reached `commit()`, so `db_session`'s ordinary rollback handled that case
  correctly on its own). The two committing tests' `try`/`finally`-guarded
  `_fetch_and_delete_committed_user()` calls delete `UserRole` rows before the `User` row (correct FK
  order) through the same database the fixture itself targets — confirmed by reading
  `tests/conftest.py`, not assumed to match.
- **Tests — independently re-run this session:** `uv run pytest tests/integration/
  test_bootstrap_admin.py -v` → 8/8 passing (5 pre-existing `T67` tests unmodified and green, 3 new).
  `uv run pytest` (full suite) → 490/490 passing. `uv run ruff check src tests alembic` → clean.
  `uv run black --check src tests alembic` → clean, 204 files unchanged.
- **Architecture:** no production code touched at all this batch — no layering or port/contract
  question arises. The mocking helpers (`_FakeSessionFactory`, patching `builtins.input` and the
  module's own imported `getpass` name) correctly target the actual interception points `bootstrap.py`
  exposes — confirmed by reading the unmodified source directly, not inferred from the test's own
  claims about it.

**Disposition:** no technical defect, no scope violation, no vacuous test. The Developer's own
disclosure (unable to run the mutation test in their sandboxing) was honest and non-blocking on its
own terms — this review closed that exact gap directly and it confirmed the tests as sound.
Plain **Approved** — no comments to record beyond what the Developer already disclosed themselves
(the two `T67`-scoped findings deferred in this batch's own Deferred Work section, out of scope for
`T68` and unaffected by it).
