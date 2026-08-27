# T94 Software Architect Report

**Task:** T94 — Draft and resolve Required ADR #13 ("Financial boundary"), per
`docs/Legal_DMS — Domain Model & Functional Specification.md` §21's planning-list terminology. Full
authorized-scope text: this task's own governing instructions (T94 authorization, recorded directly
by the project owner in this session, not as a separate `IMPLEMENTATION_QUEUE.md` governance commit
— see "Authorization" below for the disclosed difference from the `T87`–`T93` pattern).

**Role:** Software Architect, per `docs/prompts/SoftwareArchitect.md` (formally adopted, merged
`b5b3126`, unchanged since T93). This report follows that prompt's Required Output (§8) and Reviewer
Checklist (§7 item 7) structure, and this task's own required-report-contents list.

---

## 1. Verified Baseline SHA

- `git status` at session start: clean, on branch `main` at
  `e00bdb72eee0a7944c91289dc95f5cde4ce53429`.
- `git fetch origin` + `git rev-parse main`/`origin/main`: both
  `e00bdb72eee0a7944c91289dc95f5cde4ce53429` — `main == origin/main`, matching the task's claimed
  baseline exactly.
- `ADR/0021`–`ADR/0027` all present; no `ADR/0028` existed prior to this pass (confirmed via
  `ls ADR/0028*` failing before drafting). No `T94` row existed in `IMPLEMENTATION_QUEUE.md`; no
  `T94` branch existed.
- Baseline SHA recorded: `e00bdb72eee0a7944c91289dc95f5cde4ce53429`.

## 2. Authorization

**Disclosed process difference from the `T87`–`T93` pattern:** every prior task in this series
recorded its authorization as its own documentation-only governance commit in
`IMPLEMENTATION_QUEUE.md` (its own PR) *before* the Software Architect began drafting. T94's
authorization was instead granted directly by the project owner, in this conversation, as an
explicit governance decision — the authorizing message names the task number (T94), the Required
ADR (#13), the expected ADR number (`ADR/0028`), and the proposed title verbatim, and explicitly
instructs that `IMPLEMENTATION_QUEUE.md` and `PROJECT_STATE.json` are **not** to be modified as part
of this drafting pass. This is disclosed here as a factual difference, not silently normalized to
look like a git-committed authorization commit that does not exist. The immediately-preceding fresh
post-T93 dependency assessment (same session) independently concluded Required ADR #13 was the only
currently-ready unresolved Required ADR, which the project owner's authorization then confirmed and
formally authorized.

- `ADR/0021`, `ADR/0022`, `ADR/0023`, `ADR/0024`, `ADR/0025`, `ADR/0026`, and `ADR/0027` are all
  frozen, already-accepted project decisions — **not reopened** by this task (verified: none of
  them appear in this branch's diff against `main`, see §11).
- No `T95` reference exists anywhere in the repository — confirmed via a full-repository grep,
  zero matches outside this report's own text.
- No unauthorized T94 implementation had already occurred: confirmed by `git status` being clean at
  session start and by `main`'s SHA matching the supplied baseline exactly.

## 3. Specification Sections Inspected

Read directly from `docs/Legal_DMS — Domain Model & Functional Specification.md`, in full where
cited:

- §4 rules 35–38 (Finance group), quoted verbatim: "Quotation, Commercial Scope, Charges, Invoice
  and Payment are separate concepts"; "Professional fees must remain distinguishable from
  government/third-party money"; "Payment allocation must be separately represented where
  required"; "Historical financial information must not be silently overwritten."
- §6.2's configurable-vocabulary list — confirmed "Expense Categories" is explicitly named there;
  "Charge categories/types" is **not** explicitly named (consistent with §24.13's own text noting
  this).
- §2's Feature Catalogue Finance rows — confirmed Charge's stated dependency is `Matter` (not
  `Matter/File`); Expense's stated dependency is `Matter/File`; Payment Allocation's stated
  dependency is `Payment/Invoice` (not `Payment/Invoice/Charge`) — all three cited as direct textual
  evidence in `ADR/0028`'s Alternatives/Attachment-Granularity sections, not asserted without
  source.
- §17.8 "Financial tests," quoted: the mandatory lifecycle "Quotation → Commercial Scope → Charge →
  Invoice → Payment → Allocation → Refund, including partial payments and historical integrity."
- §21's Required ADR list, item 13, verbatim: "Financial boundary."
- §24.13's full "Commercial & Finance" entity group — Commercial Scope, Charge, Expense, Invoice,
  Payment, Payment Allocation, Refund — Purpose, Repository constraint, Fields, Relationships,
  Repository mapping, and Open engineering decisions read in full for each.
- §25 cross-domain invariant table, row 14 ("Financial history cannot be silently mutated... flagged
  as a real gap the Finance ADR (#13) should address, not assumed handled").
- §26 item 9, verbatim, confirming #13 is self-contained in the specification's own text (not
  textually coupled to #8/#10/#20 the way item 7's #10/#20 coupling is stated).
- §10.A's candidate-table list, confirming `commercial_scopes`, `charges`, `expenses`,
  `payment_allocations`, `refunds` are all named there.

## 4. Repository Files/Patterns Inspected

Direct inspection, read-only:

- `backend/src/app/infrastructure/persistence/models/financial.py` (full file) — `Invoice`
  confirmed as `amount`/`tax_amount`/`total_amount` direct columns, no Charge/Expense breakdown;
  `Payment.invoice_id` confirmed **nullable** (cited as the direct precedent `ADR/0028`'s Decision B
  reuses); `Receipt` confirmed reusable, untouched.
- A grep for `class Charge|class Expense|class CommercialScope|class PaymentAllocation|class
  Refund|file_number_sequences` across `backend/src/app` returned zero matches — confirming none of
  the five new Finance entities, nor `ADR/0027`'s own `file_number_sequences` table, has been
  implemented; this ADR is genuinely from-scratch, and `ADR/0027`'s architecture remains
  unimplemented exactly as its own report stated.
- `backend/src/app/infrastructure/persistence/models/mixins.py` (full file) — `AuditMixin` and
  `OptimisticLockMixin` re-confirmed; a grep for `OptimisticLockMixin` usage across all model files
  confirmed it is used by `property.py`/`matter.py`/`client.py`/`document.py` but **not** by
  `financial.py` today — cited as relevant context for why `ADR/0028` does not rely on optimistic
  locking alone to satisfy rule 38.
- `backend/src/app/infrastructure/persistence/models/document.py` — `DocumentVersion` (lines 75–85)
  re-read in full: no `AuditMixin`, no `updated_at`, no `deleted_at`, no `version` — confirmed as
  this repository's own existing append-only-immutability prior art, cited (and distinguished from)
  in `ADR/0028`'s Decision D.
- A full grep for `CREATE TRIGGER|trigger` across `backend/src/app` and the Alembic migrations
  directory returned zero matches — confirming no database-trigger infrastructure exists anywhere
  in this repository, the specific fact `ADR/0028` cites to reject a trigger-based immutability
  mechanism in favor of service-layer enforcement.
- `backend/src/app/infrastructure/persistence/migrations/` — confirmed Alembic-based, no dynamic-
  DDL-at-runtime pattern, consistent with `ADR/0027`'s own prior finding.

## 5. Decision Made

Charge and Expense adopted as two distinct, first-class, Matter-scoped tables (`charges`,
`expenses`), each carrying a nullable `invoice_id` FK mirroring `Payment.invoice_id`'s existing
precedent. Invoice retains its own persisted `amount`/`tax_amount`/`total_amount` columns, computed
from linked Charges/Expenses at issuance and frozen thereafter (a snapshot, not a live-derived
aggregate). PaymentAllocation adopted as a dedicated `payment_allocations` table targeting Invoice
only (not Charge directly), with a mandatory `invoice_id` FK and a transaction-scoped,
row-lock-enforced sum invariant (a bare `CHECK` constraint cannot aggregate across sibling rows).
Historical financial data becomes architecturally immutable once finalized (Charge/Expense: once
invoiced; Invoice: once `status` leaves `draft`; Payment: once `status` is `completed`); corrections
are new reversal/adjustment records, never in-place `UPDATE`s — enforced at the service layer, not
via a database trigger (none exist anywhere in this repository). The Matter-vs-File attachment
granularity for Charge/Expense is explicitly named as an inference (Matter-scoped, per §2's own
Charge/Expense dependency rows), not a resolution of Required ADR #8, mirroring `ADR/0027`'s
identical disclosure discipline for File Number's own format.

## 6. Alternatives Evaluated

Four alternative sets, each scored against concrete Legal_DMS requirements (not generic
architectural preference), in `ADR/0028`'s own four comparison tables:

1. **Charge/Expense structural shape** — a single generic `financial_line_items` table with a type
   discriminator was rejected as exactly the "generic 'amount' field" §7 Phase 7 warns against, and
   as insufficiently distinguishable under rule 36's own language; two distinct tables were
   selected, matching §10.A's own separate naming.
2. **Charge/Expense ↔ Invoice model** — a fully query-time-derived Invoice total was rejected as a
   direct rule 38 violation (a later Charge edit would silently change an already-issued Invoice's
   displayed total); no-linkage-at-all was rejected as failing to make Charge/Expense genuinely
   related to Invoice per rule 35; a dedicated join table was rejected as unneeded complexity given
   the specification's own linear (not many-to-many) billing chain; a nullable `invoice_id` FK with
   totals frozen at issuance was selected.
3. **PaymentAllocation target** — direct Charge-targeting was rejected against §17.8's own
   Charge→Invoice→Payment→Allocation sequencing; a discriminated either-target model was rejected on
   the same conflation-risk grounds as alternative 1, and for lacking textual support (§2 names only
   `Payment/Invoice`); Invoice-only targeting, directly evidenced by §2's own dependency row, was
   selected over a polymorphic `entity_type`/`entity_id` pattern (rejected because that pattern
   exists elsewhere in this codebase for genuinely poly-target event logs, not a singular,
   FK-enforceable target like this one).
4. **Historical mutation mechanism** — mutable-rows-plus-audit-log was rejected as logging-only, not
   prevention; `OptimisticLockMixin`-style version enforcement was rejected as solving a different
   problem (concurrent conflicts, not authorized silent edits) though noted as a reasonable
   complementary addition, not a substitute; full `DocumentVersion`-style row-versioning was
   considered seriously as proven repository prior art but rejected as the *primary* mechanism
   because a financial correction has its own accounting-standard shape (a signed reversal
   transaction, not a version bump); immutable-after-finalization rows plus explicit
   reversal/adjustment records was selected, combining `DocumentVersion`'s append-only philosophy
   with the correction-as-transaction shape rule 38 and §17.8's "historical integrity" test imply.
   A database-trigger enforcement point was explicitly rejected (no precedent anywhere in this
   repository) in favor of service-layer enforcement, mirroring `ADR/0027`'s identical "no
   unevidenced new infrastructure" discipline.

## 7. Concurrency/Integrity Reasoning

`ADR/0028`'s own "Detailed Integrity & Concurrency Analysis" section addresses concurrency **only**
where the financial invariants genuinely require it, per this task's own explicit instruction not to
introduce concurrency mechanisms merely because `ADR/0027` did. The one genuinely concurrency-
sensitive invariant — a Payment's total allocated amount never exceeding the Payment's own amount
(rule 37) — cannot be expressed as a single-row `CHECK` constraint (Postgres cannot aggregate across
sibling rows in a `CHECK`), so the architecture specifies a transaction-scoped row lock on the parent
Payment (`SELECT ... FOR UPDATE`) before validating and inserting a new allocation, the same
row-lock-then-validate shape `ADR/0027` established for its own counter table, applied here because
the underlying race (two concurrent allocation attempts against one Payment) is real, not
hypothetical. Invoice-total consistency, historical-mutation prevention, and Charge/Expense
semantic-collapse prevention are each addressed structurally (frozen snapshot totals, immutability-
after-finalization, and physically separate tables, respectively) rather than via any additional
concurrency mechanism — explicitly stated as such in `ADR/0028`, not left ambiguous.

## 8. Scope/Boundary Reasoning

The specification leaves Charge/Expense's exact Matter-vs-File attachment granularity among the
items Required ADR #8 must eventually resolve (§24.8, shared across File/Workflow/Task/
GovernmentProcess/Charge/Expense). `ADR/0028`'s "Attachment-Granularity Boundary" section states the
Matter-scoped recommendation and grounds it in one named textual signal (§2's Feature Catalogue
naming Charge's dependency as `Matter` specifically, not `Matter/File`) while explicitly disclosing
that Expense's own catalogue row names `Matter/File` — a genuine, disclosed asymmetry the ADR does
not paper over or silently resolve in either direction. This mirrors `ADR/0027`'s own disclosure
discipline for File Number's format (an inference, not a specification mandate), applied here to a
different open item.

## 9. Relationship to ADR/0021–ADR/0027

- **`ADR/0021`**: `charges`/`expenses`/`payment_allocations`/`commercial_scopes`/`refunds` all
  require a mandatory, directly-carried `organization_id`, mirroring `ADR/0024`'s, `ADR/0026`'s, and
  `ADR/0027`'s identical discipline for their own new tables. Not modified, reopened, or
  reinterpreted.
- **`ADR/0022`**: Charge/Expense/PaymentAllocation mutation, and specifically the
  reversal/adjustment operations Decision D requires, are governed by whatever future `finance:*`
  permission the existing resource+action model is extended to include — no new authorization
  surface or mechanism is introduced by this ADR itself. Not modified, reopened, or reinterpreted.
- **`ADR/0023`, `ADR/0024`, `ADR/0025`, `ADR/0026`**: no direct interaction; cited only for the
  consistency of evidentiary discipline this ADR follows. None modified.
- **`ADR/0027`**: no direct interaction with the financial ledger boundary itself; cited as
  evidentiary-discipline precedent (tenant-isolation composition pattern, deferred-scope disclosure
  pattern, and the "no unevidenced new infrastructure" rejection reasoning this ADR reuses for its
  own trigger-rejection decision). Not modified.

## 10. Explicitly Deferred Matters

- Whether Charge/Expense/Commercial Scope should ever attach at File granularity — Required ADR
  #8's territory, disclosed, not resolved.
- Required ADR #10 (Document/File relationship) and #20 (migration strategy, including
  `client_id`→Party redirect timing on Invoice/Payment) — untouched.
- Commercial Scope's own fee-structure modeling (fixed/hourly/milestone) and revision/re-baselining
  mechanism, beyond the minimum needed to name it as a related, not-yet-designed entity.
- Refund's full field list and partial/multiple-refund support.
- Charge-type and Expense-category vocabularies (organization-configurable content per §6.2, not
  architecture).
- Whether `OptimisticLockMixin` should also be adopted on Finance tables as defense-in-depth
  (explicitly named as a reasonable future addition, not required by this ADR's own mechanism to
  satisfy rule 38).

## 11. Exact Files Changed

```
$ git status
On branch docs/t94-adr-0028-financial-ledger-boundary
Untracked files:
  ADR/0028-financial-ledger-boundary-charge-expense-invoice-payment-allocation.md
  docs/reviews/T94_Software_Architect_Report.md

$ git diff --stat main
(empty prior to this commit -- both files are new, untracked)
```

Exactly two new files, both documentation. No existing file was modified — confirmed `ADR/0021`–
`ADR/0027`, `ADR/0001`–`0020`, `ADR/template.md`, the specification, `IMPLEMENTATION_QUEUE.md`, and
`PROJECT_STATE.json` do not appear anywhere in this branch's diff against `main`.

## 12. Confirmation No Implementation Occurred

No database table, migration, backend model, service, repository, route, frontend, or test was
created or modified. No schema or configuration file was touched. `ADR/0028` describes the target
mechanism; it implements none of it — stated explicitly in the ADR's own "Implementation Boundary"
section.

## 13. Confirmation Governance Files Were Untouched

`PROJECT_STATE.json` was not modified — confirmed absent from this branch's diff, per this task's
own explicit instruction not to modify it during architecture drafting. `IMPLEMENTATION_QUEUE.md`
was not modified — confirmed absent, per the same explicit instruction (this task's authorization
was recorded directly by the project owner in-session, not as a governance commit; see §2). No `T95`
was created or authorized. `T94` is not marked Done by this report or any file it changes — that
remains a post-QA, post-merge governance closeout step, per the established `T87`–`T93` pattern this
task's own governance boundary explicitly preserves.

## 14. Genuine Contradictions or Specification Gaps

None found that required stopping. Rule 38's "must not be silently overwritten" names the
requirement but not the mechanism — this is exactly the ED this ADR is meant to resolve, not a
specification defect. §2's Feature Catalogue disclosing an asymmetry between Charge's (`Matter`) and
Expense's (`Matter/File`) stated dependencies is a genuine, disclosed signal this ADR does not
resolve in either direction (see §8 above) — not a contradiction, since both rows are independently
consistent with §24.8's own "File-vs-Matter attachment granularity is ED, Required ADR #8's
territory" framing.

## 15. Final Architecture Status

`ADR/0028` resolves Required ADR #13 in full: the Charge/Expense structural shape, the Charge/
Expense↔Invoice linkage model, PaymentAllocation's target model and integrity mechanism, and the
historical-mutation enforcement mechanism are all decided, with Commercial Scope's fee-structure
design and Refund's full architecture left deliberately underspecified pending their own future
scoping. No other Required ADR is resolved, reinterpreted, or narrowed. `ADR/0021`–`ADR/0027` are
not modified.

## Reviewer Checklist

Per `docs/prompts/SoftwareArchitect.md` §8's required output and
`docs/ImplementationLog/README.md`'s standard eleven-item self-assessment:

```
Reviewer Checklist

[x] Architecture preserved -- ADR/0021, ADR/0022 composed with, not modified or contradicted;
    S4 rules cited, not reinterpreted.
[x] Existing design patterns followed -- Payment.invoice_id's nullable-FK precedent reused directly
    for Charge/Expense; DocumentVersion's append-only philosophy informs (without being copied
    verbatim into) the historical-mutation mechanism; organization_id-on-new-table pattern matches
    ADR/0024/ADR/0026/ADR/0027's identical discipline.
[ ] Tests added -- none; documentation-only architecture task, no implementation authorized.
[ ] Existing tests pass -- not applicable; no code changed for the test suite to exercise.
[x] Documentation updated -- ADR/0028 and this report are the documentation this task produces.
[x] ADR updated (if required) -- ADR/0028 created (Required ADR #13 resolution); ADR/0021-0027 not
    touched, correctly.
[ ] AI_BOOTSTRAP updated (if required) -- not required by this task's authorized scope.
[ ] PROJECT_STATE updated (if required) -- deferred by design to post-QA governance
    synchronization, per this task's own explicit instruction not to modify it now.
[ ] No unrelated refactoring -- not applicable; no code touched at all.
[x] No scope creep -- Required ADR #8, #10, #20 explicitly not touched; Commercial Scope's full
    fee-structure design and Refund's full architecture explicitly not designed; only #13 resolved.
[x] Ready for QA -- ADR/0028 and this report are complete and handed off below.
```

## QA Handoff

This branch (`docs/t94-adr-0028-financial-ledger-boundary`) is handed off to the QA Reviewer role
for an independent, formal QA Decision against the actual remote PR HEAD once opened — per this
task's own governance boundary and this repository's established documentation-only-work QA
requirement (`T80`–`T93` precedent). The QA Reviewer is specifically asked to independently verify
the allocation-sum concurrency mechanism's correctness claims (`ADR/0028`'s "Detailed Integrity &
Concurrency Analysis" section) mechanically, not merely accept them; to confirm the Matter-scoped
attachment recommendation for Charge/Expense is genuinely labeled as an inference (with the
Charge/Expense asymmetry honestly disclosed) rather than presented as resolving Required ADR #8; and
to confirm the historical-mutation mechanism (immutable-after-finalization plus reversal records)
actually satisfies rule 38 rather than merely restating it.

## QA Decision

☐ Approved
☐ Approved with comments
☐ Rework required

This Software Architect pass does not record, anticipate, or imply any of the three outcomes above
— per `docs/prompts/SoftwareArchitect.md` §11/§13, this role never renders a QA Decision or
substitutes for the QA Reviewer. `ADR/0028` and this report are not self-certifying.

---

**This report ends T94's authorized scope at the implementation PR handoff.** Per this task's own
governing instructions, T94 stops here, awaiting independent QA. No further action (opening/merging
a PR beyond the point specified below, creating T95, marking T94 Done, performing QA, governance
closeout) is taken by this pass.
