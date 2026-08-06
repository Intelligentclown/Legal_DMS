# ADR-0010: Command Bus

**Status:** Accepted
**Date:** 2026-08-05

## Problem

Stage 1 built ports for reacting to things that already happened (`EventBus`), generic CRUD
(`BaseService`/`AbstractRepository`), and querying (`SearchIndex`), but nothing for invoking a
single named unit of work — an intentional action a caller wants performed — without importing and
constructing its concrete handler directly. As business features are wired up in future stages,
routes/background jobs/workflow steps will need a uniform way to say "perform this action" (e.g.
"create this Matter") without coupling every caller to a concrete service class's constructor and
dependencies. This addition was requested directly by the project owner as net-new framework work,
outside the original Stage 1 charter and outside the (still-unapproved) Stage 2.5 hardening
backlog in [`IMPLEMENTATION_QUEUE.md`](../IMPLEMENTATION_QUEUE.md) — scoped here as a standalone,
Stage-1-style addition, not as the start of a business feature.

## Options Considered

1. **No command bus — callers invoke application services directly.** Simplest option, but
   couples every caller to a concrete service class and its constructor, and leaves no single
   dispatch seam where future cross-cutting behavior (authorization, logging, validation) could
   hook in uniformly.
2. **A full CQRS setup**: separate Command and Query buses, with pipeline/middleware behavior
   support. More powerful, but no query-side need exists yet — `SearchIndex` and
   `BaseService.list_page()` already cover querying — so a parallel Query bus and a middleware
   pipeline would be speculative infrastructure for a need that hasn't appeared, the same trap
   Stage 1 deliberately avoided everywhere else.
3. **A minimal command bus mirroring the existing `EventBus` pattern**: a `CommandBus` port
   (`register`/`dispatch`) plus one in-memory default implementation, dispatching a command to
   exactly one registered handler and returning a `Result[R, AppError]`. Same shape and rigor as
   every other Stage 1 port (`EventBus`, `JobQueue`, `Notifier`, `SearchIndex`, ...), zero business
   commands shipped with it.

## Decision

Option 3. `application/interfaces/command_bus.py` defines `Command` (a plain marker base class —
not an `ABC`, since a command declares only data), `CommandHandler` (an async callable type),
`CommandBus` (an `ABC` with `register`/`dispatch`), and `CommandBusError`.
`infrastructure/commands/in_memory_command_bus.py` implements `InMemoryCommandBus`, registered in
`configure_container()` alongside `EventBus`. Proven with a toy command + handler in
`tests/unit/test_command_bus.py` only, per Stage 1's existing pattern for the `WorkflowEngine` /
`EventBus` / CRUD router factory — no business command ships with this change.

The one semantic decision this ADR makes explicit: a command bus dispatches to **exactly one**
handler per command type (unlike `EventBus.subscribe`, which allows many). `register()` raises
`CommandBusError` if a second handler is registered for a command type that already has one, and
`dispatch()` raises `CommandBusError` if no handler is registered — both are treated as programming
errors, not business failures (business failures are reported through the handler's own
`Result[R, AppError]`).

## Reasoning

- Documents the single-handler dispatch semantics as a deliberate choice now, rather than leaving
  it to be improvised ad hoc when the first real command and handler are wired up in a future
  stage.
- Matches every other Stage 1 port's minimalism: one `ABC` port + one default in-memory
  implementation, no premature pipeline/middleware machinery.
- Raising `CommandBusError` on double-registration surfaces a wiring bug at registration time
  (deterministic, typically at startup) instead of silently overwriting the first handler and only
  surfacing the mistake when the wrong handler runs.

## Trade-offs

- No pipeline/middleware hook around dispatch (validation, authorization, transaction wrapping,
  logging) yet — deliberately deferred, mirroring `InMemoryEventBus`'s own documented stance: "if a
  future need arises ..., that's a deliberate design change worth its own decision, not a silent
  default."
- No Query bus / CQRS read side — `SearchIndex` and `BaseService.list_page()` already cover
  querying; adding a Query bus now would be speculative until a concrete need appears.
- Still zero business commands. This ADR authorizes the framework seam only; wiring a real command
  handler to it for an actual feature (e.g. "CreateMatter") remains subject to this project's
  standing rule not to start business-feature work without an explicit go-ahead.

## Future Impact

Once a business feature needs to invoke a discrete action from a route, background job, or
workflow step, that feature registers its handler with `CommandBus` in its own module's setup,
following the same `container.register(...)` pattern already established for `Settings`,
`EventBus`, and every other Stage 1 port. If dispatch later needs cross-cutting behavior common to
many commands (transaction wrapping, authorization checks, structured validation), that's worth a
new ADR extending this one — not a silent addition to `InMemoryCommandBus`.
