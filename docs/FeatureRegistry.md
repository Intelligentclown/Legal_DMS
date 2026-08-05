# Feature Registry

No business features exist yet — Stages 0–2 are infrastructure/framework/schema only, by charter.
Stage 2 built the complete 49-table database schema (see [Database.md](Database.md) and
[ERD.md](ERD.md)), but **no repository, service, or API route is wired to it** — a table existing
is not a feature. This registry will gain one entry per business feature once a future stage
actually wires one up — don't assume that's "Stage 3" without confirming with the project owner
first.

## Template for future entries

```
### <Feature Name>

- **Description:**
- **Status:** Not Started | Planned | In Progress | Completed | Deferred | Cancelled
- **Dependencies:**
- **Related APIs:**
- **Related Database Tables:**
- **Related UI Screens:**
- **Future Improvements:**
```

## Infrastructure (not a "feature", listed for completeness)

### System Health Check

- **Description:** Liveness/version endpoints and a UI page proving the full stack (Electron →
  React → FastAPI → Postgres) is wired correctly. Not a business feature — foundational plumbing.
- **Status:** Completed
- **Dependencies:** None
- **Related APIs:** `GET /api/v1/health`, `GET /api/v1/version`
- **Related Database Tables:** None
- **Related UI Screens:** `HealthCheckPage`
- **Future Improvements:** Could grow a DB-aware `/health/ready` variant if an operational need
  arises (see [FutureIdeas.md](FutureIdeas.md)).
