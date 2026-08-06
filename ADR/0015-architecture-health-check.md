# ADR-0015: Architecture Health Check

**Status:** Accepted
**Date:** 2026-08-05

## Problem

The project owner requested an "Architecture Health Check" directly, not part of a numbered
stage. This maps onto an already-documented, already-scoped item: `IMPLEMENTATION_QUEUE.md`'s T15
— "Add a startup self-check that resolves every interface registered in `configure_container()`
once at boot, failing fast on a broken factory instead of at first request-time use" — one of the
P2 "Lifecycle & exposure hardening" findings from the Stage 2.5 architecture-hardening review
(finding F7: `configure_container()` registers factories but nothing resolves them at startup, so
a broken factory — e.g. a typo'd env var — only fails the first time a request happens to need
it). That backlog as a whole is still "Not Started — pending project-owner approval"; this request
is read as approving and delivering T15 specifically, not the rest of the Stage 2.5 list.

## Options Considered

1. **Do nothing beyond documenting the gap** (the backlog's existing state). Doesn't address the
   request.
2. **A container health check, proven only by its own tests, not wired into `main.py`** — the
   conservative posture taken for the four prior post-Stage-2 additions (Command Bus, Query Bus,
   Transaction Pipeline, Caching Abstraction, Module Manifest Loader), none of which touched
   `main.py`'s actual startup path. Rejected here specifically: T15's own wording is "a **startup**
   self-check" — a check that never runs at startup isn't that. Unlike those prior additions
   (which either needed a real backing resource that doesn't exist yet, or a design decision about
   a consumer that doesn't exist yet), this check's every dependency already exists and is already
   proven working — every currently-registered factory is already exercised successfully by
   existing tests throughout the suite. Wiring it in adds negligible new risk.
3. **A container health check, wired into `main.py` immediately after `configure_container()`**,
   raising on any broken registration. Matches T15's literal scope and wording.

## Decision

Option 3. `infrastructure/di/health_check.py` adds `check_container_health(container) ->
list[ContainerHealthCheckFailure]` (attempts to resolve every interface returned by the container's
new `registered_interfaces()` accessor, catching any exception per interface and collecting
failures rather than raising immediately) and `assert_container_healthy(container)` (calls the
above, raises `ContainerHealthCheckError` listing every failure if any exist). `main.py`'s
`create_app()` calls `assert_container_healthy(container)` immediately after
`configure_container()`, before the `FastAPI` app object is even constructed.

`Container` (`infrastructure/di/container.py`) gains one small accessor, `registered_interfaces()
-> list[type]`, needed to enumerate what to check — the container previously only exposed
`is_registered(interface)` for a single lookup, not enumeration.

## Reasoning

- Directly resolves T15 as scoped in `IMPLEMENTATION_QUEUE.md`'s own review, without pulling in
  any other item from that still-unapproved backlog (T11–T14, T16–T18 remain untouched and
  unapproved).
- `check_container_health()` collects every failure rather than raising on the first one, so a
  future operator/log sees the complete list of broken registrations in one pass, not one-at-a-time
  across repeated restarts.
- Catching `Exception` broadly (not just `ContainerError`) is deliberate: a broken factory can
  raise anything — a `ValueError` from bad config parsing, a `TypeError` from a missing constructor
  argument — and all of those count as an unhealthy registration, not just the container's own
  "never registered" case. This mirrors the existing broad `except Exception` already used in this
  codebase (`InMemoryJobQueue._run`, `TransactionPipelineBehavior.dispatch`) for the same
  "anything can go wrong here, and it should all be caught" reasoning.
- Wiring into `main.py` (unlike every prior post-Stage-2 addition) is safe specifically *because*
  every currently-registered factory is already proven working by the existing test suite — this
  isn't introducing a new failure mode, it's surfacing an existing invariant (every registration
  resolves) explicitly and early, at the one point (boot) where a resolution failure is cheapest to
  notice and fix.

## Trade-offs

- Doesn't address the rest of the Stage 2.5 backlog (the `get_db()` commit bug, the query
  framework, CORS/docs exposure, the migration-head check, etc.) — those remain open, separate,
  still-unapproved items.
- Only checks that a registration *resolves* — it doesn't verify a resolved instance is
  functionally correct (e.g. that a resolved `FileStorage` can actually write to its configured
  root). That's a deliberately narrower check than a full smoke test; T15 asked for "resolves every
  interface," not "exercises every interface."
- `registered_interfaces()` returns registration order, not any semantic ordering — irrelevant
  today (nothing depends on check order), but worth noting if a future registration ever has an
  order-sensitive side effect.

## Future Impact

Any future port added to `configure_container()` is automatically covered by this check with zero
additional code — `registered_interfaces()` reflects whatever's currently registered. If a future
registration is *expected* to fail in some environment (e.g. an optional integration gated by a
feature flag), that's worth its own decision (skip list? separate "optional" registration
category?) at the point such a registration actually exists — not solved speculatively here.
