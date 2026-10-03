------------------------------------------------

# Stage 3 – Phase 38

Status: In Progress — implementation complete; awaiting Independent QA.

Started: 2026-10-03

Completed:

Related Tasks: T149

Related ADRs: ADR-0043, ADR-0020, ADR-0021, ADR-0022, ADR-0029, ADR-0037

Git Commit:

Pull Request:

Release:

------------------------------------------------

## Objective

Implement the bounded authenticated pre-acceptance application surface from
prospective Party/Enquiry intake through QuotationRevision issuance, consuming
the T148/T150 persistence foundation without changing it.

## Tasks Implemented

- Added Organization-scoped Enquiry list/get/create/update and explicit
  canonical-Party link operations.
- Added nested Quotation create/list/get and QuotationRevision create/list/get
  routes beneath the Enquiry hierarchy.
- Added proposal-snapshot creation/retrieval and one-time issuance using the
  existing T150 paired provenance transition.
- Added parent-Quotation `SELECT ... FOR UPDATE` allocation before determining
  the next revision ordinal; repositories only flush and request-scoped
  ADR-0020 ownership remains the sole commit boundary.

## Files Modified

- `backend/src/app/application/enquiry_service.py`
- `backend/src/app/application/interfaces/enquiry_repository.py`
- `backend/src/app/infrastructure/persistence/sqlalchemy_enquiry_repository.py`
- `backend/src/app/presentation/api/v1/enquiries.py`
- `backend/src/app/presentation/api/v1/router.py`
- `backend/tests/unit/test_enquiry_service.py`
- `backend/tests/integration/test_t149_enquiry_quotation_routes.py`
- `docs/ImplementationLog/Stage3/Phase38.md`

## Tests Added

- Unit coverage for prospect evidence, canonical Party linking, bounded
  mutations, hierarchy rejection, ordinal sequence, and one-time issuance.
- Disposable-PostgreSQL route coverage for RBAC, RLS/non-enumeration,
  pagination, Party linkage, concurrent revision allocation, and T150 issue
  transition.

## Test Results

- `uv run pytest tests/unit/test_enquiry_service.py -q`: 3 passed.
- `uv run pytest tests/unit -q`: 342 passed, 60 existing dependency warnings.
- `uv run pytest tests/integration/test_t149_enquiry_quotation_routes.py -q`:
  2 passed.
- `uv run pytest tests/integration/test_t148_enquiry_quotation_postgres.py -q`:
  3 passed.
- `uv run pytest tests/integration/test_operational_fresh_provenance.py -q`:
  7 passed.
- `uv run ruff check src tests alembic`: passed.
- `uv run black --check src tests alembic`: passed.
- Application import/OpenAPI smoke: passed; Enquiry routes loaded.
- `python scripts/governance_validate.py --report`: passed; Required ADRs
  `[12,15,16,17,20]` remain unresolved.

## Design Decisions

- A request never accepts Organization identity from its payload; it derives
  tenant identity and actor provenance from authenticated context.
- The T150 trigger is the final issuance integrity backstop. The service
  rejects an already-issued revision before attempting the prohibited update.
- No Acceptance, Matter, Client, File, financial, status or vocabulary surface
  is present in this batch.

## Problems Encountered

- PostgreSQL route coverage exposed an expired server-generated `updated_at`
  attribute after Enquiry flush. The scoped repository explicitly refreshes
  the Enquiry before presentation serialization; no transaction behavior was
  changed.

## Deferred Work

- Acceptance and Acceptance-to-Matter conversion remain explicitly excluded.
- Subsequent commercial content is represented by another revision, never an
  update to existing evidence.

## Future Considerations

- Independent QA must inspect the exact immutable implementation candidate,
  especially the PostgreSQL lock and T150 issuance behavior, before any
  documentation synchronization or merge.

## Reviewer Checklist

☑ Architecture preserved
☑ Existing design patterns followed
☑ Tests added
☑ Existing tests pass
☑ Documentation updated
□ ADR updated (if required) — no architecture change; ADR-0043 is unchanged.
□ AI_BOOTSTRAP updated (if required) — no standing-process change.
□ PROJECT_STATE updated (if required) — implementation is not Done and
project-wide synchronization belongs after QA.
☑ No unrelated refactoring
☑ No scope creep
☑ Ready for QA

## QA Decision

□ Approved
□ Approved with comments
□ Rework required
