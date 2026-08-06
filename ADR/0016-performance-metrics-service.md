# ADR-0016: Performance Metrics Service

**Status:** Accepted
**Date:** 2026-08-05

## Problem

The project owner requested a "Performance Metrics Service" directly, not part of a numbered
stage. Unlike the five prior post-Stage-2 additions, this one doesn't map onto an item already
named in an existing ADR trade-off, `IMPLEMENTATION_QUEUE.md` finding, or another port's docstring
— there was no pre-existing "gap" pointing at a specific design. Two readings were possible: a
standalone port for recording counters/gauges/durations (same shape as `Notifier`/`AuditLogger`/
`Cache`), or a pipeline behavior instrumenting `CommandBus`/`QueryBus` dispatch timing (same shape
as `TransactionPipelineBehavior`), or an HTTP-exposed `/metrics` endpoint.

## Options Considered

1. **A `MetricsPipelineBehavior` wrapping `CommandBus`/`QueryBus`**, recording dispatch duration
   automatically. Rejected on the same naming-convention read used for Caching Abstraction: this
   project consistently names pipeline-behavior decorators for what they *do* ("Transaction
   Pipeline"), and standalone ports "\<Thing\> Abstraction/Foundation/**Service**" — `Cache`,
   `AuthorizationService`, `AuthenticationProvider` are all standalone ports despite some having
   "Service"/"Provider" suffixes, never a bus-wrapping decorator. "Performance Metrics **Service**"
   reads as the former category, not the latter.
2. **A `/metrics` HTTP endpoint** (Prometheus-style scrape target). Rejected: every prior addition
   in this session explicitly verified the real app's route surface stayed at
   `/api/v1/health`/`/api/v1/version` only — adding a route is a materially bigger, more visible
   decision than any standalone port addition, and nothing in the request asked for HTTP exposure
   specifically.
3. **A standalone `MetricsService` port** (`increment`/`gauge`/`record_duration`, plus a concrete
   `timer()` convenience built on `record_duration`) with a `LoggingMetricsService` default
   implementation — same shape as every other Stage 1 port, and specifically mirroring
   `Notifier`/`AuditLogger`'s "logs structurally, no real backend wired yet" precedent rather than
   the "in-memory, state proven by tests" precedent used for `EventBus`/`Cache`/`UnitOfWork` (a
   metrics event is fundamentally a write with no meaningful read-back need, like an audit entry or
   a notification — not state to query later).

## Decision

Option 3. `application/interfaces/metrics.py` defines `MetricsService`: three abstract methods
(`increment`, `gauge`, `record_duration`, each accepting optional `tags: dict[str, str] | None`)
plus one concrete convenience, `timer()` — a context manager measuring wall-clock duration and
recording it via `record_duration`, built the same way `EventBus.publish_all()` is a concrete
method built on the abstract `publish()`. `infrastructure/metrics/logging_metrics_service.py`
implements `LoggingMetricsService`, logging each metric event as structured JSON to a dedicated
`app.metrics` logger channel — same pattern as `LoggingAuditLogger`'s `app.audit` channel.
Registered as a singleton in `configure_container()`, same as `Notifier`/`AuditLogger`. Not wired
into `CommandBus`/`QueryBus` dispatch, HTTP middleware, or any route.

## Reasoning

- Matches this project's established naming convention (see ADR-0013's reasoning for Caching
  Abstraction, applied here to a "Service"-suffixed name instead of "Abstraction") without
  reopening that question each time.
- `LoggingMetricsService` over an in-memory implementation: a metric event, like an audit entry or
  a notification, is a write with no in-process read-back need — nothing in this codebase queries
  "what metrics have been recorded so far," unlike `Cache`/`EventBus`/`UnitOfWork` where in-memory
  state genuinely stands in for a real backing behavior. Mirroring `LoggingNotifier`/
  `LoggingAuditLogger` here is the more honest placeholder: it's exactly as far from a real metrics
  backend (StatsD/Prometheus/CloudWatch) as those two are from a real notification/audit sink.
- `timer()` as a concrete convenience keeps every implementation's job to the three primitives,
  while giving callers (once any exist) the more ergonomic call a real feature would actually want
  — avoids every future caller hand-rolling `time.perf_counter()` deltas.
- No new route: adding one would break this session's running invariant (every addition verified
  against an unchanged `/api/v1/health`/`/api/v1/version`-only route surface) without the request
  asking for HTTP exposure specifically.

## Trade-offs

- Not wired to `CommandBus`/`QueryBus` dispatch or HTTP middleware — same "framework only, zero
  consumers" position as `Cache`. If a `MetricsPipelineBehavior` (mirroring
  `TransactionPipelineBehavior`) or request-timing middleware is wanted later, it would consume
  this same `MetricsService` port, not replace it.
- `LoggingMetricsService` produces one log line per metric event with no aggregation — a
  high-frequency counter (e.g. incremented per request) would be noisy in real log volume. Not a
  concern yet with zero callers; worth revisiting (batching? sampling?) once a real caller and
  volume exist.
- No metric-name or tag-cardinality validation — a caller could pass an unbounded set of `name`/
  `tags` values with no guardrail. Deferred: no real metrics backend is wired yet for cardinality
  to matter against.

## Future Impact

A future feature that wants automatic dispatch timing wraps its `CommandBus`/`QueryBus` with a new
`MetricsPipelineBehavior` consuming this port — following `TransactionPipelineBehavior`'s exact
precedent — rather than this port being replaced. A future need for a real metrics backend (StatsD,
Prometheus, CloudWatch, OpenTelemetry) satisfies this same `MetricsService` port with a new
implementation registered in `configure_container()`, without touching any caller. A future
`/metrics` HTTP endpoint, if wanted, is a separate, deliberate decision — not implied by this ADR.
