# Changelog

All notable changes to this project are documented here. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.3.1] — Database migration template, and GitHub Actions CI

**Versioning note:** the git tag `v0.3.0` was actually cut on the commit that already includes
seven post-Stage-2 framework additions and their QA review resolution (internally documented at
the time as versions 0.3.1 through 0.3.8, none of which were ever tagged individually — see the
`[0.3.0]` entry below, corrected to reflect what that tag actually contains). This entry covers
only what's genuinely new **since** that tag: a small documentation-template addition already on
`main`, and this session's GitHub Actions CI work. See
[`docs/releases/v0.3.1.md`](docs/releases/v0.3.1.md) for the full release note and
[`docs/CHANGELOG.md`](docs/CHANGELOG.md) for per-item detail.

- **Database migration template** (`docs/templates/DatabaseMigrationTemplate.md`, new) and
  `docs/templates/README.md` updated to reference it.
- **Stage 2.7: GitHub Actions CI** ([ADR/0017](ADR/0017-github-actions-ci.md)) — three workflows
  (`backend.yml`/`frontend.yml`/`release.yml`) validating every push and pull request: backend
  lint/format/unit-tests/import-smoke, frontend lint/format/vitest, and build verification (no
  deployment, no integration tests, per explicit scope). `engines` added to both `package.json`
  files. See [`docs/ProjectStatus.md`](docs/ProjectStatus.md) for live status and
  [`IMPLEMENTATION_QUEUE.md`](IMPLEMENTATION_QUEUE.md) for the task-by-task record (one item, a
  live CI run, still pending an explicit go-ahead to push).

## [0.3.0] — Stage 2: Database Architecture & Data Model, plus seven post-Stage-2 framework additions and QA resolution

Stage 2 complete. **This tag's commit also includes** seven standalone framework additions
requested directly by the project owner outside the numbered stage sequence — **Command Bus**
([ADR/0010](ADR/0010-command-bus.md)), **Query Bus** ([ADR/0011](ADR/0011-query-bus.md)),
**Transaction Pipeline** ([ADR/0012](ADR/0012-transaction-pipeline.md)), **Caching Abstraction**
([ADR/0013](ADR/0013-caching-abstraction.md)), **Module Manifest Loader**
([ADR/0014](ADR/0014-module-manifest-loader.md)), **Architecture Health Check**
([ADR/0015](ADR/0015-architecture-health-check.md)), **Performance Metrics Service**
([ADR/0016](ADR/0016-performance-metrics-service.md)) — plus a **QA review**
([`docs/reviews/Stage_2_5_QA_Review.md`](docs/reviews/Stage_2_5_QA_Review.md)) of those seven,
fixing two findings. These were originally documented under their own incrementing patch versions
(0.3.1–0.3.8) as each landed, but none were tagged separately — they're all part of this `v0.3.0`
tag's actual content. Backend tests: 216 → 282 across this span. See
[`docs/ProjectStatus.md`](docs/ProjectStatus.md) for live status and
[`docs/CHANGELOG.md`](docs/CHANGELOG.md) for the detailed, per-addition changelog.

## [0.2.0] — Stage 1: Core Architecture & Domain Foundation

Complete. See [`docs/ProjectStatus.md`](docs/ProjectStatus.md) for live status and
[`docs/CHANGELOG.md`](docs/CHANGELOG.md) for the detailed, per-commit changelog of this stage.

## [0.1.0] — Stage 0: Project Foundation

Complete. See [`docs/CHANGELOG.md`](docs/CHANGELOG.md) for the detailed, per-commit changelog of
this stage.
