# Phase 46 — T165 Operational-Fresh Schema Revision Compatibility

**Status:** Implementation candidate ready for Independent QA
**Started:** 2026-10-19
**Completed:** 2026-10-19
**Related Tasks:** T165; DEF-T163-01
**Related ADRs:** ADR-0047
**Git Commit:** b1d2b1b75ff3877e5a82bf096a636530402d8a97
**Pull Request:**
**Release:**

## Objective

Implement ADR-0047's release-bound schema compatibility model so valid immutable
operational-fresh bootstrap provenance remains usable after approved forward schema
upgrades, while live-schema and provenance failures remain default-deny.

## Tasks Implemented

- Added a deterministic in-memory compatibility authority containing the reviewed
  canonical post-ADR-0037 lineage and current release head.
- Replaced the stale bootstrap-revision equality check with strict provenance
  contract validation, direct active-session `public.alembic_version` inspection,
  exactly-one-head enforcement, current-head equality and directional ancestry.
- Extended real PostgreSQL classifier coverage for ADR-0047 scenarios and retained
  the mounted FastAPI Party-create path using the real classifier.

## Files Modified

- `backend/src/app/infrastructure/persistence/schema_compatibility.py`
- `backend/src/app/infrastructure/persistence/sqlalchemy_install_classifier.py`
- `backend/tests/integration/test_install_classifier.py`
- `backend/tests/integration/test_party_routes.py`
- `docs/ImplementationLog/Stage3/Phase46.md`

## Tests Added

- `backend/tests/integration/test_install_classifier.py` — approved historical
  bootstrap lineage, live schema downgrade/unknown/multi-head/missing failures,
  and provenance contradiction coverage on disposable PostgreSQL databases.
- `backend/tests/integration/test_party_routes.py` — named T-REV-16 real current-head
  `POST /api/v1/parties` operational-fresh regression path.

## Test Results

- Baseline (host Python): `python -m pytest backend/tests/integration/test_install_classifier.py -q`
  could not collect because its environment lacks declared test dependencies and
  Starlette requested `httpx2`.
- Candidate (isolated temporary environment, real PostgreSQL):
  `pytest tests/integration/test_install_classifier.py -q` — 27 passed.
- Candidate (isolated temporary environment, real PostgreSQL):
  `pytest tests/integration/test_party_routes.py -q` — 23 passed.
- Candidate lint: `ruff check` for changed Python files — passed. Formatting:
  `black` for the changed classifier/authority/tests — passed.
- A full-suite candidate attempt reached 23% and exposed existing failures outside
  the T165 surfaces before it was stopped; it did not complete, so no full-suite
  pass/fail total is claimed. Independent QA must run the repository-required
  complete candidate checks and classify those failures against a compatible baseline.

## Design Decisions

- Used a static application-release authority rather than runtime Alembic script
  discovery, as required by ADR-0047. The authority holds only reviewed lineage
  metadata and does not mutate migrations or provenance.
- The classifier queries `public.alembic_version` through the same `AsyncSession`
  used for the ensuing write, before accepting operational provenance.

## Problems Encountered

- The initially selected host interpreter had incomplete/incompatible test packages.
  An isolated temporary environment was provisioned without changing repository
  dependencies; it executed the PostgreSQL suites successfully.

## Deferred Work

- `DEF-T163-02`, `BLK-T163-01`, Required ADR #20, migration changes and M1 readiness
  remain explicitly out of scope for T165.

## Future Considerations

- A future authorized schema migration must extend the compatibility authority in
  the same release-bound change, per ADR-0047 §6.

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

Notes: the relevant PostgreSQL suites and final changed-file checks pass. The full
suite did not complete and exposed pre-existing-looking failures that were not
baselined because the host interpreter could not collect tests; it remains
unchecked. ADR, bootstrap and project-state changes are not part of the authorized
developer scope.

## QA Decision

□ Approved
□ Approved with comments
□ Rework required
