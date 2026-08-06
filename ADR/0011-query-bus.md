# ADR-0011: Query Bus

**Status:** Accepted
**Date:** 2026-08-05

## Problem

[ADR/0010](0010-command-bus.md) added a `CommandBus` for dispatching write-side actions and
explicitly deferred a companion Query bus as speculative: "no query-side need is established yet —
`SearchIndex`/`BaseService.list_page` already cover querying." The project owner has since
requested a Query Bus directly, which resolves that deferral — a concrete need is now established
by direct instruction rather than inferred. As with [ADR/0010](0010-command-bus.md), this is
standalone framework work requested outside any numbered stage, not the start of a business
feature.

## Options Considered

1. **No query bus — keep using `SearchIndex`/`BaseService.list_page()` directly.** Still valid for
   generic list/filter/sort queries against a single entity type, but gives callers no uniform way
   to request an arbitrary, possibly cross-entity or computed read (e.g. "widgets grouped by
   status") without depending on a concrete service class — the same coupling problem `CommandBus`
   solves on the write side.
2. **A single generic "Request bus"** handling both commands and queries through one port,
   distinguished only by a marker interface. Fewer files, but conflates two semantically different
   contracts (queries must not mutate state; that invariant is worth its own type) and would make a
   future read/write-specific behavior (e.g. routing queries to a read replica) awkward to hook in
   without a runtime type check.
3. **A `QueryBus` port mirroring `CommandBus`'s shape exactly**: `register`/`dispatch`, one handler
   per query type, `Result[R, AppError]` return, its own in-memory default implementation and its
   own `QueryBusError`. Symmetric sibling to `CommandBus`, not a variant of `EventBus` — a query, like
   a command, has exactly one handler, not many subscribers.

## Decision

Option 3. `application/interfaces/query_bus.py` defines `Query` (a plain marker class, not an
`ABC`, matching `Command`'s own reasoning), `QueryHandler` (an async callable type identical in
shape to `CommandHandler`), `QueryBus` (an `ABC` with `register`/`dispatch`), and `QueryBusError`.
`infrastructure/queries/in_memory_query_bus.py` implements `InMemoryQueryBus`, registered in
`configure_container()` alongside `CommandBus`. Proven with a toy query + handler in
`tests/unit/test_query_bus.py` only — no business query ships with this change.

Same single-handler-per-type dispatch semantics as `CommandBus`: `register()` raises
`QueryBusError` on a second registration for the same query type, `dispatch()` raises
`QueryBusError` when no handler is registered. The one thing that distinguishes `Query` from
`Command` is documentation, not code: a query handler must not mutate state. Nothing in this
framework layer enforces that — same trust boundary as `BaseService`'s existing "business logic
belongs in the service/handler, not the framework" split.

## Reasoning

- Resolves ADR-0010's explicit deferral now that a concrete need exists, rather than leaving two
  inconsistent read paths (`SearchIndex`/`BaseService.list_page` for generic entity queries,
  something ad hoc for everything else) once a real feature needs both.
- Mirrors `CommandBus` deliberately: same file shape, same registration/dispatch contract, same
  error type pattern. A future contributor who has read one already understands the other.
- Kept as its own type (`QueryBus`/`Query`/`QueryBusError`) rather than folded into `CommandBus`
  (Option 2) because "no mutation" is a real contract worth a distinct name, even though today
  nothing enforces it at runtime — same rationale `AppError` subclasses use to distinguish
  `ValidationError` from `ConflictError` despite sharing a common base.

## Trade-offs

- No shared base class between `CommandBus` and `QueryBus` despite near-identical implementations —
  accepted deliberately, consistent with this codebase's existing choice not to share code between
  structurally similar-but-conceptually-distinct ports (e.g. `EventBus` vs. `JobQueue`). A shared
  base would be premature abstraction for two ports total.
- Still no pipeline/middleware hook (caching, read-replica routing, authorization) around dispatch —
  same deliberate deferral as `CommandBus`'s own trade-offs section; worth its own ADR if and when a
  concrete need appears.
- Still zero business queries. This ADR authorizes the framework seam only; wiring a real query
  handler to it for an actual feature remains subject to this project's standing rule not to start
  business-feature work without an explicit go-ahead.

## Future Impact

Once a business feature needs a read that doesn't fit `SearchIndex`/`BaseService.list_page()`'s
generic entity-listing shape, that feature registers a handler with `QueryBus` in its own module's
setup, following the same `container.register(...)` pattern as every other port. If dispatch later
needs cross-cutting behavior (caching, read-replica routing), that's worth a new ADR extending this
one — not a silent addition to `InMemoryQueryBus`.
