------------------------------------------------

# Stage 3 – Phase 39

Status: In Progress — implementation complete; awaiting Independent QA.

Started: 2026-10-03

Completed:

Related Tasks: T152

Related ADRs: ADR-0043, ADR-0020, ADR-0021, ADR-0022, ADR-0039, ADR-0042

Git Commit:

Pull Request:

Release:

------------------------------------------------

## Objective

Implement the authorized, authenticated bridge from one issued
QuotationRevision through immutable Acceptance to one Party-canonical Matter,
without changing existing persistence or transaction ownership.

## Tasks Implemented

- Added a bounded AcceptanceService and route under the existing Enquiry /
  Quotation / QuotationRevision hierarchy.
- Serialized conversion with PostgreSQL `SELECT ... FOR UPDATE` on the
  Organization-scoped Enquiry, then re-read existing Acceptance state.
- Created Matters only through the existing Matter service with
  `client_id=NULL` and exactly the Enquiry's canonical Party as the `client`
  MatterParty.
- Added deterministic SHA-256 request fingerprints over exact revision and
  Matter creation facts, with same-key replay and conflict behavior.
- Preserved request-scoped final commit/rollback ownership: repositories and
  services flush only.

## Files Modified

- `backend/src/app/application/acceptance_service.py`
- `backend/src/app/application/interfaces/enquiry_repository.py`
- `backend/src/app/infrastructure/persistence/sqlalchemy_enquiry_repository.py`
- `backend/src/app/presentation/api/v1/enquiries.py`
- `backend/tests/integration/test_t149_enquiry_quotation_routes.py`
- `docs/ImplementationLog/Stage3/Phase39.md`

## Tests Added

- PostgreSQL API coverage for exact issued-revision acceptance, immutable
  provenance, Party-canonical Matter/MatterParty outcome, no Client/File
  manufacture, and tenant non-enumeration.
- PostgreSQL API coverage for same-key replay, fingerprint conflict,
  already-converted conflict, canonical-Party prerequisite, dual RBAC, and
  concurrent conversion serialization yielding exactly one Matter.

## Test Results

- `cd backend && uv run pytest tests/integration/test_t149_enquiry_quotation_routes.py -q`:
  4 passed.
- `cd backend && uv run pytest tests/unit -q`: 342 passed, 60 pre-existing
  dependency warnings.
- `cd backend && uv run ruff check src tests alembic`: passed.
- `cd backend && uv run black --check src tests alembic`: passed.
- `cd backend && uv run pytest -x -q`: blocked by the pre-existing local
  `legal_dms_dev` database not being migrated (`activity_logs` relation is
  absent); the isolated T152 disposable PostgreSQL suite passed.

## Design Decisions

- T150's persisted paired `issued_at`/`issued_by` facts are the only
  acceptance eligibility predicate. No status or vocabulary is introduced.
- Existing Acceptance uniqueness constraints remain the final integrity
  backstop; the Enquiry row lock makes competing decisions deterministic.
- The existing Matter contract continues to require caller-supplied Matter
  facts; conversion invents no numbering, type, status, or File default.

## Problems Encountered

- The local shared regression database is behind the current schema and could
  not run the full integration suite. Isolated fresh-install PostgreSQL
  coverage was used for T152 behavior and concurrency instead.

## Deferred Work

- Independent QA, documentation synchronization, and merge remain separate
  commissioned roles.
- No broader workflow/status, Client convergence, File creation, or financial
  behavior was added.

## Future Considerations

- Independent QA should inspect the exact candidate's Enquiry lock/recheck,
  request-transaction behavior, and fresh-install PostgreSQL concurrency test.

## Reviewer Checklist

☑ Architecture preserved
☑ Existing design patterns followed
☑ Tests added
☑ Existing tests pass
☑ Documentation updated
□ ADR updated (if required) — ADR-0043 remains unchanged and Proposed.
□ AI_BOOTSTRAP updated (if required) — no standing-process change.
□ PROJECT_STATE updated (if required) — post-QA synchronization belongs to the
Documentation Manager.
☑ No unrelated refactoring
☑ No scope creep
☑ Ready for QA

## QA Decision

□ Approved
□ Approved with comments
□ Rework required
