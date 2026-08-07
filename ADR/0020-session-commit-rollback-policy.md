# ADR-0020: Session Commit/Rollback Policy

**Status:** Accepted
**Date:** 2026-08-06

## Problem

`get_db()` (`backend/src/app/infrastructure/database/session.py`), the FastAPI dependency every
route/repository uses to obtain a request-scoped `AsyncSession`, never called `session.commit()`.
`SqlAlchemyRepository.add()`/`update()`/`delete()` only call `session.flush()` — visible within
the same transaction, but never persisted. The session closed at the end of every request without
committing, so a write **appeared** to succeed (flush makes it visible to any read in the same
session) and then **silently vanished** once the session closed. This was first identified as
finding F1 in the Stage 2.5 architecture-hardening review (Critical/P0) but left unfixed while
that backlog awaited approval, since nothing in Stages 0–2 wrote through it. Stage 3
(Authentication & Authorization) is the first stage whose entire purpose is writes — creating
users, hashing and storing passwords, recording `last_login_at`, assigning roles, issuing and
revoking refresh tokens — so this stopped being deferrable hardening and became a hard
prerequisite: every one of those writes would have silently failed without this fix landing
first.

## Options Considered

1. **Commit inside each repository method** (`add()`/`update()`/`delete()` call `commit()` instead
   of `flush()`). Rejected: collapses every write into its own transaction, making it impossible
   for a service to group multiple writes (e.g. "create the user, then assign the default role")
   into one atomic unit — a single failed write partway through would leave the earlier ones
   committed regardless.
2. **Commit inside `get_db()`** — the request-scoped session dependency commits once, after the
   route handler returns successfully, rolling back if it raised. Repositories stay `flush()`-only,
   so a route/service can perform several repository calls against the same session and have them
   all commit — or all roll back — together as one transaction. This is the design already sketched
   (but never implemented) in the original F1 finding and `docs/Stage3_Backend_Handoff.md`.
3. **A request-scoped `UnitOfWork`** wrapping the session with explicit `begin()`/`commit()`/
   `rollback()`, mirroring the post-Stage-2 `UnitOfWork` port (`ADR-0012`). Rejected for this
   specific fix: that port already exists but is deliberately unbacked by a real resource
   (`InMemoryUnitOfWork` only) and not wired to `CommandBus`/`QueryBus`/anything HTTP-facing —
   building a `SqlAlchemyUnitOfWork` and wiring it through `DBSessionDep` would be solving a larger,
   still-open design question (how does a handler reach the active session — `ADR-0012`'s own
   Trade-offs section names this as explicitly unsolved) as a side effect of fixing a one-line bug.
   `get_db()` already **is** the request-scoped transaction boundary FastAPI's own dependency
   system provides; option 2 uses it directly rather than layering a second transaction-boundary
   abstraction on top before anything needs one.

## Decision

Option 2. `get_db()` now wraps its `yield` in `try`/`except`:

```python
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

Every session obtained through `get_db()` (directly, or via `presentation/api/deps.py`'s
`DBSessionDep`) now **commits on success, rolls back on exception** — a deliberate, explicit
policy, not an incidental patch. Repositories are unchanged: `SqlAlchemyRepository`'s `flush()`-only
methods remain correct exactly because `get_db()` is what turns a flushed change into a persisted
one.

## Reasoning

- Matches the transaction granularity FastAPI's dependency system already gives for free: one
  request, one session, one commit/rollback decision — no new abstraction needed to get
  multi-repository-call atomicity within a request.
- Repositories staying `flush()`-only keeps them composable: a future `AuthService.register_user()`
  can create a `User` and a `UserRole` row through two repository calls in the same request and have
  both commit together, or both roll back together, without either repository method needing to
  know whether it's the only write in the request.
- `except Exception` (not `except BaseException`) is deliberate and consistent with this project's
  established default elsewhere — c.f. `ADR-0012`'s `TransactionPipelineBehavior`, which widened its
  own catch to `BaseException` specifically because `asyncio.CancelledError` bypassing rollback was
  a proven gap (QA finding Q1, `T20`). The same reasoning applies here in principle: a cancelled
  request should still roll back. **Flagged as a known follow-up, not applied silently in this
  ADR** — see Trade-offs.

## Trade-offs

- **`except Exception`, not `except BaseException`.** `asyncio.CancelledError` inherits from
  `BaseException` since Python 3.8 and would bypass this `except` clause exactly as
  `TransactionPipelineBehavior`'s did before `T20`/`ADR-0012` fixed it. Not changed here to keep
  this fix to the exact, minimal, already-reviewed shape specified in
  `docs/Stage3_Backend_Handoff.md` and `IMPLEMENTATION_QUEUE.md`'s T42 — widening it is a one-line
  follow-up worth doing deliberately, not bundled into the hard-prerequisite fix under time
  pressure. See Future Impact.
- **No request-scoped `UnitOfWork` integration.** The existing `UnitOfWork` port (`ADR-0012`) and
  `DBSessionDep` remain two separate, unconnected transaction-adjacent concepts — a future
  `CommandBus`-dispatched write handler using `UnitOfWork` and an HTTP route using `DBSessionDep`
  would have two different transaction-boundary mechanisms. Not resolved here; Stage 3's routes
  (Phase 2–3) use `DBSessionDep` directly, consistent with every other route in this codebase
  today, not through `CommandBus`.
- **Read-only requests still call `commit()`.** A request that only reads (no writes) still commits
  an empty transaction on exit. Harmless — `commit()` on a session with no pending changes is a
  no-op at the database level — but worth naming so a future reader doesn't mistake it for an
  attempt to optimize read paths.

## Future Impact

- **Widening to `except BaseException`** (matching `TransactionPipelineBehavior`'s `T20` fix) is a
  small, well-understood follow-up — flagged here rather than silently deferred, so it isn't
  rediscovered as a "new" finding later. Revisit once Stage 3's routes exist and cancellation under
  real load is worth testing against.
- Every Stage 3 write (Phase 1's `AuthService`, Phase 3's routes, Phase 4's bootstrap CLI) depends
  on this policy — this ADR is the reason those writes can be trusted to persist, and the
  regression tests in `tests/integration/test_get_db_transaction_policy.py` are what prove it
  (commit visible from an independent second session, rollback on exception, and the pre-existing
  same-session flush-visibility behavior unchanged).
- If a future feature needs multiple independent transactions within a single HTTP request (rare,
  but e.g. "log an audit entry even if the main write rolls back"), that's a deliberate exception to
  this policy needing its own decision — not something to special-case into `get_db()` itself.
