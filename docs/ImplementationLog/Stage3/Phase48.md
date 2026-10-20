# Phase 48 — T167 Backend Test Infrastructure Reliability

**Task:** T167 — Backend Test Infrastructure Reliability and Full-Suite Certification  
**Started:** 2026-10-20  
**Status:** Stopped pending scope direction  
**Protected baseline:** `ffddace12fb7bc5347fbacfec2afc52fba6a6382`

## Scope

Implement only the authorized remediation for QA-T166-NB-01 and QA-T165-ADV-01, then attempt a complete isolated backend-suite certification. No production audit logic, migrations, schema, API, RLS/RBAC, or ADR state was changed.

## Files Modified

- `backend/alembic/env.py` — preserve already-registered application loggers when Alembic configures its own loggers in-process.
- `backend/tests/support/synthetic_migration.py` — provide the existing fixture Organization to `Property` on current-schema fixture paths while retaining the pre-finalization legacy path.
- `backend/tests/integration/test_alembic_logging.py` — regression coverage for real in-process migration initialization, continued `app.audit` emission, and Alembic CLI current-head behavior.

## Verification

- `python -m pytest tests/integration/test_alembic_logging.py -q`: **1 passed, 1 warning** (6.03s).
- `python -m ruff check src tests alembic`: passed.
- `python -m black --check src tests alembic`: **332 files unchanged**.
- `python -m alembic heads`: sole head **`b155caa6d4e1`**.
- Complete unfiltered isolated run: a uniquely named PostgreSQL 16.11 database was created, migrated with `python -m alembic upgrade head`, used through `DATABASE_URL`/`APP_DATABASE_URL`, then destroyed with `DROP DATABASE ... WITH (FORCE)`. `python -m pytest tests -q` completed with **897 passed, 45 failed, 87 warnings, 0 skipped, 0 errors** in **563.51s**.

## Findings and STOP Condition

The Property correction allows the current-schema fixture to progress to a separate pre-existing defect: `seed_client_graph()` creates `Matter` with a null mandatory `organization_id`. That defect accounts for the legacy-client migration failures and was not part of T167's explicit authorized correction. The isolated run also reports pre-existing model/RLS/seed-data expectation failures. Full-suite certification is therefore not achieved. Fixing those independent failures would exceed the bounded T167 remediation; no such changes were made.

## Reviewer Checklist

- [x] Architecture — no architecture or ADR decision changed.
- [x] Scope — only the two authorized infrastructure surfaces and regression coverage changed.
- [x] Security — no audit-event business logic, RLS, RBAC, or tenant enforcement relaxed.
- [x] Migrations — no revision or lineage changed; head remains `b155caa6d4e1`.
- [x] Tests — focused regression, lint, formatting, migration head, and an unfiltered isolated suite were executed.
- [x] Failure disclosure — all certification-blocking failures are recorded above; none are hidden by selection or fail-fast execution.
- [ ] Full-suite certification — not achieved: 45 isolated-suite failures remain outside the authorized correction.
- [x] Documentation ownership — this implementation record is the only project documentation updated.
- [ ] QA Decision — reserved for separately commissioned Independent QA.

## QA Decision

- [ ] Approved
- [ ] Approved with comments
- [ ] Rework required
