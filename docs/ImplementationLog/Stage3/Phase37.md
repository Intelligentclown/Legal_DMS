------------------------------------------------

# Stage 3 – Phase 37

Status: In Progress — implementation complete; awaiting Independent QA.

Started: 2026-10-02

Completed:

Related Tasks: T150

Related ADRs: ADR-0043, ADR-0037

Git Commit:

Pull Request:

Release:

------------------------------------------------

## Objective

Correct the T148 persistence trigger so an otherwise immutable
QuotationRevision can be issued exactly once without broadening draft mutation
or weakening Acceptance evidence immutability.

## Tasks Implemented

- Generated one successor migration from the verified T148 sole head.
- Replaced only the QuotationRevision trigger with a dedicated trigger function
  that permits the atomic NULL/NULL to non-NULL/non-NULL issuance transition and
  rejects every non-issuance field change, any partial transition, re-issuance,
  reversal, and deletion.
- Preserved the T148 shared immutable trigger and its existing Acceptance
  UPDATE/DELETE behavior.
- Advanced the existing operational-fresh provenance revision guard and its
  integration expectation to the new migration revision.

## Files Modified

- `backend/alembic/versions/8d77007b9d7f_permit_quotation_revision_issuance.py`
- `backend/src/app/infrastructure/cli/fresh_install_provenance.py`
- `backend/tests/integration/test_t148_enquiry_quotation_postgres.py`
- `backend/tests/integration/test_operational_fresh_provenance.py`
- `docs/ImplementationLog/Stage3/Phase37.md`

## Tests Added

- Extended `test_t148_enquiry_quotation_postgres.py` with a populated
  `e148c0f5a8b2` upgrade, exact issuance/rejection matrix, Acceptance
  immutability, fresh-chain, FORCE-RLS, and empty-downgrade checks.
- Updated `test_operational_fresh_provenance.py` to assert T150's supported
  migration revision on fresh-install birth and operational transition evidence.

## Test Results

- `uv run black --check alembic/versions/8d77007b9d7f_permit_quotation_revision_issuance.py src/app/infrastructure/cli/fresh_install_provenance.py tests/integration/test_t148_enquiry_quotation_postgres.py tests/integration/test_operational_fresh_provenance.py`: passed.
- `uv run ruff check src tests alembic`: passed.
- `uv run pytest tests/unit -q`: 339 passed, 60 existing warnings.
- `uv run pytest tests/integration/test_t148_enquiry_quotation_postgres.py -q -rA`: 3 passed, including populated upgrade/rollback, RLS, and empty downgrade.
- `uv run pytest tests/integration/test_operational_fresh_provenance.py -q -rA`: 7 passed.
- `uv run alembic heads`: sole head `8d77007b9d7f`.
- `uv run python ../scripts/governance_validate.py --report`: passed; unresolved Required ADRs remain `[12,15,16,17,20]`.

## Design Decisions

- `to_jsonb(NEW) - ARRAY['issued_at', 'issued_by']` is compared to its OLD
  counterpart in PostgreSQL, so every present non-issuance column is immutable
  without maintaining a fallible hand-written field list.
- Downgrade restores T148's original QuotationRevision trigger and reverses the
  provenance guard only; it drops no evidence or schema data.

## Problems Encountered

- The initial Acceptance immutability test attempted an explicit transaction
  after a SELECT-created implicit transaction. The test now commits the read
  transaction before executing its isolated rejection assertions.

## Deferred Work

- T149 remains blocked until this task completes its separate Independent QA,
  synchronization, protected merge, and Control Tower verification lifecycle.

## Future Considerations

- Independent QA should inspect this exact candidate's trigger source and run
  the same PostgreSQL migration/persistence suite against the remote PR head.

## Reviewer Checklist

☑ Architecture preserved
☑ Existing design patterns followed
☑ Tests added
☑ Existing tests pass
☑ Documentation updated
□ ADR updated (if required) — no ADR mutation is authorized or required.
□ AI_BOOTSTRAP updated (if required) — no standing-process change.
□ PROJECT_STATE updated (if required) — post-QA synchronization belongs to the Documentation Manager.
☑ No unrelated refactoring
☑ No scope creep
☑ Ready for QA

## QA Decision

☑ Approved
□ Approved with comments
□ Rework required
