# ADR-0029: Activity vs Audit — Architectural Boundary and Coverage Expectations

**Status:** Proposed
**Date:** 2026-08-29

**Resolves:** `docs/Legal_DMS — Domain Model & Functional Specification.md` §21 planning-list item
**#14** ("Activity vs Audit").

**Does not resolve:** Required ADR #1–#7, #9, #13, #18, #19 (already resolved by `ADR/0021`–`ADR/0028`,
not reopened here) or Required ADR #8, #10, #11, #12, #15, #16, #17, #20 (untouched). Does not reopen
[ADR-0007](0007-audit-logging-without-database-table.md) or
[ADR-0009](0009-audit-logs-table-reverses-adr-0007.md) — both are cited and composed with, exactly as
they stand.

**Dependencies:** `ADR/0007`/`ADR/0009` (the existing `AuditLogger` port / `audit_logs` lineage this
ADR builds coverage expectations on top of, not reopens). `ADR/0021` (tenant isolation — cited below
for a disclosed, unresolved gap on the two pre-existing tables this ADR discusses; not reopened).
`ADR/0022` (authorization — the existing `permission_denied` audit call already composes with it,
unchanged). `ADR/0023` (Party/Client — `Party` is realized today by the `Client` model pending that
ADR's own subtype-modeling resolution; this ADR's Party coverage expectation applies to whichever
model currently realizes Party). Required ADR #8 (Matter-vs-File lifecycle — a disclosed, non-blocking
soft dependency for File's own coverage expectation, since File does not yet exist as a persisted
entity; see "File" below).

## Context

The governed specification freezes, as a Confirmed Business Rule, that Activity and Audit are
different concepts: **§4 rule 41 — "Audit is distinct from Activity."** Two further rules bound
Audit specifically: **rule 42 — "Historical actions remain attributable to the original actor"** and
**rule 46 — "Historical security/audit information must not be silently altered."** Rule 39
("Communication, Task, Follow-up and Activity are distinct") and rule 40 ("Timeline is a unified
view, not a replacement for underlying records") establish the same non-conflation discipline for
Activity's own neighboring concepts. §2's Feature Catalogue rates Activity "High" priority and Audit
"Critical" — the only "Critical" row in the entire Security domain.

§17.9 ("Audit tests") states the specification's own operative test for what must be audited, and
what an audit record must preserve, verbatim:

> Every sensitive change must preserve: actor, timestamp, entity, action, before/after or equivalent
> change information.

The Audit domain's own bullet list (§21, "Audit" group) names exactly six categories: **creation,
modification, status changes, relationship changes, financial changes, access-sensitive events.**
This ADR treats that six-category list as the specification's own concrete classification boundary
for "materially significant" — see "Coverage Expectations" below — rather than inventing a separate
one.

### Repository baseline (direct inspection, this ADR's authoring baseline)

- **`activity_logs` (`activity.py:27`, `ActivityLog`) exists** — `entity_type` (`String(100)`,
  unenforced), `entity_id` (`UUID`, no FK), `action`, `actor_id` (FK to `users`, nullable),
  `occurred_at`, `details` (JSONB). Indexed on `(entity_type, entity_id)`. **Zero call sites write to
  it anywhere in `backend/src/app`** — confirmed by a full grep for `ActivityLog(` returning only the
  class definition itself. The table is schema-only today, exactly as §24.12 states.
- **`audit_logs` (`activity.py:42`, `AuditLog`) exists** — `actor_id` (FK to `users`, nullable),
  `action`, `resource_type`, `resource_id`, `audit_metadata` (JSONB, mapped to a DB column literally
  named `metadata` to match the port's parameter name), `created_at`. Indexed on
  `(resource_type, resource_id)` and on `created_at`.
- **`AuditLogger` port (`application/interfaces/audit.py`) exists** —
  `record(actor: CurrentUser, action: str, resource_type: str, resource_id: str | None, metadata:
  dict | None) -> None`, an `ABC`. **`LoggingAuditLogger`
  (`infrastructure/audit/audit_logger.py`) is the only concrete implementation registered** — it logs
  each call as structured JSON to the `app.audit` logger channel and does **not** write to `audit_logs`.
  Confirmed via the DI container (`infrastructure/di/container.py:127`:
  `container.register(AuditLogger, LoggingAuditLogger)`) — no other registration exists.
- **No `SqlAlchemyAuditLogger` class exists anywhere in this repository** — confirmed by a
  full-repository grep for `SqlAlchemyAuditLogger`, returning only a docstring in `activity.py`
  describing it as future work. `audit_logs` therefore has zero rows written by any code path today;
  only `LoggingAuditLogger`'s JSON log output reflects audit calls in practice.
- **`AuditLogger.record()` is called from exactly two current call sites** — `auth_service.py`
  (`login_success`/`login_failure`) and `presentation/api/deps.py`'s `_require_permission()` closure
  (`permission_denied`, only on the *final* denial that actually produces a 403, per that file's own
  documented T65 discipline). This is genuine, working, already-composed-with-`ADR/0022`
  instrumentation — cited below as an existing precedent pattern, not something this ADR changes.
- **Neither `ActivityLog` nor `AuditLog` carries an `organization_id` column** — confirmed by direct
  inspection of `activity.py`. `ADR/0021`'s decision requires "a mandatory, non-optional
  `organization_id` on every tenant-scoped table," but both tables predate that ADR and are not named
  in it. This is a genuine, disclosed pre-existing gap — see "Tenant-Isolation Composition" below;
  this ADR does not resolve it.
- **Party is realized today by `Client` (`client.py:49`)**, pending `ADR/0023`'s own Party
  subtype-modeling resolution — `MatterStatus`/`Matter` exist (`matter.py`); a standalone `File`
  entity **does not exist** anywhere in `backend/src/app` — consistent with Required ADR #8 remaining
  unresolved. `Document`/`DocumentVersion` exist (`document.py:65`/`:75`); `DocumentVersion` is
  itself already architecturally append-only (no `AuditMixin`, no `updated_at`, no `version` — cited
  by `ADR/0028` as this repository's own immutability prior art). `Invoice`/`Payment`/`Receipt` exist
  (`financial.py`); `Charge`/`Expense`/`PaymentAllocation` are architecturally defined by `ADR/0028`
  but not yet implemented (confirmed: no such class exists in `backend/src/app`).

### Specification findings this ADR treats as already established, not its own to reargue

§24.12's "Activity" entry and §24.14's "Audit" entry both independently reach the same conclusion,
stated here verbatim because it is the direct evidentiary basis for this ADR's "no redesign" posture:

> [Activity] already coexists as a **structurally distinct** mechanism from `audit_logs` in the same
> module — i.e. §4 rule 41's Activity-vs-Audit separation is **already correctly implemented at the
> schema level today**... The required work is a straightforward extension of an existing, working
> pattern, not a redesign.

> [Audit] Gap vs. frozen architecture: **none identified at the mechanism level**... The required
> work is (a) writing the `SqlAlchemyAuditLogger` implementation... and (b) ensuring every sensitive
> action this specification's new entities introduce... actually calls `AuditLogger.record()` — an
> *instrumentation coverage* task across the new domain, not a new audit *mechanism*.

§25 invariant #13 states the same finding a third way: *"the mechanism exists and works... coverage
across the new entities this specification introduces is the open instrumentation task, not a
missing mechanism."* This ADR's role is therefore to state the **boundary** (already settled) and the
**coverage expectations** (the open item these three passages all name) — not to redesign a mechanism
the specification itself finds already sound.

## Decision

**Activity and Audit are confirmed as two permanently distinct, non-substitutable mechanisms**,
realized respectively by `ActivityLog`/`activity_logs` and the `AuditLogger` port/`audit_logs` table,
composed with — not modified by — `ADR/0007` and `ADR/0009`.

**Activity** is descriptive business-history/event visibility: a best-effort, extensible feed of
"what happened" for display purposes (timelines, activity feeds), realized by the existing polymorphic
`entity_type`+`entity_id` pattern on `activity_logs`, unmodified in shape. Extending its coverage to
a new entity (Party/Matter/File/Document/financial/relationship rows) requires only adding a new
`entity_type` string value at the call site — no schema change, no ADR amendment, per §24.12's own
"Modify... no structural change to the table itself" finding.

**Audit** is immutable accountability: a record of *who did what, to what, when*, whose purpose is
attributability (rule 42) and resistance to silent alteration (rule 46), realized by the existing
`AuditLogger` port and `audit_logs` table, unmodified in shape. Coverage expectations (below) are
calls a future instrumentation task makes against the existing, unchanged port signature.

**Coverage Expectations.** This ADR adopts §17.9's/§21's own six named categories — creation,
modification, status changes, relationship changes, financial changes, access-sensitive events — as
the operative classification boundary for "materially significant," applied to this task's six named
entity groups:

| Entity group | Operation | Audit required? | Activity appropriate? |
|---|---|---|---|
| **Party** (realized today by `Client`) | create / update / status change | **Yes** — falls under "creation"/"modification"/"status changes"; Party is the reusable master record (rule 8), and rule 45 names finer-grained access on records like this as a live concern | Yes — both apply independently |
| **Matter** | create / update / status change | **Yes** — same three §17.9 categories; Matter status changes are explicitly named as Timeline-composed input in §24.12 | Yes — both apply independently |
| **File** *(not yet a persisted entity — Required ADR #8 unresolved)* | create / update / status change | **Yes, as a principle** — once File exists as an entity, its create/update/status operations fall under the same three §17.9 categories as Party/Matter; this ADR does not design File's schema or decide Required ADR #8, only states that whatever File becomes, its materially significant operations are Audit-worthy by the same reasoning | Yes, as a principle — same deferral |
| **Document / document-version operations** | version creation; document-level status/metadata change | **Yes** — "creation"/"modification"/"status changes"; distinct from `DocumentVersion`'s own content-immutability (`ADR/0028`'s cited prior art), which protects the *content* — Audit here records the *event* of a version being created/a document's status changing, who did it and when | Yes — both apply independently |
| **Financial record creation/status changes** (Charge/Expense/Invoice/Payment/PaymentAllocation/Refund) | creation; status/finalization change; reversal | **Yes, mandatorily** — "financial changes" is its own named §17.9/§21 category, not merely inferred; complementary to, not the same as, `ADR/0028`'s data-immutability mechanism (see "Consequences" below) | Yes — both apply independently |
| **Material relationship changes** (e.g. `MatterParty` role/Client-designation changes, and any future join row representing a business relationship) | creation; role/status change | **Yes** — "relationship changes" is its own named §17.9/§21 category | Yes — both apply independently |

**General principle.** Among the six entity groups this task names, this ADR finds **none that is
Activity-only** (no-Audit) — every one falls under at least one of §17.9's/§21's own six named
categories. This is stated as an honest architectural finding, not a manufactured gap: rule 42's
"historical actions remain attributable" is written broadly, and §17.9's category list is broad by
design. An operation would be classified Activity-only under this ADR's reasoning only if it is
purely descriptive and carries no accountability weight (e.g., a read/view event, or a system-internal
housekeeping action with no actor-attributability concern) — no such operation appears among this
task's six named groups, so this ADR does not force an artificial example into that box.

**Where both apply, Audit and Activity are independent, parallel calls** — an `AuditLogger.record()`
call and a (future) `ActivityLog` write are two separate operations, neither derived from nor
contingent on the other, preserving rule 41's distinctness at the call-site level, not just the
schema level.

## Decision Drivers

Ranked in the order this ADR actually weighs them, matching `ADR/0021`–`0028`'s established
evidentiary discipline:

1. **Rule 41 (Audit is distinct from Activity)** — any candidate that merges the two mechanisms, or
   derives one from the other, is disqualified outright.
2. **Rules 42 and 46 (attributability; non-alterability)** — Audit's coverage expectations are
   evaluated against these; Activity's are not, since Activity carries no accountability weight.
3. **§17.9's/§21's six named audit-test categories** — used directly as this ADR's coverage
   classification test, since it is the specification's own concrete criterion, not an invented one.
4. **Repository/operational consistency** — reuse the existing polymorphic `entity_type`+`entity_id`
   extension pattern for Activity and the existing `AuditLogger` port for Audit, matching §24.12's and
   §24.14's own "Modify, not New" mapping — no new mechanism, table, or port signature.
5. **Non-invention** — state the coverage *principle*, not implementation-level event names or hook
   points the specification/task scope does not evidence; defer literal event-by-event mapping to a
   future, separately authorized instrumentation task, per this task's own explicit instruction.

## Alternatives Considered

### A. Coverage-classification mechanism

| Alternative | Assessment |
|---|---|
| **Hand-curated allow-list of "sensitive" operations, defaulting new/unlisted operations to Activity-only** | Rejected — inverts the specification's own posture; rule 42 speaks broadly ("historical actions," not "some historical actions"), and an allow-list risks a newly-implemented entity silently falling outside audit coverage by omission rather than by a considered decision. |
| **Merge Activity and Audit into one mechanism/table with an "immutable"/"confidence" flag** | Rejected outright — directly violates rule 41 and reopens a non-conflation the specification itself already finds correctly implemented (§24.12). |
| **Adopt §17.9's/§21's six named categories as the classification boundary (selected)** | Uses the specification's own concrete, already-published test rather than inventing a new one; every one of this task's six named entity groups is directly classifiable against it without guesswork. |

### B. Activity extensibility mechanism

| Alternative | Assessment |
|---|---|
| **A new dedicated activity table per entity type** | Rejected — contradicts §24.12's own "Modify... no structural change to the table itself" finding, and duplicates the polymorphic pattern already used consistently for `workflow_history`/`qr_code_records`/`ai_requests` for the same underlying reason those adopted it: a single feed spanning every entity type without a real FK per possible type. |
| **Reuse the existing polymorphic `entity_type`+`entity_id` `ActivityLog` table unmodified, extending only the value space (selected)** | No schema change; consistent with the sibling polymorphic tables' existing convention (`docs/ERD.md`'s own "Polymorphic references" table). |

### C. Audit mechanism, given `SqlAlchemyAuditLogger` does not yet exist

| Alternative | Assessment |
|---|---|
| **Design a new audit mechanism/table from scratch for this specification's new entities** | Rejected — `ADR/0007`/`0009`'s lineage is explicitly named by §24.14 as "genuinely one of the strongest existing foundations in the repository," already shaped to receive exactly this port's calls; discarding it would both contradict this task's explicit instruction not to reopen those ADRs and be unevidenced invention. |
| **Reuse the existing `AuditLogger` port and `audit_logs` table unmodified (selected)** | The coverage expectations this ADR states are calls a future `SqlAlchemyAuditLogger`-backed instrumentation pass makes against the existing, unchanged port signature — no port or schema change required by this ADR. |

## Consequences

- No schema, migration, service, route, or code of any kind is created or modified by this ADR — it
  is a documentation-only architectural decision, per its own "Implementation Boundary" below.
- Once a future, separately authorized task implements `SqlAlchemyAuditLogger` and instruments the
  operations this ADR names, this ADR's coverage table becomes a concrete, checkable basis for that
  task's own QA review (did the named operations actually call `AuditLogger.record()`), consistent
  with §25 invariant #13's framing of coverage as "the open instrumentation task."
- `activity_logs`'s `entity_type` value space, and `audit_logs`'s `resource_type` value space, both
  grow organically as new entities are implemented — no ADR amendment is required per new entity
  type, since both are pure content extensions to already-existing polymorphic mechanisms (Decision
  Driver 4).
- **Financial operations specifically gain two independent, non-substitutable protections** once both
  this ADR's coverage expectation and `ADR/0028`'s own mechanism are implemented: `ADR/0028`'s
  immutable-after-finalization/reversal-record mechanism protects the financial *data* from silent
  mutation (rule 38); this ADR's coverage expectation requires the *event* of that data being
  created/finalized/reversed to also be independently recorded via `AuditLogger.record()` (rules 42/
  46). A future implementer must not treat either mechanism as satisfying the other.
- The pre-existing absence of `organization_id` on `activity_logs`/`audit_logs` (see "Tenant-Isolation
  Composition" below) remains open — this ADR neither worsens nor resolves it.

## Invariants

1. No operation among Party/Matter/File/Document/financial-record/material-relationship-change
   create/update/status-change/relationship-change operations may be classified as requiring only
   Activity — each falls under at least one of §17.9's/§21's six named audit-test categories, per the
   Coverage Expectations table above.
2. Where both Audit and Activity apply to one operation, the two recordings are independent calls —
   neither is derived from, computed from, or made contingent on the other.
3. `ActivityLog` and `AuditLog` remain two structurally separate tables under all circumstances — no
   future migration may conflate them into one generic event-log table without reopening this ADR
   (mirrors `ADR/0028`'s own "remain two distinct tables" invariant style, applied here to rule 41).
4. Extending `activity_logs`' `entity_type` coverage, or `audit_logs`' `resource_type` coverage, to a
   newly-implemented entity requires no schema change, no port-signature change, and no amendment to
   this ADR.
5. A future `SqlAlchemyAuditLogger` implementation must satisfy the existing `AuditLogger` ABC
   (`application/interfaces/audit.py`) unchanged — mirrors `ADR/0009`'s own "Future Impact" statement;
   this ADR does not authorize modifying the port signature.
6. `ADR/0028`'s financial-data-immutability mechanism and this ADR's financial-event-audit expectation
   are complementary and independently required — neither may be treated as substituting for the
   other (see "Consequences" above).

## Tenant-Isolation Composition (ADR-0021) — disclosed, unresolved gap

`ADR/0021` requires "a mandatory, non-optional `organization_id` on every tenant-scoped table."
`activity_logs` and `audit_logs` both predate `ADR/0021`, are not named in it, and — confirmed by
direct inspection this session — carry no `organization_id` column today. This is a genuine,
pre-existing architectural gap relative to `ADR/0021`'s own mandate, **not created, worsened, or
resolved by this ADR**. Retrofitting tenant scoping onto these two pre-existing tables is a distinct
question from Required ADR #14's own scope (the Activity-vs-Audit conceptual boundary and coverage
expectations) and is not decided here — flagged for the project owner/Project Manager to prioritize
as its own future task if desired, consistent with this series' disclosure discipline (e.g.
`ADR/0028`'s own disclosed Charge/Expense attachment-granularity asymmetry).

## Authorization Composition (ADR-0022)

The two existing `AuditLogger.record()` call sites (`login_success`/`login_failure`;
`permission_denied` on final-candidate denial only) already compose with `ADR/0022`'s resource+action
permission model exactly as built — unchanged by this ADR. Future instrumentation this ADR's coverage
expectations motivate (Party/Matter/File/Document/financial/relationship operations) will likewise be
governed by whichever `ADR/0022`-compliant permission already gates the mutating operation itself;
this ADR introduces no new authorization surface or mechanism.

## Unresolved / Deferred Questions

- The exact call sites (which service method, which line) where each coverage-expectation entry's
  `AuditLogger.record()`/`ActivityLog` write is added — explicitly deferred to a future, separately
  authorized instrumentation task, per this task's own instruction not to invent implementation-level
  detail the repository does not yet evidence.
- `SqlAlchemyAuditLogger`'s own implementation (query shape, transaction boundary relative to the
  operation it audits, error-handling if the audit write itself fails) — not designed here.
- File's own entity architecture (Required ADR #8) — this ADR states only that File's eventual
  create/update/status operations will be Audit-worthy by the same reasoning applied to Party/Matter,
  not File's schema or lifecycle.
- The `organization_id` gap on `activity_logs`/`audit_logs` relative to `ADR/0021` (see
  "Tenant-Isolation Composition" above) — disclosed, not resolved.
- Whether `Communication` (§24.12, not yet a finalized entity) and `Timeline` (a read-side
  composition, not a table, per rule 40) fall under this ADR's coverage expectations — out of this
  task's six named entity groups, not addressed here.

## Dependencies

`ADR/0007`/`ADR/0009` (the `AuditLogger` port / `audit_logs` lineage this ADR builds coverage
expectations on top of — composed with, not reopened). `ADR/0021` (tenant isolation — a disclosed,
unresolved gap on the two pre-existing tables this ADR discusses, not created or resolved by it).
`ADR/0022` (authorization — existing audit call sites already compose with it). `ADR/0023` (Party is
currently realized by `Client`, pending that ADR's own resolution). Required ADR #8 (File's own
entity architecture — a disclosed, non-blocking soft dependency for File's coverage-expectation row).

## Explicit Out-of-Scope Boundaries

This ADR does **not** decide:

- `SqlAlchemyAuditLogger`'s implementation, or any instrumentation of any entity — future,
  separately authorized work.
- Required ADR #8 (Matter-vs-File lifecycle; File's own entity architecture), #10 (Document/File
  relationship), #11 (Document/version architecture), #12 (Workflow vs Government Status), #15 (Core
  vs configurable vocabulary), #16 (UUID vs human-readable identifiers), #17 (Soft deletion/history),
  or #20 (migration strategy) — untouched.
- The `organization_id` gap on `activity_logs`/`audit_logs` — disclosed, not resolved (see
  "Tenant-Isolation Composition" above).
- Any database schema change, migration, backend/frontend/Electron implementation, or test.
- Reopening `ADR/0007`, `ADR/0009`, or `ADR/0021`–`ADR/0028`.

## Implementation Boundary

This ADR is a documentation-only architectural decision. No table, migration, backend model, service,
repository, route, frontend, or test is created or modified by this ADR or its accompanying report.
`SqlAlchemyAuditLogger` and instrumentation of the operations this ADR names remain future,
separately authorized work — this ADR states the boundary and coverage expectations a future
implementation task would build against, and against which that task's own QA review can check
completeness.

## References

- `docs/Legal_DMS — Domain Model & Functional Specification.md` §4 rules 39–42, 45–46; §17.9; §21
  (Audit group bullet list); §24.12 (Activity, Communication, Timeline); §24.14 (Audit,
  Confidentiality); §25 invariant #13; §2 Feature Catalogue (Activity/Audit priority rows).
- `ADR/0007-audit-logging-without-database-table.md`
- `ADR/0009-audit-logs-table-reverses-adr-0007.md`
- `ADR/0021-organization-tenant-boundary-enforcement.md` (tenant-isolation gap disclosure)
- `ADR/0022-authorization-architecture.md` (existing audit call-site composition)
- `ADR/0023-party-vs-client-architecture.md` (Party's current realization as `Client`)
- `ADR/0028-financial-ledger-boundary-charge-expense-invoice-payment-allocation.md` (evidentiary
  precedent; the complementary, non-substitutable relationship between data-immutability and
  event-audit described in "Consequences" above)
- `backend/src/app/infrastructure/persistence/models/activity.py`
- `backend/src/app/application/interfaces/audit.py`
- `backend/src/app/infrastructure/audit/audit_logger.py`
- `backend/src/app/infrastructure/di/container.py`
- `backend/src/app/presentation/api/deps.py` (existing `permission_denied` audit call site)
- `backend/src/app/application/auth_service.py` (existing `login_success`/`login_failure` audit call
  sites)
- `docs/ERD.md` (polymorphic `entity_type`+`entity_id` reference table)
