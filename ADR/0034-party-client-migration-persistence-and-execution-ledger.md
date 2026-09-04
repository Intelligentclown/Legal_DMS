# ADR-0034: Party/Client Migration Persistence and Execution-Ledger Architecture

**Status:** Proposed
**Date:** 2026-09-04

**Resolves:** the durable persistence and execution-ledger architecture gap `ADR/0033` and the T109/T111
workflow intentionally left open: how a later write-capable Party/Client migration executor proves what
it has already durably applied, retries safely, and fails closed on stale or conflicting legacy data.

**Does not resolve:** the governed specification's still-open broader migration planning item in full.
That broader item still includes Matter's `property_id` / `matter_type_id` retirement, Document's
`matter_id` -> `file_id` redirect, cutover sequencing for other entities, and any non-Party slice not
named in this ADR. Also does not reopen `ADR/0020`, `ADR/0021`, `ADR/0023`, `ADR/0028`, `ADR/0032`, or
`ADR/0033`. This ADR does not authorize or implement schema migrations, Party or `MatterParty` ORM
models, bridge columns, ledger tables, data writes, executor code, API/frontend work, RLS changes, or
governance closeout.

**Dependencies:** `ADR/0020-session-commit-rollback-policy.md` (one committed unit is atomic or rolled
back), `ADR/0021-organization-tenant-boundary-enforcement.md` (every final migrated row is
Organization-scoped and fail-closed), `ADR/0023-party-vs-client-architecture.md` (Party is the master
record, Client is legacy input / Matter-role history), `ADR/0028-financial-ledger-boundary-charge-expense-invoice-payment-allocation.md`
(financial client redirects remain migration-side retargeting, not a finance redesign), `ADR/0032-user-organization-pre-existing-data-reconciliation.md`
(explicit operator reconciliation precedent for tenantless legacy data), `ADR/0033-party-client-migration-organization-boundary.md`
(the governed migration shape, unresolved-set stop rule, and T108/T109/T111 preparation chain this ADR
extends).

## Problem

`ADR/0033` decided the Party/Client migration shape, the deterministic-vs-operator-reconciled
Organization-assignment rule, the compatibility-first cutover, and the requirement for durable audit
evidence. `docs/PartyClientReconciliationContract.md` then governed the frozen reconciliation artifact,
and T110/T111 governed artifact validation plus live stale checking.

What remains genuinely undecided is the **write-capable execution boundary**:

- where durable migration-completion state lives;
- which identity proves "this legacy Client already became this exact Party in this exact Organization";
- how that proof composes with the frozen T109 artifact and the T111 live-staleness gate;
- when a retry is a safe no-op vs. a hard collision;
- how interrupted runs resume without heuristic repair;
- and what minimum contract a future executor must obey without this ADR having to implement it.

Without this decision, a future implementation would have to invent its own resumability and collision
rules at the moment it begins mutating Party-side data, which would be an unauthorized architectural
decision at the most failure-sensitive point of the migration.

## Options Considered

1. **Artifact-only persistence** — treat the frozen T109 reconciliation artifact plus live Party-table
   inspection as the only durable record of execution.
   - Pros: no extra durable structure beyond already-governed artifacts; superficially simple.
   - Cons: cannot distinguish "authorized reconciliation input exists" from "this migration unit was
     durably applied"; cannot prove retry identity without reverse-engineering live Party-side state;
     collapses execution audit into business tables; makes interrupted-run recovery and hard-collision
     detection under-specified.

2. **Reuse `parties` (and future bridge targets) as the only completion record** — infer prior success
   from a Party row and retargeted foreign keys alone.
   - Pros: no dedicated execution record to maintain.
   - Cons: violates `ADR/0033`'s requirement for a durable migration audit artifact distinct from the
     business rows; cannot distinguish identical replay from partial or conflicting application without
     ad hoc joins; forces future implementation to encode operational state inside canonical business
     entities; makes retirement/audit retention coupled to Party-row lifetime.

3. **Dedicated durable execution ledger, separate from Party business rows (selected)** — a governed
   migration-ledger persistence mechanism records one immutable completion record per migrated legacy
   Client anchor, tied to the exact accepted reconciliation basis and execution version.
   - Pros: makes completion, idempotency, collision detection, and resumability explicit; keeps
     operational evidence separate from business entities; composes cleanly with T109/T110/T111;
     supports later executor implementation without inventing rules mid-flight.
   - Cons: requires a future schema object and write path not implemented here; adds one more artifact
     for future code to maintain.

## Decision

**A future write-capable Party/Client migration executor must persist completion state in a dedicated,
append-only execution ledger that is architecturally separate from the Party/business tables it
mutates.**

The selected persistence architecture is:

1. **One durable ledger record per legacy Client anchor per executor version and accepted source basis.**
   The anchor is the legacy `clients.id` UUID that T108/T109/T111 already govern.
2. **Ledger identity is composite, not "Party row exists".** A completion record is uniquely identified
   by:
   - `legacy_client_id`
   - `party_id`
   - `organization_id`
   - `executor_version`
   - accepted reconciliation basis identity:
     - T109 `set_id`
     - T109 `source_report.report_sha256`
     - the exact selected Organization semantics from the executable T109 entry
   - source fingerprint for the exact legacy Client anchor at execution time
3. **The durable ledger is the sole architectural proof of completed execution.** A Party row or
   retargeted FK alone is insufficient proof that the same governed migration unit completed safely.
4. **Deterministic and operator-reconciled mappings share one ledger structure but must retain their
   distinction explicitly.** Each record stores whether the accepted basis was `deterministic` or
   `operator_reconciled`; operator-reconciled records additionally retain the operator-selected basis
   reference already governed by T109.
5. **One committed migration unit is atomic.** Within a given execution unit, all Party-side writes,
   bridge/retarget writes for that unit, and the ledger completion record commit together or all roll
   back together, per `ADR/0020`.
6. **Retry is idempotent only when the ledger proves an identical prior completion.** If a later run
   finds a ledger record whose full identity tuple matches the exact current governed basis, it may skip
   that unit as already complete. Any mismatch is a hard collision or stale-input failure, not a case
   for silent overwrite.
7. **Interrupted-run recovery is ledger-driven.** Recovery re-evaluates each anchor by checking for an
   identical immutable completion record. Missing record means the unit is not complete, even if some
   business rows appear present; that is a fail-closed condition requiring investigation or rollback by
   governed implementation logic, not heuristic inference by this ADR.
8. **Execution chunking is permitted only above the unit boundary.** A future executor may process many
   anchors in one run, but the minimum correctness guarantee is per-anchor (or per explicit unresolved
   anchor-set if future implementation proves such grouping necessary). A chunk must never let one
   anchor's ledger record commit while another anchor's business rows for the same committed unit do
   not.
9. **Ledger retention is long-lived and independent of legacy-table retirement.** The ledger remains as
   immutable migration history after `clients` and bridge columns are eventually retired. Any archival
   or retirement policy must preserve the ability to audit which exact reconciliation basis produced each
   Party mapping.

## Reasoning

### 1. Why the ledger must be separate from Party rows

`ADR/0023` makes Party the canonical business master record. Using Party itself as the migration
checkpoint would mix two concerns:

- "what the business entity is"; and
- "what operational run proved this entity came from this exact legacy Client basis."

Those are not the same fact. A future Party row could exist for reasons other than a cleanly completed
legacy migration unit, and a future code path inspecting only Party-side state could not reliably tell
whether it is seeing:

- a legitimate identical replay;
- a partial write left by interruption;
- a conflicting mapping from a different reconciliation basis; or
- an implementation bug that created a Party without finishing the governed retargets.

A dedicated ledger keeps the executor's proof obligation explicit and auditable.

### 2. Why artifact identity alone is not enough

T109's artifact already proves the accepted reconciliation basis, and T111 proves that basis is still
current at execution time. But neither one records **that the write actually happened**. They are input
governance artifacts, not execution completion evidence. The future executor therefore needs a durable
output-side record keyed to that governed input.

### 3. Identity and uniqueness semantics

The governing question is not merely "has this `legacy_client_id` ever been seen?" It is "has this
exact governed mapping already been completed?"

That requires the ledger record to bind together:

- the legacy anchor (`legacy_client_id`);
- the resulting canonical Party (`party_id`);
- the tenant boundary (`organization_id`);
- the accepted frozen basis (`set_id`, `report_sha256`, decision state/selection);
- the executor implementation identity (`executor_version`);
- and the exact source fingerprint observed when the executor applied it.

This composite identity yields the two required outcomes:

- **identical completion**: every field matches, so re-run is a safe no-op;
- **hard collision**: any field that changes the meaning of the completed mapping differs, so the
  executor must abort rather than reinterpret history.

### 4. Source fingerprint and legacy version relationships

`client_migration_preflight.py` already computes ledger evidence against a fingerprint shaped as
`<ModelName>:<id>:<version>:<updated_at>`. That repository reality matters here: the future execution
ledger must preserve a source fingerprint that is at least strong enough to prove the exact legacy
anchor version the executor accepted.

This ADR therefore requires the completion ledger to retain:

- `legacy_client_id`
- the legacy row `version`
- the legacy row `updated_at` or an equivalent canonical timestamp basis
- a canonical source fingerprint string derived from those values

Dependent rows do not each need independent completion rows under this ADR, but the executor must be
able to prove that the migrated unit's completion was bound to the exact accepted anchor basis and the
same governed reconciliation input. If future implementation needs richer per-dependent fingerprints,
that is consistent with this ADR so long as the anchor-level completion identity remains intact.

### 5. Deterministic vs operator-reconciled representation

`ADR/0033` and T109 distinguish deterministic evidence from operator reconciliation for a reason: the
operational risk profile differs. A deterministic mapping means "the repository's own governed evidence
yielded exactly one Organization." An operator-reconciled mapping means "the evidence did not yield a
unique result, and a human selected one Organization under T109."

Those should not be separate ledger subsystems, because the later executor must consume either through
one consistent idempotency and atomicity rule. But they must not be flattened into an indistinguishable
"resolved" bit either. The ledger therefore stores a single completion record shape with an explicit
resolution mode and the exact T109 basis reference.

### 6. Atomicity and interrupted-run recovery

Per `ADR/0020`, transaction boundaries are load-bearing. For this migration architecture, that means a
migration unit is only complete when:

- the Party-side target row exists;
- every in-scope retarget for that unit exists in the exact same transaction boundary the future
  implementation defines for that unit; and
- the immutable completion ledger record exists for that same unit.

If a run is interrupted before commit, none of those facts may survive as a reported completion. If a
run is interrupted after some earlier unit committed, that earlier unit is recoverable because its
ledger record exists unchanged. This is the minimal durable rule that lets a future executor restart
without guessing.

### 7. Exact identical-completion vs hard-collision semantics

The future executor may treat a prior record as an already-completed no-op only when all of the
following still match:

- same `legacy_client_id`
- same `party_id`
- same `organization_id`
- same `executor_version`
- same T109 `set_id`
- same T108 `report_sha256`
- same decision state (`deterministic` or `operator_reconciled`)
- same selected Organization outcome
- same source fingerprint

Any mismatch is not a soft warning. It is either:

- stale input (for example, changed source fingerprint or changed report basis); or
- hard collision (for example, same legacy client already claimed by a different Party or Organization).

In both cases the architecture requires fail-closed abort, not overwrite, merge, or heuristic repair.

### 8. Minimum contract for a future executor

A later write-capable executor must obey all of the following:

- consume only a T109 artifact that T110 validates and T111 re-verifies as executable/non-stale;
- derive one migration unit from one executable legacy Client anchor unless a separately justified
  grouped unresolved set is still governed identically;
- write the Party-side business rows and completion ledger atomically for that unit;
- skip only ledger-proven identical completions;
- abort on any collision, stale basis, or missing completion proof;
- never infer operator intent beyond what the T109 artifact explicitly records;
- preserve immutable completion history even after legacy compatibility structures are later removed.

## Trade-offs

- **Extra persistence object later:** the selected design commits the future implementation to creating a
  ledger persistence mechanism instead of hiding state in Party rows. That is more explicit work, but it
  prevents silent coupling between operational history and business identity.
- **Strict fail-closed retries:** this architecture rejects "best effort" repair of partially-present
  Party-side state. That raises the operational bar for future implementation, but it is consistent with
  the repository's governance stance on tenant safety and migration correctness.
- **Executor-version-sensitive idempotency:** a changed executor version participates in completion
  identity. That means a future implementation cannot silently reinterpret old completion records as
  identical. The cost is less flexibility; the benefit is auditability when migration logic changes.
- **Append-only history over convenience:** immutable ledger history means future tooling must layer
  summaries/views on top rather than editing old records in place. That is deliberate: completed
  migration evidence should be durable, not rewritten.

## Future Impact

- A later implementation task now has a fixed architectural target for durable completion state and
  retry semantics; it no longer needs to invent whether "Party exists" is enough proof.
- The future schema/migration task must introduce a dedicated ledger persistence mechanism consistent
  with this ADR, but that implementation remains separately unauthorized.
- `ADR/0033`'s required durable audit evidence is now concretized for the execution phase without
  broadening the Party migration scope beyond the Party/Client slice.
- If future implementation discovers that one anchor cannot be the correct atomic unit and that a
  larger grouped unresolved-set commit is required, that implementation may do so only if it preserves
  this ADR's invariants: explicit basis identity, atomic business-write-plus-ledger commit, immutable
  completion history, and fail-closed collision semantics.
- Broader Required ADR work remains open: Matter `property_id` / `matter_type_id` retirement,
  Document `matter_id` -> `file_id`, and other non-Party migration seams still need their own governed
  decisions or implementation slices.
