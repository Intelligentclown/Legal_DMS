------------------------------------------------

# Stage 3 – Phase 36

Status: In Progress — implementation complete; awaiting Independent QA.

Started: 2026-09-30

Completed:

Related Tasks: T148

Related ADRs: ADR-0043, ADR-0021, ADR-0022, ADR-0023, ADR-0037, ADR-0039

Git Commit:

Pull Request:

Release:

------------------------------------------------

## Objective

Establish T148's tenant-safe persistence foundation for Enquiry, Quotation,
QuotationRevision and Acceptance without implementing a pre-engagement API or
Acceptance-to-Matter conversion.

## Tasks Implemented

- Added persistence models and one successor Alembic migration for the four
  pre-engagement tables.
- Added mandatory direct Organization ownership, composite same-Organization
  foreign keys, technical UUIDs, revision ordinal uniqueness, Acceptance
  provenance/idempotency constraints, and one-Enquiry/one-Matter integrity.
- Added default-deny ENABLE/FORCE RLS policies for every new tenant table.
- Added immutable-evidence triggers for quotation revisions and acceptances,
  plus a database trigger requiring an Enquiry Party before Acceptance.
- Added `enquiries:read`, `enquiries:write`, `quotations:read`,
  `quotations:write`, and `quotations:accept` seed/grant support.
- Advanced the ADR-0037 operational-fresh supported revision.

## Files Modified

- `backend/src/app/infrastructure/persistence/models/enquiry.py`
- `backend/src/app/infrastructure/persistence/models/__init__.py`
- `backend/alembic/versions/e148c0f5a8b2_enquiry_quotation_acceptance_foundation.py`
- `backend/src/app/infrastructure/cli/fresh_install_provenance.py`
- `backend/tests/unit/test_t148_enquiry_quotation_foundation.py`
- `backend/tests/integration/test_t148_enquiry_quotation_postgres.py`
- `backend/tests/integration/test_operational_fresh_provenance.py`
- `docs/ImplementationLog/Stage3/Phase36.md`

## Tests Added

- `test_t148_enquiry_quotation_foundation.py`: model-level contract coverage
  for bounded prospect evidence, tenant hierarchy FKs, revision ordinal,
  Acceptance exact-revision/Matter provenance, and idempotency constraints.
- Updated operational-fresh provenance integration coverage to expect the new
  head revision.
- `test_t148_enquiry_quotation_postgres.py`: disposable-PostgreSQL verification
  of ENABLE/FORCE RLS and same-tenant/cross-tenant enquiry visibility.

## Test Results

- `uv run pytest tests/unit/test_t148_enquiry_quotation_foundation.py -q`: 3 passed.
- `uv run pytest tests/unit -q`: 339 passed, 60 existing dependency warnings.
- `uv run pytest tests/integration/test_t148_enquiry_quotation_postgres.py -q`:
  1 passed.
- Disposable PostgreSQL fresh-chain smoke: reached sole head `e148c0f5a8b2`.
- Disposable PostgreSQL empty-foundation downgrade: succeeded to `cdcfd7df5fde`.
- `uv run ruff check src tests alembic`: passed.
- `uv run black --check src tests alembic`: passed (313 files unchanged).
- Full `uv run pytest -q` was initiated twice, including once before changes;
  the execution transport returned only partial progress rather than a final
  result. It is therefore not represented as a completed full-suite result.

## Design Decisions

- Proposal facts are stored as an immutable JSONB snapshot, preserving the
  exact relied-upon proposal without inventing ledger, workflow, or
  configurable-vocabulary policy.
- Acceptance's composite keys prove the selected Quotation belongs to the
  Enquiry and the exact revision belongs to that Quotation. A separate trigger
  fails closed if the Enquiry has no canonical Party.
- Evidence-bearing rows reject UPDATE and DELETE. This is a bounded integrity
  mechanism, not a general deletion/retention policy.

## Problems Encountered

- The local test transport did not return a final result for the full mixed
  integration suite before its execution window ended. Focused unit and
  disposable-database migration verification completed normally.

## Deferred Work

- Application CRUD, issuing/eligibility state semantics, Acceptance
  orchestration, Matter/MatterParty creation, audit/activity integration, and
  API/frontend surfaces remain deferred to separately authorized work.

## Future Considerations

- Independent QA should run the complete PostgreSQL integration suite and
  directly exercise cross-Organization rejection, RLS visibility, trigger
  immutability, and evidence-bearing downgrade refusal on the exact PR head.

## Reviewer Checklist

☑ Architecture preserved
☑ Existing design patterns followed
☑ Tests added
□ Existing tests pass — unit suite passed; full mixed suite final result was not returned by the execution transport.
☑ Documentation updated
□ ADR updated (if required) — no architecture change; ADR-0043 is unchanged.
□ AI_BOOTSTRAP updated (if required) — no standing-process change.
□ PROJECT_STATE updated (if required) — implementation is not Done and project-wide synchronization belongs after QA.
☑ No unrelated refactoring
☑ No scope creep
□ Ready for QA — pending a complete integration-suite result.

## QA Decision

□ Approved
□ Approved with comments
□ Rework required
