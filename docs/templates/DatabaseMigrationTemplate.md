# Database Migration Documentation Template

**Purpose:** The skeleton for documenting a new Alembic migration in
[docs/Database.md](../Database.md) and [docs/ERD.md](../ERD.md), matching the section-by-section
shape Stage 2's 11 schema sections already use. **This template documents a migration — it does not
generate one.** The actual migration file is source code
(`backend/alembic/versions/<revision>_<slug>.py`, produced by `alembic revision --autogenerate`)
and is out of scope for anyone working from `docs/templates/` under a documentation-only
instruction; this template is for the accompanying documentation only.

**When to use:** Any time a new Alembic migration is authored — a new table, a new column, an index
change, a data migration — whether it's a new domain section (like Stage 2's 11) or a single-table
change to existing schema in a future stage.

**Copy destination:** Add a new row to [docs/Database.md](../Database.md)'s "Tables" section table
and, for a new domain section specifically, a new numbered entry in
[docs/ERD.md](../ERD.md)'s section list. For a substantial new section, consider a dedicated
subsection in both files using the shape below rather than only a table row.

---

## Migration: \<short name, e.g. "Matter Documents Attachments"\>

- **Revision ID:** \<from the generated migration file's `revision` value\>
- **Down revision:** \<the migration this one builds on — confirms a single, unforked chain; see
  [IMPLEMENTATION_QUEUE.md](../../IMPLEMENTATION_QUEUE.md) finding F6 for why this matters\>
- **Date:** YYYY-MM-DD
- **Stage:** Which numbered stage (or post-stage addition) this migration belongs to.

### Purpose

What business or technical need this migration serves — link to the
[docs/FeatureRegistry.md](../FeatureRegistry.md) entry it supports, if any.

### Tables Added / Modified

List each table touched, and for each: whether it's new or modified, and a one-line purpose (match
[docs/Database.md](../Database.md)'s existing per-table brevity — full column detail lives in the
model source file's own docstring, not duplicated here).

### Schema Details

- **Primary key / ID strategy:** confirm UUID PK convention followed (see
  [docs/Database.md](../Database.md)'s "Conventions" section) or state the deviation and why.
- **Timestamps:** confirm `TIMESTAMPTZ` convention followed.
- **Mixins applied:** `AuditMixin` / `OptimisticLockMixin` / neither — and why, following this
  project's existing case-by-case judgment convention (substantive audited business record vs.
  lookup/type table vs. immutable record vs. simple system/config table).
- **Constraints & indexes:** check constraints, foreign keys, unique constraints, and any
  performance-driving index (e.g. a GIN full-text index) — name what each protects or accelerates,
  not just that it exists.
- **Naming convention compliance:** confirm constraint/index names were left to the project-wide
  `naming_convention` rather than hand-specified, per [docs/Database.md](../Database.md)'s
  documented `CheckConstraint(name=...)` footgun (short logical name only, not the full generated
  name).
- **Polymorphic references:** if this migration adds an `entity_type`+`entity_id` pair with no FK,
  say so explicitly and link to [docs/ERD.md](../ERD.md#polymorphic-references-entity_type--entity_id-no-fk)'s
  rationale for the trade-off, rather than letting it look like an oversight.

### Relationships

Which existing tables this migration's new/modified tables reference (FKs), and whether any
`relationship()` ORM navigation was added — this project's default is no `relationship()` navigation
until a feature needs a specific traversal (see [ADR/0008](../../ADR/0008-persistence-models-not-domain-entities.md)).

### Seed Data

Whether this migration includes or requires accompanying seed data — if so, link to the seed
migration or describe what was seeded and why.

### Rollback Verified

- [ ] `alembic downgrade -1` tested and confirmed clean
- [ ] Full chain (`alembic downgrade base` → `alembic upgrade head`) still passes after this
      migration was added

### Testing

Which `tests/integration/test_*.py` file covers this migration's tables — name what's actually
asserted (constraints reject invalid data, FKs navigate correctly, soft-delete/audit columns behave
as expected — match [docs/ProjectStatus.md](../ProjectStatus.md)'s existing precedent for describing
test coverage specifically, not just "has tests").

### Related ADRs

Any architecture decision records this migration's design relies on.

### Documentation Updated

- [ ] [docs/Database.md](../Database.md)
- [ ] [docs/ERD.md](../ERD.md)
- [ ] [docs/ModuleRegistry.md](../ModuleRegistry.md) (new model module row, if applicable)
