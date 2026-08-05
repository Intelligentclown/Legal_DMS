# ADR-0006: Hand-rolled dependency injection container

**Status:** Accepted
**Date:** 2026-08-05

## Problem

Stage 1's charter requires "a scalable dependency injection system" where "every service should be
replaceable" and "dependencies should never be manually instantiated inside business code."
FastAPI's `Depends()` already solves this well for HTTP routes, but doesn't extend naturally to
non-request contexts this stage is also building — background jobs, event handlers — which need a
way to resolve the same services without going through a request.

## Options Considered

1. **Rely on FastAPI's `Depends()` alone.** Works great for routes, but background jobs/event
   handlers have no request to hang a `Depends()` off of — they'd need to import and construct
   dependencies directly, which is exactly the "manually instantiated inside business code" problem
   the charter warns against.
2. **A mature DI library** (e.g. `dependency-injector`). Full-featured (scopes, auto-wiring,
   provider types) but adds a new dependency and a DSL a future session would need to learn, for a
   project whose actual DI needs right now are simple (register a factory, resolve it, allow
   overriding in tests).
3. **A small hand-rolled container**: a type → factory registry with optional singleton caching,
   used both directly (for non-request contexts) and as the thing `presentation/api/deps.py`
   resolves through (for request contexts, alongside `Depends()`).

## Decision

Option 3. `infrastructure/di/container.py` defines `Container` (`register`, `resolve`,
`is_registered`, `override`, `reset`) and a module-level `container` singleton plus
`configure_container()`, called once in `main.py`'s `create_app()`. `presentation/api/deps.py`'s
`SettingsDep` now resolves `Settings` through `container.resolve(Settings)` instead of calling
`get_settings()` directly — same public `Annotated` alias, so no caller-visible change.

`DBSessionDep` **stays on FastAPI's native generator `Depends(get_db)` pattern**, not routed
through the container — a request-scoped resource with teardown (open session → yield → close) is
exactly what FastAPI's generator dependencies already do correctly, and the container's simple
register/resolve model doesn't (and isn't meant to) replace that.

## Reasoning

- Zero new dependency, ~70 lines, easy for any future session to read in full without learning a
  library's provider/scope vocabulary.
- Covers what's actually needed now: swappable singleton services, resolvable from both HTTP
  routes and non-request code (jobs, event handlers) via the same `container.resolve(X)` call.
- `override()` gives tests a clean way to substitute a fake implementation for any registered
  service without monkeypatching.
- Keeping `DBSessionDep` on FastAPI's own `Depends()` avoids forcing a resource-lifecycle concept
  (open/yield/close) into a container that doesn't model lifecycles beyond singleton-vs-transient.

## Trade-offs

- Less battle-tested than a mature library; no scopes beyond singleton/transient, no automatic
  type-introspection wiring (every dependency must be explicitly registered).
- Two DI mechanisms now coexist (FastAPI's `Depends()` and this `Container`) rather than one
  unified system — accepted because they serve different lifecycles (request-scoped vs.
  singleton/transient-anywhere) and forcing one to do both jobs would be worse than using each for
  what it's actually good at.

## Future Impact

Every future service with a replaceable implementation (repositories, the event bus, job queue,
file storage, notifier, search index, auth provider — all being added later in Stage 1) registers
itself in `configure_container()` and is resolved via `container.resolve(...)`, either directly in
non-request code or through a `Depends()`-wrapped accessor in `presentation/api/deps.py` for
routes, following the exact pattern established here for `Settings`. If the container's needs
outgrow this simple model (e.g. genuine multi-tenancy scoping), that's worth a new ADR evaluating
a real DI library at that point — not before.
