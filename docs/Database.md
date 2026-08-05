# Database

## Status: complete production-ready schema, zero business logic (Stage 2)

Stage 2 built the **complete database schema** for the entire eventual application — 49 tables
across 11 domain sections plus a seed-data migration — as pure schema: SQLAlchemy models, Alembic
migrations, constraints, indexes, and lookup data. **No repositories, services, or API routes are
wired to any of these tables.** `SqlAlchemyRepository[ModelT]` (built in Stage 1) can already work
against any of them generically, without any Stage-2-specific repository code — that wiring is
explicitly future-stage work.

- **Engine**: PostgreSQL 16 (Alpine), provisioned locally via [`docker-compose.yml`](../docker-compose.yml).
- **ORM**: SQLAlchemy 2.x async, typed declarative models (`Mapped[...]`/`mapped_column`),
  declarative `Base` in
  [`infrastructure/database/base.py`](../backend/src/app/infrastructure/database/base.py).
- **Session management**: lazily-constructed, cached async engine + `async_sessionmaker` in
  [`infrastructure/database/session.py`](../backend/src/app/infrastructure/database/session.py),
  exposed to routes via the `DBSessionDep` FastAPI dependency.
- **Migrations**: Alembic, async template, in `backend/alembic/`. `env.py` pulls `DATABASE_URL`
  from the app's own validated `Settings` and imports
  `app.infrastructure.persistence.models` so `Base.metadata` — and therefore
  `alembic revision --autogenerate` — sees every table.
- **Models location**: `backend/src/app/infrastructure/persistence/models/`, one module per domain
  section (see the table list below). These are **persistence-layer ORM models, not domain
  entities** — see [ADR/0008](../ADR/0008-persistence-models-not-domain-entities.md). No
  `relationship()` navigation is declared anywhere; it's a query-ergonomics convenience deliberately
  left for the first feature that needs a specific traversal.

## Conventions

- **UUID primary keys** everywhere (`uuid4` default), **`TIMESTAMPTZ`**
  (`DateTime(timezone=True)`) for every timestamp.
- **Naming convention** set once on `Base.metadata` (`NAMING_CONVENTION` in
  `infrastructure/database/base.py`) so every constraint/index name is generated automatically and
  consistently — see [ERD.md](ERD.md#naming-conventions) for the exact patterns.
- **`AuditMixin`** (`infrastructure/persistence/models/mixins.py`): `created_at`, `updated_at`,
  `deleted_at` (soft delete), `created_by`/`updated_by` (FK → `users.id`, nullable), `version`
  (optimistic locking counter). Applied to every table representing a substantive, audited business
  record (`users`, `roles`, `permissions`, `clients`, `properties`, `matters`, `documents`,
  `document_templates`, `invoices`, `payments`, `receipts`, `tasks`, `appointments`,
  `client_contacts`, `addresses`). **Not** applied to lookup/type tables (`matter_types`,
  `document_types`, `payment_methods`, geography tables, ...), immutable records
  (`document_versions`), or system/config tables with their own simpler timestamp shape
  (`application_settings`, `feature_flags`, `background_jobs`, `system_events`, ...) — judged
  case-by-case per table, consistent throughout all 11 sections.
- **`OptimisticLockMixin`**: `__mapper_args__ = {"version_id_col": version}` via `@declared_attr`
  (deferred until the table is fully built). Turned on only where concurrent edits are realistic:
  `matters`, `documents`, `clients`. (`properties` and other `AuditMixin` tables have the `version`
  *column* from the mixin but don't enforce it via `OptimisticLockMixin` unless concurrent-edit risk
  was judged real enough to warrant it — see each model file's class bases.)
- **Soft delete**: `deleted_at IS NULL` convention. No ORM-level global filter is added — that's
  query/repository behavior, out of scope for a schema-only stage; documented here as a convention
  future repositories must apply.
- **Lookup/type tables, not native enums**: `matter_types`, `matter_statuses`, `document_types`,
  `payment_methods`, etc. are real tables (data-driven, extensible without a migration), not
  Postgres enum types.
- **Polymorphic references** (`entity_type` + `entity_id`, no FK): `workflow_history`,
  `activity_logs`, `audit_logs`, `qr_code_records`, `ai_requests`. See
  [ERD.md](ERD.md#polymorphic-references-entity_type--entity_id-no-fk) for the full rationale and
  trade-off.
- **File storage**: the database **never** stores document content — `file_storage_records` holds
  only metadata (path, hash, checksum, size, provider, version, retention policy), the DB-metadata
  companion to Stage 1's `FileStorage`/`StoredFile` port.

## Tables (49, across 11 sections + 1 seed migration)

See [ERD.md](ERD.md) for the diagram and full section-by-section list with descriptions. Full
column-level detail lives in the model source files themselves
(`backend/src/app/infrastructure/persistence/models/*.py`), each with a module docstring explaining
its section's design choices.

| Section | Module | Tables |
|---|---|---|
| 1. Identity & Access | `identity.py` | `users`, `roles`, `permissions`, `user_roles`, `role_permissions` |
| 2. Geography | `geography.py` | `countries`, `states`, `districts`, `talukas`, `villages` |
| 3. Clients | `client.py` | `addresses`, `clients`, `client_contacts` |
| 4. Properties | `property.py` | `properties`, `property_owners` |
| 5. Matters & Workflow | `matter.py`, `workflow.py` | `matter_types`, `matter_statuses`, `matters`, `workflow_definitions`, `workflow_states`, `workflow_history` |
| 6. Documents | `document.py`, `storage.py` | `document_types`, `document_templates`, `document_variables`, `documents`, `document_versions`, `file_storage_records` |
| 7. Financial | `financial.py` | `payment_methods`, `invoices`, `payments`, `receipts` |
| 8. Activity, Audit & Notifications | `activity.py` | `activity_logs`, `audit_logs`, `notifications` |
| 9. Scheduling & Tags | `scheduling.py` | `tasks`, `appointments`, `tags`, `matter_tags` |
| 10. OCR, QR & Backups | `storage.py` | `ocr_jobs`, `ocr_results`, `qr_code_records`, `backups` |
| 11. System, Config, AI & Plugins | `system.py` | `application_settings`, `feature_flags`, `ai_requests`, `ai_responses`, `plugin_registry`, `background_jobs`, `system_events` |

Confirmed live: `SELECT count(*) FROM information_schema.tables WHERE table_schema='public'` (minus
`alembic_version`) = **49**.

## Migrations

One Alembic revision per section (11 schema revisions) plus one seed-data revision, applied in
order:

| Revision | Section |
|---|---|
| `4c661976b322` | Identity & Access |
| `198cbb4bbeb6` | Geography |
| `ac077004afeb` | Clients |
| `7789f56da7f9` | Properties |
| `c52ee7c83023` | Matters & Workflow |
| `9a68ef4298ae` | Documents & File Storage |
| `cf6b0519b74c` | Financial |
| `40ce220538c1` | Activity, Audit & Notifications |
| `07150e442816` | Scheduling & Tags |
| `ac2214fdce03` | OCR, QR & Backups |
| `5c13f11da784` | System, Config, AI & Plugins |
| `9963e15f2752` (head) | Seed lookup data |

Every revision was generated via `alembic revision --autogenerate`, hand-reviewed (partial/GIN
indexes and check constraints aren't autogenerate-detected), formatted with `black` + `ruff check
--fix`, applied to a live Postgres container, and verified reversible
(`alembic downgrade -1` → `alembic upgrade head`) before being committed. Full chain reversibility
(`alembic downgrade base` → `alembic upgrade head`) was also verified at the end of Stage 2.

## Seed data

Migration `9963e15f2752` populates lookup/reference tables only (`op.bulk_insert` against
migration-local `sa.table()` shadows, not the ORM models — see the migration's own docstring for
why). Downgrade deletes exactly what upgrade inserted.

| Table | Rows | Content |
|---|---|---|
| `countries` | 1 | India |
| `states` | 36 | All Indian states + union territories |
| `districts` | 33 | Gujarat's districts only (this system's target practice) — other states' districts are added when a real need arises |
| `roles` | 6 | Administrator, Advocate, Paralegal, Clerk, Accountant, Read Only |
| `permissions` | 18 | `<resource>:<action>` codes across matters/clients/properties/documents/financial/administration/reports, matching `AuthorizationService.require_permission()`'s string convention |
| `matter_types` | 8 | Sale Deed, Registration, Title Search, Mortgage, Lease, Will/Succession, Partition, POA |
| `matter_statuses` | 6 | Open, In Progress, Pending Review, On Hold, Closed*, Cancelled* (*terminal) |
| `workflow_definitions` / `workflow_states` | 1 / 6 | A starter `matter_lifecycle` definition mirroring the matter statuses above |
| `document_types` | 10 | Sale Deed, Agreement to Sell, POA, Title Search Report, Encumbrance Certificate, Mutation Extract, Property Tax Receipt, Identity Proof, Court Order, Affidavit |
| `payment_methods` | 6 | Cash, Cheque, Bank Transfer, UPI, Card, Demand Draft |
| `application_settings` | 6 | `app.name`, `app.timezone`, `app.date_format`, `app.default_currency`, `app.max_upload_size_mb`, `app.session_timeout_minutes` |
| `feature_flags` | 5 | `ocr_pipeline`, `ai_drafting`, `e_signature`, `client_portal`, `cloud_sync` — all disabled (no corresponding feature exists yet) |

Deliberately **not** seeded: `role_permissions` (which permissions each role gets is an
authorization business decision with no consuming feature yet) and `users` (no auth exists to log
in with).

## Deviations from the approved plan (documented, not hidden)

- **`file_storage_records` created in Section 6, not Section 10.** `document_templates` and
  `document_versions` both need it — a cross-section dependency the original grouping didn't
  account for.
- **`documents.current_version_id` dropped entirely**, rather than adding it and fighting a
  circular FK with `document_versions`. "Latest version" is derived via
  `ORDER BY version_number DESC LIMIT 1` — no proven query need for the denormalized pointer yet.
- **`CheckConstraint` naming pitfall**: passing a *full* name (e.g. `"ck_addresses_address_type"`)
  double-prefixes under the naming convention (`ck_addresses_ck_addresses_address_type`). Fix:
  always pass a short logical name (`"address_type"`) and let the convention build the rest. This
  does **not** apply to `Index(name=...)` — explicit index names are used as-is.
- **`AuditLog.metadata` renamed to `audit_metadata`** at the Python attribute level (DB column
  stays `"metadata"` via `mapped_column("metadata", ...)`) — `metadata` as an attribute name would
  shadow SQLAlchemy's own `Base.metadata`.

## Local setup

```bash
cp .env.example .env
docker compose up -d
cd backend && cp .env.example .env
uv run alembic upgrade head
```

Verify: `docker exec legal_dms_postgres psql -U legal_dms -d legal_dms_dev -c "\dt"` should list all
49 application tables plus `alembic_version`.

## Testing

Schema-level integration tests (constraints, FKs, defaults, soft-delete/optimistic-locking
behavior, seed row counts) live in `backend/tests/integration/test_*_models.py` and
`test_seed_data.py`, one file per section, run against the real migrated schema via a shared
`db_session` pytest fixture. No repository, service, or API-route tests exist yet for these tables
— that's future-stage work once a feature is actually wired to them.

## Future tables

None currently planned beyond the 49 above. The schema was designed to support Matter/Client/
Property Management, Document Automation, OCR, QR, AI features, Payments, and Plugins "without
major redesign" per the charter — the next stage to touch this schema should be the one that wires
a real repository/service to it, not a schema redesign.
