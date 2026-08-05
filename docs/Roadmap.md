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

## Stage 1+ — Not yet planned

Nothing below has an estimated stage, priority, or dependency graph yet. Listed here only because
the original project charter named them as the eventual scope; **do not implement any of these
without an explicit go-ahead** — see [FutureIdeas.md](FutureIdeas.md) for why Stage 0 stayed
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
| Search | Not Started |
| Reports | Not Started |
| Payments | Not Started |
| AI features | Not Started |
| Cloud synchronization | Not Started |

This table should be rewritten with real priorities/dependencies/stages once Stage 1 planning
actually starts.
