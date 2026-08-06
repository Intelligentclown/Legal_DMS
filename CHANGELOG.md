# Changelog

All notable changes to this project are documented here. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.3.8] — QA Review Resolution (post-Stage-2 QA fixes)

Two findings fixed from a QA review of the seven post-Stage-2 framework additions
([`docs/reviews/Stage_2_5_QA_Review.md`](docs/reviews/Stage_2_5_QA_Review.md)): `TransactionPipelineBehavior.dispatch()`
now catches `BaseException` instead of `Exception` so `asyncio.CancelledError` still rolls back
before re-raising, and `MetricsService`/`LoggingMetricsService` gained docstring notes that `tags`
are logged verbatim with no redaction. Backend tests: 280 → 282. See
[`docs/ProjectStatus.md`](docs/ProjectStatus.md) for live status,
[`docs/CHANGELOG.md`](docs/CHANGELOG.md) for detail,
[`IMPLEMENTATION_QUEUE.md`](IMPLEMENTATION_QUEUE.md) (T20/T21) for the task record, and
[`docs/releases/v0.3.8.md`](docs/releases/v0.3.8.md) for the full release note.

## [0.3.7] — Performance Metrics Service (post-Stage-2 framework addition)

Standalone framework addition requested directly by the project owner, not part of a numbered
stage — a `MetricsService` port + `LoggingMetricsService`, not wired to `CommandBus`/`QueryBus`
dispatch, HTTP middleware, or a `/metrics` route. See
[`docs/ProjectStatus.md`](docs/ProjectStatus.md) for live status,
[`docs/CHANGELOG.md`](docs/CHANGELOG.md) for detail, and
[`ADR/0016`](ADR/0016-performance-metrics-service.md) for the decision record.

## [0.3.6] — Architecture Health Check (post-Stage-2 framework addition)

Standalone framework addition requested directly by the project owner, not part of a numbered
stage — resolves `IMPLEMENTATION_QUEUE.md`'s T15/F7 finding. The only post-Stage-2 addition wired
into the real app's startup path (`main.py`). See [`docs/ProjectStatus.md`](docs/ProjectStatus.md)
for live status, [`docs/CHANGELOG.md`](docs/CHANGELOG.md) for detail, and
[`ADR/0015`](ADR/0015-architecture-health-check.md) for the decision record.

## [0.3.5] — Module Manifest Loader (post-Stage-2 framework addition)

Standalone framework addition requested directly by the project owner, not part of a numbered
stage — closes a gap `ModuleRegistry`'s own docstring left open (which packages to import so their
registration side effect runs). See [`docs/ProjectStatus.md`](docs/ProjectStatus.md) for live
status, [`docs/CHANGELOG.md`](docs/CHANGELOG.md) for detail, and
[`ADR/0014`](ADR/0014-module-manifest-loader.md) for the decision record.

## [0.3.4] — Caching Abstraction (post-Stage-2 framework addition)

Standalone framework addition requested directly by the project owner, not part of a numbered
stage — a `Cache` port + `InMemoryCache`, not wired to `QueryBus`/`CommandBus`. See
[`docs/ProjectStatus.md`](docs/ProjectStatus.md) for live status,
[`docs/CHANGELOG.md`](docs/CHANGELOG.md) for detail, and
[`ADR/0013`](ADR/0013-caching-abstraction.md) for the decision record.

## [0.3.3] — Transaction Pipeline (post-Stage-2 framework addition)

Standalone framework addition requested directly by the project owner, not part of a numbered
stage — resolves the "transaction wrapping" trade-off the Command Bus and Query Bus ADRs both
deferred. See [`docs/ProjectStatus.md`](docs/ProjectStatus.md) for live status,
[`docs/CHANGELOG.md`](docs/CHANGELOG.md) for detail, and
[`ADR/0012`](ADR/0012-transaction-pipeline.md) for the decision record.

## [0.3.2] — Query Bus (post-Stage-2 framework addition)

Standalone framework addition requested directly by the project owner, not part of a numbered
stage — symmetric sibling to the Command Bus below. See
[`docs/ProjectStatus.md`](docs/ProjectStatus.md) for live status,
[`docs/CHANGELOG.md`](docs/CHANGELOG.md) for detail, and [`ADR/0011`](ADR/0011-query-bus.md) for
the decision record.

## [0.3.1] — Command Bus (post-Stage-2 framework addition)

Standalone framework addition requested directly by the project owner, not part of a numbered
stage. See [`docs/ProjectStatus.md`](docs/ProjectStatus.md) for live status,
[`docs/CHANGELOG.md`](docs/CHANGELOG.md) for detail, and [`ADR/0010`](ADR/0010-command-bus.md) for
the decision record.

## [0.3.0] — Stage 2: Database Architecture & Data Model

Complete. See [`docs/ProjectStatus.md`](docs/ProjectStatus.md) for live status and
[`docs/CHANGELOG.md`](docs/CHANGELOG.md) for the detailed, per-commit changelog of this stage.

## [0.2.0] — Stage 1: Core Architecture & Domain Foundation

Complete. See [`docs/ProjectStatus.md`](docs/ProjectStatus.md) for live status and
[`docs/CHANGELOG.md`](docs/CHANGELOG.md) for the detailed, per-commit changelog of this stage.

## [0.1.0] — Stage 0: Project Foundation

Complete. See [`docs/CHANGELOG.md`](docs/CHANGELOG.md) for the detailed, per-commit changelog of
this stage.
