# ADR-0013: Caching Abstraction

**Status:** Accepted
**Date:** 2026-08-05

## Problem

The project owner requested a "Caching Abstraction" directly, not part of a numbered stage.
"Caching" was already named once in this project's history — [ADR/0011](0011-query-bus.md)'s
Trade-offs section listed "caching, read-replica routing, authorization" as pipeline/middleware
hooks deliberately deferred from wrapping `QueryBus` dispatch, the same category of deferral
[ADR/0012](0012-transaction-pipeline.md) later resolved for "transaction wrapping" by building
`TransactionPipelineBehavior`. That precedent raised a real question here: is "Caching
Abstraction" asking for the same treatment — a pipeline behavior wrapping `QueryBus`, mirroring
`TransactionPipelineBehavior` — or a standalone capability?

Unlike the "Transaction Pipeline" request, this one carries a strong naming signal rather than
genuine structural ambiguity: every existing standalone, not-yet-wired-to-anything Stage 1 port in
this project is named "\<Thing\> Abstraction" or "\<Thing\> Foundation" in `PROJECT_STATE.json`/
`docs/ProjectStatus.md` — "File Storage **Abstraction**," "Search **Foundation**," "Notification
**Framework**," "Audit Logging **Framework**" — none of which are wired into `CommandBus`/
`QueryBus` dispatch. The pipeline-behavior additions, by contrast, are named for what they *do*:
"**Transaction Pipeline**," "Command Bus," "Query Bus." "Caching **Abstraction**" matches the
former naming pattern, not the latter — read as a request for a standalone `Cache` port, the same
category as `FileStorage`/`SearchIndex`, not a `QueryBus`-wrapping decorator. Because guessing
wrong here is low-cost (purely additive either way; nothing existing would need to change or
break), this was implemented directly on that reading rather than raised as a clarifying question.

## Options Considered

1. **A `CachingPipelineBehavior` wrapping `QueryBus`**, mirroring `TransactionPipelineBehavior`'s
   shape exactly — read-through caching keyed by the dispatched `Query`. Would resolve ADR-0011's
   deferral literally, but the request's own wording doesn't point here (see Problem), and it
   would require deciding a cache-key scheme for arbitrary `Query` subclasses (hash the dataclass?
   require an explicit key method?) — a real design question this request didn't ask to resolve.
2. **A standalone `Cache` port** (`get`/`set`/`delete`/`clear`, optional per-entry TTL) plus one
   in-memory default implementation, wired into nothing — same shape and rigor as `FileStorage`,
   `SearchIndex`, `Notifier`. Matches the naming precedent, requires no design decision about
   `QueryBus` integration, and stays useful as a building block if a caching pipeline is requested
   later (option 1 would consume this port rather than duplicate it).

## Decision

Option 2. `application/interfaces/cache.py` defines `Cache` (an `ABC` with `get`/`set`/`delete`/
`clear`; `set` takes an optional `ttl_seconds`). `infrastructure/cache/in_memory_cache.py`
implements `InMemoryCache` — a dict-backed store with lazy TTL expiry on read (checked against
`time.monotonic()`, not wall-clock time, so a system clock change can't perturb expiry), no
background sweep. Registered in `configure_container()` as a singleton (unlike `UnitOfWork`, a
shared cache instance *is* the correct semantics — the whole point is one shared store, not
per-operation isolation). Not wired into `QueryBus` or anywhere else — a standalone capability,
proven by its own tests only.

## Reasoning

- Matches this project's own naming convention for standalone ports versus pipeline behaviors,
  used consistently since Stage 1.
- Avoids deciding a cache-key scheme for `Query` objects now, which the "Abstraction" wording never
  asked to resolve and which deserves its own decision if and when a caching pipeline is actually
  requested (same "worth its own decision, not a silent default" principle every prior ADR in this
  sequence has repeated).
- `time.monotonic()` for expiry avoids a real, easy-to-miss bug class (wall-clock adjustments
  causing early/late expiry) at zero extra cost — worth stating explicitly since it's not the
  obvious first choice (`time.time()` reads more naturally for "TTL" but is the wrong tool).
- Registered as a singleton, unlike `UnitOfWork` ([ADR/0012](0012-transaction-pipeline.md)) — a
  cache's entire purpose is being shared across callers; per-operation isolation would defeat it.

## Trade-offs

- Not wired to `QueryBus`, `CommandBus`, or anything else — same "framework only, zero consumers"
  position every Stage 1 port started from. If this reading of the request was wrong and a
  `QueryBus`-wrapping caching pipeline was actually wanted, that's a small, low-risk follow-up
  (`CachingPipelineBehavior` would consume this same `Cache` port, not replace it).
- `get()` returns `None` for both "not cached" and "cached value is `None`" — documented as a
  known limitation in the port's docstring rather than solved with a sentinel value, since no
  consumer exists yet to know whether that ambiguity actually matters.
- In-memory only, single process, no eviction policy beyond TTL (no LRU/size bound) — acceptable
  for a framework-only proof with no real workload to size against, same reasoning
  [ADR/0006](0006-dependency-injection-container.md) and this project's `FutureIdeas.md` have
  applied to every other "revisit once a real workload exists" deferral.

## Future Impact

A future feature that needs to memoize a query result wraps whatever `QueryBus` it resolves with a
new `CachingPipelineBehavior` built against this same `Cache` port — following
`TransactionPipelineBehavior`'s exact precedent — rather than this port being replaced. A future
need for a distributed cache (Redis, etc.) satisfies this same `Cache` port with a new
implementation registered in `configure_container()`, without touching any caller, per this
project's standard port/implementation swap pattern.
