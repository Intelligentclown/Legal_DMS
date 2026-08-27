# ADR-0027: File Numbering Algorithm and Concurrency Strategy

**Status:** Proposed
**Date:** 2026-08-27

**Resolves:** `docs/Legal_DMS — Domain Model & Functional Specification.md` §21 planning-list item
**#9** ("File numbering strategy").

**Does not resolve:** Required ADR #1–#7, #18, or #19 (already resolved by
`ADR/0021`–`ADR/0026`, not reopened here) or Required ADR #8, #10–#17, #20 (untouched — in
particular, File's own broader field list, Matter-vs-File lifecycle, Matter-deletion cascade
behavior, and Workflow/Task/GovernmentProcess attachment granularity all remain #8's territory,
not decided by naming a `file_number` field here).

**Dependencies:** `ADR/0021` (tenant isolation — the generator table this ADR decides is
Organization-scoped, composed with, not reopened). `ADR/0022` (authorization — File-number
generation is governed by the existing resource+action permission model, composed with, not
reopened). `ADR/0023`–`ADR/0026` (no direct interaction; cited for consistency of evidentiary
discipline only).

## Context

The governed specification freezes, as Confirmed Business Rules, that a File Number is assigned
when the File is created (§4 rule 6) and must never be silently reused (§4 rule 7), and treats
"Concurrent File creation → no duplicate" as one of five **mandatory** tests (§17.5). §12, §25
(invariant #8), and §26 (item 6) all classify the numbering algorithm and its concurrency
mechanism as blocking correct schema design, with §26 explicitly flagging it "concurrency-critical,
not cosmetic" — the strongest urgency language given to any remaining unresolved item in that list.

What is **not** frozen: the algorithm itself, the concurrency-safety mechanism, and the numbering
scope/format. §24.8's own "File Numbering" block states all three are `ED — must decide before
implementation`, naming three unchosen candidate mechanisms (a Postgres `SEQUENCE`, a locked
generator-row table, an application-level distributed lock) and three unchosen scope options
(Organization-scoped, Matter-scoped, globally sequential). This ADR resolves all three questions.

### Repository baseline (direct inspection, `main` at this ADR's authoring baseline)

- **No File entity, and no File-numbering mechanism, exists anywhere in `backend/src/app`.**
  `documents.matter_id` links directly to `Matter` with no intermediate File concept — confirmed;
  this matches §9.4's own "No finalized File entity identified" finding.
- **The closest existing precedent is `matters.matter_number`**
  (`backend/src/app/infrastructure/persistence/models/matter.py:49`) — a plain
  `String(50)`, `unique=True` column, **no visible generation mechanism anywhere in the
  application**: a full grep for `matter_number`/`invoice_number`/`receipt_number` outside the
  model files themselves returns zero matches — confirming these values are never actually
  *generated* by any application-layer service today (uniqueness is DB-enforced; the algorithm
  that would produce the next value does not exist in code). `invoices.invoice_number`
  (`financial.py:34`) and `receipts.receipt_number` (`financial.py:65`) are the identical pattern.
- **No Postgres `SEQUENCE`, `SELECT ... FOR UPDATE`/`with_for_update()`, or advisory-lock usage
  exists anywhere in `backend/src/app`** — confirmed by a full grep. This is a genuinely
  from-scratch mechanism decision, not an extension of existing code, unlike several of this
  cluster's prior ADRs.
- **`OptimisticLockMixin`** (`infrastructure/persistence/models/mixins.py`) is this codebase's
  existing concurrency-control default — SQLAlchemy-enforced version-column optimistic locking,
  opted into "per model where concurrent edits are realistic," per the mixin's own docstring. This
  is directly relevant context, not directly applicable: optimistic locking is well-suited to
  *infrequent* concurrent edits of a business row (the mixin's own stated use case), not to a
  counter row every File-creation request under the same scope must touch — see "Alternatives
  Considered" for why this ADR deliberately does not reach for this codebase's own default pattern
  here.
- **`docker-compose.yml` runs `postgres:16-alpine` only** — no Redis, no external lock/queue
  service exists in this repository's infrastructure. Postgres 16 fully supports both native
  `SEQUENCE` objects and row-level `SELECT ... FOR UPDATE` locking; the async engine
  (`create_async_engine`, `asyncpg`, confirmed in `infrastructure/database/session.py` and
  `backend/pyproject.toml`) supports both without complication.
- **§9.4/§10.A's own candidate table list names `file_number_sequences`** — a *table* name, not a
  description of a native database `SEQUENCE` object. This is a real, if non-binding, textual
  signal (not a specification mandate) toward the locked-row-table mechanism this ADR selects —
  named honestly as suggestive evidence, not overclaimed as dispositive.
- **`ADR/0020`'s existing per-request transaction boundary** (`get_db()`: commit on success,
  rollback on exception) is the transaction scope this ADR's mechanism operates inside — no new
  transaction-management infrastructure is required.

## Decision

**A dedicated, Matter-scoped generator table, `file_number_sequences`, using an atomic
`INSERT ... ON CONFLICT DO UPDATE ... RETURNING` upsert (Postgres's standard atomic-counter idiom,
functionally equivalent to `SELECT ... FOR UPDATE` row locking) is adopted** — not a native Postgres
`SEQUENCE`, not an application-level lock, not a distributed lock. File Numbers are **Matter-scoped**
by architectural recommendation (the specification leaves this genuinely open; see "Scope Decision"
below for why this is an inference, not a mandate). The counter's increment and the new File row's
own creation must occur in the same database transaction, so that a failed/rolled-back File-creation
attempt never permanently consumes a number.

## Decision Drivers

Ranked in the order this ADR actually weighs them, matching `ADR/0021`–`0026`'s established
evidentiary discipline:

1. **§17.5's mandatory "no duplicate under concurrent creation" test** — any candidate that cannot
   explain, mechanically, why two concurrent transactions can never receive the same number is
   disqualified outright, regardless of other merits.
2. **§4 rule 7 (never silently reused)** — the mechanism must not create a code path where a
   number, once truly assigned to a persisted File, could ever be reissued.
3. **Repository/operational consistency** — prefer a mechanism using this codebase's existing
   transaction/session conventions (`ADR/0020`) over one requiring new infrastructure (external
   locks) or new operational lifecycle management (per-Organization dynamic DDL).
4. **Contention/throughput** — among mechanisms that equally satisfy 1–3, prefer the one that
   distributes lock contention most naturally across this system's actual write pattern, not the
   one that is merely simplest to describe.

## Alternatives Considered

### 1. Native PostgreSQL `SEQUENCE` object

One `CREATE SEQUENCE` per numbering scope (e.g., per Organization), `nextval()` called at File
creation.

| Criterion | Assessment |
|---|---|
| Concurrency correctness | **Strong** — Postgres sequences are internally atomic and safe across concurrent transactions/processes by design. |
| Rollback behavior | **Genuine weakness for this use case** — `nextval()` is explicitly non-transactional; a value obtained by a transaction that later rolls back is *not* returned to the pool, permanently burning a gap on every failed File-creation attempt. Not a rule-7 violation (the number was never assigned to a persisted File), but a real, avoidable property this ADR's selected mechanism does not share. |
| Scope compatibility | **Poor fit for Matter- or Organization-scoped numbering** — a `SEQUENCE` is a schema-level object; creating one per Organization (or per Matter) requires dynamic DDL executed at Organization/Matter-creation time, mixing schema changes into ordinary business-data operations. This codebase's only DDL path today is Alembic migrations, run at deploy time — confirmed no dynamic-DDL-at-runtime pattern exists anywhere in the repository. Introducing one would be new operational infrastructure, not a reuse of an existing pattern. |
| Repository precedent | None. |

**Rejected** — the scope-compatibility problem is the deciding factor: a single global `SEQUENCE`
would satisfy concurrency safety trivially but forecloses Organization/Matter-scoped numbering
without a strong justification for choosing global scope on other grounds (see "Scope Decision"),
and a per-scope `SEQUENCE` requires dynamic DDL this codebase has no precedent for and this ADR is
not positioned to introduce as a side effect of a numbering decision.

### 2. Dedicated generator-row table, atomic upsert (this ADR's selection)

One row per numbering-scope key (this ADR: per `matter_id`) in `file_number_sequences`, holding a
`next_number` counter. Generation uses `INSERT INTO file_number_sequences (matter_id,
organization_id, next_number) VALUES (:matter_id, :org_id, 1) ON CONFLICT (matter_id) DO UPDATE SET
next_number = file_number_sequences.next_number + 1 RETURNING next_number` — a single atomic
statement that both lazily creates the counter row on a Matter's first File and increments it on
every subsequent one, executed inside the same transaction as the new File row's own `INSERT`.

| Criterion | Assessment |
|---|---|
| Concurrency correctness | **Strong** — Postgres serializes concurrent `INSERT ... ON CONFLICT` statements targeting the same conflict key at the row level; a second concurrent transaction targeting the same `matter_id` blocks until the first commits or rolls back, then proceeds against the now-current value. Identical guarantee to explicit `SELECT ... FOR UPDATE`, expressed as one atomic statement instead of two. |
| Rollback behavior | **Correct by construction** — the counter's `UPDATE`/`INSERT` and the File row's own `INSERT` share one transaction (`ADR/0020`'s existing per-request boundary); if the File row fails to persist for any reason, the whole transaction rolls back, including the counter change — the number is never burned by a failed attempt, unlike option 1. |
| Scope compatibility | **Direct** — one row per `matter_id` (or per `organization_id`, if that scope were chosen instead) is ordinary DML, requiring no schema-level operation per new Matter/Organization; the row is created lazily, on demand, by the same statement that increments it. |
| Repository/session consistency | **Direct** — operates entirely within `ADR/0020`'s existing `get_db()` transaction boundary; no new transaction-management code needed. |
| Tenant isolation | Direct — `organization_id` sits on `file_number_sequences` exactly like any other tenant-scoped table under `ADR/0021` (see "Tenant-Isolation Composition"). |
| Repository precedent | None directly (no existing counter table), but the mechanism is ordinary SQLAlchemy Core/`INSERT ... ON CONFLICT` usage, not a novel idiom for this codebase's stack. |
| Textual signal | §9.4/§10.A names a *table*, `file_number_sequences`, matching this option's shape more directly than option 1's (which would need no table at all). |

**Selected** — the only option that simultaneously satisfies strict concurrency correctness,
correct rollback behavior, and Matter/Organization-scoping without new infrastructure.

### 3. PostgreSQL advisory lock (`pg_advisory_xact_lock`)

A transaction-scoped advisory lock keyed by a hash of the numbering-scope identifier (e.g.
`matter_id`), acquired before reading/incrementing a counter value stored elsewhere (e.g. directly
computed via `MAX(file_number) + 1` over existing Files in the Matter, or a separate counter
column).

| Criterion | Assessment |
|---|---|
| Concurrency correctness | Strong, if paired with a correct read-increment step inside the lock — the lock itself only serializes access; it does not compute the next value. |
| Extra complexity vs. option 2 | Requires a *separate* mechanism to actually determine the next number (e.g., `MAX(file_number)+1`, which is itself fragile if numbers are ever non-sequential strings, or a counter column needing the same upsert logic option 2 already provides) — advisory locks solve only the serialization half of the problem, and option 2's `INSERT ... ON CONFLICT` already provides both serialization *and* the counter value in one statement, at no extra cost. |
| Auditability/introspection | Weaker — an advisory lock leaves no queryable row showing the current counter state, unlike option 2's `file_number_sequences` table, which is directly inspectable for operational/debugging purposes. |
| Repository precedent | None. |

**Rejected** — not because it is unsafe, but because it solves only part of the problem option 2
solves in a single, simpler, more auditable statement; adopting it would add a second mechanism
(advisory lock + a separate counter source) for no correctness or performance gain over option 2.

### 4. Application-level in-process lock (e.g., a Python `asyncio.Lock`)

| Criterion | Assessment |
|---|---|
| Concurrency correctness across processes | **Fails outright** — an in-process lock is invisible to any other worker process, container, or horizontally-scaled instance of the application. Any deployment running more than one application process (the normal case for a production API server) would have concurrent File-creation requests landing on *different* processes, each with its own independent, non-communicating lock — duplicates become possible, silently, exactly the failure mode §17.5's mandatory test exists to catch. |

**Rejected outright** — cannot satisfy the mandatory concurrency test in any realistic multi-process
deployment; named explicitly as the "claims thread-safe without explaining the actual mechanism"
failure mode this task's own instructions warn against.

### 5. External distributed lock (e.g., Redis-based)

| Criterion | Assessment |
|---|---|
| Concurrency correctness | Strong, if correctly implemented. |
| Infrastructure precedent | **None** — `docker-compose.yml` runs Postgres only; no distributed-lock service exists anywhere in this repository's infrastructure. Adopting this option means introducing an entirely new operational dependency (a Redis deployment, its own availability/failover concerns) to solve a problem Postgres's own row-locking already solves natively, inside the database transaction the application already opens for every request. |

**Rejected** — no evidenced need justifies the operational cost of new infrastructure when a
native, already-available Postgres mechanism (option 2) satisfies every requirement.

| Criterion | Native SEQUENCE | Generator-row upsert (selected) | Advisory lock | In-process lock | External distributed lock |
|---|---|---|---|---|---|
| Concurrency correctness (multi-process) | Strong | **Strong** | Strong | **Fails** | Strong |
| Correct rollback (no gap on failure) | No | **Yes** | Depends on paired mechanism | N/A | Depends |
| Scope compatibility (Matter/Org) without dynamic DDL | No | **Yes** | Yes | N/A | Yes |
| New infrastructure required | No | **No** | No | No | **Yes** |
| Repository/session consistency | Partial | **Full** | Full | Full | None |
| Auditable counter state | No | **Yes** | No | N/A | Depends |

## Detailed Concurrency Analysis

**What happens when two or more transactions attempt to create a File under the same Matter
concurrently**, mechanically:

1. Transaction T1 begins (per `ADR/0020`'s existing per-request transaction boundary), and as part
   of File creation executes `INSERT INTO file_number_sequences (matter_id, organization_id,
   next_number) VALUES (:matter_id, :org_id, 1) ON CONFLICT (matter_id) DO UPDATE SET next_number =
   file_number_sequences.next_number + 1 RETURNING next_number`.
2. Postgres's own `INSERT ... ON CONFLICT` implementation acquires an exclusive lock on the target
   row (or, if the row doesn't yet exist, on the unique index entry that would conflict) as part of
   evaluating the conflict — this is a database-level lock, not an application-level one, and
   applies identically regardless of which process, container, or connection issued the statement.
3. Transaction T2, targeting the **same** `matter_id`, issued concurrently from any process,
   **blocks** at the same statement until T1's transaction resolves (commits or rolls back) — this
   is Postgres's ordinary row-lock wait behavior, requiring no application-level coordination.
4. If T1 **commits**: its `next_number` value (say, `N`) becomes durably visible; T1 proceeds to
   `INSERT` its new File row with `file_number` derived from `N`, and commits that in the same
   transaction. T2, now unblocked, re-evaluates against the committed state and receives `N+1` —
   no duplicate, by construction, not by chance.
5. If T1 **rolls back** (for any reason — a later step in File creation fails, a constraint
   violation, an application exception caught by `ADR/0020`'s `get_db()` handler): Postgres
   reverts T1's counter change entirely. T2, now unblocked, sees the counter exactly as it stood
   before T1 ever ran, and receives the *same* value `N` T1 would have received. No number is
   burned, no gap appears, and no duplicate is possible, because T1's File row was never actually
   persisted — the specification's rule 7 concerns numbers assigned to *existing* Files, and a
   rolled-back attempt never created one.
6. **Across multiple application worker processes**: because the serialization point is a Postgres
   row lock, not any in-process Python state, this holds identically whether T1 and T2 originate
   from the same process, different processes on the same host, or different hosts entirely — the
   database is the single point of truth for lock state, which is precisely why option 4 (an
   in-process lock) fails and this option does not.
7. **Multiple Organizations, multiple Matters**: because the lock key is `matter_id`, concurrent
   File creation under *different* Matters — whether in the same Organization or different
   Organizations — never contends for the same row and never blocks each other. Throughput scales
   naturally with the number of distinct, actively-in-use Matters, not bottlenecked through one
   shared counter.
8. **Allocation gaps**: possible only if a transaction that already advanced the counter later
   fails to commit for reasons *unrelated* to the counter itself after having already read the
   `RETURNING` value in application code but before the transaction's final commit is attempted and
   that commit itself then fails — an inherent, unavoidable property of any transactional system
   (not specific to this mechanism) and not a rule-7 violation, since — again — no File was ever
   actually persisted with that number in such a case.

## Scope Decision

The specification leaves File Number scope (Organization-scoped, Matter-scoped, or globally
sequential) explicitly `ED`. **This ADR recommends Matter-scoped numbering as an architectural
inference, not a business mandate** — stated explicitly as such, per this task's own instruction
not to present an inference as a specification requirement.

Reasoning:

- §24.8's own Format bullet is the only place in the specification that gives a **concrete format
  example** for any of the three candidate scopes — "Matter-scoped (e.g. `MatterNumber-01`, `-02`)"
  — a genuine, if non-binding, textual signal toward this option specifically, not toward
  Organization-scoped or global numbering, neither of which receives an example.
- §4 rule 4 defines File as fundamentally "a work package **within** a Matter" — a File Number
  that reads as "the Nth File under this Matter" directly reflects the entity's own defining
  relationship, more legibly than an Organization-wide or global count would.
- **Concurrency/throughput**: Matter-scoping distributes lock contention across every Matter an
  Organization has open, rather than funneling all of an Organization's File creation through one
  shared counter row (Organization-scoped) or all File creation system-wide through one row
  (globally sequential) — the worst-case contention scenario. This is a genuine, evidenced
  architectural advantage, not merely a tie-breaker.
- Matter-scoping does **not** conflict with `ADR/0021`'s tenant-boundary emphasis — Matter is
  itself already Organization-scoped (transitively, per rule 43), so Matter-scoped numbering is a
  finer-grained scope nested *within* Organization scope, not an alternative to it. The
  `file_number_sequences` table still carries `organization_id` directly, per `ADR/0021`'s own
  requirement (see "Tenant-Isolation Composition").

Organization-scoped numbering is a genuinely defensible alternative this ADR does not select, not a
straw man — it would satisfy every mandatory test equally well, using the identical mechanism keyed
on `organization_id` instead of `matter_id`. It is not selected because it lacks the textual example
signal Matter-scoped numbering has, and creates coarser-grained (Organization-wide) lock contention
for no offsetting benefit. Globally sequential numbering is rejected on the same throughput grounds,
more severely, with no textual support at all.

## Format Decision

Decided only to the extent necessary for architectural coherence, per this task's own instruction
against inventing unnecessary business semantics:

- The File Number's numeric component is a per-Matter sequential integer, generated by the
  mechanism above.
- Its human-readable, stored form is **not fully decided here** — whether it is stored as the bare
  integer, a zero-padded suffix, or a string that embeds the owning Matter's own `matter_number` as
  a prefix (the shape §24.8's own example suggests) is a **presentation/formatting detail deferred
  to whichever future task resolves File's broader field architecture (#8)** — this ADR decides the
  numbering *mechanism and scope*, not the exact display format, string length, padding width, or
  separator character. No office code, district code, year prefix, department code, or category
  prefix is introduced — none is evidenced by the specification or repository, and inventing one
  would violate this task's own explicit instruction.
- What this ADR **does** require, as a necessary consequence of rule 7: whatever the final stored
  form, it must be derived deterministically and exclusively from the counter value this mechanism
  produces, and must carry a database uniqueness guarantee scoped at least as tightly as the
  numbering scope itself (i.e., unique per Matter, at minimum) — the specific constraint's exact
  shape (a composite `UNIQUE(matter_id, file_number)` if the stored value is the bare per-Matter
  suffix, or a plain global `UNIQUE` if the stored value embeds the already-globally-unique
  `matter_number`) is implementation guidance for #8, not decided here.

## Consequences

- `file_number_sequences` can be created with a shape directly informed by this decision once a
  future implementation task (necessarily coupled to #8's own File-entity work) is authorized —
  this ADR itself creates no schema.
- Required ADR #8, once authorized, inherits a fixed, correct numbering mechanism and scope to
  build the rest of File's field architecture against, without needing to revisit concurrency
  design.
- File creation's per-request transaction (`ADR/0020`) now has a concrete, correct pattern for
  atomically consuming a File Number as part of that same transaction — no new transaction
  management is introduced.

## Invariants

Must hold permanently, by construction of this mechanism:

- A File Number is assigned exactly once, atomically with the File row's own persisted creation —
  never pre-allocated speculatively, never assigned outside the creation transaction (rule 6).
- Once a File is successfully persisted, its File Number is never reissued to any other File,
  including after the File is later soft-deleted/archived (rule 7; the counter never decrements or
  "returns" a consumed value regardless of the File's later lifecycle state).
- Concurrent File creation under the same Matter can never produce two Files with the same number
  (§17.5's mandatory test) — guaranteed by Postgres row-level lock serialization on
  `file_number_sequences`, not by application-level coordination.
- A File-creation attempt that fails and rolls back never permanently consumes a number (a stronger
  guarantee than rule 7 strictly requires, and a deliberate advantage of this mechanism over a
  native `SEQUENCE`).
- `file_number_sequences.organization_id` always matches its `matter_id`'s own owning Organization —
  the concrete tenant-isolation invariant this ADR's structure creates, verified independently at
  the data-access layer per `ADR/0021`.

## Tenant-Isolation Composition (ADR-0021)

`ADR/0021` is not modified, reopened, or reinterpreted. `file_number_sequences` is tenant-scoped and
requires a mandatory `organization_id` column under `ADR/0021`'s already-decided rule. Mirroring
`ADR/0024`'s and `ADR/0026`'s identical discipline for their own generator/structure tables:
**`file_number_sequences` must carry its own `organization_id` directly, not merely inherit tenant
scope by joining to `matters`** — so the RLS backstop applies to the counter row itself,
independent of whether any particular query's join to `matters` is correctly present.

## Authorization Composition (ADR-0022)

`ADR/0022` is not modified, reopened, or reinterpreted. File-number generation is not an
independently user-facing operation — it occurs only as an internal step of File creation, governed
by whatever `files:*`-style permission `ADR/0022`'s model applies to File creation once #8 defines
that resource. This ADR does not introduce, and does not need, any new permission code for
`file_number_sequences` itself, consistent with `ADR/0023`'s/`ADR/0024`'s/`ADR/0026`'s identical
reasoning for their own internal, not-independently-accessed sub-tables.

## Implementation Guidance / Constraints

Named as guidance for whichever future implementation task carries this decision out — not
performed by this ADR:

- Use `INSERT ... ON CONFLICT (matter_id) DO UPDATE SET next_number = next_number + 1 RETURNING
  next_number` (or the SQLAlchemy Core equivalent) as a single atomic statement — do not implement
  this as a separate `SELECT ... FOR UPDATE` followed by a conditional `INSERT`/`UPDATE`, which
  would reintroduce a race between the existence-check and the write.
- Execute the counter upsert and the new File row's `INSERT` within the same transaction/session
  (the existing `ADR/0020` per-request boundary) — never as two independently-committed operations.
- Do not seed `file_number_sequences` rows proactively at Matter-creation time; rely on the upsert's
  own `ON CONFLICT` branch to create the row lazily on a Matter's first File — this avoids coupling
  File-numbering implementation to Matter-creation logic, which belongs to #8's own scope.

## Unresolved / Deferred Questions

- File's own broader field architecture, Matter-vs-File lifecycle, Matter-deletion cascade
  behavior, and Workflow/Task/GovernmentProcess attachment granularity — all Required ADR #8's
  territory, not touched here.
- The exact stored/displayed format of `file_number` (padding, separator, whether it embeds
  `matter_number` as a prefix) — deferred to #8, per "Format Decision" above.
- The exact `UNIQUE` constraint shape on the future `files.file_number` column — deferred to #8, per
  "Format Decision" above; this ADR establishes only that one must exist, scoped at least per
  Matter.
- Document/File relationship (#10), migration strategy for existing `matter_number`/`invoice_number`
  patterns (#20) — untouched.

## Dependencies

- **#1, #2, #3, #4, #5, #6, #7, #18, #19** — already resolved by `ADR/0021`–`ADR/0026`. Not
  reopened.
- **#9** — **resolved by this ADR.**
- **#8, #10–#17, #20** — remain fully unresolved; #8 specifically inherits this ADR's fixed
  numbering mechanism/scope as an input, without needing to revisit it.

## Explicit Out-of-Scope Boundaries

This ADR does not decide, and nothing in it should be read as deciding: File's own entity/field
architecture beyond the Number itself; Matter-vs-File lifecycle semantics; Matter-deletion cascade
behavior; Workflow/Task/GovernmentProcess attachment granularity; Document/File relationship
mechanics; general migration/backfill strategy for existing `matter_number`-style columns; any
Stage 4 business feature; any decision already frozen by `ADR/0021`–`ADR/0026`.

## Implementation Boundary

This ADR is an architecture decision, not implementation. No database table, migration, model,
service, repository, route, frontend, or test is created or modified by this document.
`file_number_sequences` and the mechanism described above describe what a future,
separately-authorized implementation task (coupled to #8) must build — none of it exists in code as
a result of this ADR.

## References

- `docs/Legal_DMS — Domain Model & Functional Specification.md` §4 rules 6–7, §17.5, §21 item 9,
  §24.8 ("File" and "File Numbering"), §25 invariant #8, §26 item 6.
- `ADR/0020-session-commit-rollback-policy.md`
- `ADR/0021-organization-tenant-boundary-enforcement.md`
- `ADR/0022-authorization-architecture.md`
- `backend/src/app/infrastructure/persistence/models/matter.py`
- `backend/src/app/infrastructure/persistence/models/financial.py`
- `backend/src/app/infrastructure/persistence/models/mixins.py`
- `backend/src/app/infrastructure/database/session.py`
- `docker-compose.yml`
