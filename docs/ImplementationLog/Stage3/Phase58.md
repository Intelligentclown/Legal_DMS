------------------------------------------------

# Stage 3 – Phase 58

Status: Awaiting Comprehensive / Risk Tier 1 Independent QA

Started: 2026-10-28

Completed:

Related Tasks: T184

Related ADRs: ADR-0021; ADR-0022; ADR-0024; ADR-0025; ADR-0037

Git Commit: 07fba07f964f2fd6986f623824178baa30ef853d (backend integration); b82779dd68dbf0f060fee404b805ce029d6226e1 (frontend)

Pull Request: [#403](https://github.com/Intelligentclown/Legal_DMS/pull/403)

Release:

------------------------------------------------

## Objective

Implement the backend portion of T184: tenant-scoped server-side Property-register search on the
existing paginated `GET /api/v1/properties` endpoint, while preserving its response contract and
the canonical Matter–Property association boundary.

Complete the corresponding Matter workspace integration so operators can search the tenant-scoped
Property register without page-by-page manual navigation.

## Tasks Implemented

- Added optional `search` handling for `survey_number`, `sub_division_number`, and
  `registration_number`.
- Applied the same organization-scoped SQLAlchemy predicate to list and count queries before
  pagination, with whitespace-only input normalized to the existing unfiltered behavior.
- Added PostgreSQL-backed route coverage for off-page search, all three fields, filtered totals,
  empty-search compatibility, tenant isolation, and the existing `properties:read` gate.
- Replaced the Matter workspace's current-page-only filter with server-side search while preserving
  the canonical UUID link/unlink flows.
- Added query-keyed loading, no-results, error/retry, filtered-pagination, selection-reset and
  stale-response behavior to the Property selector.

## Files Modified

- `backend/src/app/application/interfaces/property_repository.py`
- `backend/src/app/application/property_service.py`
- `backend/src/app/infrastructure/persistence/sqlalchemy_property_repository.py`
- `backend/src/app/presentation/api/v1/properties.py`
- `backend/tests/integration/test_property_routes.py`
- `docs/ImplementationLog/Stage3/Phase58.md`
- `frontend/src/infrastructure/api/propertiesApi.ts`
- `frontend/src/infrastructure/api/propertiesApi.test.ts`
- `frontend/src/presentation/pages/MatterDetailPage.tsx`
- `frontend/src/presentation/pages/MatterDetailPage.test.tsx`

## Tests Added

- `test_list_search_filters_before_pagination_and_stays_tenant_scoped` verifies a result beyond
  an unfiltered first page; survey, subdivision, and registration matching; filtered pagination
  metadata; organization isolation; empty/whitespace compatibility; and `properties:read` denial.
- `propertiesApi.test.ts` verifies `search` query forwarding and unfiltered empty-search compatibility.
- `MatterDetailPage.test.tsx` covers off-page server results, all three identifiers, pagination
  reset and totals, loading, no-match, retry, stale responses, selection consistency, idempotent
  linking, unlinking, and mutation permission errors.

## Test Results

- `uv run ruff check src tests` — passed.
- `uv run black --check src tests` — passed.
- `uv run pytest tests/unit/test_property_service.py tests/integration/test_property_routes.py tests/integration/test_matter_property_routes.py` — **16 passed, 1 warning** in 11.34 seconds against isolated PostgreSQL 16.
- `tests/integration/test_matter_property_tenant_integrity_foundation.py` was started twice but
  could not complete within this executor's 30-second command window; it is not claimed as passed.
- The complete backend suite was not run in this implementation assignment and is not certified.
- `frontend: npm run test` — **196 passed** across 22 files.
- `frontend: npm run lint` — passed with 0 errors and 4 pre-existing Fast Refresh warnings.
- `frontend: npm run format:check` — passed.
- `frontend: npm run build` — passed.
- Integrated backend rerun: Ruff and Black passed; the focused Property/Matter–Property command
  passed **16 tests** (14 warnings).
- Native Windows Electron changed-path verification is **pending**. A browser-only result was not
  substituted: the default port was occupied by an unrelated runtime and an isolated alternate-port
  Electron session could not be launched through the available process controls.

## Design Decisions

- Kept filtering in the existing repository layer. SQLAlchemy constructs the predicate and binds
  the search value; the route remains responsible only for API input and pagination.
- The organization predicate is retained in both queries, then the optional three-column `ILIKE`
  predicate is added, so matching never expands the authenticated tenant boundary.
- No schema, migration, Matter–Property, UUID-identity, or permission-contract change was made.
- The Matter page relies on existing `useAsyncResource` request-key cancellation behavior instead
  of adding a selector-specific asynchronous state abstraction.

## Problems Encountered

- The default local database URL pointed to port 5432, while the available isolated PostgreSQL 16
  container was bound to host port 5433. The focused tests then passed after using the container's
  configured connection without modifying repository configuration.
- The long-running T155 tenant-integrity migration suite exceeds this executor's 30-second command
  window; its completion is deferred to independent QA.
- Native Electron verification requires an isolated runtime and authenticated operator workflow;
  it remains pending for Independent QA rather than inferred from browser tests or a build.

## Deferred Work

- Independent QA must execute the complete relevant backend suite, including the T155 integrity
  regression, before any protected merge decision.
- Independent QA must perform AC-10's native Windows Electron search-and-link workflow.

## Future Considerations

- Search uses the existing indexed field model and introduces no new database index or migration;
  any future search-ranking, normalization, or indexing work requires separate authorization.
- No new Property editing, Party, taxonomy, government, finance, legacy-migration or schema scope
  was introduced.

## Reviewer Checklist

☑ Architecture preserved

☑ Existing design patterns followed

☑ Tests added

□ Existing tests pass

☑ Documentation updated

□ ADR updated (if required)

□ AI_BOOTSTRAP updated (if required)

□ PROJECT_STATE updated (if required)

☑ No unrelated refactoring

☑ No scope creep

☑ Ready for QA

Notes: `Existing tests pass` remains unchecked because the complete backend suite and the
long-running T155 tenant-integrity regression are not certified in this assignment. ADR,
AI_BOOTSTRAP, and PROJECT_STATE changes are not required by this bounded implementation.
Native Windows Electron evidence remains pending for Independent QA.

## QA Decision

□ Approved

□ Approved with comments

□ Rework required
