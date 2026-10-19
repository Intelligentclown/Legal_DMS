------------------------------------------------

# Stage 3 – Phase 45

Status: Operational acceptance execution complete — PR open; pending Independent QA review

Started: 2026-10-19

Completed:

Related Tasks: T163

Related ADRs: ADR-0018, ADR-0021, ADR-0023, ADR-0024, ADR-0044, ADR-0046

Git Commit:

Pull Request:

Release:

------------------------------------------------

## Objective

Establish the controlled local application environment, execute reproducible M1 office-workflow acceptance scenarios (A1–A11), and publish evidence-backed execution artifacts, defect register, and a separate M1 operational-readiness recommendation for Independent QA review under `PROJECT_WORKFLOW.md §3`.

## Tasks Implemented

- Verified all ten (10) required environment capabilities (writable checkout, Python/Node/uv/Docker toolchains, PostgreSQL 16 container, alembic migrations at frontier `b155caa6d4e1`, FastAPI backend on port 8000, React frontend on port 5173, unit test baselines, browser interaction, LocalFileStorage, and multi-tenant test identities).
- Established reproducible non-production fixtures for Organization A (`Apex Legal Chambers`) and Organization B (`Beacon Law Associates`) with permitted and restricted identities, baseline parties, matters, properties, files, and documents.
- Executed a complete live browser walkthrough via Chrome subagent validating authentication, dashboard context, party catalog, matter details, matter–property association selector, files navigation, document upload, and version history.
- Executed an automated 35-scenario acceptance suite covering Groups A1–A11:
  - **A1:** Authentication, login, invalid credential rejection, route guards, token rotation, logout revocation.
  - **A2:** Organization context resolution (`/auth/me`) and lookup vocabularies.
  - **A3:** Party selection, dynamic party creation, and matter creation with canonical client resolution.
  - **A4:** Canonical Matter–Property association and 200 idempotent re-association (T157 contract).
  - **A5:** File creation with sequential file number allocation and detail navigation.
  - **A6:** Document creation and binary stream upload with SHA256 checksum persistence.
  - **A7:** DocumentVersion history listing in chronological sequence.
  - **A8:** Document download with exact binary stream matching and `Content-Disposition` verification.
  - **A9:** Browser session clearing on reload (ADR-0018 D6).
  - **A10:** Complete multi-tenant isolation (cross-tenant 404s for matters, parties, documents, cross-tenant property association rejection) and RBAC permission enforcement for Read-Only role.
  - **A11:** Validation errors (422), not-found handling (404), and duplicate matter number conflict handling.
- Isolated and documented two material defects (`DEF-T163-01` and `DEF-T163-02`) and one environmental constraint (`BLK-T163-01`).
- Authored the comprehensive acceptance report `docs/acceptance/T163_M1_Acceptance_Report.md` and packaged sanitized screenshots, test scripts, and machine-readable scenario results.

## Files Modified / Created

- `docs/acceptance/T163_M1_Acceptance_Report.md` (new)
- `docs/acceptance/scripts/setup_acceptance_fixtures.py` (new)
- `docs/acceptance/scripts/run_acceptance_scenarios.py` (new)
- `docs/acceptance/evidence/acceptance_results.json` (new)
- `docs/acceptance/evidence/screenshots/*.png` (13 sanitized screenshots)
- `docs/ImplementationLog/Stage3/Phase45.md` (new)

## Test Results

- Acceptance Matrix: Total 35 scenarios:
  - **32 PASSED** (91.4%)
  - **2 FAILED** (5.7%): A3.2 (`DEF-T163-01`) and A11.3 (`DEF-T163-02`)
  - **1 BLOCKED** (2.9%): A9.2 (`BLK-T163-01`)
  - **0 NOT IN SCOPE**
- Baseline Unit Suites:
  - Backend unit suite: 342/342 passed
  - Frontend suite: 185/185 passed across 21 test files
- Governance Validation:
  - `python scripts/governance_validate.py`: OK (0 warnings, 0 errors)
  - `python -m pytest scripts/tests/test_governance_validate.py`: 68/68 passed

## Design Decisions

- **Strict Role Boundary:** Maintained strict operational acceptance executor boundaries per §8. Discovered defects are recorded in the defect register rather than silently repaired in application code.
- **Milestone Decoupling:** The M1 readiness recommendation (NOT READY pending remediation of `DEF-T163-01` and `DEF-T163-02`) is strictly decoupled from the T163 task execution verdict (EXECUTION COMPLETE with full evidence).

## Problems Encountered

- **`DEF-T163-01`:** `SqlAlchemyInstallationClassifier` hardcoded schema revision `cdcfd7df5fde` caused `InstallationClassificationError` on migration frontier `b155caa6d4e1`, causing `PartyWriteGate.ensure_writable()` to fail closed with HTTP 403 on dynamic party creation.
- **`DEF-T163-02`:** Duplicate `matter_number` submission raised an unhandled database `IntegrityError` resulting in HTTP 500 rather than user-actionable HTTP 409 Conflict.
- **`BLK-T163-01`:** Headless CI/agent environment cannot drive native Electron BrowserWindow for live restart verification (precedent T79/T82).

## Deferred Work

- Remediation of `DEF-T163-01` (update/generalize `SqlAlchemyInstallationClassifier`).
- Remediation of `DEF-T163-02` (translate unique constraint violation on `matters.matter_number` to HTTP 409).
- These remain recommended follow-up tasks for Backend Developer assignment.

## Reviewer Checklist

☑ Architecture preserved
☑ Existing design patterns followed
☑ No substantive backend/frontend code or schema modifications
☑ Reproducible acceptance procedures and test scripts included
☑ Sanitized evidence and screenshots packaged
☑ Defect register and M1 readiness recommendation documented
☑ Governance and linters verified
☑ Ready for QA (Independent QA Reviewer evaluation)
