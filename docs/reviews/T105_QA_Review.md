# T105 QA Review — Implementation PR #174

**Record type:** Genuine pre-merge QA Decision, rendered and persisted on PR #174's actual remote
HEAD before that PR is merged, per T105's own authorization row (three-PR pattern, step 3). Every
factual claim below was independently reproduced against live repository/GitHub/PostgreSQL state —
including hand-executed SQL against the project's actual Postgres 16.15 container — not accepted
from `docs/ImplementationLog`, commit messages, or code comments on their own word.

**Task:** T105 — Organization/Tenant Core Foundational Implementation.

**Authorization:** PR #173 (`docs(governance): authorize T105...`), merged as
`1eea22cbe13698c32ab86d058b2faca39ac3e9c1` — this is also PR #174's base, so authorization ancestry
is definitional here (confirmed via `git merge-base --is-ancestor` regardless).

**PR under review:** #174 (`feature/T105-organization-tenant-core-foundation` → `main`).

**Base:** `1eea22cbe13698c32ab86d058b2faca39ac3e9c1` — confirmed identical to `gh pr view 174`'s
`baseRefOid` and to live `origin/main` at review start.

**Reviewed commit — exactly:**

```
c0888aa834a97e0eef0491e86b694168d647f07f
```

Confirmed identical to `gh pr view 174 --json headRefOid` (no drift from the expected handoff SHA).
`git merge-base --is-ancestor 1eea22cb... c0888aa...` → true. If PR #174's branch changes after this
review, this QA Decision must be reconsidered against the new HEAD before merge.

**Date:** 2026-09-01.

---

## 1. Scope firewall — exact diff

`git diff 1eea22cb...c0888aa... --name-only` — **32 files, all under `backend/`:**

```
backend/.env.example
backend/alembic/versions/64c319444b4c_organizations_and_users_organization_.py
backend/alembic/versions/7192e84e9a2f_organization_tenant_isolation_rls.py
backend/pyproject.toml
backend/src/app/application/interfaces/auth.py
backend/src/app/application/interfaces/user_repository.py
backend/src/app/infrastructure/auth/jwt_authentication_provider.py
backend/src/app/infrastructure/cli/bootstrap.py
backend/src/app/infrastructure/cli/provision_app_role.py
backend/src/app/infrastructure/cli/reconcile_organizations.py
backend/src/app/infrastructure/config/settings.py
backend/src/app/infrastructure/database/session.py
backend/src/app/infrastructure/persistence/models/__init__.py
backend/src/app/infrastructure/persistence/models/identity.py
backend/src/app/infrastructure/persistence/models/organization.py
backend/src/app/infrastructure/persistence/sqlalchemy_user_repository.py
backend/src/app/presentation/api/deps.py
backend/src/app/presentation/api/v1/users.py
+ 14 test files (backend/tests/...)
```

Independently confirmed **absent**: `IMPLEMENTATION_QUEUE.md`, `PROJECT_STATE.json`,
`PROJECT_WORKFLOW.md`, any `ADR/*.md`, any `.github/workflows/` file, any ruleset config. No `T106`
row, branch, or PR exists anywhere (`grep -c "^| T106" IMPLEMENTATION_QUEUE.md` → `0`; the only
`T106` string matches are the authorization row's own negation clauses). `organization_id` was added
to `users` only (confirmed by reading `identity.py`'s diff — no other model file changed). No
unrelated table received RLS (confirmed live, §5). `POST /users` behavior is unchanged (confirmed
line-by-line, §7). No CI/ruleset/governance file touched. **Scope firewall: clean.**

## 2. T105 authorization items — individually verified

| # | Item | Verification |
|---|---|---|
| 1 | `organizations` table | `organization.py`: `id`, `name` (required), `legal_name` (nullable), audit columns only — matches ADR-0031 §24.1's "name/legal-name" spec exactly, nothing invented. Live schema confirmed via `\d organizations`. |
| 2 | nullable `users.organization_id` | `identity.py` diff: `Mapped[UUID \| None] = mapped_column(ForeignKey("organizations.id"), index=True)` — direct FK, not a join table, matching ADR-0031 §6.4. |
| 3 | atomic `bootstrap-admin` extension | `bootstrap.py`'s `run_bootstrap()`: User created+flushed, Organization created+flushed (attributed to the new user), `user.organization_id` set, `UserRole` added — all in one caller-owned transaction (no commit inside), matching ADR-0031 §6.2/§6.3 exactly. |
| 4 | ADR-0032 reconciliation CLI | `reconcile_organizations.py`: requires every `organization_id IS NULL` user to be explicitly mapped (raises `ValueError` naming unmapped/double-mapped ids), no heuristic grouping, operator-supplied names only, one transaction. Matches ADR-0032's "no automatic grouping" mandate. |
| 5 | `CurrentUser.organization_id` + live rederivation | `auth.py` diff adds exactly one field. `jwt_authentication_provider.py`: sets `app.current_user_id` GUC, self-row-looks-up the user, then sets `app.current_organization_id` from the **freshly-read DB row**, never the JWT — matches ADR-0031 §6.5/§6.6 exactly. |
| 6 | app-layer scoping + `FORCE` RLS on `organizations`/`users` only | `users.py`'s six routes all call `_require_organization()` (fail-closed `ForbiddenError` if unresolved) before any org-scoped lookup. Live catalog query confirms RLS enabled+forced on exactly these two tables, no others (§5). |
| 7 | non-owning runtime role | `provision_app_role.py` creates `legal_dms_app` with `NOSUPERUSER NOCREATEROLE NOCREATEDB NOBYPASSRLS`; live query confirms it is not the table owner (§5). |
| 8 | existing user routes scoped; `create_user` excluded | Confirmed line-by-line in `users.py` (§7 below) — five routes scoped, `create_user` genuinely untouched at the code level. |
| 9 | tests | 14 new/modified test files; 573/573 pass independently (§10). |

**All nine items verified as implemented, matching their respective ADR sections, with nothing
broader invented.**

## 3. Critical Finding #1 — NULL GUC behavior (independently reproduced against live Postgres 16.15)

Hand-executed directly against the project's own `legal_dms_postgres` container (not assumed, not
taken from the implementation's own claim):

- **Never-set custom GUC**: `current_setting('app.x', true)` correctly returns true `NULL`.
- **Once set, then `set_config(name, NULL, ...)`** (session-level *or* transaction-local, committed
  *or* rolled back): `current_setting(name, true)` returns an **empty string**, never true `NULL`
  again, for the life of that connection. Reproduced in four independent variations (session-level
  reset; transaction-local reset then commit; set-then-null within one transaction; transaction-local
  reset then rollback) — **all four produce the identical empty-string behavior.** This is a genuine,
  reproducible PostgreSQL 16 characteristic of custom/placeholder GUCs, not a documentation
  misreading.
- **Pooled-connection-reuse simulation**: a transaction that sets a real Organization UUID
  transaction-locally, commits, and is followed by a later transaction on the *same* connection that
  sets `NULL` — the naive `current_setting(...)::uuid` cast **raises `invalid input syntax for type
  uuid: ""`**, reproducing the exact failure mode the implementation's docstrings predict. The
  `NULLIF(current_setting(...), '')::uuid` expression, tested identically, **does not raise** and
  correctly evaluates to `NULL`.
- **Fail-closed semantics**: `NULL::uuid = <uuid>` evaluates to `NULL` (not `TRUE`) in a `USING`
  clause, which PostgreSQL treats as row-excluded — confirmed directly. A caller with no resolved
  Organization can never accidentally match another tenant's rows through this comparison.
- **Valid UUID round-trip**: `NULLIF('<real-uuid>', '')::uuid` passes through unaffected — the fix
  does not break normal operation.
- **Genuinely invalid, non-empty input**: still raises even with `NULLIF` (expected — `NULLIF` only
  targets the empty-string case; application code never binds an arbitrary non-UUID string here, only
  `str(uuid.UUID)` or `None`, confirmed by reading every call site).
- **No unwrapped cast remains**: `grep` across the entire migration confirms all five
  `current_setting(...)::uuid` occurrences are `NULLIF`-wrapped; the sole unwrapped occurrence
  anywhere in the diff is inside `test_tenant_context_guc_scoping.py`'s own
  `test_raw_current_setting_cast_does_raise_after_a_null_set_config` — a test that **deliberately**
  proves the naive cast fails (see `pytest.raises(...)` in that test), not a live code defect.
- **Self-row lookup with no Organization**: independently tested live — the bootstrap admin's
  self-row is visible via the `id`-match clause with `app.current_organization_id` left unset.
- **Unassigned User cannot leak as another tenant's User**: created two separate
  `organization_id IS NULL` users live; on a connection with the org GUC unset, or explicitly reset to
  `NULL` after having held a real value (the pooled-reuse hazard), only the self-matched row is ever
  visible — the second unassigned user never appears, in either scenario, because `NULL = NULL` is
  `NULL`, never `TRUE`.

**Verdict: the NULL-GUC premise is real, correctly diagnosed, and correctly, consistently mitigated.
The revised design (RLS-level `NULLIF`, not a fixed application-level assumption) is safer than the
original plan's premise and stays fully within T105's authorization (no schema/scope change beyond
what §6 of the authorization row permits).**

## 4. Critical Finding #2 — authentication/admin-session split

- **Why authentication needs the admin connection**: `AuthService` (T50/T58, unmodified) resolves a
  `User` by email (login) or a stored `user_id` (refresh) *before* any JWT — and therefore before any
  tenant context — can exist. The plain org-scoped `users_select` policy's self-row carve-out depends
  on `app.current_user_id` already being set from a *verified* JWT, which does not exist yet at
  login/refresh time. Confirmed genuine, not a workaround for a self-inflicted problem.
- **Which code uses `AdminDBSessionDep`**: `grep -rn "AdminDBSessionDep\|get_admin_db"
  backend/src` — exactly one call site, `get_auth_service()` in `deps.py`. No route, repository, or
  service anywhere else references it.
- **`AuthService` itself**: confirmed unmodified — the diff touches only which session constructs its
  two repositories (`deps.py`), never `AuthService`'s own file/logic.
- **No accidental tenant-isolation bypass for ordinary data**: `get_authentication_provider()` (used
  by `CurrentUserDep`, i.e. every already-authenticated request) uses `DBSessionDep` — the
  RLS-restricted `legal_dms_app` session — not the admin session. Only the pre-tenant-context
  login/refresh/logout path uses the admin session; every subsequent tenant-scoped query in the same
  request goes through `DBSessionDep`.
- **No tenant-scoped route accidentally gets admin access**: confirmed by the single-call-site grep
  above — `users.py`'s six routes all declare `DBSessionDep`-derived dependencies only.
- **ADR-0021 consistency**: ADR-0021 explicitly requires "administrative/system-level operations" to
  use "an explicit, separately-named, audited system context," while explicitly declining to
  prescribe the mechanism ("this ADR does not enumerate which operations qualify; that is
  implementation-phase work"). `get_admin_db()`/`AdminDBSessionDep` is exactly this: explicit,
  separately named, and reuses the *existing*, pre-T105 `database_url` trust boundary (already used
  by Alembic/`bootstrap-admin`) rather than inventing a new one.
- **Refresh-token authentication**: `get_auth_service()` is the single dependency backing login,
  refresh, and logout alike (`AuthServiceDep`) — the same admin session is used identically for all
  three, confirmed by reading the auth routes' dependency declarations.
- **The two session paths cannot silently mix within one request**: `get_db()`/`get_app_engine()` and
  `get_admin_db()`/`get_engine()` are two independently cached engines with distinct connection
  factories; `AuthServiceDep` and `DBSessionDep` are two separate FastAPI dependency chains with no
  shared session object — a given request either resolves `AuthServiceDep` (auth routes only) or
  `DBSessionDep`-derived dependencies (every other route), never both against the same session.

**Verdict: the split is minimal, correctly and narrowly scoped to exactly the pre-tenant-context
authentication case, faithful to ADR-0021's own carve-out, and does not create a privilege-escalation
surface for ordinary route code.**

## 5. RLS security review — live PostgreSQL catalog inspection

Directly queried against the project's actual `legal_dms_postgres` (16.15) container, migrated to
this PR's exact head (`7192e84e9a2f`):

- `organizations`: `relrowsecurity=t`, `relforcerowsecurity=t`. `users`: same. **Every other checked
  table** (`matters`, `documents`, `clients`, `properties`, `invoices`, `payments`, `roles`,
  `permissions`, `role_permissions`, `user_roles`, `activity_logs`, `audit_logs`, `refresh_tokens`):
  `f`/`f`. A full-schema query (`relrowsecurity = true`) confirms **only** `organizations`/`users`
  have RLS enabled anywhere in `public`.
- `legal_dms_app`: `rolsuper=f`, `rolbypassrls=f`, `rolcreaterole=f`, `rolcreatedb=f`, `rolcanlogin=t`
  — all four required-false attributes confirmed false, live, not merely asserted by
  `provision_app_role.py`'s own validation logic.
- Table ownership: `organizations`/`users`/`matters` all owned by `legal_dms`, **not**
  `legal_dms_app` — confirmed via `pg_tables`.
- `legal_dms_app` privileges, full schema: only `SELECT/INSERT/UPDATE/DELETE` anywhere — no
  `TRUNCATE`, `ALTER`, `DROP`, `CREATE`, or `BYPASSRLS`-equivalent grant exists.
- Per-table privilege asymmetry confirmed exactly: `organizations` → `SELECT` only;
  `users` → `SELECT/INSERT/UPDATE`, no `DELETE`.
- All four live policies read back **byte-identical** to the migration source
  (`organizations_select`, `users_select`, `users_insert`, `users_update`).
- **Admin/owning role (`legal_dms`)**: independently confirmed `rolsuper=t`, `rolbypassrls=t` — the
  migration docstring's claim that `bootstrap-admin`/`reconcile-organizations` "run via the
  admin/owning role, which is a Postgres superuser and bypasses RLS entirely" is **verified true**,
  not merely asserted. This is also why those two CLIs' own writes (e.g. `bootstrap.py`'s
  `user.organization_id = organization.id` UPDATE, which sets no GUC at all) are never blocked by
  `FORCE` RLS — genuine superuser bypass, confirmed live, not a latent bug.

**Verdict: RLS configuration matches T105's authorization exactly, confirmed against live catalogs,
not source code alone.**

## 6. Option-4 invariant — live, structural verification (not just behavioral)

Connected **as** `legal_dms_app` (not the admin role) against the live database and executed real
`INSERT`/`UPDATE` statements:

- `organization_id = NULL` → **`INSERT 0 1`, permitted.**
- `organization_id = caller's own Organization` → **rejected**, `new row violates row-level security
  policy for table "users"`.
- `organization_id = a different Organization` → **rejected**, identical RLS violation.
- `organization_id = an arbitrary/unrelated UUID` → **rejected**, identical RLS violation.
- `UPDATE ... SET organization_id = <another org>` on a row already in the caller's org → **rejected**
  (`WITH CHECK` violation, no `UPDATE N` success line).
- `UPDATE ... SET organization_id = NULL` (attempting to unassign a row back out of an Organization)
  → **also rejected** — the `WITH CHECK` clause requires the post-update row to still equal the
  caller's org, so a downgrade-to-unassigned is blocked too, not only a lateral move.
- An **ordinary** `UPDATE` (e.g. `full_name`) that leaves `organization_id` untouched, within the
  caller's own org → **permitted** (`UPDATE 1`) — confirms the policy is not over-broad.
- Legitimate administrative paths: `bootstrap-admin` and `reconcile-organizations` both connect via
  `get_session_factory()` (the admin/superuser role, §5), which genuinely bypasses RLS — independently
  confirmed by reading their imports and by the live `rolbypassrls=t` finding — so both remain able to
  establish Organization membership through their intended, distinct connection, never through
  `legal_dms_app`.

**Verdict: the INSERT policy makes it structurally impossible for the application-facing path to
assign any Organization, matching the "Option-4" acceptance criterion exactly — confirmed by direct
execution, not inferred from the policy's SQL text alone.**

## 7. `POST /users` regression boundary

Read `users.py`'s `create_user` in full, current state (not just the diff):

- **Route implementation**: the actual function body (`get_by_email` check, `User(...)` construction,
  `repository.add(user)`) is byte-identical to before T105 — the diff adds only a docstring above it,
  confirmed by the diff showing no `-`/`+` pairs inside the function body itself.
- **Request schema**: `UserCreate` (`email`, `full_name`, `phone`, `password`) has **no**
  `organization_id` field — confirmed by reading the current class definition directly, not the
  docstring's claim. A client-supplied extra field is silently ignored by Pydantic's default behavior
  and never reaches the handler.
- **Repository call**: `repository.add(user)` — `user.organization_id` is never set, defaulting to
  `NULL`, which the live `users_insert` RLS policy independently permits (§6) — a second, independent
  enforcement layer, not merely an application-level convention.
- **Assignment logic**: none exists — no code path in `create_user` reads or writes
  `organization_id`.
- **Visibility**: an org-unassigned User created here is invisible to every org-scoped listing
  (`list_in_organization`/`get_by_id_in_organization` both filter on `organization_id = :org`, which
  a `NULL` row never satisfies) — confirmed by the same SQL semantics verified live in §3/§6.
- **No accidental admin-privilege acquisition**: `create_user`'s only session dependency is
  `UserRepositoryDep` → `get_user_repository(session: DBSessionDep)` — the ordinary, RLS-restricted
  app-role session. It never touches `AdminDBSessionDep`. The router-level `RequirePermission`
  dependency it sits behind also resolves through `DBSessionDep` via `get_authentication_provider()`,
  not the admin session.

**Verdict: `create_user` is genuinely, verifiably unchanged in behavior, and its `organization_id =
NULL` invariant is enforced at both the application and database layers.**

## 8. Same-session/same-transaction test — real path, not mocked

`test_users_organization_scoping_end_to_end.py` uses the **plain, unmodified `TestClient(app)`**
(explicitly *not* the usual `get_db`-override fixture every other route test in this suite uses),
so `GET /users`/`GET /users/{id}` flow through the real `app_database_url`/`legal_dms_app`/RLS path
exactly as production would. Its one test:

- Seeds two real Organizations with one real, `users:manage`-permitted User each (via the admin
  engine, committed).
- Performs a genuine HTTP `POST /api/v1/auth/login` (real password verification, real JWT issuance).
- `GET /api/v1/users/{own_id}` → `200`, correct row — same-org self-access.
- `GET /api/v1/users/{other_org_user_id}` → `404` — cross-Organization request, proving the
  authentication lookup and this route's own query share the same GUC-bearing transaction (if they
  didn't, the org GUC set during authentication wouldn't be visible to this later query at all, and
  the result would differ unpredictably rather than cleanly 404).
- `GET /api/v1/users` → lists the caller's own user, **not** the other Organization's.

Independently re-run as part of the full suite (§10) — passes. **This is a genuine end-to-end proof
through the real dependency chain, not a hand-assembled unit test or a mocked chain**, satisfying this
section's explicit requirement.

## 9. Migration review

- **Ordering**: `64c319444b4c` (schema) → `7192e84e9a2f` (RLS/grants), correctly sequenced (RLS
  migration `Revises: 64c319444b4c`).
- **Upgrade from baseline**: independently re-applied — `uv run alembic upgrade head` from the T105
  authorization baseline succeeds cleanly (already at head when review began; separately verified via
  full downgrade+upgrade cycle below).
- **Downgrade**: `uv run alembic downgrade -2` — succeeds; live-verified afterward: `organizations`
  table gone, `users.organization_id` column gone, `users` RLS disabled — a genuine, complete revert,
  not a partial no-op.
- **Upgrade again**: `uv run alembic upgrade head` from the downgraded state — succeeds cleanly; live
  re-verified: RLS re-enabled+forced on both tables, all 4 policies recreated, `alembic current`
  reports `7192e84e9a2f (head)` again. **Full downgrade → upgrade → upgrade-again round-trip
  confirmed genuinely reversible, not merely declared so.**
- **Fresh-database behavior**: not tested against a brand-new, never-migrated Postgres instance from
  scratch (only downgraded-to-pre-T105-baseline then re-upgraded) — a reasonably close proxy, but not
  byte-identical to a truly empty database. Recorded as a minor verification-depth gap, non-blocking
  (the schema/RLS DDL is unconditional `CREATE`/`ALTER`, with no environment-dependent branching that
  a from-scratch run would exercise differently).
- **No credentials/secrets embedded**: both migration files read in full — the schema migration is
  pure DDL; the RLS migration references `legal_dms_app` by name only, contains no `CREATE ROLE`, no
  password, anywhere.
- **Role provisioning outside Alembic**: confirmed — `provision_app_role.py` is a separate,
  independently-run script; the RLS migration's `upgrade()` fails loudly
  (`RuntimeError`) if the role doesn't exist yet, rather than silently creating it.
- **Idempotent, rejects misconfigured roles**: confirmed by direct code reading (§2/§5) — a
  second run against an already-correct role prints "nothing to do" and exits 0; an existing role with
  wrong attributes is reported and the command exits non-zero, **never** auto-corrected.
- **Password never printed**: confirmed — only role name and, on a real DB error, the exception
  *type* (never `str(exc)`, which some drivers embed the failed statement/parameters into) are ever
  surfaced, on every code path including failure paths.

## 10. Full regression suite — independently run

**Initial run**: `19 failed, 554 passed`. Investigation found a single pre-existing, already-committed
`User` row in the shared local dev database (predating this review's own testing — present before any
data was created during this session) that broke every test in `test_bootstrap_admin.py`/
`test_reconcile_organizations.py` asserting a "no existing user" precondition. **19 + 554 = 573 —
exactly the reported total**, strongly indicating an environment-state issue rather than a code
defect or a different test count. Confirmed by contents: every one of the 19 failures traced to
`_any_user_exists()`/`_unassigned_users()` returning non-empty because of that one stray row, not to
any assertion about T105's actual logic. With the user's explicit permission, cleaned the stray row
(and its dependent `user_roles`/`refresh_tokens` rows) from the local Docker dev database and re-ran:

```
573 passed, 83 warnings in 48.89s
```

**Independently confirms the handoff's reported 573/573 result** — not accepted on the report's word,
reproduced from a genuinely clean environment, with the initial discrepancy correctly root-caused
rather than dismissed.

- `uv run ruff check .` → **All checks passed!**
- `uv run black --check .` → **All done! 217 files would be left unchanged.**
- `python scripts/governance_validate.py` → **OK (0 warning(s), 0 errors)**
- `python scripts/tests/test_governance_validate.py -v` → **51/51 passing**
- Re-ran the full suite a second time after the migration downgrade/upgrade round-trip (§9) —
  still **573 passed**, confirming the round-trip left no residual state issue.
- `test_organizations_users_rls.py`'s own test classes (`TestRoleIsNotTheTableOwner`,
  `TestRoleHasNoRlsBypassAttributes`, `TestForceRlsIsEnabledOnExactlyTheseTwoTables`,
  `TestPoliciesExistForExactlyOrganizationsAndUsers`, `TestCrossOrganizationSelectReturnsEmpty`,
  `TestSelfRowCarveOut`, `TestUsersInsertPolicy`, `TestUsersUpdatePolicy`,
  `TestOrganizationsWritePrivilege`) independently cover the identical ground this review verified by
  hand in §5/§6 — both sources agree.

## 11. Required ADR compliance

- **ADR-0021**: "Administrative/system-level operations" carve-out matches `get_admin_db()`'s design
  exactly (§4). The RLS-only alternative's own stated risks (owner/`BYPASSRLS` bypass, pooled-GUC
  leakage) are the exact risks this implementation's `FORCE` RLS + non-owning role + `NULLIF` design
  addresses — confirmed the ADR's own analysis anticipated precisely this implementation.
- **ADR-0022**: Roles/Permissions remain global, unmodified by this diff (no `role_permissions`/
  `roles`/`permissions` file touched) — confirmed.
- **ADR-0031**: §6.1–§6.7 cross-checked section-by-section against the implementation (§2 table above)
  — matches exactly, nothing narrower or broader.
- **ADR-0032**: reconciliation CLI's explicit-mapping-only design, no heuristic grouping, verified
  directly in `reconcile_organizations.py`'s code (§2).
- **Required ADR #20**: independently re-run via `governance_validate.py --report` — still lists `20`
  under `Unresolved`, byte-identical to the pre-T105 state; T105's diff touches no ADR file.
- **No invented policy**: no Organization #2/#3/N onboarding capability, no User-assignment policy,
  and no new Organization-facing HTTP route exist anywhere in the diff (confirmed via `grep`/`find` —
  zero results for any organization-facing route file or path).

## Issues / Required Rework

**None blocking.**

**Non-blocking observations:**

1. The admin/owning role (`legal_dms`) is a full Postgres **superuser**, not merely a `BYPASSRLS`
   role or plain table owner. This is verified genuine and safe (superusers always bypass RLS,
   confirmed live), and it is an **unchanged, pre-existing trust boundary** (the same `database_url`
   role Alembic/`bootstrap-admin` already used before T105) rather than a new privilege T105
   introduces — but ADR-0021's own text does not explicitly mandate "superuser" specifically for the
   administrative-context carve-out; it leaves the mechanism to implementation-phase discretion,
   which this satisfies. Worth a documentation note in a future pass that production deployments
   should treat `DATABASE_URL`'s credential with the operational care due a superuser, not merely an
   elevated application role. Does not block this PR — the trust boundary was not created or widened
   by T105.
2. Migration reversibility was verified via a downgrade-to-pre-T105-baseline-then-upgrade round-trip
   rather than a truly from-scratch empty-database migration run. The DDL itself is unconditional and
   environment-independent, so this is assessed as low-risk, but a genuinely fresh-database CI/local
   run was not separately exercised by this review.
3. This review did not line-review every one of the 14 test files in the diff individually beyond
   `test_tenant_context_guc_scoping.py`, `test_organizations_users_rls.py`, and
   `test_users_organization_scoping_end_to_end.py` (the three most safety-critical for the two named
   critical findings) — coverage of the remainder was verified by independently running the full suite
   (573/573) rather than by manual inspection of each file's assertions.

## QA Classification

**ACCEPTED WITH COMMENTS**

Both named critical findings — the NULL-GUC behavior and the authentication/admin-session split —
were independently reproduced and verified correct, not merely accepted from the implementation's own
account. The NULL-GUC behavior is real (reproduced four independent ways against live Postgres 16.15)
and is consistently, correctly mitigated everywhere it matters (`NULLIF` wraps every relevant cast; no
unwrapped occurrence exists in shipped code). The admin-session split is minimal, correctly scoped to
exactly the one call site that genuinely needs it, faithful to ADR-0021's own administrative-context
carve-out, and does not create a privilege-escalation path for ordinary tenant-scoped routes. The
Option-4 invariant was independently, structurally confirmed by executing real `INSERT`/`UPDATE`
statements as the restricted role, not merely read from policy SQL. RLS configuration matches
authorization exactly, confirmed against live PostgreSQL catalogs. `POST /users` is genuinely
unchanged. Scope firewall is clean — no governance, ADR, CI, or unrelated-table file touched, no
`T106` implied. The full regression suite passes (573/573, independently reproduced after correctly
diagnosing an unrelated environment-contamination issue as the initial failure cause), along with
ruff, black, and the governance validator/test suite. Required ADR #20 remains genuinely unresolved.
The three non-blocking comments above do not require rework — they are process/documentation notes,
not defects.

## Independently Confirmed (summary)

- Reviewed HEAD: `c0888aa834a97e0eef0491e86b694168d647f07f` — matches expected, no drift.
- Base: `1eea22cbe13698c32ab86d058b2faca39ac3e9c1` — matches live `origin/main` and PR #173's merge.
- Ancestry: confirmed via `git merge-base --is-ancestor`.
- CI (`gh pr checks 174`): all required checks passing at review time.
- Diff scope: 32 files, all `backend/`, no governance/ADR/CI file.
- Live RLS/catalog state, Option-4 invariant, and NULL-GUC behavior: all independently reproduced
  against the project's actual Postgres 16.15 container, not inferred from source alone.
- Test suite: 573/573, ruff clean, black clean, governance validator clean, 51/51 governance tests.

---

## Reviewed Commit

```
c0888aa834a97e0eef0491e86b694168d647f07f
```

## Merge Recommendation

**PR #174 is content-ready for GitCI/PR Manager.** This review does not merge PR #174, does not
modify implementation code, does not touch any governance file, does not create T106, and does not
mark T105 Done — all per this review's explicit stopping boundary. Per T105's own authorization row,
a separate, later Governance Closeout PR is required before T105 can be marked Done; that is not this
PR and not this record.
