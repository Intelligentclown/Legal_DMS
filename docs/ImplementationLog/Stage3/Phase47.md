# Phase 47 — T166 Matter Duplicate-Number Conflict Remediation

**Status:** Implementation and Independent QA completed; protected merge pending
**Started:** 2026-10-19
**Completed:** 2026-10-19
**Related Tasks:** T166; DEF-T163-02
**Related ADRs:** ADR-0020; ADR-0021; ADR-0022
**Git Commit:** a8fd172c710da6cfcef216502bcc1b2ab624910b
**Pull Request:** #325 — https://github.com/Intelligentclown/Legal_DMS/pull/325
**Release:**

## Objective

Translate only the protected PostgreSQL Matter-number unique violation into the
established structured HTTP 409 response while retaining global uniqueness,
aggregate atomicity, request transaction ownership, tenant isolation and RBAC.

## Tasks Implemented

- Added a targeted MatterService translation from an IntegrityError to
  ConflictError only when the PostgreSQL exception chain identifies SQLSTATE
  `23505` and the protected fresh-schema constraint
  `uq_matters_matter_number`.
- Retained the repository's existing nested savepoint for atomic Matter and
  MatterParty persistence; non-target integrity failures still propagate.
- Added real PostgreSQL API and concurrency evidence for duplicate handling,
  global cross-Organization uniqueness, no partial aggregate persistence,
  post-conflict request recovery and RBAC protection.

## Files Modified

- `backend/src/app/application/matter_service.py`
- `backend/tests/unit/test_matter_service.py`
- `backend/tests/integration/test_matter_routes.py`
- `docs/ImplementationLog/Stage3/Phase47.md`

## Tests Added

- `test_verified_matter_number_unique_violation_becomes_conflict` verifies the
  exact SQLSTATE/constraint translation through SQLAlchemy's asyncpg exception
  wrapping chain.
- `test_non_target_integrity_error_remains_untranslated` verifies a different
  unique constraint remains fail-closed.
- `test_duplicate_matter_number_is_a_scoped_conflict_and_request_recovers`
  verifies HTTP 409 response shape, global cross-Organization uniqueness, no
  partial MatterParty, subsequent request usability and RBAC denial.
- `test_concurrent_duplicate_matter_number_keeps_global_integrity` verifies two
  real PostgreSQL sessions create exactly one Matter and MatterParty.

## Test Results

- Protected migration graph: `uv run alembic heads` reported sole head
  `b155caa6d4e1`; a fresh isolated PostgreSQL 16 database migrated to that
  revision.
- Live catalog: `uq_matters_matter_number UNIQUE (matter_number)`. The prior
  T163 evidence spelling `matters_matter_number_key` is a clarified historical
  discrepancy; the protected migration and fresh catalog are authoritative.
- Focused candidate suite: `pytest tests/unit/test_matter_service.py
  tests/integration/test_matter_routes.py` — 9 passed (real PostgreSQL for the
  route and concurrency cases).
- Candidate unit suite: `pytest tests/unit -q` — 348 passed.
- Candidate lint: `ruff check src tests alembic` — passed. Candidate formatting:
  `black --check src tests alembic` — passed (331 files unchanged).
- A full `pytest` attempt collected 941 tests but exceeded this executor's
  30-second command window before a final result; no full-suite pass claim is
  made. Independent QA should run the complete candidate suite in an
  unconstrained runner.

## Design Decisions

- The predicate requires both PostgreSQL `23505` and the exact current protected
  constraint identity. It deliberately does not recognize the historical name.
- Translation occurs in the service after the repository's nested savepoint has
  rolled back the failed aggregate, preserving ADR-0020 request transaction
  ownership and subsequent request usability.
- The conflict message does not identify an Organization or return any
  cross-tenant information. No pre-insert existence check was added; the unique
  index remains the concurrency authority.

## Problems Encountered

- SQLAlchemy's asyncpg adapter exposes the original PostgreSQL exception in the
  exception chain. Initial targeted coverage demonstrated that checking only
  `IntegrityError.orig` remained fail-closed rather than returning 409. The
  predicate was corrected to traverse only the cause/context chain and still
  requires both verified identifiers.
- Fresh disposable PostgreSQL setup required the documented `legal_dms_app`
  runtime-role provision before applying the RLS migration. This was performed
  only in the disposable environment.

## Deferred Work

- Operational acceptance A3.2, native Electron A9.2, the consolidated T166
  reacceptance report, independent QA, PR publication/merge, Done status and
  M1 readiness remain separate authorized roles/workstreams.

## Future Considerations

- If an authorized future migration changes this constraint name, its matching
  translation and real PostgreSQL evidence must be updated together; do not
  add historic-name matching absent provenance for that schema.

## Reviewer Checklist

☑ Architecture preserved
☑ Existing design patterns followed
☑ Tests added
☑ Existing tests pass (unit and focused PostgreSQL suites; full-suite result not established)
☑ Documentation updated
☑ ADR updated (if required — not required)
☑ AI_BOOTSTRAP updated (if required — not required)
☑ PROJECT_STATE updated (if required — not required before protected closeout)
☑ No unrelated refactoring
☑ No scope creep
☑ Ready for QA (completed: Approved with comments)

Notes: focused PostgreSQL and complete unit suites pass; independent QA verified 348 unit tests, 9 focused tests, Ruff/Black, sole Alembic head and governance validation. The full candidate suite exceeded the executor command window after collecting 941 tests; no full-suite pass is claimed. The operational evidence PR #324 freshly passed A11.3 against the exact reviewed PR #325 head. No ADR, bootstrap or project-state change is required or authorized for this bounded fix. QA-T166-NB-01 remains nonblocking and unresolved: pre-existing in-process Alembic fileConfig disables application audit logging during multi-file suites. This log synchronization changes no product code, tests, acceptance evidence or architecture.

## QA Decision

□ Approved
☑ Approved with comments
□ Rework required

**Independent QA:** Comprehensive / Risk Tier 1; zero blocking findings. Formal review artifact: `docs/reviews/T166_QA_Review.md` on dedicated PR #326 (`98f9d51c3a451d8e96b51f981b64373971d0426f`). Reviewed implementation PR #325 head: `dde7fdf9e011bd61677c4b0edc4dde875daba7f0`. Reviewed operational evidence PR #324 head: `66ec49f4c4ce12733b98f878e2370d5fe57d2761`. Nonblocking QA-T166-NB-01 remains open. GitHub's independent collaborator approval and protected-merge gates are distinct from this formal QA Decision; T166 Not Done and M1 NOT READY.
