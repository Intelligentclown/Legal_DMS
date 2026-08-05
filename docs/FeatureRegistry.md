# Feature Registry

No business features exist yet — Stage 0 is infrastructure only. This registry will gain one
entry per business feature starting in Stage 1.

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

## Stage 0 infrastructure (not a "feature", listed for completeness)

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
