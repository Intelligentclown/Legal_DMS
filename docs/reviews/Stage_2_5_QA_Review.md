# Stage 2.5 QA Review

**Scope:** Command Bus, Query Bus, Transaction Pipeline, Caching Abstraction, Module Manifest
Loader, Architecture Health Check, Performance Metrics Service — the seven post-Stage-2 framework
additions requested directly by the project owner (see [ADR/0010](../../ADR/0010-command-bus.md)
through [ADR/0016](../../ADR/0016-performance-metrics-service.md)). These are distinct from the
formal `IMPLEMENTATION_QUEUE.md` Stage 2.5 "Architecture Hardening" backlog, which remains
unstarted except for T15 (Architecture Health Check, covered here).

**Reviewed:**
`backend/src/app/application/interfaces/{command_bus,query_bus,unit_of_work,cache,metrics}.py`,
`backend/src/app/infrastructure/{commands,queries,transactions,cache,metrics}/`,
`backend/src/app/infrastructure/modules/manifest.py`,
`backend/src/app/infrastructure/di/{container,health_check}.py`, all 8 corresponding test files,
and ADR-0010–0016.

**Evaluated against:** Architecture, Performance, SOLID, Maintainability, Security, Scalability,
Thread Safety, Error Handling, Code Duplication.

**Date:** 2026-08-06

**Resolution status (2026-08-06):** Findings #1 and the tags-redaction note under Security /
Suggested improvement #3 are **RESOLVED** — see `IMPLEMENTATION_QUEUE.md` T20/T21 and the
"Resolution" notes inline below. Verified: fix matches the finding, all targeted tests plus the
full unit suite pass (175/175; the 107 integration tests could not be re-run in this environment —
no local Postgres/Docker available — but neither change touches persistence), ruff/black clean
project-wide, no regressions in the three pre-existing pipeline tests. All other findings (#2–#7)
remain open/deferred as originally scoped.

---

## Summary judgment

Architecturally consistent, well-documented, conservatively scoped. Each piece mirrors an existing
Stage 1 pattern (`EventBus`'s shape for `CommandBus`/`QueryBus`, `LoggingNotifier`'s shape for
`MetricsService`) rather than inventing new conventions. Test coverage is thorough for stated
behavior. The two things worth real attention: a **silent transactional-integrity gap under task
cancellation** in `TransactionPipelineBehavior`, and the fact that **nothing currently uses the
transaction pipeline**, so its correctness is unverified against a real resource. Everything else
is lower-severity or forward-looking.

Most "why isn't X wired up" questions that would normally surface as findings in a review like this
were already pre-empted, explicitly, in each item's own ADR — the ADRs name their trade-offs before
a reviewer can find them independently. That materially changed the shape of this review: it
focuses on what the ADRs *don't* already cover, not on re-litigating decisions they've already made
deliberately.

---

## Findings, ranked by severity

### 1. `TransactionPipelineBehavior` doesn't roll back on cancellation (Error Handling / Correctness)

`backend/src/app/infrastructure/commands/transaction_pipeline_behavior.py:43-47`:

```python
try:
    result = await self._inner.dispatch(command)
except Exception:
    await unit_of_work.rollback()
    raise
```

`asyncio.CancelledError` inherits from `BaseException`, not `Exception`, since Python 3.8. If a
dispatched command is cancelled mid-flight — a client disconnect, a request timeout, a server
shutdown grace period — this `except Exception` clause does not fire, `rollback()` is never
called, and the exception propagates straight past this method with the unit of work left
`_active=True`.

Invisible today because `InMemoryUnitOfWork` backs no real resource — the abandoned instance is
just garbage-collected. Becomes a real bug the moment a resource-backed `UnitOfWork` (e.g. wrapping
a SQLAlchemy `AsyncSession`, the next step ADR-0012's Future Impact section describes) is plugged
in: a cancelled request would leave a DB transaction open on a pooled connection instead of rolling
it back, risking a leaked connection or held locks until pool timeout.

**Suggested fix:** catch `BaseException` (or explicitly `(Exception, asyncio.CancelledError)`) in
that block, still `raise` afterward so cancellation propagates correctly to the caller. Only worth
doing once the first real `UnitOfWork` implementation lands — flagged now so it isn't forgotten,
since the in-memory implementation will never surface it in testing.

> **RESOLVED (T20, 2026-08-06):** `transaction_pipeline_behavior.py:47` now reads `except
> BaseException:`, with an inline comment explaining why `Exception` alone was wrong. Two new
> regression tests in `test_transaction_pipeline_behavior.py`
> (`test_dispatch_rolls_back_and_reraises_on_cancellation` and
> `test_dispatch_rolls_back_and_reraises_on_a_base_exception`) prove rollback + re-raise for both
> `asyncio.CancelledError` specifically and an arbitrary `BaseException` subclass generally. All 5
> tests in that file pass; the 3 pre-existing tests (success/failure/handler-exception) are
> unchanged and still pass — no regression. Verified directly against source and a live test run.

### 2. The transaction pipeline is unverified against anything it would actually protect (Architecture / Test Coverage)

Correctly documented as a trade-off in ADR-0012 ("proves *orchestration*, not persistence"), so not
a defect — but worth stating plainly: zero code path in this repo currently constructs
`TransactionPipelineBehavior` outside its own test file. `configure_container()` still registers a
bare `InMemoryCommandBus` for `CommandBus`. The begin→dispatch→commit/rollback sequencing has only
ever been exercised against a `UnitOfWork` that can't fail in interesting ways (no I/O, no partial
commits, no connection contention). When a real `UnitOfWork` is built, budget for a fresh round of
tests against *that* — the existing `test_transaction_pipeline_behavior.py` suite proves the
decorator's control flow, not transactional correctness.

### 3. `Container.resolve()` has a check-then-act race if ever called off the event-loop thread (Thread Safety)

`backend/src/app/infrastructure/di/container.py:69-78`:

```python
if self._singletons[interface]:
    if interface not in self._instances:
        self._instances[interface] = self._factories[interface]()
    return self._instances[interface]
```

Safe under pure asyncio single-threaded cooperative scheduling — `resolve()` is synchronous with no
`await` inside it, so nothing can interleave mid-call. But FastAPI does run sync `def` route
handlers (and anything wrapped in `run_in_threadpool`) on a real OS thread pool. If two such threads
race to resolve the same not-yet-cached singleton concurrently, both can pass the `interface not in
self._instances` check before either writes, each constructs its own instance, and the second write
silently wins — a correctness bug for a genuinely stateful singleton, though none registered today
trigger it (every factory in `configure_container()` is cheap/idempotent even if duplicated).

**Suggested fix:** a one-line docstring note on `Container` stating the single-event-loop-thread
assumption explicitly, so a future contributor doesn't reach for `run_in_threadpool` around a
container resolve without knowing the constraint. Low priority.

### 4. Structural duplication across `InMemoryCommandBus` / `InMemoryQueryBus` / `InMemoryEventBus` (Code Duplication)

`InMemoryCommandBus` and `InMemoryQueryBus` are near line-for-line identical: a `dict[type,
Handler]`, a `register()` that raises on double-registration, a `dispatch()`/`publish()` that looks
up by `type()` and raises if absent. `InMemoryEventBus` differs only in allowing multiple handlers
per key.

This is a **deliberate, ADR-documented choice**, not an oversight — ADR-0011's Trade-offs section
explicitly weighs and rejects a shared base class, citing this project's stated preference against
premature abstraction for two structurally-similar-but-conceptually-distinct ports. Defensible at
N=2, still defensible at N=3. If a fourth single-handler bus is ever requested, a small generic
`_SingleHandlerRegistry[TMessage, TError]` mixin (register/dispatch only, leaving the ABC and error
type distinct per port) would start paying for itself — worth a note for whoever picks up the next
one, not an action item now.

### 5. `ModuleManifestLoader.import_enabled()` performs unrestricted dynamic import (Security — defense in depth)

`backend/src/app/infrastructure/modules/manifest.py:88-104` calls
`importlib.import_module(entry.import_path)` for every enabled manifest entry, with no constraint
on what `import_path` can be. Since this loader isn't wired into `main.py` yet (per ADR-0014,
deliberately), there's no live attack surface today. The manifest file itself is the trust boundary:
whatever process can write to the manifest JSON gets arbitrary import-time code execution the next
time the app boots. Inherent to "load a package by dotted path from a config file," not a flaw in
this implementation — but worth carrying forward as a constraint when this gets wired in: the
manifest file needs the same trust level as source code (not, say, admin-editable through a future
UI), and an allowlist prefix check (e.g. require `import_path.startswith("app.modules.")`) would be
a cheap belt-and-suspenders addition at that point.

### 6. `InMemoryCache` has no eviction beyond TTL, and non-TTL/unread entries never get reclaimed (Scalability)

Already flagged as an accepted trade-off in ADR-0013. Restating so it isn't lost once a real caller
appears: expiry is lazy-on-read only (`in_memory_cache.py:30-37`) — a key set with a TTL and never
read again stays in the dict forever, and a key set with no TTL never expires at all. Fine for a
proof-of-port with zero callers; becomes a real memory-growth concern the moment something calls
`cache.set()` in a hot path. Whoever wires the first consumer should either size-bound this
implementation or move straight to the Redis-backed one ADR-0013's Future Impact section
anticipates.

### 7. Minor: exception-chaining edge case if `rollback()` itself raises

`transaction_pipeline_behavior.py:45-47`: if `unit_of_work.rollback()` raises inside the `except
Exception:` block, that new exception propagates instead of the original (Python's implicit
`__context__` chaining preserves the original as "during handling of the above exception," so it's
not *lost*, just no longer primary). Same asymmetry exists in the failure-`Result` path at line 52 —
a `rollback()` failure there skips the trailing log line entirely. Cosmetic today
(`InMemoryUnitOfWork.rollback()` can't fail); worth keeping in mind once a real implementation's
`rollback()` can genuinely throw.

---

## Dimension-by-dimension notes

**Architecture** — Consistent with Stage 1's port/adapter discipline throughout: every new
capability is an `ABC` in `application/interfaces/` plus a default implementation in
`infrastructure/`, registered through the same `Container.register()` call shape.
`TransactionPipelineBehavior` correctly uses the decorator pattern over `CommandBus` rather than
mutating `CommandHandler`'s signature. The consistent refusal to wire new pieces into
`main.py`/`configure_container()` beyond what's proven keeps six substantial additions from
touching the app's actual runtime behavior, verified by `TestRealAppContainer` in
`test_container_health_check.py:76-80` still passing unchanged.

**Performance** — Nothing here is on a hot path yet (zero callers by design). The one
performance-relevant decision — `time.monotonic()` for cache TTL instead of `time.time()` — is
correct and explicitly justified in ADR-0013.

**SOLID** — Interfaces are appropriately narrow (ISP: `Cache` has 4 methods, `UnitOfWork` has 3).
DIP is respected everywhere — `TransactionPipelineBehavior` depends on the `UnitOfWork` abstraction
and a factory `Callable`, never a concrete class. SRP holds: `ModuleManifestLoader` reads/imports
and explicitly does *not* register (that stays `ModuleRegistry`'s job per each imported module's own
side effect).

**Maintainability** — Docstrings consistently explain *why*, not *what*. ADRs mean the reasoning
behind "why isn't X wired in" survives outside tribal knowledge. Minor drag: six near-simultaneous
single-purpose ADRs with heavy cross-referencing is a lot to hold in your head at once when
auditing — this review took longer to do correctly because verifying "is this actually a gap or a
documented decision" required reading all seven ADRs before touching the diff.

**Security** — No new attack surface in the shipped app (nothing here is reachable from an HTTP
route). Two things worth carrying forward: the module manifest's dynamic import needs to stay
config-trust-boundary-only (#5), and `MetricsService`/`LoggingMetricsService`'s `tags: dict[str,
str]` gets logged verbatim with no redaction — fine with zero callers, but the first real caller
that tags a metric with something like a raw email or document ID needs to know that lands in
plaintext structured logs.

**Scalability** — Every default implementation is explicitly in-process/single-instance by design,
with the port boundary already in place for a distributed swap-in later (Redis cache, broker-backed
command bus, SQLAlchemy-backed unit of work). One gap worth flagging early: `Container.resolve()` is
fully synchronous — no support for an async factory. A future Redis-backed `Cache` or broker-backed
`CommandBus` needing awaited connection setup won't fit this container's `Callable[[], T]` factory
shape without either a sync wrapper doing blocking I/O at resolve time or a container change.

**Thread Safety** — Covered above (#3). Everything is safe under the assumed single-event-loop-thread
model; the assumption itself isn't written down anywhere on `Container`.

**Error Handling** — Generally strong: exceptions from handlers are deliberately allowed to
propagate rather than being swallowed into a generic failure `Result` (consistent across
`InMemoryCommandBus`, `InMemoryQueryBus`, `InMemoryEventBus`), and `ContainerHealthCheckError`
aggregates every failure in one pass instead of failing on the first. The one real gap is #1
(cancellation bypassing rollback).

**Code Duplication** — Covered above (#4); acceptable at current scale, worth watching.

---

## Test coverage assessment

All 8 new test files consistently test the actually-interesting behaviors (double-registration
errors, unregistered-type errors, exception propagation, singleton vs. non-singleton registration,
TTL expiry via a mocked clock rather than real `sleep()`, manifest parse/import failure modes)
rather than just happy-path smoke tests. `test_container_health_check.py`'s `TestRealAppContainer`
class exercises `configure_container()` against the real app container rather than only a toy
`Container()`, which is exactly what would have caught a broken registration.

The one coverage gap, already named above (#2): nothing tests `TransactionPipelineBehavior` against
cancellation, and nothing can test it against a real resource yet because none exists. Not something
to fix now — just don't let "the transaction pipeline is tested" become "the transaction pipeline is
proven to roll back correctly" in anyone's head; those are different claims until a real
`UnitOfWork` exists.

---

## Suggested improvements (not applied — review only)

1. **Do soon, cheap:** widen `TransactionPipelineBehavior.dispatch()`'s `except Exception` to also
   catch `BaseException`/`CancelledError` and still roll back before re-raising (#1). Zero risk,
   closes a real gap that will otherwise resurface silently once a real `UnitOfWork` exists.
2. **Do when the first `UnitOfWork` implementation lands:** add a docstring note on `Container`
   naming the single-event-loop-thread assumption (#3), and add tests against that real
   implementation specifically for the cancellation path (#1, #2).
3. **Worth a one-line comment, not urgent:** document on `MetricsService`/`LoggingMetricsService`
   that `tags` values are logged verbatim, so the first real caller knows not to put sensitive data
   in a tag (#5 security note).
4. **Watch, don't act:** revisit `InMemoryCache`'s eviction story (#6) once it has a real caller;
   revisit the `InMemoryCommandBus`/`InMemoryQueryBus` duplication (#4) if a third single-handler
   bus is ever requested.

> **Improvement #3 RESOLVED (T21, 2026-08-06):** `MetricsService` (`metrics.py:10-12`) and
> `LoggingMetricsService` (`logging_metrics_service.py:6-7`) both gained a docstring line stating
> `tags` values are logged verbatim with no redaction. No test changes were needed — the
> pre-existing `test_increment_accepts_an_explicit_value_and_tags` already asserts tags come through
> the logger unmodified, so the documented behavior and the tested behavior now agree. Verified
> directly against source; full metrics test file (9 tests) still passes.
