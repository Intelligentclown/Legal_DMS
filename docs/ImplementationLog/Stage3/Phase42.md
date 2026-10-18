------------------------------------------------

# Stage 3 – Phase 42

Status: In Progress — implementation candidate awaiting Independent QA

Started: 2026-10-18

Completed:

Related Tasks: T157

Related ADRs: ADR-0044, ADR-0020, ADR-0021, ADR-0022, ADR-0029

Git Commit: fe38f7287dcb6e51f703952da83f2dbff81772b2

Pull Request:

Release:

------------------------------------------------

## Objective

Implement the bounded Matter-owned canonical MatterProperty application surface without changing the schema, legacy relationship semantics, RBAC families, or Party/ownership aggregates.

## Tasks Implemented

- Added canonical Matter-scoped list, associate, and unlink operations backed only by `matter_properties`.
- Implemented deterministic duplicate association behavior (201 when created, 200 when already present) and idempotent unlink (204 whether present or already absent).
- Added existing-port audit evidence for actual association creation and removal.

## Files Modified

- `backend/src/app/application/interfaces/matter_property_repository.py`
- `backend/src/app/infrastructure/persistence/sqlalchemy_matter_property_repository.py`
- `backend/src/app/application/matter_property_service.py`
- `backend/src/app/presentation/api/v1/matters.py`
- `backend/tests/integration/test_matter_property_routes.py`
- `docs/ImplementationLog/Stage3/Phase42.md`

## Tests Added

- Canonical zero/multiple-link listing, duplicate creation, idempotent unlink, unchanged endpoints/neighbour aggregates, and audit evidence.
- Cross-tenant non-enumeration, Matter/Property read authority, Matter write authority, and default-deny absent Organization context.
- Legacy `Matter.property_id` isolation and a real PostgreSQL two-session duplicate race that ends with exactly one row.

## Test Results

- `uv run pytest tests/integration/test_matter_property_routes.py -q` — 3 passed.
- `uv run pytest tests/unit/test_matter_service.py tests/unit/test_property_service.py tests/unit/test_audit_logger.py -q` — 15 passed.
- `uv run pytest tests/integration/test_matter_routes.py tests/integration/test_property_routes.py -q` — 6 passed.
- `uv run pytest tests/integration/test_auth_login.py -q` — 10 passed.
- `uv run pytest tests/integration/test_matter_property_tenant_integrity_foundation.py -q` — 5 passed.
- `uv run ruff check src tests alembic` and `uv run black --check src tests alembic` — passed.
- `python scripts/governance_validate.py --report` and `python scripts/tests/test_governance_validate.py -v` — passed; 60 governance tests.
- A full `uv run pytest -q` attempt was terminated after stalling near 40% with many failures in pre-existing, unrelated suites; it is explicitly not claimed as a pass. Focused T157 and named regression suites above pass.

## Design Decisions

- A narrow dedicated association port preserves Matter write ownership without widening Matter or Property repositories into generic query APIs.
- List requires `matters:read` plus `properties:read`; mutation requires `matters:write` plus `properties:read`.
- Writes only flush. A nested savepoint turns only PostgreSQL unique-pair collisions into the stable no-op result; request transaction ownership remains with the existing dependency.
- The response matches existing Property/owner content conventions and no Property-side writable association API is added.

## Problems Encountered

- The first focused test fixture omitted a pre-existing required Party phone field; only the fixture was corrected.
- Combining the existing audit logger unit test before caplog-based audit integration tests suppresses those caplog records. Their normal isolated invocation passes; no T157 code touches login/audit infrastructure.

## Deferred Work

- Independent QA, QA publication, documentation synchronization, merge, completion/calendar actuals, and frontend controls are not performed by this role.
- Historical `Matter.property_id` convergence remains Required ADR #20 work.

## Future Considerations

- A separately authorized Property-scoped reverse lookup may be read-only.
- Qualifiers, generalized history/lifecycle, and legacy reconciliation remain outside T157 under Required ADRs #15, #17, and #20.

## Reviewer Checklist

☑ Architecture preserved
☑ Existing design patterns followed
☑ Tests added
□ Existing tests pass
☑ Documentation updated
□ ADR updated (if required) — ADR-0044 remains unchanged.
□ AI_BOOTSTRAP updated (if required) — no process change.
□ PROJECT_STATE updated (if required) — Documentation Manager work after QA.
☑ No unrelated refactoring
☑ No scope creep
□ Ready for QA

## QA Decision

None — Independent QA has not yet been commissioned or performed.
