# Database

## Status: no business schema yet (Stage 0)

Stage 0 deliberately creates zero business tables. What exists:

- **Engine**: PostgreSQL 16 (Alpine), provisioned locally via [`docker-compose.yml`](../docker-compose.yml).
- **ORM**: SQLAlchemy 2.x async, declarative `Base` in
  [`infrastructure/database/base.py`](../backend/src/app/infrastructure/database/base.py).
- **Session management**: lazily-constructed, cached async engine + `async_sessionmaker` in
  [`infrastructure/database/session.py`](../backend/src/app/infrastructure/database/session.py),
  exposed to routes via the `DBSessionDep` FastAPI dependency.
- **Migrations**: Alembic, async template, initialized in `backend/alembic/`. `env.py` pulls
  `DATABASE_URL` from the app's own validated `Settings` — never a hardcoded connection string —
  and targets `Base.metadata` so `alembic revision --autogenerate` will pick up future models
  automatically once they're added.

## Tables

| Table | Purpose | Added by |
|---|---|---|
| `alembic_version` | Alembic's own migration-tracking table | created automatically the first time `alembic upgrade head` runs against a fresh database |

No application tables exist yet. There are zero migration scripts in `backend/alembic/versions/`.

## Local setup

```bash
cp .env.example .env
docker compose up -d
cd backend && cp .env.example .env
uv run alembic upgrade head
```

Verified in Stage 0: `docker compose up -d` → `alembic upgrade head` connects successfully and
creates `alembic_version` (confirmed via `docker exec legal_dms_postgres psql -U legal_dms -d
legal_dms_dev -c "\dt"`).

## Future tables

None designed yet — out of scope for Stage 0 by design (no Matter/Client/Document/User models).
The first migration of Stage 1+ should add whatever the first business feature needs and update
this document with the table, its relationships, and indexes at that time.
