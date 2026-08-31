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

**REWORK NOTICE (2026-08-31):** this section originally decided that the reconciliation mechanism
should *automatically* create exactly one Organization and assign every pre-existing `NULL`-
organization `User` row to it, reasoning that the product is a single-practice-per-deployment tool.
That reasoning was wrong and has been withdrawn — see "3a. Corrected Multi-Practice Analysis" below
for why, and "3b. Corrected Decision" for the replacement. The withdrawn reasoning is not deleted from
this ADR's history; it is superseded in place, consistent with this repository's own practice of
recording a defect and its correction rather than silently rewriting history (`docs/reviews/
T103_Software_Architect_Report.md`'s own Rework section carries the full account).

### 3a. Corrected Multi-Practice Analysis

The withdrawn reasoning rested on an inference — "this deployment serves exactly one practice" — drawn
from `ADR/0021`'s stated *deployment-scale assumption* ("a single legal-documentation office's internal
tool," used there only to justify shared-schema over schema-per-tenant on operational-cost grounds) and
from an incomplete reading of `docs/BusinessRequirementsPlan.md`. That inference does not survive
closer inspection of either source:

- **`docs/BusinessRequirementsPlan.md`'s own status note, quoted verbatim and in full this time:** *"the
  system is not scoped to a single practitioner and is intended for use by multiple users/practices once
  complete."* The withdrawn reasoning cited this document's general single-practice framing while missing
  this specific, directly on-point sentence.
- **`ADR/0021`'s own architecture is itself first-party evidence against single-Organization-per-database.**
  `ADR/0021` did not merely permit tenant isolation as a defensive nicety — it built a genuinely
  multi-tenant enforcement mechanism: mandatory, non-nullable `organization_id` on every tenant-scoped
  table, `FORCE`d default-deny Row-Level Security, and an explicit rejection of schema-per-tenant/
  database-per-tenant *on cost grounds*, which presupposes multiple tenants actually need isolating within
  one shared database. A product where every deployment genuinely serves only one Organization would need
  none of this — a single-tenant deployment has nothing to isolate from. The existence of `ADR/0021`'s
  entire hybrid enforcement design is direct evidence that this repository's own architecture already
  expects multiple Organizations to coexist within one database.
- **This does not reopen `ADR/0031`.** `ADR/0031`'s actual decision — a given `User` belongs to at most
  one Organization (cardinality) — is a separate, orthogonal question from "how many Organizations exist
  in total in one database," and is fully compatible with many Organizations coexisting: a standard
  multi-tenant shape has exactly this property (each user in exactly one org; many orgs total). Nothing
  about the corrected analysis below requires touching `ADR/0031`'s cardinality decision, and it is not
  reopened here.

**Consequence for reconciliation:** a mechanism that automatically groups *every* pre-existing
`NULL`-organization `User` row into one auto-created Organization is not a safe product-wide migration
rule. If a given deployment's legacy data in fact spans more than one practice — which the repository's
own architecture is built to support and the product's own requirements document says is the intended
target market — that mechanism would silently merge distinct practices' Users into a single tenant, a
genuine tenant-isolation/confidentiality failure of exactly the kind `ADR/0021` exists to prevent.

**What is, and is not, safely inferable from `T83`'s evidence.** `T83`'s record — `legal_dms_dev` has
exactly one pre-existing `User` row — is real, valid evidence that the reconciliation *problem* exists
(a working reconciliation mechanism is genuinely needed). It is *not* valid evidence for a *universal
migration rule* that every deployment's legacy data belongs to one practice; one observed database
proves the problem is real, not that every future case has the same shape. Conversely, this correction
does not invent an opposite universal rule ("legacy data always spans multiple practices") either —
that would be equally unsupported. Neither shape is assumed; the mechanism itself must not presume
either one.

### 3b. Corrected Decision

**A dedicated, interactive CLI command — still mirroring `bootstrap-admin`'s own established shape,
still separate from Alembic, still atomic, still idempotent, still free of any hardcoded/placeholder
Organization identity — reconciles pre-existing `User` rows by requiring the deployment operator to
explicitly map each `organization_id IS NULL` `User` row to an Organization, creating one or more
Organizations as the operator specifies, rather than presuming a single Organization for all of
them.** The command supports creating however many Organizations the operator's actual legacy data
requires (one, in the common single-practice case this repository has direct evidence for via `T83`;
more, if the operator's data genuinely spans multiple practices) — but the *number* and the *mapping*
are operator-supplied facts about real-world data the architecture cannot see, never an architectural
default.

**The distinction this correction preserves, stated explicitly per this task's own governing
instruction:** a deployment operator who already knows their own legacy data (which existing Users
belong to which practice) *entering that mapping* is fundamentally different from *the architecture
deciding, as a rule, that all Users necessarily belong to one Organization*. The corrected mechanism
requires the former and forbids the latter. In the common case where the operator's answer genuinely is
"one Organization, all existing Users" (as `legal_dms_dev` most likely is, per `T83`), the interactive
flow is short — but that outcome is reached because the operator said so, not because the mechanism
assumed it.

**What the mechanism must not do, restated as an explicit safety constraint:** it must never produce an
Organization-to-User assignment without the operator having explicitly confirmed which Users belong to
which Organization. There is no code path in this design that infers a grouping from existing data —
today's pre-`ADR/0031` schema has no field anywhere that could distinguish "practice A's User" from
"practice B's User" (confirmed: no tenant-adjacent column exists on `users` prior to this reconciliation
column itself), so no automatic grouping heuristic is even technically possible without inventing
unevidenced data; requiring explicit operator input is not merely the safer choice, it is the only
choice consistent with what the data actually contains.

**Organization identity remains operator-supplied, as originally decided and unchanged by this rework:**
each Organization's name is entered interactively at the point of creation — never hardcoded, never
defaulted, never inferred — mirroring `ADR/0018` D4's reasoning for why identity-bearing data belongs to
an interactive prompt, exactly as the withdrawn version of this section already correctly established
for the single-Organization case; the correction is to how many Organizations and which Users go where,
not to how each Organization's identity is captured.

**Idempotency, preserved:** the command checks for any `organization_id IS NULL` `User` row before doing
anything. If none exist (a fresh, post-`ADR/0031` deployment, or a database already fully reconciled —
every existing User assigned to some Organization by a prior run), it prints a message and exits
cleanly. A partially-completed prior run (some Users mapped, others still `NULL`, only possible if a
prior attempt was interrupted before its own commit — see §8) is not a distinct idempotent state; §8's
atomicity guarantee means a prior run either fully committed (leaving no `NULL` rows) or fully rolled
back (leaving the pre-run state exactly, including all rows still `NULL`) — the command has no
in-between state to special-case.

## 4. Alternatives Considered

| Alternative | Assessment against the stated criteria |
|---|---|
| **Automatic single-Organization backfill — create exactly one Organization, assign every `NULL`-organization `User` to it (the withdrawn original decision)** | **Rejected on rework.** Fails **tenant isolation** and **multi-practice semantics** — the two highest-priority criteria per this task's own safety requirement: if a deployment's legacy data spans more than one practice, this silently merges them into one tenant, exactly the confidentiality failure `ADR/0021`'s entire enforcement design exists to prevent. Scored well on **determinism**/**operational simplicity** in isolation, but those do not outweigh a tenant-isolation failure mode. |
| **Explicit operator mapping — the operator maps each `NULL`-organization `User` to an Organization (creating one or more as needed), no automatic grouping (selected)** | **Tenant isolation:** no code path can produce a cross-practice assignment, since no assignment happens without operator confirmation. **Data integrity:** atomic per §8, unchanged. **Bootstrap-admin continuity:** still a dedicated interactive CLI, still separate from Alembic, still mirroring the same precedent — only the *shape* of the interaction (mapping, not a single default) changes. **Repeatability/idempotency:** unchanged — a second run against a fully-reconciled database is a no-op. **Operational safety:** additive only, unchanged; a genuinely single-practice deployment still completes in a short interactive flow. **Failure behavior:** unchanged, §8. **Auditability:** unchanged, composes with `ADR/0029`. **Multi-practice semantics:** now genuinely supported — this is the corrected criterion this rework exists to satisfy. **Future migration compatibility:** unchanged — still mutually exclusive with `ADR/0031`'s fresh-bootstrap path by construction. |
| **A data-migration step embedded directly in the Alembic migration that adds the column** | Still rejected, unchanged from the original analysis — this repository's own migrations are non-interactive by convention; an interactive step (whether prompting for one Organization's name or for a full multi-Organization mapping) does not belong embedded in Alembic DDL, only more so now that the interaction is richer, not simpler. |
| **An automatic heuristic that attempts to infer practice groupings from existing data (e.g. by role, creation date, or another existing column)** | Rejected — no column on today's pre-`ADR/0031` schema encodes practice membership in any form (confirmed: no tenant-adjacent field exists on `users` prior to this reconciliation column); any such heuristic would be inventing a grouping signal the data does not actually contain, precisely the "silently invented business assumption" this task's own authorization and this rework's own governing instruction both prohibit. |
| **Leave `organization_id` `NULL` indefinitely for legacy Users; treat "no Organization" as a permanently valid state** | Still rejected, unchanged — directly contradicts `ADR/0021`'s fail-closed principle and would permanently strand every legacy User, a pure regression with no offsetting benefit. |
| **Silently default all `NULL`-organization Users into a synthetic, unnamed "Legacy"/"Default" Organization with a hardcoded placeholder name** | Still rejected, unchanged — remains exactly the "unapproved tenant identity" this task's own authorization warned against, now doubly so since it would also risk merging distinct practices into that one placeholder. |

## 5. Consequences

- A future implementer building the reconciliation command has an unambiguous mechanism to build
  against: interactive CLI, idempotent, one atomic transaction, one-or-more Organizations per the
  operator's own explicit mapping, every `NULL`-organization `User` row reconciled to whichever
  Organization the operator assigned it to.
- The command's own registration (a new `[project.scripts]` entry in `backend/pyproject.toml`,
  mirroring `bootstrap-admin`'s exact registration shape) is a concrete, checkable implementation
  consequence — not designed further here (no script content, no CLI flag surface, no exact prompt
  sequence decided).
- Every fresh, post-`ADR/0031` deployment never triggers this command's reconciliation branch at all
  (no `NULL`-organization row ever exists for it) — this ADR adds no new obligation to the already-
  decided fresh-bootstrap path.
- The interactive surface is necessarily larger than the withdrawn single-Organization version (the
  operator must be walked through a mapping, not just a single name prompt) — an accepted operational
  cost of correctness, not a defect; the common single-practice case (per `T83`'s evidence) still
  resolves in a short flow, since the operator's own answer in that case is simply "one Organization,
  all of them."

## 6. Migration/Reconciliation Semantics

Two, mutually-exclusive scenarios, distinguished purely by whether any `organization_id IS NULL`
`User` row exists at the time the reconciliation command is run:

1. **Fresh deployment, or already-reconciled database:** no `NULL` rows exist → no-op, exits cleanly.
2. **Legacy, pre-`ADR/0031` deployment (e.g. `legal_dms_dev`, per `T83`):** one or more `NULL` rows
   exist → the operator is walked through mapping every such `User` row to an Organization — creating
   one or more Organizations, each with an operator-supplied name, as the operator's own mapping
   requires — and every `NULL`-organization `User` row is updated to reference the Organization the
   operator assigned it to, all within one transaction (`ADR/0020`). The number of Organizations
   created is whatever the operator's mapping produces (one, in the common case this repository has
   direct evidence for; more, if warranted) — never a number this ADR presumes in advance.

## 7. Existing-User Handling

Every existing `User` row with `organization_id IS NULL` at reconciliation time must be explicitly
accounted for by the operator's mapping before the transaction commits — none may be silently defaulted,
silently skipped, or silently grouped by an inferred heuristic. No row is treated specially by role,
`is_active` status, or any other field beyond the operator's own explicit Organization assignment; the
mechanism has no basis — and, per §3a, no data — for inferring differential treatment on its own.

## 8. Failure/Rollback Implications

Per `ADR/0020`'s existing one-request-one-commit-boundary discipline, extended here to this
command's own transaction: if the reconciliation fails partway (some Organizations created but not all
mapped `User` rows updated, an operator abort mid-mapping, or any other interruption), the whole
operation must roll back, leaving the database exactly as it was before the command ran — never a
partially-reconciled state where some `User` rows reference a newly-created Organization and others
remain `NULL`, and never a state with an Organization created but no Users actually assigned to it.
This matters more, not less, than in the withdrawn single-Organization version: a partial multi-
Organization mapping left uncommitted could otherwise leave some Users correctly isolated and others
not, a strictly worse failure mode than the single-Organization case's simpler partial state. Re-running
the (idempotent) command after a failed or aborted attempt is the recovery path — the operator simply
re-enters the mapping; no separate rollback procedure is designed here, since the atomicity requirement
itself is what makes a clean re-run always safe.

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
dedicated interactive CLI command (not an embedded data migration), that it requires an explicit
operator-supplied mapping of existing Users to Organizations rather than presuming a single-Organization
default, that each Organization's identifying content is operator-supplied at run time (not invented),
and that the operation is idempotent and atomic regardless of how many Organizations the operator's
mapping produces. Nothing else.

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
mirroring `bootstrap.py`'s own `_any_user_exists()` shape); implement an interactive flow that lists the
unassigned Users and walks the operator through creating one or more Organizations and mapping each
User to one of them (no exact UI/prompt sequence decided here — a per-User prompt, a batch-selection
prompt, or another interaction shape are all consistent with this ADR; only the *requirement* that every
User be explicitly mapped, never defaulted, is decided); and implement the atomic multi-Organization-
creation-plus-User-update transaction (mirroring `run_bootstrap()`'s own `flush()`-then-caller-commits
shape, composing with `ADR/0020`, generalized from one Organization to however many the mapping
produces). None of this is implemented by this ADR — stated as the concrete shape a future task should
build against, per §14's acceptance criteria.

## 14. Acceptance Criteria for Future Implementation

A future implementation task, once separately authorized, should be verifiable against:

- **No-op on a clean database:** running the command against a database with zero `organization_id
  IS NULL` `User` rows creates no Organization and modifies no row.
- **No assignment without explicit operator mapping:** a test confirming the command cannot complete
  without the operator explicitly mapping every `NULL`-organization `User` row to an Organization —
  no code path produces an assignment the operator did not confirm.
- **Multi-Organization support:** a test confirming the command can produce more than one Organization
  in a single reconciliation run when the operator's mapping calls for it — the mechanism must not be
  hardcoded to a single-Organization outcome.
- **Single-Organization case still works simply:** a test confirming the common case (all existing
  Users mapped to one, newly-created Organization — the shape `T83`'s own evidence suggests for
  `legal_dms_dev`) completes correctly and without unnecessary friction.
- **Atomicity:** a simulated failure or operator abort partway through (mirroring `ADR/0020`'s own
  `test_get_db_transaction_policy.py` pattern) leaves no partially-reconciled state — either every
  Organization and every mapped row update exist, or none of them do.
- **Idempotency:** running the command twice in succession is safe — the second run (against a fully-
  reconciled database) is a no-op, producing no additional Organization and no error.
- **No hardcoded/placeholder Organization name:** a test confirming the command requires and uses
  operator-supplied input for every Organization's name, never a default/placeholder string.
- **No inferred grouping:** a test confirming the command never groups Users by role, creation date, or
  any other existing column as a substitute for explicit operator mapping.
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
- `docs/BusinessRequirementsPlan.md` (its own status note: *"the system is not scoped to a single
  practitioner and is intended for use by multiple users/practices once complete"* — the evidence this
  rework is built on)
- `IMPLEMENTATION_QUEUE.md`'s `T83` row (the concrete, non-theoretical evidence this reconciliation
  is needed against a real, existing database — evidence that the problem is real, not evidence for a
  universal single-Organization migration rule; see §3a)
