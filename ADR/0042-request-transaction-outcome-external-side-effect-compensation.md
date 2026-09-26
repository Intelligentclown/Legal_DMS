# ADR-0042: Request Transaction Outcome and External-Side-Effect Compensation

**Status:** Proposed
**Date:** 2026-09-26
**Related task:** T143 — Request Transaction Outcome and External-Side-Effect Compensation Architecture.

**Resolves:** None.

**Does not resolve:** Required ADR #12 (Workflow vs Government Status), #15 (Core vs configurable vocabulary), #16 (UUID vs human-readable identifiers), #17 (Soft deletion/history), or #20 (Migration strategy from the current schema). Required ADR #11 remains resolved by ADR-0041. This ADR does not authorize implementation, schema changes, T142 resumption, committed-content deletion, retention policy, or T144+.

**Composes with:** ADR-0020 session commit/rollback policy, ADR-0021 Organization tenant isolation, ADR-0022 authorization, ADR-0041 document versioning/storage transaction architecture, and T141's persisted DocumentVersion idempotency foundation.

## Problem

ADR-0020 deliberately makes FastAPI's request-scoped `get_db()` dependency the sole owner of the SQLAlchemy request transaction: repositories flush, the route/service returns, then the dependency commits on success or rolls back on an exception. ADR-0041 deliberately composes with that policy while requiring external document bytes to be saved before database metadata is committed.

T142 correctly stopped before tracked implementation because those two valid decisions expose a missing outcome boundary. Application orchestration can save an external blob and flush database work, but final `session.commit()` occurs only after route/service execution returns to `get_db()`. If that commit fails, the code that knows the just-created external resource is no longer executing. Blind deletion is unsafe because a commit-call exception does not prove PostgreSQL did not commit; connection loss or timeout can make the server outcome unknowable to the client.

The repository has an abstract `UnitOfWork`, `TransactionPipelineBehavior`, and an `InMemoryUnitOfWork`, but they are intentionally not backed by the active HTTP AsyncSession. ADR-0020 considered and rejected introducing a request-scoped SQLAlchemy UnitOfWork merely to establish its original transaction policy. No existing request callback registry, SQLAlchemy transaction-event convention, or external-side-effect coordinator exists.

The architecture therefore needs a narrow, generic extension point without changing ADR-0020's fundamental owner.

## Decision drivers

The design must simultaneously preserve:

1. one HTTP request → one request-scoped AsyncSession → one database transaction owned by `get_db()`;
2. flush-only repositories and services with no independent commit authority;
3. best-effort destructive compensation when database non-commit is definitive;
4. no destructive compensation when final commit outcome is uncertain;
5. durable idempotency/reconciliation at the application layer for uncertain outcomes;
6. domain-neutral transaction infrastructure;
7. request/concurrency isolation and deterministic cleanup;
8. ADR-0021 FORCE RLS, trusted Organization GUC and restricted runtime role;
9. no migration or persistent transaction-state requirement.

## Options considered

### 1. Request-scoped transaction outcome / compensation context — selected

Create one generic context for the lifetime of a request database session. Trusted application orchestration may register compensation only after an external side effect succeeds. The request transaction owner classifies the terminal database outcome and tells the context to discard, compensate, or preserve-for-reconciliation accordingly.

This preserves ADR-0020 ownership while adding the extension point ADR-0041 discovered it needed.

### 2. New request-scoped transaction coordinator owning commit/rollback

Viable in a different architecture, but rejected here. A second owner or wrapper with its own transaction authority would reopen the UnitOfWork question ADR-0020 deliberately left outside HTTP. T143 does not need that broader change.

### 3. Revive the existing UnitOfWork for HTTP

Rejected. The current port is resource-agnostic and the concrete implementation is in-memory. It has no active AsyncSession, outcome model, compensation contract, or HTTP request wiring. Retrofitting it would be a broader transaction architecture change than necessary.

### 4. Explicit commit in T142 service or route

Rejected. It violates ADR-0020's sole-owner invariant and makes one feature an exceptional transaction authority. Repositories/services remain flush-only.

### 5. Put FileStorage compensation directly in get_db()

Rejected. Database infrastructure must not know DocumentVersion, FileStorage, storage keys, permission codes, or any other domain/provider concept. Only a generic trusted compensation action crosses the boundary.

### 6. SQLAlchemy session events

Rejected as the primary mechanism. The repository has no such convention; synchronous session-event callbacks are a poor boundary for asynchronous external cleanup; and events do not solve whether a DBAPI/connection failure during COMMIT means definitive non-commit or unknown server outcome.

### 7. Reconciliation only for every commit exception

Rejected as the whole policy. Conservative reconciliation is correct for unclassifiable commit failures, but ADR-0041 also requires best-effort cleanup for failures known not to have committed. Known pre-commit/rollback cases should not intentionally leave avoidable orphan artifacts.

### 8. Database-first or persisted pending version state

Rejected by ADR-0041. Committed metadata must never advertise content whose durable bytes are absent, and no pending DocumentVersion lifecycle is authorized.

### 9. Outbox/saga/persistent compensation state

Not required for the present contract. It would add schema/migration and operational machinery without evidence that in-request best-effort cleanup plus durable domain idempotency is insufficient. If future evidence proves persistence necessary, implementation must stop and seek separate authority.

## Decision

### 1. Preserve ADR-0020 transaction ownership

ADR-0020 remains Accepted and its fundamental policy is unchanged:

```text
request
  → one request-scoped AsyncSession
  → repositories/services flush only
  → get_db() owns the one final commit/rollback decision
```

T143 adds outcome/compensation composition; it does not transfer commit authority.

### 2. Explicit terminal outcome model

The request transaction boundary exposes exactly three semantic terminal outcomes to registered external-side-effect coordination.

#### CONFIRMED_COMMIT

The request transaction owner received successful completion of `session.commit()`.

Consequences:
- database result is authoritative;
- destructive compensation MUST NOT run;
- all registered compensation is discarded;
- normal committed-result semantics proceed.

#### DEFINITIVE_NON_COMMIT

The request transaction owner has sufficient evidence that the transaction did not commit.

This includes a handler/application/flush failure before COMMIT followed by successful rollback, explicit rollback, or another case where non-commit is independently established rather than inferred from a generic commit exception.

Consequences:
- rollback completes where applicable before external compensation;
- registered compensation becomes eligible;
- compensation executes best-effort;
- compensation failure cannot change the database outcome;
- the external artifact remains non-authoritative if cleanup fails.

#### COMMIT_OUTCOME_UNCERTAIN

The application cannot establish whether PostgreSQL committed.

Examples include connection loss or timeout while COMMIT may be in flight, loss of acknowledgement after the server may have committed, session/connection invalidation that destroys evidence, or any generic `session.commit()` exception not covered by an evidence-backed definitive classifier.

Consequences:
- destructive compensation MUST NOT execute;
- the business operation MUST NOT be blindly repeated;
- registered compensation is discarded from the in-memory request context without executing;
- application-specific durable idempotency/reconciliation decides what committed;
- a local `rollback()` attempt after uncertainty does not reclassify the outcome as definitive non-commit.

### 3. Conservative commit-exception rule

The initial implementation MUST classify an exception raised by the `session.commit()` call as `COMMIT_OUTCOME_UNCERTAIN` unless repository code has an explicit, tested, driver/database-backed proof that the particular failure means COMMIT was not accepted and the transaction could not have committed.

Exception class names alone are not sufficient evidence. SQLAlchemy/asyncpg exception taxonomy may describe transport or transaction failure without proving the remote commit result.

This deliberately favors orphan retention plus reconciliation over deleting bytes that may belong to a committed row.

A later narrower classifier may be added only with tests proving its PostgreSQL/asyncpg semantics; it must fail closed to uncertain.

### 4. Pre-commit failures

Validation failure before an external side effect creates no compensation.

External-side-effect failure creates no registration because registration occurs only after success.

After external success:
- application failure before DB flush;
- integrity/uniqueness failure during flush;
- statement-time serialization/deadlock abort;
- handler exception;
- cancellation before COMMIT;

are eligible for `DEFINITIVE_NON_COMMIT` only after the request owner successfully establishes rollback/non-commit. If rollback itself fails or connection state prevents establishing non-commit, classification becomes `COMMIT_OUTCOME_UNCERTAIN`.

A failure known to occur before COMMIT is sent may be definitive only when the transaction owner can also establish that the transaction did not commit. Merely observing a later local cleanup call is not proof.

### 5. Request-scoped TransactionOutcomeContext

Implementation should introduce a small domain-neutral request-scoped component (name illustrative; semantics normative) with responsibilities equivalent to:

- register one or more trusted asynchronous compensation actions;
- mark/handle one terminal outcome exactly once;
- execute eligible compensation in reverse registration order;
- discard actions on confirmed commit;
- suppress destructive actions on uncertain outcome;
- prevent registration after terminal finalization;
- guarantee terminal cleanup of in-memory references;
- expose no commit/rollback method.

It is not a UnitOfWork and does not own SQLAlchemy transactions.

### 6. Ownership and FastAPI wiring

The canonical request context is created by the database-session dependency because its lifetime is exactly the active request AsyncSession transaction.

The preferred implementation is:

1. `get_db()` creates a fresh `TransactionOutcomeContext` immediately after creating the AsyncSession;
2. the context is associated with that active session using server-owned session-local state (for example SQLAlchemy session `info` under a private repository key);
3. `get_db()` yields the same AsyncSession as today, preserving `DBSessionDep` and existing route signatures;
4. a companion FastAPI dependency accepts `DBSessionDep` and retrieves the already-created context from that exact session;
5. T142 or another trusted orchestrator requests that companion dependency and registers compensation after its external side effect succeeds;
6. `get_db()` remains the only component that calls final commit/rollback and finalizes the context;
7. context association is removed/cleared before request/session teardown completes.

This avoids a global mutable registry, ContextVar inheritance surprises, a second request owner, and dependence on FastAPI sibling-dependency teardown ordering. The active session is already the unique request transaction identity.

If implementation discovers SQLAlchemy session-local state cannot safely provide this identity without changing session semantics, it MUST STOP rather than substitute a global/contextvar registry silently.

### 7. Domain-neutral compensation representation

The transaction layer MUST NOT accept caller-provided executable code or resource identifiers.

Only trusted server application code may register a compensation action. The minimum contract is an async no-argument callable/protocol object constructed from already-validated server-side state.

For T142 the trusted application layer may close over the FileStorage instance and deterministic server-created storage key. The transaction context knows only “run this registered compensation”; it does not know FileStorage, DocumentVersion, Organization, Matter, FileStorageRecord, RBAC, or storage-provider semantics.

A typed protocol/dataclass wrapper is preferred over unstructured dictionaries because it is testable and prevents the coordinator from interpreting domain payloads. A closure is acceptable behind that trusted typed interface.

Compensation MUST NOT use the failed request AsyncSession or attempt to repair database state.

### 8. Registration lifecycle and ordering

Registration occurs only after the external side effect successfully completes.

For multiple registered actions, compensation executes in strict LIFO/reverse-registration order, matching rollback of effects acquired in forward order.

All eligible actions are attempted even if an earlier compensation fails. Each failure is recorded; one cleanup failure MUST NOT prevent attempts for remaining registered actions.

On `CONFIRMED_COMMIT`, actions are discarded without execution.

On `COMMIT_OUTCOME_UNCERTAIN`, actions are discarded from request memory without destructive execution. Durable application reconciliation, not the callback list, carries uncertainty beyond the request.

After any terminal outcome, registration/finalization reuse is an error and all in-memory references are cleared.

### 9. Compensation failure semantics

When the database is definitively non-committed and compensation fails:

- the original database/request failure remains primary;
- no database ownership is fabricated;
- the external artifact remains an orphan/non-authoritative artifact;
- compensation failure is logged with exception information and safe technical correlation;
- cleanup failure does not become committed-history deletion;
- automatic destructive retries are not invented by this ADR;
- later bounded orphan reconciliation/cleanup may be separately implemented under proper authority.

### 10. Cancellation semantics

Cancellation is a `BaseException` concern and cannot be allowed to bypass safe transaction finalization.

- Before external success: no compensation exists.
- After external success but before COMMIT: cancellation must cause rollback/non-commit establishment; if definitive, compensation is eligible.
- During DB work: same rule; definitive rollback permits compensation, inability to establish outcome becomes uncertain.
- After handler return and during COMMIT: cancellation is `COMMIT_OUTCOME_UNCERTAIN` unless non-commit is independently established.
- During rollback or outcome establishment: if cancellation prevents authoritative classification, treat outcome as uncertain.
- During compensation: once definitive non-commit is established, cleanup should be given a bounded opportunity to complete despite request cancellation. Implementation may use a narrowly shielded finalization section, but MUST NOT shield the whole request/DB operation indefinitely. Cancellation is re-propagated after bounded cleanup.
- After uncertain commit: never compensate merely because cancellation occurred.

Implementation must use `BaseException`-aware finalization where needed; ADR-0020's historical `except Exception` cancellation limitation cannot be allowed to make registered compensation silently disappear. If safely fixing this requires changing ADR-0020's fundamental transaction owner rather than bounded finalization, STOP.

### 11. FastAPI response/error semantics

Transaction finalization is part of request success. A route/service return is provisional until dependency-owned commit completes.

- confirmed commit permits normal response completion;
- definitive failure propagates the original failure after rollback/compensation;
- uncertain commit must surface as a server-side transaction-outcome-uncertain failure, not as claimed business success.

The transaction layer may raise a domain-neutral infrastructure exception indicating “commit outcome uncertain.” Error translation must not claim rollback or invite an automatic blind retry. T142's application/API layer may use the original idempotency key to reconcile on a later request.

Implementation must test the actual installed FastAPI yield-dependency lifecycle so a teardown/finalization exception is observable and not emitted after a successful response has irreversibly been sent. If the framework lifecycle cannot provide that property with the current dependency scope, STOP for a new transaction-boundary decision rather than moving commit into T142.

### 12. T141 idempotency handoff

The transaction layer does not query DocumentVersion idempotency.

T142 owns domain reconciliation through T141's existing unique scope:

```text
(organization_id, document_id, idempotency_key)
```

with payload fingerprint and resulting DocumentVersion persisted in the same transaction.

After uncertainty:
- same key + same fingerprint + committed result → return the existing committed version;
- same key + different fingerprint → conflict;
- no committed result found → a later retry may proceed only after reconciliation establishes absence under the normal idempotent creation rules.

No idempotency row may claim success before the DB transaction commits. No pending DocumentVersion state is introduced. T141 persistence is sufficient; T143 requires no schema change.

### 13. Organization/RLS/security

This architecture changes no tenant authority.

ADR-0021 remains authoritative:
- FORCE RLS/default-deny remains;
- `legal_dms_app` remains restricted/non-owning/non-superuser/NOBYPASSRLS;
- trusted Organization GUC remains request transaction context;
- existing RBAC remains;
- no privileged DB path is introduced for compensation.

External compensation uses only server-created, already-validated resource identity. User input must never be registered as an arbitrary deletion target.

Because each context is attached only to its active request session and never globally shared, request A cannot execute request B's compensation. T142 must still construct its technical storage key from authenticated Organization and server-generated identity under ADR-0041.

### 14. SQLAlchemy integration boundary

The design relies only on ordinary AsyncSession behavior:
- flush exposes statement/constraint failures before final commit;
- `get_db()` remains the commit/rollback caller;
- rollback is attempted where applicable;
- commit success is confirmed only by normal return from `await session.commit()`;
- connection invalidation/DBAPI failure can destroy certainty.

No SQLAlchemy event hook is required.

A successful `rollback()` after a handler/flush failure helps establish definitive non-commit because COMMIT was never entered. A rollback attempted after an uncertain COMMIT exception does not retroactively prove non-commit.

### 15. Observability

Use the repository's structured logging convention.

Transaction finalization should emit safe structured fields sufficient to diagnose:
- terminal outcome;
- request ID when available;
- compensation count;
- compensation attempted/succeeded/failed counts;
- whether uncertainty suppressed compensation;
- exception class/category without secrets;
- safe technical operation correlation supplied by trusted code when appropriate.

Never log document bytes, credentials, arbitrary authorization headers, or user-controlled storage deletion targets.

Compensation failures must be logged individually while preserving the original transaction exception as primary.

### 16. Required future test contract

Implementation evidence must include:

1. confirmed commit → compensation never executes;
2. known pre-commit failure after external success → rollback then compensation;
3. definitive rollback → compensation eligible;
4. compensation succeeds;
5. compensation failure does not hide original failure;
6. all LIFO compensations are attempted despite one callback failure;
7. uncertain commit → no destructive compensation;
8. uncertain commit → infrastructure exposes reconciliation-required outcome;
9. T141 durable idempotency reconciliation after uncertainty;
10. same key/same fingerprint/committed result returns existing result;
11. same key/different fingerprint conflicts;
12. sequential requests do not share compensation state;
13. concurrent requests do not share compensation state;
14. cleanup after confirmed commit;
15. cleanup after definitive failure;
16. cleanup after uncertainty;
17. cancellation before external effect;
18. cancellation after external effect before commit;
19. cancellation during commit/finalization;
20. cancellation during compensation;
21. rollback failure degrades to uncertain;
22. connection invalidation/timeout around commit degrades to uncertain;
23. existing `test_get_db_transaction_policy.py` semantics remain valid;
24. ordinary routes still commit exactly once at request boundary;
25. repositories remain flush-only;
26. services have no independent commit authority;
27. FORCE RLS/default-deny unchanged;
28. Organization GUC behavior unchanged;
29. no cross-request/cross-Organization external deletion;
30. Alembic/provenance remains unchanged.

Real PostgreSQL is mandatory for request commit/rollback behavior, transaction-abort cases, RLS/GUC preservation, idempotency durability and any claimed definitive database outcome classification. Unit/fault-injection tests are appropriate for registry lifecycle, LIFO ordering, callback failure, synthetic connection-loss/uncertainty paths and cancellation control flow. Framework integration tests must exercise FastAPI's actual yield-dependency teardown/error behavior.

### 17. Implementation decomposition

After T143 completes its full §3.1 architecture + independent QA + architecture merge + governance closeout lifecycle, the smallest dependency-safe recommendation is **Path 1**:

> implement the generic transaction-outcome/compensation mechanism as the first bounded infrastructure portion of resumed T142, then use it for T142's blob-first DocumentVersion orchestration under T142's already-authorized no-migration scope.

Reasoning:
- the mechanism is small, generic infrastructure directly required by T142;
- it does not need persistence, migration, RBAC/RLS redesign or a new transaction owner;
- separating another implementation task would add lifecycle overhead without an independent deployable dependency;
- T142 remains the first consumer and its existing authorization already requires ADR-0020-preserving compensation/uncertainty handling.

This is a recommendation only. T142 remains blocked until T143 fully closes and Control Tower separately authorizes resumption under repository governance.

If implementation discovers the generic mechanism cannot be delivered without a migration, persistent saga/outbox, or changing the transaction owner, T142 must STOP again and Control Tower must sequence a separately authorized prerequisite.

## Failure classification matrix

| Situation | Outcome / action |
|---|---|
| Validation fails before external effect | no registration; ordinary failure |
| External effect fails | no registration; ordinary failure |
| Application fails after external success, before COMMIT | rollback; definitive if rollback/non-commit established; then compensate |
| Integrity/uniqueness failure during flush | rollback; definitive if established; then compensate |
| Statement-time serialization/deadlock abort before COMMIT | rollback; definitive if established; then compensate |
| Explicit rollback/non-commit established | DEFINITIVE_NON_COMMIT; compensate |
| Handler exception/cancellation before COMMIT | rollback; definitive if established; compensate |
| Failure proven before COMMIT can be sent | definitive only with established non-commit; compensate |
| COMMIT explicitly rejected with independently proven abort/non-commit | DEFINITIVE_NON_COMMIT; compensate |
| Connection loss before COMMIT with established non-commit | DEFINITIVE_NON_COMMIT; compensate |
| Connection loss while COMMIT executes | COMMIT_OUTCOME_UNCERTAIN; do not compensate |
| Connection loss after server may have committed | COMMIT_OUTCOME_UNCERTAIN; do not compensate |
| Timeout around COMMIT | COMMIT_OUTCOME_UNCERTAIN unless non-commit independently proven |
| Generic `session.commit()` exception | COMMIT_OUTCOME_UNCERTAIN by default |
| Rollback failure / unusable connection prevents proof | COMMIT_OUTCOME_UNCERTAIN |
| Process cancellation/shutdown during COMMIT | COMMIT_OUTCOME_UNCERTAIN unless non-commit independently proven |
| Compensation fails after definitive non-commit | DB outcome remains definitive; orphan observable; continue remaining cleanup |

## Consequences

### Positive

- T142 can later observe the transaction result without taking commit ownership.
- Known failures clean up best-effort while uncertain commits never trigger blind deletion.
- Existing T141 idempotency is reused instead of adding transaction-state persistence.
- The mechanism is reusable for future request-scoped external side effects without embedding storage/domain knowledge.
- Existing DBSessionDep/repository patterns remain intact.

### Costs

- `get_db()` gains bounded finalization responsibility beyond raw commit/rollback.
- Cancellation and dependency-teardown behavior require explicit integration tests.
- Conservative classification can leave orphan external artifacts after commit uncertainty even when the DB ultimately rolled back; this is intentionally safer than deleting content that may belong to a committed record.
- Future operational orphan cleanup remains separate work if needed.

## STOP conditions

Implementation must STOP rather than expand this decision if safe delivery requires:

- changing ADR-0020's fundamental request transaction owner;
- repository/service-level independent commits;
- a migration or new persistent transaction/outbox/saga/compensation state;
- a pending/staged DocumentVersion lifecycle;
- weakening FORCE RLS, Organization GUC or runtime-role restrictions;
- RBAC redesign;
- committed DocumentVersion deletion/retention semantics or Required ADR #17;
- Required ADR #20 or another unresolved Required ADR;
- provider-specific storage redesign;
- global mutable compensation state;
- caller-controlled arbitrary destructive targets;
- treating an unclassified commit exception as definitive rollback;
- framework behavior that can send an irreversible success response before transaction-finalization failure can be surfaced;
- another task materially changing the transaction or migration frontier.

## Future impact

ADR-0020 remains Accepted and authoritative for transaction ownership. ADR-0041 remains Proposed and authoritative for DocumentVersion blob-first/database-second orchestration. This ADR supplies the missing generic outcome bridge between them.

No migration is required by this architecture. Alembic and operational-fresh supported revision remain `cdcfd7df5fde`.

T142 remains Authorized, blocked and not Done until T143 completes its entire §3.1 lifecycle and Control Tower separately decides resumption.

T143 resolves no Required ADR and changes no existing ADR status.
