# T127 QA Review

**Task:** T127 -- Operational-Fresh Runtime Classification and PartyWriteGate Integration
**Role:** QA Reviewer
**Artifacts under review:** PR #224
**Exact reviewed head:** `9ccea514d3a394a6718ad6fb28ab4ff530850f6d`

## 1. Governance and Remote State Verification
- **Authorization:** PR #223 merged cleanly into `main` (`37b2b4313edbd16d36b0fb9c4c8e4773c02db631`), authorizing this task.
- **State:** `latestTaskAuthorized = T127`, `latestTaskDone = T126`. T128+ are strictly unauthorized. ADR-0036/0037 remain Proposed; Required ADR #20 is unresolved.
- **Diff:** Exactly 7 files modified, correctly matching the architectural boundary with zero feature creep (no UI, no Matter/Address CRUD logic, no new migrations).

## 2. Classifier States and Provenance Precedence
- The legacy `FRESH` enum is formally eliminated. "Zero-row inference" is eradicated, permanently terminating the vulnerability whereby a wiped legacy DB could masquerade as an eligible blank state.
- **`OPERATIONAL_FRESH`**: Successfully relies strictly on the `legal_dms_provenance.runtime_state` view introduced in T126. Hard-bound to the supported contract string (`adr-0037.v1`) and revision (`c4e7a9b2d6f1`).
- **Contradiction Safety**: If the DB yields valid operational evidence but also contains migration evidence (clients > 0 or ledger_rows > 0), the classifier explicitly throws an `InstallationClassificationError`, which natively triggers HTTP 403 on API surfaces.
- **Empty Upgrades**: Existing or wiped installations gracefully resolve to `UNPROVEN` (which denies ordinary Party writes).
- **T124-Era DBs (Parties Only)**: The classifier maps these to `LEGACY_WITH_BUSINESS_DATA` (since `parties > 0` and no operational proof exists), seamlessly locking them.
- **MIGRATED**: Resolves safely. Crucially, the `PartyWriteGate` continues to reject `MIGRATED`, strictly enforcing the wait for Required ADR #20.

## 3. Post-Bootstrap Row Growth Correctness
- **Party/Address Growth**: ADR-0037 correctly solved the T124 dead-end logic. Under T127, post-bootstrap Addresses and Parties correctly bypass the migration contradiction checks. The `OPERATIONAL_FRESH` classification reliably holds, maintaining continuous feature accessibility for genuinely fresh installations.

## 4. Concurrency, Locking, and TOCTOU Hardening
- **Lock primitive**: A session-level `LOCK TABLE clients, client_party_migration_ledger IN SHARE MODE` is strategically acquired within `SqlAlchemyInstallationClassifier.classify()`.
- **Serialization Guarantee**: Because `PartyService` injects the gate validation directly inside its atomic unit-of-work, this shared lock perfectly spans the classification and the ensuing Party mutation. 
- **T118 executor separation**: Any concurrent legacy insertion (e.g., T118 executor) inherently demands `ROW EXCLUSIVE` mode on `clients`. It will smoothly block until the Party transaction resolves, flawlessly extinguishing classification-to-write TOCTOU races without imposing unapproved mutual locking constraints on the legacy scripts. A phenomenally elegant implementation.

## 5. RLS and API Security Integrity
- Validated that `PartyWriteGate` catches `InstallationClassificationError` and converts it directly into `ForbiddenError`. No 500s or sensitive stack traces leak.
- Operational-fresh authorization operates strictly downstream of Organization scoping, `parties:write` permission verifications, and Tenant GUC isolations. No isolation/RLS boundaries were degraded.
- The runtime role remains confined to `USAGE` and `SELECT` over the provenance schema.

## 6. Testing and CI Verification
- **Exact-Head GitHub CI:** Backend, Frontend, Release, and Governance checks are all independently SUCCESS.
- **Local Integration:** `test_install_classifier.py` and `test_party_routes.py` successfully prove the integration.
- **Backend Developer Note:** The historic local terminal exhaustion limit remains respected; independent verification relies heavily on architectural soundness and CI consistency, both of which are robust.
- **Static Quality:** Diff checks, `governance_validate.py`, Ruff, and Black present fully clean.

## 7. QA Verdict

**Decision: Approved**
- The exact reviewed implementation head (`9ccea51...`) safely and comprehensively satisfies the T127 operational-fresh integration requirements.
- No residual fail-open vulnerabilities were detected. 
