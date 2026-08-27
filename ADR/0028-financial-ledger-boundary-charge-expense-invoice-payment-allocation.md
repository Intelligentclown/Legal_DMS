# ADR-0028: Financial Ledger Boundary — Charge/Expense/Invoice/Payment-Allocation Architecture

**Status:** Proposed
**Date:** 2026-08-27

**Resolves:** `docs/Legal_DMS — Domain Model & Functional Specification.md` §21 planning-list item
**#13** ("Financial boundary").

**Does not resolve:** Required ADR #1–#7, #9, #18, or #19 (already resolved by `ADR/0021`–`ADR/0027`,
not reopened here) or Required ADR #8, #10, #12, #20 (untouched — in particular, the Matter-vs-File
attachment granularity for Charge/Expense/Commercial Scope remains #8's territory, disclosed as a
deferred boundary below, not decided by this ADR). Commercial Scope's own fee-structure modeling
(fixed/hourly/milestone billing) and Refund's full field design are also not resolved here beyond
the minimum needed to state the Charge/Invoice boundary and the historical-mutation invariant.

**Dependencies:** `ADR/0021` (tenant isolation — every new table this ADR introduces carries a
mandatory, directly-carried `organization_id`, composed with, not reopened). `ADR/0022`
(authorization — Charge/Expense/PaymentAllocation mutation is governed by the existing
resource+action permission model, composed with, not reopened). `ADR/0023`–`ADR/0027` (no direct
interaction; cited for consistency of evidentiary discipline only). Required ADR #8 (Matter-vs-File
attachment granularity — a disclosed, deferred soft dependency for Charge/Expense ownership, not a
blocking one; see "Attachment-Granularity Boundary" below).

## Context

The governed specification freezes, as Confirmed Business Rules, that Quotation, Commercial Scope,
Charges, Invoice and Payment are separate concepts that must not be compressed into fewer entities
for implementation convenience (§4 rule 35; §7 Phase 7 explicitly warns against "a generic 'amount'
field attached to Matter"), that professional fees must remain distinguishable from
government/third-party money passing through the firm (§4 rule 36), that payment allocation must be
separately represented where required (§4 rule 37), and that historical financial information must
not be silently overwritten (§4 rule 38). §17.8 names a mandatory test lifecycle — Quotation →
Commercial Scope → Charge → Invoice → Payment → Allocation → Refund, "including partial payments and
historical integrity" — and §25 invariant #14 flags financial-history immutability as one of the
two most consequential open items in the entire specification alongside tenant isolation.

What is **not** frozen: the exact schema shape of Charge and Expense, whether Invoice totals are
line-item-derived or independently persisted, PaymentAllocation's target model, and the concrete
mechanism that enforces rule 38. §24.13's own entity blocks name all of these `ED — must decide
before implementation`. This ADR resolves them.

### Repository baseline (direct inspection, `main` at this ADR's authoring baseline)

- **`invoices` (`financial.py:25`) exists** — `invoice_number` (unique), `matter_id` (direct FK),
  `client_id` (direct FK, pending a future Party redirect tracked under Required ADR #20, not this
  ADR), `amount`/`tax_amount`/`total_amount` (all `Numeric(12,2)`, all `CHECK`'d non-negative),
  `status` (default `draft`), `issued_at`/`due_at`. No Charge/Expense line-item breakdown exists —
  the three amount columns are independently entered today, confirmed by a full grep for
  `charge|Charge` across `backend/src/app` returning zero matches outside this ADR's own
  authoring context.
- **`payments` (`financial.py:45`) exists** — `invoice_id` **nullable** (already correctly allows a
  Payment not tied to one specific Invoice), `matter_id`, `client_id`, `payment_method_id` (lookup
  table, already exists), `amount` (`CHECK`'d positive), `paid_at`, `reference_number`, `status`
  (default `completed`). No `payment_allocations` table exists — a Payment today has at most one
  `invoice_id`, which cannot represent rule 37's "separately represented where required."
- **`receipts` (`financial.py:60`) exists** — `payment_id`, `receipt_number` (unique), `issued_at`,
  optional `file_storage_record_id` — genuinely reusable, not touched by this ADR.
- **No `Charge`, `Expense`, `CommercialScope`, or `PaymentAllocation` model exists anywhere in
  `backend/src/app`** — confirmed by a full class-name grep returning zero matches. This is a
  genuinely from-scratch design for these four entities, not an extension of existing code.
- **`AuditMixin` (`mixins.py`)** — `created_at`/`updated_at`/`deleted_at`/`created_by`/`updated_by`
  plus a tracked-but-not-necessarily-enforced `version` column — is used by `Invoice`/`Payment`/
  `Receipt` today. **`OptimisticLockMixin`** (SQLAlchemy-enforced version-conflict on `UPDATE`) is
  used elsewhere (`property.py`, `matter.py`, `client.py`, `document.py`) but **not** by any
  Finance model today — relevant context for why this ADR does not rely on optimistic locking alone
  to satisfy rule 38 (see "Historical Mutation Mechanism" below): it prevents *concurrent*
  overwrites, not *authorized, non-concurrent* silent edits, which is rule 38's actual concern.
- **`DocumentVersion` (`document.py:75`) is this repository's own existing precedent for
  append-only immutability** — deliberately no `updated_at`/`deleted_at`/`version`/`AuditMixin` at
  all; a version row, once created, is never mutated. This is directly relevant prior art for this
  ADR's historical-mutation mechanism, though — as discussed below — not directly reusable
  unmodified, because a financial correction has its own accounting-standard shape (a reversal is a
  new signed transaction, not a new "version" of the old one).
- **No database trigger exists anywhere in this repository** — confirmed by a full grep for
  `CREATE TRIGGER`/`trigger` across `backend/src/app` and the Alembic migrations directory. This is
  a genuine architectural constraint this ADR respects (see "Historical Mutation Mechanism"): a
  DB-trigger-based immutability mechanism would be new infrastructure with no precedent, the same
  category of rejection `ADR/0027` applied to dynamic DDL and external distributed locks.
- **§10.A's own candidate table list names `commercial_scopes`, `charges`, `expenses`,
  `payment_allocations`, `refunds`** — real, if non-binding, textual signals (not specification
  mandates) toward this ADR's selected shape: four/five distinct tables, not one generic
  "financial line item" table.
- **§2's Feature Catalogue lists Charge's dependency as `Matter` and Expense's dependency as
  `Matter/File`, and Payment Allocation's dependency as `Payment/Invoice`** — the first is a real
  textual signal that Charge is intended as Matter-scoped by default (informing, not resolving,
  the disclosed #8 boundary below); the third is a real textual signal that Payment Allocation's
  target is Invoice, not Charge directly (informing this ADR's Decision C below).

## Decision

**Charge and Expense are adopted as two distinct, first-class, Matter-scoped tables** (`charges`,
`expenses`) — not a single generic financial-line-item table with a type discriminator. **Each
carries a nullable `invoice_id` FK** (mirroring `Payment.invoice_id`'s existing nullable-FK
precedent) rather than a separate join table, so a Charge/Expense may exist un-invoiced and an
Invoice may exist with no linked Charges/Expenses (preserving today's existing Invoice rows
unmodified). **Invoice retains its own persisted `amount`/`tax_amount`/`total_amount` columns**,
computed from linked Charges/Expenses at issuance and frozen thereafter — not a fully
query-time-derived total. **PaymentAllocation is adopted as a dedicated `payment_allocations`
table targeting Invoice only** (not Charge directly), with a database-enforced
sum-does-not-exceed-payment invariant realized through transaction-scoped row locking on the
parent Payment, not a bare `CHECK` constraint (which cannot aggregate across rows). **Historical
financial data (Charge, Expense, Invoice, Payment amounts) becomes architecturally immutable once
finalized**; corrections are represented as new reversal/adjustment records, never as `UPDATE`s to
a finalized amount — enforced at the service layer, consistent with this codebase's lack of any
existing database-trigger infrastructure.

## Decision Drivers

Ranked in the order this ADR actually weighs them, matching `ADR/0021`–`0027`'s established
evidentiary discipline:

1. **Rule 36 (professional fees vs. third-party money must remain distinguishable)** — any
   candidate that risks collapsing Charge and Expense into one generic "amount" concept is
   disqualified outright, per §7 Phase 7's explicit warning.
2. **Rule 38 (historical financial information must not be silently overwritten)** — the mechanism
   must make silent overwriting structurally difficult, not merely logged after the fact.
3. **Rule 37 (payment allocation must be separately represented where required)** — the mechanism
   must support partial/multi-target allocation, per §17.8's mandatory "including partial
   payments" test.
4. **Repository/operational consistency** — prefer mechanisms using this codebase's existing
   conventions (nullable FKs, lookup tables, service-layer enforcement, `AuditMixin`) over ones
   requiring new infrastructure (DB triggers, generic polymorphic tables) with no precedent here.
5. **Non-disruption of existing data** — `invoices`/`payments` rows that predate this ADR must
   remain valid without a mandatory backfill as a precondition of this decision (backfill
   *strategy*, if any is ever chosen, belongs to Required ADR #20).

## Alternatives Considered

### A. Charge/Expense structural shape

| Alternative | Assessment |
|---|---|
| **Single generic `financial_line_items` table with a `kind` discriminator (charge/expense)** | Rejected — a shared table with a type column is exactly the "generic 'amount' field" §7 Phase 7 warns against; a single accidental omission of a `WHERE kind = ...` filter anywhere in the codebase silently conflates professional fees with third-party money, violating rule 36's distinguishability requirement at the schema level, not just in application logic. |
| **Two distinct tables, `charges` and `expenses` (selected)** | Structural separation is the strongest available guarantee against accidental conflation — a query or report that reads `charges` physically cannot pull in `expenses` data by omission. Matches §10.A's own naming (two separate candidate table names, not one). |
| **Single table, but with mandatory, separately-validated `charge_type`/`expense_type` enum columns instead of a table split** | Rejected for the same reason as the discriminator option — the schema itself does not prevent conflation, only application-level discipline does, which rule 36's language ("must remain distinguishable") reads as requiring more than. |

### B. Charge/Expense ↔ Invoice model

| Alternative | Assessment |
|---|---|
| **Fully query-time-derived Invoice totals (drop `amount`/`tax_amount`/`total_amount`, always `SUM()` linked Charges/Expenses)** | Rejected — directly violates rule 38: if a Charge is edited or added after an Invoice has already been issued/sent to a client, the Invoice's *displayed* total would silently change with no persisted record of what the client was actually billed at issuance time. |
| **No real linkage — Invoice keeps independent totals, Charges/Expenses reconciled only via reporting** | Rejected — this is close to today's status quo and does not actually satisfy rule 35's requirement that these be genuinely separate *and related* concepts; without a real FK, introducing Charge/Expense as first-class entities would add schema without adding any enforceable relationship, defeating the purpose. |
| **Nullable `invoice_id` FK on Charge/Expense (mirrors `Payment.invoice_id`); Invoice totals computed from linked line items at issuance and persisted/frozen thereafter (selected)** | Satisfies rule 35 (real, queryable linkage) and rule 38 (the persisted total is a frozen snapshot, not a live-recomputed value) simultaneously. Reuses the exact nullable-FK precedent `Payment` already establishes, no new relationship idiom introduced. Existing `invoices` rows with no linked Charges remain valid — the FK is nullable on the Charge/Expense side, and Invoice requires no schema change to its own columns. |
| **A dedicated `invoice_line_items` join table (Invoice ⟷ Charge/Expense many-to-many)** | Rejected as unnecessary complexity — a Charge/Expense is invoiced by at most one Invoice in this specification's own model (§17.8's lifecycle names a single linear chain, not a many-to-many billing relationship); a simple many-to-one nullable FK captures this cardinality directly, with no join table needed. |

### C. Payment allocation target

| Alternative | Assessment |
|---|---|
| **Allocate directly to Charge/Expense (bypassing Invoice)** | Rejected — real-world legal billing practice (and §17.8's own lifecycle ordering: Charge → Invoice → Payment → Allocation) has clients paying against Invoices, not individual Charges; allocating directly to Charges would let a Payment be reconciled against unbilled liabilities, which conflicts with the Charge → Invoice → Payment sequencing this specification's own test lifecycle implies. |
| **Allocate to either Invoice or Charge, discriminated by a target-type column** | Rejected on the same "discriminator risks conflation" reasoning as Alternative A above, and rejected on evidentiary grounds — §2's Feature Catalogue explicitly names Payment Allocation's dependency as `Payment/Invoice`, not `Payment/Invoice/Charge`, giving no textual support for a Charge target. |
| **Allocate to Invoice only, via a dedicated `payment_allocations` table (selected)** | Directly supported by §2's own stated dependency (`Payment/Invoice`). One Payment may produce multiple `PaymentAllocation` rows, each targeting a distinct Invoice with its own `allocated_amount` — satisfies rule 37 and §17.8's mandatory partial-payment test without introducing an unevidenced Charge-targeting capability. |
| **Polymorphic `entity_type`+`entity_id` target (matching the existing `workflow_history`/`activity_logs` pattern)** | Rejected — that pattern is deliberately used elsewhere for genuinely poly-target event logs with no enforced FK; `PaymentAllocation`'s target is architecturally singular (Invoice only, per the decision above), so a real FK (`invoice_id`) is both stronger (DB-enforced referential integrity) and simpler than reusing a polymorphic idiom that exists here for a different reason. |

### D. Historical mutation mechanism (rule 38)

| Alternative | Assessment |
|---|---|
| **Mutable rows + `AuditMixin`/activity-log audit trail (today's status quo for `invoices`/`payments`)** | Rejected as the sole mechanism — audit logging records *that* a change happened, which satisfies rule 42/46's attributability requirement, but does not *prevent* the amount column itself from being silently overwritten; rule 38 requires prevention, not just after-the-fact visibility. |
| **`OptimisticLockMixin`-style version enforcement** | Rejected as the sole mechanism — it prevents *concurrent* conflicting writes (a `StaleDataError` on a stale `version`), which is a genuinely different problem from an *authorized, non-concurrent* edit that silently changes a historical amount; the two are complementary, not substitutes (see "Invariants" below — version enforcement remains a reasonable *addition*, not decided against, just insufficient alone). |
| **Full row-versioning, mirroring `DocumentVersion`'s exact append-only shape (a new numbered version row per edit, "current" derived by latest `version_number`)** | Considered seriously given this is proven, working prior art in this exact repository. Rejected as the primary mechanism specifically for financial rows because a financial correction has a different real-world shape than a document edit: accounting practice represents a correction as a new, independently-auditable *transaction* (a credit note, a reversal, an adjustment) with its own signed amount and its own timestamp/actor, not as "version 2 of the same row" — collapsing a correction into a version-number bump would obscure the amount of the correction itself, which §17.8's "historical integrity" test almost certainly expects to be independently visible. |
| **Immutable-after-finalization rows + explicit reversal/adjustment records (selected)** | Combines this repository's own `DocumentVersion` philosophy (append-only, no in-place mutation once finalized) with the correction-as-transaction shape accounting practice requires. A Charge/Expense/Invoice amount becomes immutable once the row transitions to a finalized state (Charge/Expense: once linked to an issued Invoice; Invoice: once `status` leaves `draft`; Payment: once `status` is `completed`); any subsequent correction is expressed as a new row (a negative-amount Charge/Expense, a Payment reversal, or — for the client-facing case — a `Refund`, already a named entity in this specification's own catalogue), never as an `UPDATE` to the original amount. |
| **Database-trigger-enforced immutability (e.g., a `BEFORE UPDATE` trigger rejecting amount changes on finalized rows)** | Rejected as the *enforcement point*, not the *concept* — the concept (immutability after finalization) is adopted; the mechanism is not implemented via triggers because no trigger infrastructure exists anywhere in this repository today (confirmed by grep), and introducing one would be new operational infrastructure this ADR is not positioned to introduce as a side effect of a financial-boundary decision, mirroring `ADR/0027`'s identical reasoning for rejecting dynamic DDL. Service-layer enforcement (the mutation-path service methods simply do not expose an "edit amount" operation on a finalized row) is the RC-consistent mechanism instead. |

## Detailed Integrity & Concurrency Analysis

Concurrency is addressed **only** where the financial invariants themselves genuinely require it —
not merely because `ADR/0027` addressed concurrency for an unrelated reason.

- **Preventing payment over-allocation (rule 37):** the invariant "sum of a Payment's
  `PaymentAllocation.allocated_amount` rows must never exceed `Payment.amount`" cannot be expressed
  as a single-row `CHECK` constraint (Postgres `CHECK` cannot aggregate across sibling rows). The
  architectural mechanism is a transaction-scoped invariant: before inserting a new
  `PaymentAllocation` row, the owning `Payment` row is locked (`SELECT ... FOR UPDATE`) within the
  same transaction, the existing allocation sum is read, and the new allocation is rejected if it
  would exceed the Payment's amount — the same row-lock-then-validate shape `ADR/0027` uses for its
  counter table, applied here because two concurrent allocation attempts against the same Payment
  are a real, not hypothetical, integrity risk (a firm's billing staff allocating a single payment
  across multiple invoices from different sessions concurrently). This is stated as an
  architectural invariant to be enforced in whichever service handles allocation creation, not as
  implementation code.
- **Preventing inconsistent Invoice totals:** because Invoice totals are a frozen snapshot computed
  at issuance (Decision B), not a live aggregate, there is no ongoing consistency requirement
  between an Invoice's persisted totals and its linked Charges/Expenses after issuance — editing a
  linked Charge after its Invoice is issued is exactly the case Decision D's immutability rule
  forbids (the Charge itself becomes immutable once invoiced), so the two decisions jointly close
  this gap rather than requiring a separate reconciliation mechanism.
- **Preventing accidental mutation of historical financial records:** addressed structurally by
  Decision D (immutability after finalization), not by a concurrency mechanism — this is a
  service-layer authorization/business-rule concern (the mutation operation simply is not offered),
  not a race condition.
- **Preventing Charge/Expense semantic collapse:** addressed structurally by Decision A (two
  distinct tables), not by a runtime check — there is no code path that could conflate the two
  because they are not the same table.
- **No new database-level locking primitive is introduced beyond `SELECT ... FOR UPDATE`**, which
  is already standard Postgres functionality this codebase's async engine (`asyncpg`,
  `create_async_engine`) supports without complication, per `ADR/0027`'s own confirmed baseline.

## Attachment-Granularity Boundary (Required ADR #8 — explicitly deferred)

Charge and Expense are specified above as **Matter-scoped** (`matter_id`, mandatory, mirroring
`Invoice`/`Payment`'s existing `matter_id` columns). This is an **inference**, not a resolution of
Required ADR #8, grounded in §2's Feature Catalogue naming Charge's dependency as `Matter` (not
`Matter/File`). §2 names Expense's dependency as `Matter/File` — a real textual signal that Expense
specifically may eventually need File-level attachment (e.g., a government-filing-fee Expense tied
to a specific File within a Matter), which this ADR does **not** resolve. **This ADR does not add a
`file_id` column to Charge or Expense, does not decide whether Charge/Expense should ever attach at
File granularity, and treats the File-level question as entirely Required ADR #8's territory** —
exactly the same disclosure discipline `ADR/0027` applied to File Number's own format, deferred to
#8. Should #8 later establish File-level attachment as required, adding a nullable `file_id` column
to `expenses` (and, if warranted, `charges`) is additive and does not require reopening this ADR's
Matter-scoped baseline.

## Consequences

- Four new tables are introduced: `charges`, `expenses`, `payment_allocations`, and (named but
  minimally specified per the "must not fully design" boundary) a placeholder acknowledgment that
  `commercial_scopes` and `refunds` remain **not** designed by this ADR beyond what §24.13 already
  states — see "Explicit Out-of-Scope Boundaries."
- `invoices` and `payments` require no structural change to their existing columns — only new
  inbound nullable FKs from `charges`/`expenses` (to `invoices`) and a new `payment_allocations`
  table (referencing both `payments` and `invoices`). Existing rows remain valid with no backfill
  required as a precondition of this ADR (backfill *strategy*, if any, is Required ADR #20's
  territory).
- Reporting/reconciliation logic gains a real, FK-backed way to verify an Invoice's persisted total
  against its linked Charges/Expenses at issuance time, closing part of §25 invariant #14's
  identified gap.
- Financial correction workflows must be built around reversal/adjustment records rather than
  in-place edits once a row is finalized — a genuine service-layer/API design constraint for
  whichever future task implements this ADR, not optional.

## Invariants

1. A `Charge`/`Expense` row's `invoice_id`, once set (invoiced), is itself immutable — re-invoicing
   under a different Invoice is not supported by this architecture; a correction is a reversal, not
   a re-link.
2. A `Charge`/`Expense`/`Invoice`/`Payment` row's amount-bearing columns become immutable once the
   row is finalized (Charge/Expense: linked to an issued Invoice; Invoice: `status` leaves `draft`;
   Payment: `status` is `completed`) — enforced at the service layer, not by a database trigger.
3. `sum(PaymentAllocation.allocated_amount WHERE payment_id = :p)` must never exceed
   `Payment.amount` for that Payment — enforced via transaction-scoped row locking on the parent
   Payment at allocation-creation time, not a bare `CHECK` constraint.
4. `PaymentAllocation.invoice_id` is mandatory and non-nullable — this ADR does not support a
   Charge-targeted allocation (see Alternative C).
5. `charges`/`expenses`/`payment_allocations`/`commercial_scopes`/`refunds` all carry a mandatory,
   directly-carried `organization_id` (see "Tenant-Isolation Composition" below) — never
   join-derived only.
6. Charge and Expense remain two distinct tables under all circumstances — no future migration may
   merge them into one generic financial-line-item table without reopening this ADR.

## Tenant-Isolation Composition (ADR-0021)

Every new table this ADR introduces (`charges`, `expenses`, `payment_allocations`, and — to the
minimal extent named — `commercial_scopes`, `refunds`) carries a mandatory, directly-carried
`organization_id`, mirroring `ADR/0021`'s discipline already applied by `ADR/0024`, `ADR/0026`, and
`ADR/0027` to their own generator/structural tables. `ADR/0021` itself is not reopened, reinterpreted,
or narrowed by this decision.

## Authorization Composition (ADR-0022)

Charge/Expense/PaymentAllocation creation, and — most significantly — the reversal/adjustment
operations Decision D requires in place of in-place amount edits, are governed by whatever
`finance:*` (or equivalent) permission the existing resource+action model (`ADR/0022`) is extended
to include once implementation begins. This ADR does not introduce a new authorization mechanism,
model, or enforcement point — it composes with `ADR/0022` exactly as `ADR/0027` composed File-number
generation with the same model, without reopening it.

## Implementation Guidance / Constraints

- `charges`/`expenses` schema (minimum): `id`, `organization_id`, `matter_id` (mandatory FK),
  `invoice_id` (nullable FK), `description`, `amount` (`Numeric(12,2)`, `CHECK >= 0`), a
  `charge_type_id`/`expense_category_id` lookup-table FK (organization-configurable vocabulary, per
  §6.2 — `expenses` additionally per §6.2's explicitly named "Expense Categories"; `charges`'
  category vocabulary is a consistent extension, not itself named in §6.2's example list), plus
  `AuditMixin`. `expenses` additionally carries a `reimbursable: bool`, per §24.13's own field list.
- `payment_allocations` schema (minimum): `id`, `organization_id`, `payment_id` (mandatory FK),
  `invoice_id` (mandatory FK), `allocated_amount` (`Numeric(12,2)`, `CHECK > 0`), plus `AuditMixin`.
- No schema, migration, service, route, or test is created by this ADR — all of the above are
  architectural shapes for a future implementation task to build against, not a schema this task
  applies.

## Unresolved / Deferred Questions

- Whether Charge/Expense/Commercial Scope should ever attach at File granularity (Required ADR #8).
- Commercial Scope's own fee-structure modeling (fixed/hourly/milestone) and its
  revision/re-baselining mechanism beyond the minimum stated in "Explicit Out-of-Scope Boundaries."
- Refund's full field list and whether multiple partial refunds against one Payment are supported.
- Whether `OptimisticLockMixin` should also be adopted on Finance tables as a defense-in-depth
  addition to Decision D's immutability rule (a reasonable future hardening, not required by this
  ADR to satisfy rule 38, which Decision D already satisfies independently).
- Exact `charge_type`/`expense_category` seed vocabulary (organization-configurable content, per
  §6.2, not architecture).
- `client_id`→Party redirect timing on `Invoice`/`Payment` (Required ADR #20).
- Migration/backfill of any existing `invoices`/`payments` rows to the new Charge/Expense/
  PaymentAllocation model (Required ADR #20).

## Dependencies

`ADR/0021` (tenant isolation — composed with). `ADR/0022` (authorization — composed with). Required
ADR #8 (Matter-vs-File attachment granularity — a disclosed, non-blocking soft dependency for
Expense specifically, per "Attachment-Granularity Boundary" above). Required ADR #20 (migration
strategy — for `client_id`→Party redirects and any future backfill of existing Finance rows; not
required to resolve *this* ADR's core boundary decision).

## Explicit Out-of-Scope Boundaries

This ADR does **not** decide:

- Required ADR #8 (Matter-vs-File attachment granularity; File's broader entity architecture;
  Matter deletion cascade; Workflow/Task/GovernmentProcess attachment granularity) — explicitly
  deferred, see above.
- Required ADR #10 (Document/File relationship; `matter_id`→`file_id` migration mechanics).
- Required ADR #20 (migration sequencing; legacy-data backfill; `client_id`→Party migration
  timing).
- Commercial Scope's full fee-structure architecture (fixed/hourly/milestone billing) — only
  acknowledged as a named, related entity that will eventually reference this ADR's Invoice/Charge
  boundary; not designed here.
- Refund's detailed architecture and partial-refund support — acknowledged as the mechanism a
  Payment-side correction may eventually use, per Decision D, but not fully designed.
- Charge-type/Expense-category business vocabularies — organization-configurable content (§6.2),
  not architecture.
- Any backend, frontend, or Electron implementation; any database migration; any test.

## Implementation Boundary

This ADR is a documentation-only architectural decision. No table, migration, backend model,
service, repository, route, frontend, or test is created or modified by this ADR or its
accompanying report. A future implementation task, once separately authorized, builds against the
shapes and invariants stated above.

## References

- `docs/Legal_DMS — Domain Model & Functional Specification.md` §4 rules 35–38, §6.2, §17.8, §24.13,
  §25 invariant #14, §26 item 9.
- `ADR/0021-organization-tenant-boundary-enforcement.md`
- `ADR/0022-authorization-architecture.md`
- `ADR/0027-file-numbering-algorithm-and-concurrency-strategy.md` (evidentiary-discipline precedent
  for tenant-isolation composition, deferred-scope disclosure, and rejection of infrastructure with
  no repository precedent)
- `backend/src/app/infrastructure/persistence/models/financial.py`
- `backend/src/app/infrastructure/persistence/models/document.py` (`DocumentVersion` — immutability
  prior art)
- `backend/src/app/infrastructure/persistence/models/mixins.py`
