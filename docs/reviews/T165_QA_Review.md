# T165 Independent QA Review — Operational-Fresh Schema Revision Compatibility Implementation

**Task:** T165 — Operational-Fresh Schema Revision Compatibility Implementation  
**Lifecycle Stage:** `PROJECT_WORKFLOW.md §3` — Implementation Independent QA  
**Candidate Evaluated:** `dbbbcd26d2fa033c9179f6631db1fc6ad8ce086a`  
**Protected Base Commit:** `18e98dea285585e46ae5befa0f4699dc1c2449ec` (`origin/main`, merge PR #320)  
**Pull Request:** [#321 — `T165: operational-fresh schema revision compatibility`](https://github.com/Intelligentclown/Legal_DMS/pull/321)  
**Branch:** `feature/t165-operational-fresh-schema-compatibility`  
**Reviewer:** Independent QA Reviewer (Antigravity)  
**QA Depth:** Comprehensive / Risk Tier 1  
**Date:** 2026-10-19  

---

## 1. Executive Summary & Formal QA Decision

- **Formal QA Decision:** **Approved with comments**
- **Exact Candidate SHA Evaluated:** `dbbbcd26d2fa033c9179f6631db1fc6ad8ce086a`
- **Scope Audit:** Exactly six (6) files modified (+293 / −9 lines against base `18e98dea285585e46ae5befa0f4699dc1c2449ec`):
  1. `backend/src/app/infrastructure/persistence/schema_compatibility.py` (+48 / −0)
  2. `backend/src/app/infrastructure/persistence/sqlalchemy_install_classifier.py` (+27 / −7)
  3. `backend/tests/integration/test_install_classifier.py` (+73 / −1)
  4. `backend/tests/integration/test_party_routes.py` (+1 / −1)
  5. `backend/tests/unit/test_schema_compatibility.py` (+32 / −0)
  6. `docs/ImplementationLog/Stage3/Phase46.md` (+112 / −0)
- **Zero Prohibited Implementation:**
  - Zero database migrations or Alembic revision modifications.
  - Sole Alembic head is strictly preserved at `b155caa6d4e1`.
  - Zero governance-state modifications or downstream authorizations (T166+).
  - Zero ADR promotions: ADR-0047 remains `Proposed`.
  - Required ADRs remain unresolved at `[12, 15, 16, 17, 20]`. Required ADR #20 is strictly preserved.
  - `DEF-T163-02` and `BLK-T163-01` remain open; Milestone M1 remains `NOT READY / PENDING REMEDIATION`.
- **Architectural & Security Soundness:**
  - Implements ADR-0047's combined compatibility authority, decoupling immutable bootstrap provenance ($R_{\text{boot}}$) from live schema inspection ($R_{\text{curr}}$).
  - Establishes `SchemaCompatibilityAuthority` as a dedicated in-memory, release-bound authority with the complete canonical 10-revision post-ADR-0037 lineage (`c4e7a9b2d6f1` through `b155caa6d4e1`).
  - Queries `public.alembic_version` on the active connection in the same transaction as the ensuing write; enforces exactly one head, current head equality (`b155caa6d4e1`), and directional ancestry ($R_{\text{boot}} \preceq R_{\text{curr}}$).
  - Maintains strict fail-closed default-deny for all invalid, unversioned, multi-head, downgraded, unknown, or contradictory states.
  - Successfully resolves `DEF-T163-01` across all 16 mandatory ADR-0047 scenarios.
- **Independent Test Reproduction:**
  - Targeted unit suite (`backend/tests/unit/test_schema_compatibility.py`): 4 passed in 0.05s.
  - Comprehensive unit suite (`backend/tests/unit/`): 346 passed in 7.41s.
  - Classifier PostgreSQL integration suite (`test_install_classifier.py`): 27 passed in 15.75s.
  - Party route PostgreSQL integration suite (`test_party_routes.py`): 23 passed in 12.82s.
  - Linters (`ruff check`, `black --check`): passed cleanly.
  - Full-suite failure attribution: The partial failures encountered during full-suite execution were investigated and definitively traced to a pre-existing baseline fixture issue in `tests/support/synthetic_migration.py` (`NotNullViolationError: null value in column "organization_id" of relation "properties"`), untracked and unaffected by T165.
- **Blocking Findings:** Zero (0).
- **Non-Blocking Advisories:** Two (2).

---

## 2. Baseline & Remote Repository Provenance

- **Protected `main` Baseline:** `18e98dea285585e46ae5befa0f4699dc1c2449ec` (Merge PR #320 — T165 Authorization & Calendar Registration).
- **PR #321 State:** Independently queried via GitHub CLI (`gh pr view 321`):
  - State: `OPEN`, unmerged.
  - `isDraft`: `true`.
  - Mergeable: `MERGEABLE`.
  - Base Ref: `main` (`18e98dea285585e46ae5befa0f4699dc1c2449ec`).
  - Head Ref: `feature/t165-operational-fresh-schema-compatibility` (`dbbbcd26d2fa033c9179f6631db1fc6ad8ce086a`).
  - Ancestry: Direct linear fast-forward descendant of base `18e98dea285585e46ae5befa0f4699dc1c2449ec` (`git merge-base --is-ancestor` confirmed).
  - Commit Lineage on PR:
    1. `b1d2b1b` fix(t165): validate operational-fresh schema compatibility
    2. `d4e539f` docs(t165): record implementation self-assessment
    3. `33c5ab0` docs(t165): link draft QA handoff
    4. `dbbbcd2` test(t165): cover schema compatibility authority

---

## 3. Candidate Scope & Prohibited Modifications Check

| Scope Item | Candidate Status | Independent QA Finding |
|---|---|---|
| **Production Code** | Strictly `schema_compatibility.py` and `sqlalchemy_install_classifier.py` | Verified. No extraneous runtime changes. |
| **Migrations** | Zero migration files added or modified in `backend/alembic/versions/` | Verified. Frontier remains sole head `b155caa6d4e1`. |
| **Governance State** | `PROJECT_STATE.json` and `IMPLEMENTATION_QUEUE.md` untouched | Verified. T165 remains Authorized; no T166 authorized. |
| **ADR Promotions** | `ADR/0047-operational-fresh-schema-revision-compatibility.md` untouched | Verified. Status remains `Proposed`. |
| **Required ADRs** | No changes to Required ADR status | Verified. `[12, 15, 16, 17, 20]` remain unresolved. |
| **Other Open Defects** | `DEF-T163-02`, `BLK-T163-01` untouched | Verified. Defect and blocker records remain open. |
| **Milestone Readiness** | No M1 acceptance declared | Verified. M1 remains `NOT READY / PENDING REMEDIATION`. |

---

## 4. Architecture & Security Review against ADR-0047

Independent code inspection of `schema_compatibility.py` and `sqlalchemy_install_classifier.py` confirms adherence to all decisions in ADR-0047:

1. **Release-Bound Lineage & Exact Head (ADR-0047 Decision 1):**
   `SchemaCompatibilityAuthority` specifies `provenance_contract_version = "adr-0037.v1"` and the immutable tuple of 10 approved revisions:
   `("c4e7a9b2d6f1", "5d8a3f2e9c6b", "7f1b9c3d4a2e", "9e6a4b2c8d1f", "b8c4d2e1f7a9", "be439c0d6fdb", "cdcfd7df5fde", "e148c0f5a8b2", "8d77007b9d7f", "b155caa6d4e1")`.
   `approved_runtime_head` is dynamically bound to `approved_lineage[-1]` (`"b155caa6d4e1"`).
2. **Immutable Historical Bootstrap Provenance (ADR-0047 Decision 2):**
   The classifier evaluates `observed_schema_revision` ($R_{\text{boot}}$) from `legal_dms_provenance.runtime_state` without attempting to mutate database evidence or requiring re-bootstrap.
3. **Active Connection & Live Head Inspection (ADR-0047 Decision 3):**
   `_current_schema_revision()` queries `SELECT version_num FROM public.alembic_version` directly on the active `AsyncSession`. Exactly one row is required: 0 rows triggers `"schema version is missing"`, $>1$ rows triggers `"schema has multiple migration heads"`, and head mismatch triggers `"unsupported or divergent schema revision"` or `"schema downgrade detected"`.
4. **Directional Ancestry Validation (ADR-0047 Decision 4):**
   `validate_bootstrap_ancestry(bootstrap_revision, current_revision)` computes indices within `approved_lineage`. If `bootstrap_position > current_position`, `"schema downgrade detected"` is raised. Unknown revisions raise `"unsupported or divergent schema revision"`.
5. **Deterministic Precedence & Contradiction Detection (ADR-0047 §4):**
   Table-level `SHARE` locks on `clients` and `client_party_migration_ledger` are held. If operational provenance is detected but `clients_total > 0` or `ledger_rows > 0`, the classifier raises `InstallationClassificationError("operational-fresh provenance contradicts migration evidence")`.
6. **No Request-Time Alembic Filesystem Discovery (ADR-0047 §2 Alternative 2):**
   The authority is purely in-memory with zero filesystem traversal or dynamic Alembic script inspection at request time.
7. **Security Invariants Preserved:**
   `PartyWriteGate` default-deny, tenant context isolation (`app.current_organization_id`), `FORCE ROW LEVEL SECURITY`, RBAC permission enforcement (`parties:write`, `parties:delete`), and non-superuser role privilege separation remain strictly intact.

---

## 5. Mandatory ADR-0047 16-Scenario Evidence Matrix

| Scenario | Condition | Expected State | Gate Behavior | Actual Test Evidence | Observed Result |
|---|---|---|---|---|:---:|
| **T-REV-01** | Fresh bootstrap on `b155caa6d4e1` ($R_{\text{boot}} = R_{\text{curr}} = \text{"b155caa6d4e1"}$) | `OPERATIONAL_FRESH` | Party write permitted | `test_install_classifier.py::test_bootstrapped_installation_classifies_operational_fresh` | **PASSED** |
| **T-REV-02** | Historical bootstrap on `cdcfd7df5fde`, upgraded to `b155caa6d4e1` | `OPERATIONAL_FRESH` | Party write permitted | `test_install_classifier.py::test_historical_approved_bootstrap_revisions_upgrade_to_current_head[cdcfd7df5fde]` | **PASSED** (Remediates DEF-T163-01) |
| **T-REV-03** | Historical bootstrap on `c4e7a9b2d6f1`, upgraded to `b155caa6d4e1` | `OPERATIONAL_FRESH` | Party write permitted | `test_install_classifier.py::test_historical_approved_bootstrap_revisions_upgrade_to_current_head[c4e7a9b2d6f1]` | **PASSED** |
| **T-REV-04** | Historical bootstrap on intermediate revisions (`5d8a3f2e9c6b` .. `8d77007b9d7f`), upgraded to `b155caa6d4e1` | `OPERATIONAL_FRESH` | Party write permitted | `test_install_classifier.py::test_historical_approved_bootstrap_revisions_upgrade_to_current_head[<rev>]` (7 parameterized runs) | **PASSED** |
| **T-REV-05** | Legitimately accumulated Party/Address rows in valid operational-fresh DB | `OPERATIONAL_FRESH` | Status preserved; write permitted | `test_install_classifier.py::test_party_and_address_growth_preserve_operational_fresh` | **PASSED** |
| **T-REV-06** | Schema downgrade: bootstrapped at `b155caa6d4e1`, DB schema downgraded to `cdcfd7df5fde` | `InstallationClassificationError` ("downgrade") | Denied (HTTP 403) | `test_install_classifier.py::test_invalid_live_schema_version_fails_closed[UPDATE...cdcfd7df5fde-downgrade]` | **PASSED** |
| **T-REV-07** | Unknown current schema revision (e.g. unapproved branch head) | `InstallationClassificationError` ("divergent") | Denied (HTTP 403) | `test_install_classifier.py::test_invalid_live_schema_version_fails_closed[UPDATE...unapproved-head-divergent]` | **PASSED** |
| **T-REV-08** | Multi-head `alembic_version` table ($>1$ rows) | `InstallationClassificationError` ("multiple migration heads") | Denied (HTTP 403) | `test_install_classifier.py::test_invalid_live_schema_version_fails_closed[INSERT...multiple migration heads]` | **PASSED** |
| **T-REV-09** | Empty `alembic_version` table (0 rows) | `InstallationClassificationError` ("schema version is missing") | Denied (HTTP 403) | `test_install_classifier.py::test_invalid_live_schema_version_fails_closed[DELETE...schema version is missing]` | **PASSED** |
| **T-REV-10** | Contradiction: valid operational provenance present but `clients > 0` | `InstallationClassificationError` ("contradicts migration evidence") | Denied (HTTP 403) | `test_install_classifier.py::test_operational_provenance_with_migration_evidence_fails_closed` | **PASSED** |
| **T-REV-11** | Contradiction: valid operational provenance present but `client_party_migration_ledger > 0` | `InstallationClassificationError` ("contradicts migration evidence") | Denied (HTTP 403) | `test_install_classifier.py::test_operational_provenance_with_ledger_evidence_fails_closed` | **PASSED** |
| **T-REV-12** | Migrated DB (`client_party_migration_ledger` complete) | `MIGRATED` | Denied pending ADR #20 (HTTP 403) | `test_install_classifier.py::test_complete_migration_is_migrated_and_ordinary_writes_remain_denied` | **PASSED** |
| **T-REV-13** | Legacy DB with `clients` rows, no provenance | `LEGACY_WITH_BUSINESS_DATA` | Denied (HTTP 403) | `test_install_classifier.py::test_legacy_and_partial_migration_are_denied` | **PASSED** |
| **T-REV-14** | Empty unmigrated DB without provenance events | `UNPROVEN` | Denied (HTTP 403) | `test_install_classifier.py::test_empty_upgraded_database_is_unproven_and_denied` | **PASSED** |
| **T-REV-15** | Malformed provenance contract (`provenance_contract_version = "unsupported.v1"`) | `InstallationClassificationError` ("operational provenance is unsupported") | Denied (HTTP 403) | `test_install_classifier.py::test_unsupported_projection_evidence_fails_closed` | **PASSED** |
| **T-REV-16** | End-to-end authenticated `POST /api/v1/parties` using production classifier against real DB | HTTP 201 Created | Verifies resolution of `DEF-T163-01` | `test_party_routes.py::TestPartyCrud::test_t_rev_16_current_head_real_classifier_create_get_list_update_and_delete` | **PASSED** |

### Special Audit of Scenario T-REV-16
The test `test_t_rev_16_current_head_real_classifier_create_get_list_update_and_delete` was scrutinized:
1. It does not declare or use the `force_install_state` fixture (which mocks `get_install_classifier`).
2. The route dependency `get_install_classifier` falls through to production `SqlAlchemyInstallationClassifier(session)`.
3. The session connects to a live disposable PostgreSQL database created via `provision_empty_disposable_database`, `establish_fresh_installation`, and `run_bootstrap`.
4. Execution verified: The real classifier queries the database tables, confirms `b155caa6d4e1`, evaluates `PartyWriteGate.ensure_writable()`, and creates the Party row, returning HTTP 201 Created. The test genuinely exercises the production code path.

---

## 6. Test Execution & Failure Attribution Analysis

### 6.1. Independent Reproduction of Targeted Suites

All tests directly covering T165 surfaces were independently executed and passed:
- `backend/tests/unit/test_schema_compatibility.py`: **4 passed** (0.05s).
- `backend/tests/unit/` (Full backend unit suite): **346 passed** (7.41s).
- `backend/tests/integration/test_install_classifier.py`: **27 passed** (15.75s).
- `backend/tests/integration/test_party_routes.py`: **23 passed** (12.82s).

### 6.2. Full-Suite Failure Investigation & Attribution

The developer noted in `Phase46.md` that a full-suite run reached ~23% before encountering failures and being stopped. Independent reproduction revealed:
1. **Pre-Existing Baseline Fixture Failure:**
   - Failure: `IntegrityError: null value in column "organization_id" of relation "properties" violates not-null constraint`.
   - Root Cause: In `backend/tests/support/synthetic_migration.py` line 165, the helper `seed_client_graph()` instantiates `Property` without specifying `organization_id`.
   - Provenance: In migration `b155caa6d4e1` (and earlier in T135 `9e6a4b2c8d1f`), `properties.organization_id` was made a non-nullable foreign key column. `synthetic_migration.py` was last edited in T126 (`929709e`) and has not been updated for the post-T135 schema.
   - Impact: Causes older rehearsal integration tests (`test_client_migration_executor.py`, `test_synthetic_migration_rehearsal.py`) to fail when run against a database migrated to the current head.
   - Attribution: **Existing baseline fixture defect**. It is completely unrelated to T165 schema compatibility or the installation classifier.
2. **Host Python Environment Discrepancy:**
   - The default Windows host Python 3.12 lacks `pydantic_settings` and encounters a `starlette.testclient` dependency error requiring `httpx2`.
   - Provisioning an isolated Python 3.14 environment matching `backend/uv.lock` resolves the collection issues.
3. **CI Scope Boundary:**
   - Per `.github/workflows/backend.yml` and `ADR/0017-github-actions-ci.md`, CI deliberately runs **only `tests/unit/`** to avoid external database dependencies. The Postgres integration suite is executed against local containerized PostgreSQL instances.
4. **Conclusion on Risk Tier 1 Approval:**
   - Because all T165 implementation surfaces, unit tests, classifier integration tests, and mounted FastAPI route tests pass against real PostgreSQL, and the full-suite failures are demonstrably confined to pre-existing legacy migration rehearsal fixtures, this does not block Risk Tier 1 approval.

---

## 7. Remote CI Verification & Workflow Coverage

GitHub Actions workflows were independently verified on candidate HEAD `dbbbcd26d2fa033c9179f6631db1fc6ad8ce086a`:

| Workflow | Conclusion | Duration | Run URL | Notes |
|---|---|---|---|---|
| **Backend validation** | **Success** | 21s / 27s | [Run 39272032753](https://github.com/Intelligentclown/Legal_DMS/actions/runs/39272032753) | Runs unit suite (346 tests), format/lint, and import smoke |
| **Frontend validation** | **Success** | 30s | [Run 39272032784](https://github.com/Intelligentclown/Legal_DMS/actions/runs/39272032784) | Verified frontend build & tests |
| **Governance validation** | **Success** | 7s | [Run 39272032733](https://github.com/Intelligentclown/Legal_DMS/actions/runs/39272032733) | Validated queue, project state, ADRs, calendar |
| **Release build** | **Success** | 32s | [Run 39272032669](https://github.com/Intelligentclown/Legal_DMS/actions/runs/39272032669) | Verified packaging scripts |

---

## 8. Findings Register

### Blocking Findings
**Zero (0)** blocking findings. The candidate implementation is robust, correct, and strictly compliant with ADR-0047.

### Non-Blocking Advisories

1. **Finding QA-T165-ADV-01 — Baseline Fixture Gap in `tests/support/synthetic_migration.py`:**
   - **Severity:** Low / Advisory (Non-blocking).
   - **Evidence:** `seed_client_graph()` creates `Property` rows without `organization_id`, failing on `b155caa6d4e1`.
   - **Affected File:** `backend/tests/support/synthetic_migration.py`.
   - **Remediation Guidance:** A future maintenance task should update `synthetic_migration.py` to assign `organization.id` to seeded properties when running against post-T135 schemas.
2. **Finding QA-T165-ADV-02 — Future Migration Lineage Maintenance Protocol:**
   - **Severity:** Low / Advisory (Non-blocking).
   - **Evidence:** `SchemaCompatibilityAuthority.approved_lineage` is hardcoded to `b155caa6d4e1`.
   - **Affected File:** `backend/src/app/infrastructure/persistence/schema_compatibility.py`.
   - **Remediation Guidance:** Whenever a future migration task introduces a new Alembic head advancing past `b155caa6d4e1`, the author must append the new revision ID to `approved_lineage` in `SchemaCompatibilityAuthority` per ADR-0047 §6 to maintain continuous compatibility.

---

## 9. Reviewer Checklist

- [x] **Architecture** — Follows ADR-0047 Decision 5 (Combined Compatibility Authority).
- [x] **Security** — Fail-closed default-deny preserved for all invalid, downgraded, and multi-head states.
- [x] **Invariants** — `PartyWriteGate`, tenant isolation, FORCE RLS, and RBAC permissions preserved.
- [x] **Scope** — Exactly 6 files modified; zero database migrations or governance-state modifications.
- [x] **Scenario Matrix** — All 16 ADR-0047 scenarios verified with passing tests.
- [x] **Independent Execution** — 346 unit tests, 27 classifier tests, 23 party route tests pass.
- [x] **Failure Attribution** — Incomplete full-suite run investigated; baseline failure attributed to `synthetic_migration.py`.
- [x] **CI Verification** — All 4 GitHub Actions workflows green on candidate HEAD.
- [x] **QA Decision** — Formally rendered as `Approved with comments`.

---

## 10. QA Publication Provenance & Next Lifecycle Steps

- **QA Review Artifact Path:** `docs/reviews/T165_QA_Review.md`
- **Reviewed Candidate SHA:** `dbbbcd26d2fa033c9179f6631db1fc6ad8ce086a`
- **Publication Target Branch:** `feature/t165-operational-fresh-schema-compatibility` (PR #321)
- **Publication Commit:** Descends directly from candidate `dbbbcd26d2fa033c9179f6631db1fc6ad8ce086a`.

### Remaining Protected-Merge Prerequisites:
1. **PR Readiness:** PR #321 must be marked ready for review (converted from draft).
2. **Independent Collaborator Review:** An eligible collaborator must submit an approving review.
3. **CI Re-Verification:** Exact-head CI checks must pass on the publication commit.
4. **Merge Execution:** Project Manager / Control Tower performs pre-merge verification and standard merge commit to `main`.
5. **Governance Closeout:** Dedicated §3 PR 3 closeout required before T165 is marked `Done`.
