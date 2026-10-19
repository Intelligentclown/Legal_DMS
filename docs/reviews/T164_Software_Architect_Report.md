# T164 Software Architect Report — Operational-Fresh Schema Revision Compatibility Architecture

**Task:** T164 — Operational-Fresh Schema Revision Compatibility Architecture
**Role:** Software Architect
**Lifecycle Stage:** `PROJECT_WORKFLOW.md §3.1` — PR 2 of 3 (Architecture Candidate)
**Proposed Architecture Decision Record:** [`ADR/0047-operational-fresh-schema-revision-compatibility.md`](file:///d:/Code/Legal_DMS_Clean/ADR/0047-operational-fresh-schema-revision-compatibility.md)
**Protected Base Commit:** `8116402356b38b65964bbfdb76ede475349eb7ec` (`origin/main`, merge PR #316)
**Branch:** `docs/t164-operational-fresh-schema-revision-compatibility-architecture`
**Date:** 2026-10-19

---

## 1. Verified Baseline and Authorization

1. **Protected `main` Verification:**
   - Fresh remote query independently verified protected `main` at `8116402356b38b65964bbfdb76ede475349eb7ec`.
   - Merge PR #316 (`docs: authorize T164 operational-fresh revision architecture`) is the exact head commit of protected `main`.
   - Parent 1: `7087c5eabaf18bbccd18d0503998619e04333b06` (Merge PR #315 — T163 dedicated governance closeout).
   - Parent 2: `f0528956973ba4bf26b38bf228beea67a050dcfd` (PR #316 reviewed candidate head containing Independent QA review `docs/reviews/T164_Authorization_QA_Review.md`).
2. **Governance State Verified:**
   - `latestTaskDone = T163`
   - `latestTaskAuthorized = T164`
   - `inProgressTransitions = []`
   - Unresolved Required ADRs: `[12, 15, 16, 17, 20]` (strictly preserved; Required ADR #20 remains unresolved).
   - Database migration frontier: strictly `b155caa6d4e1`.
   - Zero open pull requests present on repository.
   - Zero conflicting T164 work present.
3. **Execution Environment Gate Established:**
   - Authenticated, writable repository checkout on Windows: verified.
   - GitHub CLI (`gh`) authenticated as `Intelligentclown` with `repo` and `workflow` scopes: verified.
   - Complete repository tree accessible: verified.
   - Python 3.12.10, pytest 9.1.1, git 2.53.0: verified.
   - Governance and ADR validators executable: verified.

---

## 2. Problem Statement & T163 Evidence Reconciliation

During the T163 M1 operational acceptance verification pass (`docs/acceptance/T163_M1_Acceptance_Report.md`), scenario A3.2 (dynamic Party creation via `POST /api/v1/parties`) failed closed with `HTTP 403 Forbidden` (`{"error": {"code": "installation_classification_error", "message": "operational provenance is unsupported"}}`). This was registered as material defect **`DEF-T163-01`**.

### Root Cause Analysis
1. In `backend/src/app/infrastructure/persistence/sqlalchemy_install_classifier.py`, `_SUPPORTED_SCHEMA_REVISION` was hardcoded to `"cdcfd7df5fde"` (dating from T141).
2. The classifier's `_operational_transition()` method reads the `observed_schema_revision` column from `legal_dms_provenance.runtime_state` (which projects `legal_dms_provenance.installation_events`) and enforces strict equality against `_SUPPORTED_SCHEMA_REVISION`.
3. Meanwhile, schema migrations advanced from `cdcfd7df5fde` through `e148c0f5a8b2` (T148) and `8d77007b9d7f` (T150) to `b155caa6d4e1` (T155).
4. When operational-fresh bootstrap ran against `b155caa6d4e1`, `enter_operational_fresh()` recorded `observed_schema_revision = "b155caa6d4e1"`.
5. At runtime, the classifier observed `"b155caa6d4e1" != "cdcfd7df5fde"`, raised `InstallationClassificationError`, and `PartyWriteGate.ensure_writable()` correctly failed closed with HTTP 403.

### Historical Provenance vs. Present Compatibility
The architectural defect arises from conflating two distinct concepts:
- **Historical Provenance ($R_{\text{boot}}$):** An immutable historical record of the schema revision active when the unique operational-fresh bootstrap transition occurred. Under ADR-0037, this value never mutates.
- **Present Schema Compatibility ($R_{\text{curr}}$):** The live schema revision currently active in the database (recorded in `alembic_version.version_num`).

A single static equality check fails both when a fresh database is bootstrapped on a newer revision, and when an older database legitimately bootstrapped on an earlier revision is upgraded. Furthermore, `SqlAlchemyInstallationClassifier` previously failed to query `alembic_version` at all, leaving current schema state and downgrades unverified.

---

## 3. Evaluation of Alternatives

1. **Alternative 1: Fixed Supported-Revision Replacement (e.g. bump to `b155caa6d4e1`)**
   *Rejected.* Breaks all previously bootstrapped installations upon upgrade; re-breaks immediately on the next migration (T165+); fails to inspect live `alembic_version`.
2. **Alternative 2: Unconstrained Dynamic Migration Graph Ancestry**
   *Rejected on its own.* Incurs runtime file-system I/O overhead inside classification hot paths; lacks an explicit governance boundary around which revisions are approved for production operation.
3. **Alternative 3: Static Revision Allow-List / Registry Only**
   *Rejected on its own.* Lacks directionality; cannot detect illegal schema downgrades from a newer approved revision to an older approved revision.
4. **Alternative 4: Coarse Provenance Contract Versioning Only (`adr-0037.v1`)**
   *Rejected.* Far too coarse; completely decouples runtime eligibility from schema compatibility.
5. **Alternative 5: Combined Compatibility Model (Selected Architecture)**
   *Selected.* Combines provenance contract verification (`adr-0037.v1`), approved bootstrap lineage verification, live schema head verification ($R_{\text{curr}} \in \text{alembic\_version}$), and directional ancestry verification ($R_{\text{boot}} \preceq R_{\text{curr}}$).

---

## 4. Architectural Decision Summary (Proposed ADR-0047)

[`ADR/0047-operational-fresh-schema-revision-compatibility.md`](file:///d:/Code/Legal_DMS_Clean/ADR/0047-operational-fresh-schema-revision-compatibility.md) establishes:

1. **Trusted Compatibility Authority:**
   A dedicated in-memory authority in the backend infrastructure layer defines the approved post-ADR-0037 canonical revision lineage:
   ```text
   c4e7a9b2d6f1 -> 5d8a3f2e9c6b -> 7f1b9c3d4a2e -> 9e6a4b2c8d1f -> b8c4d2e1f7a9 ->
   be439c0d6fdb -> cdcfd7df5fde -> e148c0f5a8b2 -> 8d77007b9d7f -> b155caa6d4e1
   ```
   - Current Approved Head ($R_{\text{head}}$): `b155caa6d4e1`.
   - Supported Contract Version: `adr-0037.v1`.
2. **Immutable Historical Provenance ($R_{\text{boot}}$):**
   `observed_schema_revision` in `legal_dms_provenance.installation_events` remains immutable. Any $R_{\text{boot}}$ in the approved canonical sequence is recognized as a valid historical bootstrap.
3. **Present Schema Verification ($R_{\text{curr}}$):**
   `alembic_version.version_num` is queried within the classification transaction:
   - Exactly one row must exist (0 rows $\to$ unmigrated fail-closed; $>1$ rows $\to$ multi-head fail-closed).
   - $R_{\text{curr}}$ must equal $R_{\text{head}}$ (`b155caa6d4e1`).
4. **Directional Lineage Invariant ($R_{\text{boot}} \preceq R_{\text{curr}}$):**
   - $R_{\text{boot}} == R_{\text{curr}}$ (fresh bootstrap on current head): Valid.
   - $R_{\text{boot}} \prec R_{\text{curr}}$ (upgraded installation along canonical chain): Valid.
   - $R_{\text{curr}} \prec R_{\text{boot}}$ (downgrade detected): Fail closed (`InstallationClassificationError`).
   - Disjoint / unapproved revisions: Fail closed.
5. **Deterministic Precedence Matrix:**
   Database/Lock errors $\to$ `alembic_version` validation $\to$ provenance shape/contract validation $\to$ directional lineage check $\to$ contradiction detection (`clients > 0` or `ledger > 0`) $\to$ state assignment (`MIGRATED`, `OPERATIONAL_FRESH`, `LEGACY_WITH_BUSINESS_DATA`, `UNPROVEN`).
6. **PartyWriteGate Default-Deny Invariant:**
   Ordinary Party create/update/delete strictly permitted ONLY when state is `OPERATIONAL_FRESH`. All other states and exceptions raise `ForbiddenError` (HTTP 403).
7. **Security & Privilege Invariants:**
   - Tenant isolation, `FORCE ROW LEVEL SECURITY`, and RBAC permissions (`parties:write`) remain independent and mandatory.
   - Non-owning runtime role `legal_dms_app` has `SELECT` only on `runtime_state` and `alembic_version`; zero DML or execute on bootstrap procedures.
   - Table locks (`LOCK TABLE clients, client_party_migration_ledger IN SHARE MODE`) held during classification prevent concurrent migration/legacy ingestion races.
8. **Future Migration Protocol:**
   Future migrations continue calling `_advance_provenance()`, and the Backend Developer adds the new revision to the Compatibility Authority, providing automatic, non-regressive forward compatibility.

---

## 5. Scope Audit & Strict Exclusions

This architecture deliverable strictly adheres to `PROJECT_WORKFLOW.md §3.1` PR 2 boundaries:

- **Files Added:** Exactly two (2) documentation files:
  1. [`ADR/0047-operational-fresh-schema-revision-compatibility.md`](file:///d:/Code/Legal_DMS_Clean/ADR/0047-operational-fresh-schema-revision-compatibility.md)
  2. [`docs/reviews/T164_Software_Architect_Report.md`](file:///d:/Code/Legal_DMS_Clean/docs/reviews/T164_Software_Architect_Report.md)
- **Zero Product Implementation:** Zero modifications to backend, frontend, classifier, or `PartyWriteGate` source code.
- **Zero Schema / Database Changes:** Zero migrations created or altered; zero database rows modified; migration frontier strictly preserved at `b155caa6d4e1`.
- **Zero Required ADR Resolutions:** Required ADRs `[12, 15, 16, 17, 20]` remain unresolved; Required ADR #20 is strictly unresolved.
- **Zero Defect Fixes Implemented:** `DEF-T163-01` and `DEF-T163-02` remain open for dedicated developer remediation.
- **Zero Acceptance Declarations:** Milestone 1 (M1) remains `NOT READY / PENDING REMEDIATION`.
- **Zero Downstream Authorizations:** T165+ remains unauthorized.
- **Zero Closeout Actions:** `PROJECT_STATE.json` and `IMPLEMENTATION_QUEUE.md` are untouched; PR 3 alone records governance closeout after PR 2 merges.

---

## 6. Validation Commands and Results

| Command | Target / Purpose | Result |
|---|---|:---:|
| `python scripts/governance_validate.py` | Repository governance consistency & ADR integrity | **PASSED** (0 warnings, 0 errors) |
| `python scripts/tests/test_governance_validate.py -v` | 68 governance validator unit tests | **PASSED** (68/68 passed in 0.11s) |
| `python scripts/delivery_calendar.py --check` | Delivery calendar schema & schedule integrity | **PASSED** (clean exit 0) |
| `git diff --check` | Whitespace and syntax diff checks | **PASSED** (clean exit 0) |

---

## 7. Handoff to Independent QA

The Software Architect role is complete. Candidate commit on branch `docs/t164-operational-fresh-schema-revision-compatibility-architecture` is ready for independent review by the Independent QA Reviewer role under `PROJECT_WORKFLOW.md §3.1`. The architect does not self-review, approve, or merge this pull request.
