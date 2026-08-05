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

## Stage 2+ — Not yet planned

Nothing below has an estimated stage, priority, or dependency graph yet. Listed here only because
the original project charter named them as the eventual scope; **do not implement any of these
without an explicit go-ahead** — see [FutureIdeas.md](FutureIdeas.md) for why Stages 0–1 stayed
deliberately business-logic-free.

| Feature | Status |
|---|---|
| Authentication / login | Not Started |
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

This table should be rewritten with real priorities/dependencies/stages once Stage 2 planning
actually starts — with explicit direction from the project owner on what Stage 2 covers.
