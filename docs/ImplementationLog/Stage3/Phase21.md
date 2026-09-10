# Stage 3 - Phase 21

Status: Done (QA Approved; ready for PM pre-merge gate)

Started: 2026-09-10

Completed: 2026-09-10

Related Tasks: [T123](IMPLEMENTATION_QUEUE.md) (Party Row-Level-Security Backstop)

Related ADRs: [ADR-0021](../../../ADR/0021-organization-tenant-boundary-enforcement.md) (Organization is the tenant boundary), [ADR-0035](../../../ADR/0035-party-persistence-schema-contract-and-tenant-safe-migration-bridges.md) (§ Decision 5: Party must have forced default-deny RLS before it becomes a normal application-visible table), [ADR-0036](../../../ADR/0036-fresh-installation-party-enablement-boundary.md) (Proposed; T123 does not alter its status)

Git Commit: implementation `c2008718db8f6c4a85943274662b0fbed522697f`; reviewed implementation head `4e7615b7544da7f3503e126137414076dca8491e`; QA approval evidence `d0b9636782c22fa68ceb90c7b4e72ed1d7cf8263`

Pull Request: #215 (open; QA Approved; ready for PM pre-merge gate)

Release:

---

## Objective

Install the T123 Party Row-Level-Security backstop: add a reversible Alembic
migration that `ENABLE`s and `FORCE`s Row Level Security on `parties` with
exactly four default-deny, Organization-GUC-driven policies, closing the last
hold-out tenant table per ADR-0021 / ADR-0035 Decision 5 / ADR-0036 — without
touching Party schema, `matter_parties`, the migration ledger, or any
application-layer code — then publish via an implementation PR and stop for
independent QA.

## Tasks Implemented

- New reversible Alembic migration `62cadaff2571` (parent `9c4a7e2d1b5f`):
  - `ALTER TABLE parties ENABLE ROW LEVEL SECURITY` + `FORCE ROW LEVEL
    SECURITY` (no column change: `parties.organization_id` has been NOT NULL
    since T116).
  - Exactly four default-deny policies (`parties_select` / `parties_insert` /
    `parties_update` / `parties_delete`), each scoped by the T105/T122
    null-safe Organization GUC
    `organization_id = NULLIF(current_setting('app.current_organization_id', true), '')::uuid`
    (SELECT/UPDATE/DELETE by `USING`; INSERT/UPDATE by `WITH CHECK`).
  - Downgrade fully reverses: drop the four policies, `NO FORCE`, `DISABLE
    ROW LEVEL SECURITY` — restoring exactly T116's contract while preserving
    all rows and org values (asserted by test).
- Era-split pin of the T122 test module: the T122
  `test_address_tenant_finalization_and_rls.py` disposable fixture now
  provisions at its own head `9c4a7e2d1b5f` (not the moving repository
  `head`), so its "exactly three tenant tables with RLS" catalog assertions
  stay era-correct — the same era-split discipline T122 itself applied to the
  T119/T120-era suites.
- No other files changed: no Party API/app-layer/permission-code changes, no
  `matter_parties`/ledger/`clients`/`properties`/`addresses` changes, no
  changes to `legal_dms_app`'s grants, no shared-development-DB writes.

## Files Modified

- `backend/alembic/versions/62cadaff2571_party_row_level_security_backstop.py`
  (new; parent `9c4a7e2d1b5f`)
- `backend/tests/integration/test_party_tenant_finalization_and_rls.py` (new)
- `backend/tests/unit/test_party_tenant_finalization_foundation.py` (new)
- `backend/tests/integration/test_address_tenant_finalization_and_rls.py`
  (T122 era-pin: disposable fixture pinned to `upgrade_target=NEW_HEAD`
  `9c4a7e2d1b5f`)

## Tests Added

- `test_party_tenant_finalization_foundation.py` (unit, CI-runnable): Party
  schema contract unchanged (org NOT NULL, `uq_parties_organization_id_id`
  support key, `fk_parties_organization_id_addresses` composite FK still
  present); migration wiring (revision `62cadaff2571` extends `9c4a7e2d1b5f`,
  no branch labels/depends); migration intent via recording ops wrapper —
  upgrade emits ENABLE/FORCE then exactly the four CREATE POLICY statements,
  downgrade reverses them with no schema operations.
- `test_party_tenant_finalization_and_rls.py` (integration, disposable DB at
  the T123 head): fresh-upgrade evidence (`current == 62cadaff2571`); catalog
  surface is exactly the four tenant tables {parties, addresses,
  organizations, users} (both `relrowsecurity` and `pg_policies`); parties has
  exactly four default-deny GUC policies with the correct qual/with_check
  split and no `current_user` dependence; `legal_dms_app` owns nothing, is not
  SUPERUSER/BYPASSRLS; Party schema contract unchanged in the catalog; the
  owning/admin path (the T118 executor's `database_url` session) can write a
  Party with no GUC and the owner sees it while the runtime role stays scoped
  (RLS backstopped, not weakened); no-context default denial of every
  command; org-scoped visibility; cross-org SELECT/INSERT/UPDATE/DELETE
  denied; same-org UPDATE and INSERT succeed; org-reassignment UPDATE denied
  by the policy's WITH CHECK; GUC isolation across commit and pooled-
  connection reuse; Party→Address composite-FK integrity through the owning
  path and layered with RLS (app-role org-scoped insert cannot point at a
  cross-org Address); downgrade restoration (last test) back to `9c4a7e2d1b5f`
  with flags (False, False), zero Party policies, rows/org values preserved,
  T122-era three-table RLS surface restored, and the T116 schema contract
  retained.

## Test Results

Implementation-phase validation, run 2026-09-10 (QA is a separate,
independent step; none of this substitutes for it):

- Tooling: `uv run ruff check src tests alembic` — All checks passed;
  `uv run black --check src tests alembic` — 243 files unchanged;
  `git diff --check` — clean.
- New unit tests: `test_party_tenant_finalization_foundation.py` — 6 passed.
- New integration: `test_party_tenant_finalization_and_rls.py` — 26 passed on
  a disposable DB migrated to the head (after one typed-SQL correction below;
  every test green on the final run).
- Era/legacy regressions (all green together, 65 passed): T122
  `test_address_tenant_finalization_and_rls.py` (era-pinned to `9c4a7e2d1b5f`),
  `test_address_null_legacy_upgrade_fails_closed.py`, T122 foundation unit,
  T119 `test_synthetic_migration_rehearsal.py`, T118
  `test_client_migration_executor.py`.
- Full backend suite: **693 passed, 21 skipped**.
- Alembic migration-range cycle on a scratch disposable DB:
  `upgrade head` → `current == 62cadaff2571`, parties RLS (True, True);
  `downgrade 9c4a7e2d1b5f` → parties RLS (False, False);
  `upgrade head` again → `current == 62cadaff2571`, parties RLS (True, True).
  All disposable databases dropped in teardown.
- Shared development database intentionally untouched: alembic current still
  `f3b7c9d1e2a4` (confirmed). No offline `--sql` evidence was produced for
  this phase; range verification used real disposable-DB migrations.
- Governance: `python scripts/governance_validate.py` — OK (0 warnings, 0
  errors); `scripts/tests/test_governance_validate.py` — 51 passed (6
  subtests).

## Design Decisions

- **Mirror T122 exactly.** Identical policy set, GUC expression, ENABLE/FORCE
  ordering, and downgrade — the only divergence is that parties needs no
  column change (org was already NOT NULL since T116).
- **Era-pin the T122 module rather than distort it.** The task requires not
  distorting historical tests to force them through T123; the T122 module's
  exact-three-tenant-table assertions are era-correct only at its own head,
  so its disposable fixture now pins there. This is the only change to
  existing tests, and it is the change T123's own scope requires.
- **Executor compatibility proven via the owning path, not a full T118 run.**
  `client_migration_executor.py` obtains its session from
  `get_session_factory()` → `settings.database_url`, the owning/admin role
  (`backend/src/app/infrastructure/database/session.py`), which bypasses RLS.
  A full executor run at the current head is structurally impossible for
  reasons T122 introduced (its legacy seed requires pre-finalization
  nullable-org Addresses), so compatibility is evidenced two ways: the
  existing T118/T119 suites remain green against the legacy-pinned head, and
  a dedicated test proves a Party write straight through the owning path at
  the T123 head succeeds with the runtime role still RLS-scoped.
- **No `parties:*` permission codes, no app-layer changes, no policy on
  `matter_parties`/ledger** — all explicitly excluded by the T123 row.

## Problems Encountered

- First run of the GUC-isolation test failed on a typed-SQL mistake in one
  negative-assertion INSERT (four VALUES supplied against five target
  columns); the missing `party_type` literal was added and the full module
  re-ran green.
- Project tooling drift surfaced as fixture-format nits: black (pinned
  `line-length = 100`) wanted the T122 era-pin joined to its canonical
  exactly-100-character single line, and my new files needed trailing-newline
  / long-line normalization. Resolved by applying the project's own black
  formatting; no unrelated reformatting of pre-existing files occurred
  (ruff/black clean against the full `src tests alembic` surface).

## Deferred Work

The PM pre-merge gate and merge of PR #215 remain pending. The full-history
Alembic offline SQL JSONB literal-rendering failure (around the pre-existing
`9963e15f2752` seed migration) remains a pre-existing limitation outside T123;
the T123 migration range and disposable-PostgreSQL behavior are valid.
- ADR-0036 remains **Proposed**; T123 implements its Decision 5 prerequisite
  but does not accept the ADR itself.
- Required ADR **#20** remains unresolved — unrelated to and unaffected by
  T123.
- T124+ remain unauthorized.

## Future Considerations

- `parties` is now the fourth tenant table under forced default-deny RLS
  (alongside `organizations`, `users`, `addresses`). Any future Party
  application surface will get org scoping for free via the existing
  tenant-context GUC plumbing (`JwtAuthenticationProvider` /
  `sqlalchemy_user_repository.py`) — no new backstop work needed.
- When `matter_parties` and the migration ledger later gain RLS, a following
  migration will extend the policy surface; the "exactly N tenant tables"
  assertions in T122/T123 era modules will need similar era-pin treatment.
- The pre-existing full-history offline `--sql` JSONB literal-rendering
  limitation (T116 seed migration) remains present and unaffected; T123's own
  range was verified against real disposable databases instead.

## Reviewer Checklist

- ☑ Architecture preserved
- ☑ Existing design patterns followed
- ☑ Tests added
- ☑ Existing tests pass
- ☑ Documentation updated
- □ ADR updated (if required)
- □ AI_BOOTSTRAP updated (if required)
- □ PROJECT_STATE updated (if required)
- ☑ No unrelated refactoring
- ☑ No scope creep
- ☑ Ready for QA

Notes on unchecked boxes: "ADR updated" — no architectural decision was
created or changed this phase (correct N/A; ADR-0036 status unchanged);
"AI_BOOTSTRAP updated" — no standing convention changed (N/A);
"PROJECT_STATE updated" — closeout synchronization is the Documentation
Manager's responsibility after QA, per `docs/ImplementationLog/README.md`.

## QA Decision

Approved. Independent QA reviewed implementation head
`4e7615b7544da7f3503e126137414076dca8491e` against authorization baseline
`33536b0c9ef20fbdf7d86a0ec92750b5a644b873`; QA-only evidence
`d0b9636782c22fa68ceb90c7b4e72ed1d7cf8263` (which changed only
`docs/reviews/T123_QA_Review.md`) is on the remote PR head. The review
confirms enabled/forced Party RLS with exactly the four intended
Organization-scoped default-deny policies, no-GUC and cross-Organization
denial, tenant-GUC isolation, Party-to-Address same-Organization integrity,
T118 owning/admin-path compatibility, the T122 era-pin to `9c4a7e2d1b5f` as
legitimate historical-era testing, range-scoped offline downgrade SQL, and
exact-head CI green. PR #215 remains open and is not recorded as merged.