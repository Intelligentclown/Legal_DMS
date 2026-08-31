# ADR-0032: User–Organization Pre-Existing-Data Reconciliation

**Status:** Proposed
**Date:** 2026-08-31

**Resolves:** the narrow reconciliation-mechanism gap `ADR/0031` §6.7/§12 explicitly named and declined
to design: how a `User` row created *before* `ADR/0031` existed — and therefore before
`users.organization_id` existed — is associated with an Organization once that column is introduced.
**This ADR intentionally does not claim to resolve any numbered item on the specification's own §21
Required-ADR planning list** — see "Does not resolve" immediately below for exactly why, stated there
rather than here so this repository's own governance validator (which parses this field literally for
resolution claims) does not mistake a narrative reference for a resolution claim, and so a future ADR
that resolves that list's migration-strategy item in full is never blocked by a false duplicate-
resolution conflict with this one.

**Does not resolve:** the item on the specification's §21 Required-ADR planning list covering overall
migration strategy — that item covers Matter's `client_id`/`property_id`/`matter_type_id` retirement,
Document's `matter_id`→`file_id` redirect, and every other entity's own migration sequencing, none of
which this ADR touches; only the narrow, `ADR/0031`-flagged User/Organization reconciliation question
above is in scope, and that item's planning-list number remains genuinely unresolved after this ADR,
not silently narrowed or partially claimed. Also does not resolve the planning-list items covering
Document/File relationship mechanics, Document/version architecture, Workflow vs. Government Status,
core-vs-configurable vocabulary, UUID-vs-human-readable identifiers, or soft deletion/history. Does not
reopen `ADR/0031`, `ADR/0021`, `ADR/0022`, `ADR/0020`, `ADR/0018`, `ADR/0019`, `ADR/0029`, `ADR/0030`,
or any other accepted ADR. Does not design, authorize, or begin Organization/Tenant Core implementation
(schema, backend, frontend, API, or migration application) — that remains a separate, future,
separately re-gated task.

**Dependencies:** `ADR/0031` (the seven items this ADR treats as already frozen — cardinality,
bootstrap-folded creation, first-Administrator semantics, membership representation, tenant-context
resolution, `CurrentUser` extension — and whose own §6.7/§12 disclosure this ADR resolves).
`ADR/0021` (tenant-boundary fail-closed principle — directly informs why an unreconciled `NULL`
`organization_id` cannot be left as a permanent valid state). `ADR/0020` (transaction boundary — this
ADR's atomicity requirement composes with it directly). `ADR/0018` D4 (the interactive-only,
no-argv/env/config first-admin bootstrap precedent this ADR's mechanism directly extends).

## 1. Context

`ADR/0031` decided that first-Organization creation is folded into the existing `bootstrap-admin` CLI
(T67/`ADR-0018` D4) — for a *fresh* deployment, Organization, first `User`, and membership are all
created together, in one transaction, and `users.organization_id` is never `NULL` for a bootstrap-era
admin. But this repository already has deployments that bootstrapped *before* `ADR/0031` existed: `T83`'s
own governance record confirms `legal_dms_dev` has exactly one `User` row (the bootstrapped
Administrator) created via `bootstrap-admin` before any Organization concept existed. `ADR/0031` §6.7
names this precisely: *"a nullable `organization_id` column is additive... What it does require...
[is] a decision for how this repository's existing `User` rows... are associated with an
Organization... This ADR states the requirement exists; it does not sequence, design, or resolve it."*

## 2. Problem

Once the Organization/Tenant Core migration eventually adds `users.organization_id`, a database that
already has `User` rows from before `ADR/0031` will have those rows with `organization_id IS NULL`.
`ADR/0021`'s own fail-closed principle means any tenant-scoped operation attempted by such a User must
be rejected — permanently stranding the bootstrapped Administrator from a working system unless a
reconciliation mechanism exists. Without one, a future implementer would face exactly the "unauthorized
ad hoc workaround" `T103`'s own authorization named as the risk this task exists to prevent.

## 3. Decision

**A dedicated, one-time, interactive CLI command — mirroring `bootstrap-admin`'s own established shape
exactly — reconciles pre-existing `User` rows by creating exactly one Organization (if any
`organization_id IS NULL` row exists) and assigning every such row to it, atomically, in a single
transaction.** This is a **mechanism decision**, not a data-migration-embedded-in-Alembic decision:
schema change (adding the nullable column) and data reconciliation (populating it for legacy rows)
are kept as two separate concerns, exactly as this repository already separates "seed lookup data via
Alembic" from "create the first identity-bearing business row via an interactive CLI" (T67's own
precedent).

**What the auto-created Organization represents — resolved from existing evidence, not invented:** it
represents **the actual, real legal practice operating this deployment** — not a throwaway "legacy"
placeholder, not an arbitrarily-chosen tenant, and not a synthetic "System" account. This follows
directly from evidence already established, not newly asserted here: `docs/BusinessRequirementsPlan.md`
describes a single-practice internal tool throughout (no multi-firm/client-facing scenario named
anywhere); `ADR/0021`'s own deployment-scale assumption is explicitly "a single legal-documentation
office's internal tool"; `ADR/0031`'s own cardinality decision (one-to-one) rests on the same
single-practice premise. Given a deployment has, by this already-established assumption, exactly one
real practice using it, every pre-existing `User` row in that deployment's database necessarily
belongs to that same one, real Organization — there is no second candidate Organization to choose
among, so this is a mechanical consequence of already-accepted evidence, not a new business choice.

**What remains genuinely unresolved by this ADR, and is not invented here:** the Organization's actual
identifying content (its name/legal-name, per `ADR/0031` §1's own `DERIVED` "near-certainly required"
field) is real business data only the deployment operator knows — this ADR does not hardcode, default,
or guess it. The command prompts for it interactively at the point of reconciliation, mirroring
`ADR/0018` D4's own reasoning for why first-admin credentials are never accepted via argv/env/config:
identity-bearing business data belongs to an interactive prompt, not a script default.

**Idempotency:** the command checks for any `organization_id IS NULL` `User` row before doing anything.
If none exist (a fresh, post-`ADR/0031` deployment, or a database already reconciled), it prints a
message and exits cleanly — no error, no duplicate Organization, mirroring `bootstrap-admin`'s own
idempotency check exactly.

## 4. Alternatives Considered

| Alternative | Assessment against the stated criteria |
|---|---|
| **A dedicated, interactive, idempotent CLI command creating one Organization and backfilling every `NULL`-organization `User` row to it (selected)** | **Tenant isolation:** satisfies `ADR/0021`'s fail-closed principle by eliminating the `NULL` state rather than tolerating it. **Data integrity/deterministic behavior:** exactly one Organization created, deterministic assignment (every `NULL` row, not a subset). **Bootstrap-admin continuity:** directly extends an already-proven, already-accepted pattern — same interactive-only discipline, same idempotency shape. **Repeatability/idempotency:** a second run is a safe no-op. **Operational safety:** no destructive operation; additive only. **Auditability:** composes with `ADR/0029`'s existing "creation" coverage category (disclosed, not designed, in §7). **Future migration compatibility:** does not touch or conflict with `ADR/0031`'s own bootstrap-extension path for fresh deployments — the two are mutually exclusive by construction (a fresh deployment never has a `NULL`-organization row to reconcile). |
| **A data-migration step embedded directly in the Alembic migration that adds the column** | Rejected — this repository's own migrations are non-interactive by convention (run in CI/deployment pipelines); prompting for a real Organization name mid-migration would be a genuinely new, unevidenced pattern this repository has never used, and risks the migration blocking or failing in a non-interactive deployment context. Schema change and data reconciliation are kept as two separably-runnable steps instead, matching T67's own precedent for exactly this reason. |
| **Explicit/manual reconciliation only — no automatic default, an operator manually assigns each `User` individually** | Rejected as the *default* mechanism — for the actual evidenced case (a single bootstrapped Administrator, single practice), forcing a per-row manual assignment step solves a multi-candidate-Organization problem that does not exist for this product's evidenced deployment shape, adding operational burden with no corresponding benefit. Not designed as a formal alternative path here since no evidence names a database with more than one candidate Organization to choose among; if one is ever discovered, that is new evidence warranting a superseding decision, not something to design speculatively now. |
| **Leave `organization_id` `NULL` indefinitely for legacy Users; treat "no Organization" as a permanently valid state** | Rejected outright — directly contradicts `ADR/0021`'s fail-closed principle and would permanently strand the bootstrapped Administrator, a pure regression with no offsetting benefit. |
| **Silently default all `NULL`-organization Users into a synthetic, unnamed "Legacy"/"Default" Organization with a hardcoded placeholder name** | Rejected — this is precisely the "unapproved tenant identity" / "silently invented business assumption" this task's own authorization warned against. A hardcoded placeholder misrepresents the real practice's own Organization record and would need a real, undecided rename/re-identification event later to correct — deferring a problem this ADR can resolve now by simply asking the operator once, at reconciliation time. |

## 5. Consequences

- A future implementer building the reconciliation command has an unambiguous mechanism to build
  against: interactive CLI, idempotent, one atomic transaction, one Organization, every `NULL`-
  organization `User` row reconciled to it.
- The command's own registration (a new `[project.scripts]` entry in `backend/pyproject.toml`,
  mirroring `bootstrap-admin`'s exact registration shape) is a concrete, checkable implementation
  consequence — not designed further here (no script content, no CLI flag surface decided).
- Every fresh, post-`ADR/0031` deployment never triggers this command's reconciliation branch at all
  (no `NULL`-organization row ever exists for it) — this ADR adds no new obligation to the already-
  decided fresh-bootstrap path.

## 6. Migration/Reconciliation Semantics

Two, mutually-exclusive scenarios, distinguished purely by whether any `organization_id IS NULL`
`User` row exists at the time the reconciliation command is run:

1. **Fresh deployment, or already-reconciled database:** no `NULL` rows exist → no-op, exits cleanly.
2. **Legacy, pre-`ADR/0031` deployment (e.g. `legal_dms_dev`, per `T83`):** one or more `NULL` rows
   exist → the operator is prompted for the real Organization's name, exactly one Organization row is
   created, and every `NULL`-organization `User` row is updated to reference it, all within one
   transaction (`ADR/0020`).

## 7. Existing-User Handling

Every existing `User` row with `organization_id IS NULL` at reconciliation time is treated identically
— assigned to the single, newly-created Organization. No row is skipped, no row is treated specially by
role, `is_active` status, or any other field; the specification's own single-practice-per-deployment
assumption (§3 above) gives no basis for differential treatment, and inventing one here would itself be
an unevidenced business rule.

## 8. Failure/Rollback Implications

Per `ADR/0020`'s existing one-request-one-commit-boundary discipline, extended here to this
command's own transaction: if the reconciliation fails partway (Organization created but not all
`User` rows updated, or vice versa), the whole operation must roll back, leaving the database exactly
as it was before the command ran — never a partially-reconciled state where some `User` rows reference
the new Organization and others remain `NULL`. Re-running the (idempotent) command after a failed
attempt is the recovery path — no separate rollback procedure is designed here, since the atomicity
requirement itself is what makes a clean re-run always safe.

## 9. Relationship to `ADR/0021`

This ADR does not modify `ADR/0021`'s enforcement mechanism (mandatory application-layer scoping +
RLS backstop, fail-closed) in any way. It exists specifically to eliminate the one condition (a
`User` with `organization_id IS NULL` after the column is introduced) that `ADR/0021`'s own fail-closed
principle would otherwise leave as a permanently broken state for legacy deployments — a
consequence of `ADR/0021`, not a modification to it.

## 10. Relationship to `ADR/0031`

`ADR/0031`'s own seven decisions are all treated as frozen and reused directly: this ADR's mechanism
produces the identical column shape §6.4 already decided (`users.organization_id`, nullable FK,
one-to-one cardinality); it does not introduce a second membership representation, a join table, or
any relationship to `UserRole` beyond what `ADR/0031` already established. `ADR/0031` §6.7 is the
provision this ADR directly resolves; no other part of `ADR/0031` is touched, reinterpreted, or
narrowed.

## 11. Explicit Scope Boundary

This ADR decides only the reconciliation *mechanism* for pre-`ADR/0031` `User` rows: that it is a
dedicated interactive CLI command (not an embedded data migration), that it creates exactly one
Organization representing the deployment's real practice (not a placeholder), that the Organization's
identifying content is operator-supplied at run time (not invented), and that the operation is
idempotent and atomic. Nothing else.

## 12. What This ADR Does NOT Decide

- The general Required ADR #20 migration strategy for any other entity (Matter's `client_id`/
  `property_id`/`matter_type_id` retirement, Document's `matter_id`→`file_id` redirect, or any other
  entity's own migration sequencing).
- The reconciliation command's own literal implementation (script name beyond the registration
  pattern noted in §5, exact prompts, exact error messages, exact database queries).
- Whether/how this command is invoked as part of a larger deployment runbook for the Organization/
  Tenant Core slice — that is that future, separately-authorized task's own operational-procedure
  concern.
- Required ADR #10, #11, #12, #15, #16, #17.
- Any part of `ADR/0031`, `ADR/0021`, `ADR/0022`, `ADR/0020`, `ADR/0018`, `ADR/0019`, `ADR/0029`,
  `ADR/0030`, or any other accepted ADR.
- Organization/Tenant Core implementation of any kind (schema, backend, frontend, API, migration
  application).

## 13. Implementation Consequences (stated, not implemented)

A future, separately-authorized implementation task building the Organization/Tenant Core slice would
need to: register a new `[project.scripts]` entry in `backend/pyproject.toml` (mirroring
`bootstrap-admin = "app.infrastructure.cli.bootstrap:main"`'s exact shape) for this reconciliation
command; implement its idempotency check (`SELECT` for any `organization_id IS NULL` `User` row,
mirroring `bootstrap.py`'s own `_any_user_exists()` shape); implement the interactive prompt for the
Organization's name (mirroring `bootstrap.py`'s `input()`/`getpass()` split, though no credential is
involved here — a plain `input()` is sufficient); and implement the atomic Organization-creation-plus-
User-update transaction (mirroring `run_bootstrap()`'s own `flush()`-then-caller-commits shape,
composing with `ADR/0020`). None of this is implemented by this ADR — stated as the concrete shape a
future task should build against, per §16's acceptance criteria.

## 14. Acceptance Criteria for Future Implementation

A future implementation task, once separately authorized, should be verifiable against:

- **No-op on a clean database:** running the command against a database with zero `organization_id
  IS NULL` `User` rows creates no Organization and modifies no row.
- **Deterministic single-Organization backfill:** running the command against a database with N
  `organization_id IS NULL` `User` rows creates exactly one Organization and updates all N rows to
  reference it — never zero, never more than one Organization created.
- **Atomicity:** a simulated failure partway through (mirroring `ADR/0020`'s own
  `test_get_db_transaction_policy.py` pattern) leaves no partially-reconciled state — either the
  Organization and all row updates exist, or none of them do.
- **Idempotency:** running the command twice in succession is safe — the second run is a no-op,
  producing no second Organization and no error.
- **No hardcoded/placeholder Organization name:** a test confirming the command requires and uses
  operator-supplied input for the Organization's name, never a default/placeholder string.
- **Interoperability with `ADR/0031`'s bootstrap path:** a test confirming a *fresh* deployment (one
  that runs the `ADR/0031`-extended `bootstrap-admin` first) never has a `NULL`-organization `User`
  row for this command to act on — the two mechanisms are mutually exclusive in practice, not merely
  in this ADR's own prose.

These are acceptance criteria for a future implementation task to satisfy, not tests this ADR itself
adds — no test file, script, or application code is created or modified by this ADR.

## References

- `ADR/0031-user-organization-membership-onboarding-tenant-context.md` (§6.2, §6.4, §6.7, §12, §15)
- `ADR/0021-organization-tenant-boundary-enforcement.md` (fail-closed principle)
- `ADR/0020-session-commit-rollback-policy.md` (transaction boundary)
- `ADR/0018-authentication-authorization-architecture.md` (D4 — interactive-only bootstrap precedent)
- `ADR/0029-activity-vs-audit-architecture-boundary-and-coverage.md` (audit-significance of creation
  events, cited for §5's disclosure only)
- `backend/src/app/infrastructure/cli/bootstrap.py` (the extended precedent this mechanism mirrors)
- `backend/pyproject.toml` (`[project.scripts]` registration convention)
- `docs/BusinessRequirementsPlan.md` (single-practice deployment context)
- `IMPLEMENTATION_QUEUE.md`'s `T83` row (the concrete, non-theoretical evidence this reconciliation
  is needed against a real, existing database)
