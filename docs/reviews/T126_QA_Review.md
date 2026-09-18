# T126 QA Review

**Task:** T126 -- Operational-Fresh Provenance Persistence and Bootstrap Foundation
**Role:** QA Reviewer
**Artifacts under review:** PR #222
**Exact reviewed head:** `929709e47ff85606fda5eb765b02d21bdac853da`

## 1. Governance and Remote State Verification
- PR #222 is OPEN and unmerged, accurately targeting `main` at `086978b770292c8e067e7a8da3f7a5b34060dd9f` (T126 authorization baseline).
- The exact implementation head `929709e47ff85606fda5eb765b02d21bdac853da` descends directly from the authorization commit.
- T126 is authorized but not Done. T127+ remains unauthorized.
- Required ADR #20 is unresolved and ADR-0036 remains Proposed.

## 2. Diff and Scope Audit
- 11 files changed exactly matching the expected diff. 
- No hidden integrations (Classifier/PartyWriteGate), frontend surfaces, Address/Matter implementations, or ADR status changes were included. The behavior is fundamentally inert regarding existing app authorization logic, preserving T124 exact functionality.

## 3. New-Install vs Upgrade Distinction
- **Upgrades:** Upgrading an existing DB (or a legacy-shaped DB) strictly adds schema support (tables/triggers/functions) but completely omits `FRESH_BIRTH` or `OPERATIONAL_FRESH_ENTERED`. Existing databases remain reliably `UNPROVEN`.
- **Initial Install:** The guarded `fresh_install_provenance.py` locks a serializable transaction, strictly verifies `relkind IN ('r', 'p', 'v', 'm')` is completely empty within the `public` schema (blank target), injects a temporary pg_temp guard, performs schema generation, and explicitly writes the `FRESH_BIRTH` event within the same atomic commit.

## 4. Privilege Boundary & Provenance Integrity
- **Privilege Enforcement:** The `legal_dms_app` runtime role is firmly restricted via `REVOKE ALL` and `GRANT SELECT ON _SCHEMA.runtime_state`. It maintains `NOSUPERUSER` and `NOBYPASSRLS`. Tests independently verify `legal_dms_app` cannot `INSERT/UPDATE/DELETE` events or `EXECUTE` the bootstrap function.
- **Bootstrap Execution:** Relegated exclusively to `legal_dms_bootstrap` with narrow schema/execute access.
- **Data Mutability:** A robust PostgreSQL trigger (`reject_event_mutation`) intercepts any `UPDATE` or `DELETE` attempt against `installation_events`, making the provenance immutable even to privileged DML without dropping triggers (within the DB owner boundary).

## 5. Bootstrap Predicate & Serialization
- The bootstrap execution utilizes a precise advisory lock (`pg_advisory_xact_lock`) ensuring serialized execution. Concurrent attempts natively yield exactly one `OPERATIONAL_FRESH_ENTERED` transition, with the second safely observing idempotency.
- The SQL-level predicate accurately counts 12 distinct legacy tables (`parties` inclusive), natively blocking transition if *any* business record is inserted before the gate executes. Tests cleanly assert a rollback if a `parties` record arrives first.
- Revisions are safely enforced. Upgrading beyond `c4e7a9b2d6f1` without adjusting the bootstrap logic gracefully trips the `alembic_version` mismatch trigger (failing closed).

## 6. Migration Contradictions & Alembic
- The Alembic structure cleanly provides downgrade support (`DROP SCHEMA CASCADE`).
- All integrations, legacy behavior, and migration contradictions correctly fail closed through the strict 12-table `COUNT(*) <> 0` verification sequence inside `enter_operational_fresh`.

## 7. Retained Development DB and RLS
- The existing dev db boundary was strictly preserved. `legal_dms_dev` gains no provenance out of bounds.
- T123 Party RLS, T124 gating, and T122 Tenant GUC rules remain strictly unmodified and continue fully enforcing zero-leak isolation across tenants. 

## 8. Exact-Head CI and Governance Checks
- All exact-head GitHub CI checks map correctly:
  - Backend validation (Pass)
  - Frontend validation (Pass)
  - Release build (Pass)
  - Governance consistency (Pass)
- Independent tests confirm the 7 targeted T126 integration tests are green.

## 9. QA Verdict

**Decision: Approved**
- The exact reviewed implementation head safely satisfies T126.
- The classifier and PartyWriteGate integrations remain future authorized work natively untouched by this slice. No residual defects were detected against the ADR-0037 contract framework.
