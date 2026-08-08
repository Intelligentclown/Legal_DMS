# Roadmap

Status values: `Not Started`, `Planned`, `In Progress`, `Completed`, `Deferred`, `Cancelled`.

## Stage 0 — Project Foundation

| Item | Priority | Dependencies | Status |
|---|---|---|---|
| Repo skeleton & dev tooling | High | — | Completed |
| Backend foundation (config, logging, errors) | High | Repo skeleton | Completed |
| Backend API + DB (FastAPI, SQLAlchemy, Alembic) | High | Backend foundation | Completed |
| Backend tests (pytest) | High | Backend API + DB | Completed |
| Electron shell | High | Repo skeleton | Completed |
| Frontend foundation (Vite/React/Tailwind/shadcn) | High | Repo skeleton | Completed |
| Frontend↔backend E2E proof (HealthCheckPage) | High | Frontend + backend foundations | Completed |
| Frontend tests (Vitest/RTL) | High | Frontend foundation | Completed |
| Full documentation pass | High | All of the above | Completed |

Stage 0 has no business features — see [KnownIssues.md](KnownIssues.md) for the two open
tooling caveats (shadcn CLI, react-router-dom advisory) carried forward.

## Stage 1 — Core Architecture & Domain Foundation

| Item | Priority | Dependencies | Status |
|---|---|---|---|
| Domain foundation (AggregateRoot, DomainEvent, Result) | High | Stage 0 | Completed |
| Dependency Injection Container | High | Domain foundation | Completed |
| Repository Pattern | High | DI Container | Completed |
| Base Service | High | Repository Pattern | Completed |
| Validation / Pagination / Query / Response frameworks | High | Base Service | Completed |
| Base Controller (CRUD router factory) | High | Above frameworks | Completed |
| Event System | High | DI Container | Completed |
| Background Job Framework | High | DI Container | Completed |
| File Storage Abstraction | High | DI Container | Completed |
| Notification Framework (backend) | Medium | DI Container | Completed |
| Auth + Authorization Frameworks (no login) | High | DI Container | Completed |
| Audit Logging Framework | Medium | Auth framework | Completed |
| Search Foundation | Medium | Query framework | Completed |
| Plugin Architecture | High | DI Container | Completed |
| Workflow Engine | Medium | — | Completed |
| Feature Flags + Config Service extension | Medium | Stage 0 config | Completed |
| Frontend Result + query types | Low | Backend query framework | Completed |
| Full documentation pass | High | All of the above | Completed |

Stage 1 has no business features either — every subsystem is a framework with exactly one minimal
default implementation. See [ProjectStatus.md](ProjectStatus.md) for the full checklist and
[ADR/0006](../ADR/0006-dependency-injection-container.md) /
[ADR/0007](../ADR/0007-audit-logging-without-database-table.md) for the two Stage 1-specific
architectural decisions.

## Stage 2 — Database Architecture & Data Model

| Item | Priority | Dependencies | Status |
|---|---|---|---|
| Schema conventions (naming convention, AuditMixin, OptimisticLockMixin) + Identity & Access | High | Stage 1 | Completed |
| Geography (Country→Village hierarchy) | High | Identity & Access | Completed |
| Clients | High | Geography | Completed |
| Properties | High | Clients | Completed |
| Matters & Workflow | High | Clients, Properties | Completed |
| Documents & File Storage | High | Matters | Completed |
| Financial | Medium | Matters, Clients | Completed |
| Activity, Audit & Notifications | Medium | Identity & Access | Completed |
| Scheduling & Tags | Medium | Matters, Clients | Completed |
| OCR, QR & Backups | Medium | Documents | Completed |
| System, Config, AI & Plugins | Low | Identity & Access | Completed |
| Seed lookup data | Medium | All schema sections | Completed |
| `docs/ERD.md` + full documentation pass | High | All of the above | Completed |

Stage 2 built the complete 49-table schema as pure schema — **no repositories, services, or API
routes wired to any table**. See [Database.md](Database.md), [ERD.md](ERD.md), and
[ProjectStatus.md](ProjectStatus.md) for the full checklist, and
[ADR/0008](../ADR/0008-persistence-models-not-domain-entities.md) /
[ADR/0009](../ADR/0009-audit-logs-table-reverses-adr-0007.md) for the two Stage 2-specific
architectural decisions.

## Post-Stage-2 — Standalone Framework Additions

Requested directly by the project owner outside the numbered-stage process — framework-only, same
"no business logic" charter as Stages 0–2. Each is a port + one minimal default implementation,
following the Stage 1 pattern.

| Item | Priority | Dependencies | Status |
|---|---|---|---|
| Command Bus (`CommandBus`, `InMemoryCommandBus`) | — | Stage 2 | Completed |
| Query Bus (`QueryBus`, `InMemoryQueryBus`) | — | Command Bus | Completed |
| Transaction Pipeline (`UnitOfWork`, `InMemoryUnitOfWork`, `TransactionPipelineBehavior`) | — | Command Bus, Query Bus | Completed |
| Caching Abstraction (`Cache`, `InMemoryCache`) | — | Stage 2 | Completed |
| Module Manifest Loader (`ModuleManifest`, `ModuleManifestLoader`) | — | Stage 1 Plugin Architecture | Completed |
| Architecture Health Check (`check_container_health`, `assert_container_healthy`) | — | DI Container | Completed |
| Performance Metrics Service (`MetricsService`, `LoggingMetricsService`) | — | Stage 2 | Completed |
| QA review of the seven additions above + resolution of its two immediately-actionable findings | — | All of the above | Completed |

See [ProjectStatus.md](ProjectStatus.md) for the full checklist, [ADR/0010](../ADR/0010-command-bus.md)
through [ADR/0016](../ADR/0016-performance-metrics-service.md) for the decision records, and
[docs/reviews/Stage_2_5_QA_Review.md](reviews/Stage_2_5_QA_Review.md) plus
[IMPLEMENTATION_QUEUE.md](../IMPLEMENTATION_QUEUE.md)'s "QA Review Findings" section for the review
itself — five findings remain deferred pending a gating dependency, two are accepted ADR-documented
trade-offs, none are outstanding action items.

## Stage 3 — Authentication & Authorization (in progress)

Scoped, architecture-approved (D1–D7, `ADR-0018`/`0019`/`0020`), and under active implementation —
see `IMPLEMENTATION_QUEUE.md`'s "Stage 3" section for the full task list (`T41`–`T80`), acceptance
criteria, and current status; this row is a pointer, not a duplicate. As of 2026-08-08: **Phase 0
(`T41`–`T45`) and Phase 1 (`T46`–`T51`) are both complete.** `T46`/`T47` (password hashing, JWT
encode/decode) merged to `main`; `T48` satisfied by `T44`'s work; `T49` (the `refresh_tokens`
migration) independently QA-approved after one rework round; `T50`/`T51` (`AuthService` — `authenticate`/
`issue_tokens`/`refresh`/`revoke` — plus its 28 tests) QA Decision: Approved with comments, 2026-08-08
(see `docs/ImplementationLog/Stage3/Phase1.md`). `T50`/`T51`'s work is uncommitted on `main` as of
this update — see `PROJECT_STATE.json`'s `git` block. `T52` (`JwtAuthenticationProvider`, Phase 2) is
next, not yet authorized.

| Feature | Status |
|---|---|
| Authentication / login | In Progress — see `IMPLEMENTATION_QUEUE.md` |
| Authorization (RBAC) | In Progress — see `IMPLEMENTATION_QUEUE.md` |

## Stage 4+ — Not yet planned

Nothing below has an estimated stage, priority, or dependency graph yet. Listed here only because
the original project charter named them as the eventual scope; **do not implement any of these
without an explicit go-ahead** — see [FutureIdeas.md](FutureIdeas.md) for why Stages 0–2 stayed
deliberately business-logic-free. The database schema each of these would sit on already exists
(Stage 2) — the work here is wiring a repository/service/route to it, not schema design.

| Feature | Status |
|---|---|
| Matter Management | Not Started |
| Client Management | Not Started |
| Property Management | Not Started |
| Document Automation | Not Started |
| OCR | Not Started |
| QR codes | Not Started |
| Search (real implementation) | Not Started |
| Reports | Not Started |
| Payments | Not Started |
| AI features | Not Started |
| Cloud synchronization | Not Started |

This table should be rewritten with real priorities/dependencies/stages once Stage 4 planning
actually starts — with explicit direction from the project owner on what Stage 4 covers.
