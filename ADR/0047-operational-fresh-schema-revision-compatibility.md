# ADR-0047: Operational-Fresh Schema Revision Compatibility Architecture

**Status:** Proposed
**Date:** 2026-10-19
**Related task:** T164 — Operational-Fresh Schema Revision Compatibility Architecture
**Qualifies and extends:** ADR-0036 Decisions 1, 2, 3, 7; ADR-0037 Decisions 1, 2, 5, 6, 7, 9, 11. ADR-0036 and ADR-0037 remain Proposed; this ADR does not silently rewrite, accept, or close them.
**Resolves:** None (does not resolve any item from `docs/Legal_DMS — Domain Model & Functional Specification.md` §21 Required-ADR planning list).
**Does not resolve:** Required ADR #20 (migration strategy), normal Party-write eligibility for migrated installations, Client-master cutover, `matters.client_id` or `clients` retirement, compatibility-bridge removal, final migration completion, legacy cleanup, DEF-T163-02 remediation, BLK-T163-01 Electron acceptance, or Milestone 1 (M1) acceptance.

---

## 1. Problem Statement & Verified T163 Evidence

During the T163 M1 Operational Dogfooding and Acceptance Verification pass (`docs/acceptance/T163_M1_Acceptance_Report.md`, PR #314 merged as `7e5ec9e6cf47683078657d727503f6d3c535bb0c`), scenario A3.2 (dynamic Party creation via `POST /api/v1/parties`) failed closed with `HTTP 403 Forbidden`. The failure was registered as material defect **`DEF-T163-01`**:
```text
{"error": {"code": "installation_classification_error", "message": "operational provenance is unsupported"}}
```

### Verified Root Cause
Investigation of `backend/src/app/infrastructure/persistence/sqlalchemy_install_classifier.py` and the database migration history reveals the underlying architectural flaw:

1. **Stale Hardcoded Revision Constant:**
   `SqlAlchemyInstallationClassifier` defines a static constant:
   ```python
   _SUPPORTED_SCHEMA_REVISION = "cdcfd7df5fde"
   ```
   In its `_operational_transition()` check, it reads `observed_schema_revision` from `legal_dms_provenance.runtime_state` (which projects `legal_dms_provenance.installation_events`) and enforces strict equality:
   ```python
   if row["observed_schema_revision"] != _SUPPORTED_SCHEMA_REVISION:
       raise InstallationClassificationError("operational provenance is unsupported")
   ```
2. **Migration Frontier Advancement:**
   Protected `main` schema migrations advanced past `cdcfd7df5fde` (T141) through `e148c0f5a8b2` (T148) and `8d77007b9d7f` (T150) to the current protected migration frontier `b155caa6d4e1` (T155).
3. **Database Provenance Routine Behavior:**
   Each migration correctly called `_advance_provenance(from_rev, to_rev)` to update the database-side stored procedures `record_fresh_birth()` and `enter_operational_fresh()` so that future bootstrap transactions on that revision bind to the new head. When T163 deployed and bootstrapped fresh operational fixtures on current head `b155caa6d4e1`, the immutable event row recorded:
   ```text
   event_kind: 'OPERATIONAL_FRESH_ENTERED'
   provenance_contract_version: 'adr-0037.v1'
   observed_schema_revision: 'b155caa6d4e1'
   ```
4. **Classifier Breakdown:**
   At runtime, `SqlAlchemyInstallationClassifier` compared `observed_schema_revision` (`b155caa6d4e1`) against its hardcoded constant (`cdcfd7df5fde`). Finding a mismatch, it raised `InstallationClassificationError`, which `PartyWriteGate.ensure_writable()` correctly translated into `ForbiddenError` (HTTP 403).

### The Core Architectural Distinction: Historical Provenance vs. Present Compatibility
The failure stems from conflating two independent concepts:
- **Historical Installation Provenance ($R_{\text{boot}}$):** An immutable, append-only historical snapshot recording the schema revision that was verified when the privileged, one-time `OPERATIONAL_FRESH_ENTERED` bootstrap transition executed. Under ADR-0037, this value never mutates after commit, even when the database is subsequently upgraded through dozens of forward schema migrations.
- **Present Schema Compatibility ($R_{\text{curr}}$):** The live schema revision currently active in the database (recorded in `alembic_version.version_num`). This represents the actual physical database structures available to the running backend application.

`SqlAlchemyInstallationClassifier` committed two architectural errors:
1. It demanded that the historical bootstrap revision $R_{\text{boot}}$ equal a single static string (`cdcfd7df5fde`), which breaks whenever a new database is bootstrapped on a newer revision, AND breaks whenever an older database bootstrapped on an earlier revision is upgraded.
2. It failed to inspect the present schema revision $R_{\text{curr}}$ in `alembic_version` at all, creating an unverified assumption about the live database schema.

---

## 2. Alternatives Considered & Evaluation

### Alternative 1: Fixed Supported-Revision Constant Replacement
Update `_SUPPORTED_SCHEMA_REVISION = "b155caa6d4e1"` in `sqlalchemy_install_classifier.py`.
- **Trade-offs:** Minimal one-line edit.
- **Why Rejected:** Architecturally defective.
  - Breaks any legitimately operational installation that was bootstrapped at `cdcfd7df5fde` (or earlier) and subsequently upgraded to `b155caa6d4e1`. Its historical `observed_schema_revision` is `cdcfd7df5fde`; comparing that with `"b155caa6d4e1"` causes immediate failure.
  - Immediately re-breaks on the very next schema migration (e.g., T165+), requiring emergency manual code patches on every migration.
  - Continues to ignore the live `alembic_version` table, leaving downgrades, partial migrations, or unapplied migrations completely undetected.

### Alternative 2: Unconstrained Dynamic Migration Graph Ancestry
Dynamically load `alembic.script.ScriptDirectory` at runtime to check if $R_{\text{boot}}$ is an ancestor of $R_{\text{curr}}$.
- **Trade-offs:** Automatically handles arbitrary linear migration chains.
- **Why Rejected:**
  - Dynamic file-system discovery of Alembic revision files inside request-time classification hot paths adds latency, I/O overhead, and external packaging dependencies.
  - Lacks an explicit governance boundary: any arbitrary local branch or unauthorized migration script present in the directory would be accepted without architectural approval.
  - Does not define an explicit contract version or trusted set of approved revisions.

### Alternative 3: Static Revision Allow-List / Registry Only
Maintain a set of approved revisions `{"c4e7a9b2d6f1", ..., "b155caa6d4e1"}` and check if `observed_schema_revision` is in the set.
- **Trade-offs:** Simple in-memory lookup.
- **Why Rejected:** Lacks directionality. If an installation was bootstrapped at `b155caa6d4e1` and an operator subsequently downgraded the database schema to `cdcfd7df5fde`, both revisions are in the set, but the database is in an illegal downgraded state that this model fails to catch.

### Alternative 4: Coarse Provenance Contract Versioning Only
Rely solely on `provenance_contract_version == "adr-0037.v1"`.
- **Trade-offs:** High decoupling between schema revisions and provenance.
- **Why Rejected:** Far too coarse. It completely decouples runtime eligibility from schema compatibility. An installation with missing tables or an ancient incompatible schema would be admitted simply because the provenance table format has not changed.

### Alternative 5: Combined Compatibility Model (Selected Architecture)
Synthesizes four necessary, orthogonal verification layers into a single deterministic, fail-closed compatibility authority:
1. **Provenance Contract Verification:** Strict verification of `provenance_contract_version == "adr-0037.v1"`.
2. **Historical Bootstrap Eligibility:** Verification that the historical bootstrap revision $R_{\text{boot}}$ belongs to the approved canonical lineage of post-ADR-0037 provenance-supporting revisions.
3. **Present Schema Verification:** Direct query of `alembic_version.version_num` within the same transaction to verify that exactly one head exists ($R_{\text{curr}}$) and matches the running application's approved head.
4. **Directional Lineage Invariant ($R_{\text{boot}} \preceq R_{\text{curr}}$):** Strict verification that $R_{\text{boot}} == R_{\text{curr}}$ (fresh bootstrap at current head) OR $R_{\text{boot}}$ is an approved linear ancestor of $R_{\text{curr}}$ along the canonical migration path.
- **Why Selected:** Fully resolves `DEF-T163-01`; preserves immutable historical provenance; accommodates forward schema upgrades; detects downgrades and divergent forks; enforces fail-closed security; and eliminates recurring emergency patches on future migrations.

---

## 3. Decision

### 1. Trusted Compatibility Authority
A dedicated, in-memory **Schema Compatibility Authority** must be established within the backend infrastructure layer. It serves as the single trusted source of truth for schema compatibility and lineage verification during runtime installation classification.

#### Canonical Lineage Definition
The authority maintains the immutable, ordered sequence of approved post-ADR-0037 schema revisions:
```text
c4e7a9b2d6f1  (T126: Operational-fresh provenance foundation introduced)
     ↓
5d8a3f2e9c6b  (T130: Address permissions and role grants seeded)
     ↓
7f1b9c3d4a2e  (T132: Matter tenant party foundation)
     ↓
9e6a4b2c8d1f  (T135: Property tenant party ownership foundation)
     ↓
b8c4d2e1f7a9  (T137: File & document tenant foundation)
     ↓
be439c0d6fdb  (T139: File permissions and role grants seeded)
     ↓
cdcfd7df5fde  (T141: DocumentVersion storage tenant foundation)
     ↓
e148c0f5a8b2  (T148: Enquiry quotation acceptance foundation)
     ↓
8d77007b9d7f  (T150: Quotation revision issuance permit)
     ↓
b155caa6d4e1  (T155: Matter-Property tenant integrity foundation — CURRENT PROTECTED HEAD)
```

- **Current Approved Head ($R_{\text{head}}$):** `b155caa6d4e1`.
- **Supported Provenance Contract Version:** `adr-0037.v1`.
- **Approved Bootstrap Revisions ($\mathcal{R}_{\text{boot}}$):** All revisions in the canonical sequence from `c4e7a9b2d6f1` through `b155caa6d4e1` inclusive.

### 2. Historical Installation Provenance Semantics
The `observed_schema_revision` ($R_{\text{boot}}$) recorded in `legal_dms_provenance.installation_events` represents immutable historical evidence.
- An installation bootstrapped at any revision $R_{\text{boot}} \in \mathcal{R}_{\text{boot}}$ retains that identical $R_{\text{boot}}$ value forever.
- Database triggers (`installation_events_immutable`) prevent mutation, deletion, or truncation of this evidence.
- The classifier must accept any $R_{\text{boot}} \in \mathcal{R}_{\text{boot}}$ provided the directional lineage invariant holds.

### 3. Present Schema Verification Semantics
The classifier must explicitly query `public.alembic_version.version_num` on the active connection:
- Exactly one row must be returned.
- If 0 rows are returned: the schema is unversioned or unmigrated $\to$ Fail closed (`InstallationClassificationError("schema version is missing")`).
- If $>1$ rows are returned: the migration graph has multiple heads or divergent branches $\to$ Fail closed (`InstallationClassificationError("schema has multiple migration heads")`).
- The returned revision ($R_{\text{curr}}$) must equal the current approved runtime head ($R_{\text{head}} = \text{"b155caa6d4e1"}$). If $R_{\text{curr}} \ne R_{\text{head}}$, the schema is unsupported for this application release $\to$ Fail closed (`InstallationClassificationError("unsupported schema revision")`).

### 4. Directional Lineage Invariant ($R_{\text{boot}} \preceq R_{\text{curr}}$)
To preserve integrity across upgrades, the classifier evaluates the topological relationship between $R_{\text{boot}}$ and $R_{\text{curr}}$:
- **Case A (Fresh Installation at Head):** $R_{\text{boot}} == R_{\text{curr}} == \text{"b155caa6d4e1"}$. Valid.
- **Case B (Legitimately Upgraded Installation):** $R_{\text{boot}} \in \mathcal{R}_{\text{boot}}$ and $R_{\text{boot}}$ is an ancestor of $R_{\text{curr}}$ along the canonical chain. Valid.
- **Case C (Illegal Schema Downgrade):** $R_{\text{curr}}$ is an ancestor of $R_{\text{boot}}$ (i.e. $R_{\text{curr}} \prec R_{\text{boot}}$). The database was bootstrapped on a newer schema and downgraded to an older schema $\to$ Fail closed (`InstallationClassificationError("schema downgrade detected")`).
- **Case D (Divergent / Unknown Lineage):** $R_{\text{boot}}$ or $R_{\text{curr}}$ is not on the canonical path $\to$ Fail closed (`InstallationClassificationError("unsupported or divergent schema revision")`).

---

## 4. Deterministic Classifier Precedence & State Matrix

During `SqlAlchemyInstallationClassifier.classify()`, checks are executed in the following strict order:

```text
[Request Transaction Boundary]
       │
       ▼
1. Acquire SHARE lock on `clients` and `client_party_migration_ledger`
   └─ Failure / DB error ──► Fail closed (InstallationClassificationError)
       │
       ▼
2. Query `alembic_version.version_num`
   ├─ Count != 1 ──────────► Fail closed (Missing / multiple heads)
   └─ R_curr != R_head ────► Fail closed (Unsupported runtime schema revision)
       │
       ▼
3. Query `legal_dms_provenance.runtime_state`
   ├─ Count > 1 ───────────► Fail closed (Forked provenance)
   └─ Count == 1:
       ├─ installation_id is NULL ────────────────► Fail closed (Malformed)
       ├─ event_kind != 'OPERATIONAL_FRESH_ENTERED' ► Fail closed (Malformed)
       ├─ provenance_contract_version != 'adr-0037.v1' ► Fail closed (Contract mismatch)
       ├─ R_boot not in ApprovedLineage ──────────► Fail closed (Unknown bootstrap revision)
       ├─ R_curr < R_boot (Downgrade) ────────────► Fail closed (Downgrade detected)
       └─ Lineage valid (R_boot <= R_curr) ───────► Operational evidence valid
       │
       ▼
4. Contradiction Detection
   └─ Operational evidence valid AND (clients > 0 OR ledger > 0)
      └─ YES ──────────────► Fail closed (Operational provenance contradicts migration evidence)
       │
       ▼
5. State Classification Assignment
   ├─ migration_complete (ledger > 0 and ledger_covered == clients_total)
   │  └─ Return InstallationState.MIGRATED
   ├─ Operational evidence valid and no contradiction
   │  └─ Return InstallationState.OPERATIONAL_FRESH
   ├─ Any business table count > 0 (clients, addresses, properties, matters, etc.)
   │  └─ Return InstallationState.LEGACY_WITH_BUSINESS_DATA
   └─ Otherwise (no operational evidence, zero business rows)
      └─ Return InstallationState.UNPROVEN
```

### Comprehensive State Matrix

| Runtime State Condition | `R_boot` State | `R_curr` State | Business / Ledger Rows | Classifier Output | `PartyWriteGate` Action |
|---|---|---|---|---|---|
| Unreadable DB / SQL Error | Any | Any | Any | Exception (`InstallationClassificationError`) | Denied (HTTP 403) |
| Missing `alembic_version` | Any | 0 rows | Any | Exception (`InstallationClassificationError`) | Denied (HTTP 403) |
| Multi-head `alembic_version` | Any | $>1$ rows | Any | Exception (`InstallationClassificationError`) | Denied (HTTP 403) |
| Unsupported current head | Any | Not `b155caa6d4e1` | Any | Exception (`InstallationClassificationError`) | Denied (HTTP 403) |
| Forked provenance | Multiple rows | `b155caa6d4e1` | Any | Exception (`InstallationClassificationError`) | Denied (HTTP 403) |
| Invalid contract version | $\ne \text{"adr-0037.v1"}$ | `b155caa6d4e1` | Any | Exception (`InstallationClassificationError`) | Denied (HTTP 403) |
| Unknown bootstrap revision | Not in lineage | `b155caa6d4e1` | Any | Exception (`InstallationClassificationError`) | Denied (HTTP 403) |
| Schema Downgrade | $R_{\text{boot}} \succ R_{\text{curr}}$ | $R_{\text{curr}} \in \text{lineage}$ | Any | Exception (`InstallationClassificationError`) | Denied (HTTP 403) |
| Provenance Contradiction | $R_{\text{boot}} \preceq R_{\text{curr}}$ | `b155caa6d4e1` | `clients > 0` or `ledger > 0` | Exception (`InstallationClassificationError`) | Denied (HTTP 403) |
| Migration Complete | None | `b155caa6d4e1` | `ledger > 0`, covered == clients | `InstallationState.MIGRATED` | Denied pending ADR #20 (HTTP 403) |
| **Valid Fresh (Current Head)** | `b155caa6d4e1` | `b155caa6d4e1` | 0 clients, 0 ledger, new-domain data permitted | **`InstallationState.OPERATIONAL_FRESH`** | **Eligible (Proceeds to RLS/RBAC)** |
| **Valid Upgraded Fresh** | `cdcfd7df5fde` (or earlier) | `b155caa6d4e1` | 0 clients, 0 ledger, new-domain data permitted | **`InstallationState.OPERATIONAL_FRESH`** | **Eligible (Proceeds to RLS/RBAC)** |
| Legacy with Data | None | `b155caa6d4e1` | `clients > 0` or legacy business rows | `InstallationState.LEGACY_WITH_BUSINESS_DATA` | Denied (HTTP 403) |
| Empty without Provenance | None | `b155caa6d4e1` | All business tables 0 rows | `InstallationState.UNPROVEN` | Denied (HTTP 403) |

---

## 5. Security & Transaction Invariants

1. **PartyWriteGate Default-Deny Invariant:**
   `PartyWriteGate.ensure_writable()` strictly permits ordinary Party create/update/delete mutations ONLY when `classify()` returns `InstallationState.OPERATIONAL_FRESH`. Every other state (`UNPROVEN`, `LEGACY_WITH_BUSINESS_DATA`, `MIGRATED`) and all classification errors raise `ForbiddenError` (HTTP 403).
2. **Strict RLS & Tenant Scoping:**
   `OPERATIONAL_FRESH` is strictly an installation-level prerequisite. Passing the gate grants no bypass of:
   - Authenticated Organization context (`app.current_organization_id`).
   - Tenant isolation policies (`FORCE ROW LEVEL SECURITY`).
   - RBAC permission checks (`parties:write`, `parties:delete`).
   - Same-organization reference integrity (e.g. `address_id`).
3. **Runtime Non-Owning Privilege Isolation:**
   The application runtime database role (`legal_dms_app`) remains strictly non-owning, non-superuser, with `NOBYPASSRLS`. It holds `SELECT` privileges only on `legal_dms_provenance.runtime_state` and `alembic_version`. It has zero DML (`INSERT`, `UPDATE`, `DELETE`) on provenance tables and zero execute privileges on database bootstrap routines.
4. **Transaction & Concurrency Safety:**
   Classification runs inside the same database session and transaction as the ensuing write operation. Table locks (`LOCK TABLE clients, client_party_migration_ledger IN SHARE MODE`) prevent concurrent legacy data ingestion or migration execution from creating a time-of-check to time-of-use (TOCTOU) fail-open race.

---

## 6. Future Migration Compatibility Rules (Governance Protocol)

To ensure future tasks (e.g., T165+) never re-introduce `DEF-T163-01`:

1. **Database Migration Standard:**
   Every new schema migration that advances the sole Alembic head from $R_{\text{old}}$ to $R_{\text{new}}$ must continue invoking `_advance_provenance(from_revision=R_old, to_revision=R_new)` in its `upgrade()` function (and the reverse in `downgrade()`). This ensures database-side bootstrap procedures bind to the new head for future clean-install deployments.
2. **Backend Compatibility Authority Synchronization:**
   When a migration PR merges, the Backend Developer must add $R_{\text{new}}$ as the new head in the Schema Compatibility Authority's canonical sequence.
3. **Continuous Forward Compatibility:**
   Because the compatibility model verifies directional ancestry ($R_{\text{boot}} \preceq R_{\text{curr}}$), installations bootstrapped on earlier revisions (`c4e7a9b2d6f1`, `cdcfd7df5fde`, `b155caa6d4e1`) remain permanently recognized as `OPERATIONAL_FRESH` when upgraded to $R_{\text{new}}$ without needing database-side data updates.

---

## 7. Required Implementation Test Matrix (for Subsequent Implementation Task)

When the subsequent implementation task is commissioned, the following test scenarios must be executed and verified against isolated PostgreSQL targets:

| Scenario ID | Test Condition | Expected Classifier State | Expected Gate Behavior |
|---|---|---|---|
| **T-REV-01** | Fresh bootstrap on `b155caa6d4e1` ($R_{\text{boot}} = R_{\text{curr}} = \text{"b155caa6d4e1"}$) | `OPERATIONAL_FRESH` | Party write permitted |
| **T-REV-02** | Historical bootstrap on `cdcfd7df5fde`, upgraded to `b155caa6d4e1` | `OPERATIONAL_FRESH` | Party write permitted |
| **T-REV-03** | Historical bootstrap on `c4e7a9b2d6f1`, upgraded to `b155caa6d4e1` | `OPERATIONAL_FRESH` | Party write permitted |
| **T-REV-04** | Historical bootstrap on intermediate revisions (`5d8a3f2e9c6b`, `7f1b9c3d4a2e`, etc.), upgraded to `b155caa6d4e1` | `OPERATIONAL_FRESH` | Party write permitted |
| **T-REV-05** | Legitimately accumulated Party and Address business rows in valid operational-fresh DB | `OPERATIONAL_FRESH` | Status preserved; write permitted |
| **T-REV-06** | Schema downgrade: bootstrapped at `b155caa6d4e1`, DB schema downgraded to `cdcfd7df5fde` | Exception (`InstallationClassificationError`) | Denied (HTTP 403) |
| **T-REV-07** | Unknown current schema revision (e.g. unapproved branch head) | Exception (`InstallationClassificationError`) | Denied (HTTP 403) |
| **T-REV-08** | Multi-head `alembic_version` table ($>1$ rows) | Exception (`InstallationClassificationError`) | Denied (HTTP 403) |
| **T-REV-09** | Empty `alembic_version` table (0 rows) | Exception (`InstallationClassificationError`) | Denied (HTTP 403) |
| **T-REV-10** | Contradiction: valid operational provenance present but `clients > 0` | Exception (`InstallationClassificationError`) | Denied (HTTP 403) |
| **T-REV-11** | Contradiction: valid operational provenance present but `client_party_migration_ledger > 0` | Exception (`InstallationClassificationError`) | Denied (HTTP 403) |
| **T-REV-12** | Migrated DB (`client_party_migration_ledger` complete) | `MIGRATED` | Denied pending ADR #20 (HTTP 403) |
| **T-REV-13** | Legacy DB with `clients` rows, no provenance | `LEGACY_WITH_BUSINESS_DATA` | Denied (HTTP 403) |
| **T-REV-14** | Empty unmigrated DB without provenance events | `UNPROVEN` | Denied (HTTP 403) |
| **T-REV-15** | Malformed provenance contract (`provenance_contract_version = "adr-0037.v2"`) | Exception (`InstallationClassificationError`) | Denied (HTTP 403) |
| **T-REV-16** | End-to-end `POST /api/v1/parties` dynamic creation against live `b155caa6d4e1` schema | HTTP 201 Created | Verifies resolution of `DEF-T163-01` |

---

## 8. Relationship to Existing ADRs

- **ADR-0020 (Session Commit/Rollback Policy):** Preserved; classification and writes occur within the managed request session transaction.
- **ADR-0021 (Organization Tenant Boundary & FORCE RLS):** Preserved; tenant isolation and RLS policies remain strictly independent of installation classification.
- **ADR-0022 (Authorization Architecture & RBAC):** Preserved; `parties:write` permission remains mandatory.
- **ADR-0036 (Fresh Installation Party Enablement Boundary):** Preserved; zero-row testing remains bootstrap-only; operational installations do not revert to legacy on business row accumulation.
- **ADR-0037 (Operational-Fresh Installation Provenance):** Clarified and extended; establishes the directional compatibility model bridging historical bootstrap revision and live schema head without modifying ADR-0037's database table definitions.
- **ADR-0042 (Request Transaction Outcome & Side Effect Compensation):** Preserved; pre-response finalization and transaction boundaries remain fail-closed.
- **ADR-0045 (Protected Merge Completion & Governance Closeout):** Preserved; lifecycle boundaries remain strictly three PRs.
- **ADR-0046 (Risk-Proportional Independent QA):** Preserved; implementation of this architecture will require Comprehensive QA due to security and migration-boundary sensitivity.

---

## 9. Residual Risks & Mitigations

1. **Risk:** Future schema migrations fail to update the Compatibility Authority.
   - **Mitigation:** Governed CI integration tests (`T-REV-01`, `T-REV-02`) run on every PR and assert that the current Alembic head is registered in the authority.
2. **Risk:** Manual database tampering by database superuser.
   - **Mitigation:** The database owner/superuser is inside the administrative trust boundary per ADR-0037 §10; tampering cannot be completely prevented by application-level code, but database triggers reject runtime mutations.
3. **Risk:** Unhandled duplicate matter number defect (`DEF-T163-02`).
   - **Mitigation:** Explicitly declared out of scope for T164; preserved in the defect backlog for dedicated Developer remediation.

---

## 10. Strict Exclusions & Scope Boundaries

This architecture PR 2:
- Does NOT contain backend, frontend, classifier, or `PartyWriteGate` implementation code.
- Does NOT alter database schema, Alembic migrations, or provenance tables.
- Does NOT modify live database rows.
- Does NOT resolve Required ADR #20 or any other Required ADR (`[12, 15, 16, 17, 20]` remain unresolved).
- Does NOT resolve or fix `DEF-T163-02`.
- Does NOT perform Electron acceptance (`BLK-T163-01`).
- Does NOT declare Milestone 1 (M1) accepted (M1 remains NOT READY / PENDING REMEDIATION).
- Does NOT authorize T165+ or close out T164.
