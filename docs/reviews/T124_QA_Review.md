# T124 QA Review

**Task:** T124 -- Tenant-Safe Party Application Surface & Fresh-Install Enablement
**Role:** QA Reviewer
**Artifacts under review:** PR #217

## 1. Verified Baseline and Authorization Ancestry
- **Baseline:** `01bae6f2aca43b41612da1ab3a818ddaa482ca06` (verified as ancestor).
- **PR Head:** `72fd061729b30345d15a8a98be75634148a33cad` (exact head reviewed).
- **Governance:** `latestTaskDone = T123`, `latestTaskAuthorized = T124`. ADR-0036 remains Proposed, Required ADR #20 is unresolved. T125+ is unauthorized.

## 2. Diff and Scope Audit
- 22 changed files natively reported by Git. The developer's report of "21 implementation files" accurately maps to this count once accounting for the single documentation artifact (`Phase22.md`).
- **Scope Analysis:** All file changes strictly belong to: Permission Migrations, Application Domain (Service, Gate, Classifier, Repository), API Routes, Support/Infrastructure logic, and Integrated Tests. No out-of-bounds redesigns occurred.

## 3. Migration and Permissions Verification
- Migration `1b8f4a9c2e6d` cleanly succeeds `62cadaff2571`.
- Accurately creates 3 permissions (`parties:read`, `parties:write`, `parties:delete`).
- Seeds 12 associations logically across roles matching repository conventions (18 -> 21 permissions, 59 -> 71 associations).

## 4. API and Organization Scoping
- **RequirePermission:** Correctly enforced across all `/parties` routes. Read does not grant write; missing permissions yield robust `ForbiddenError`.
- **Tenant Spoof Resistance:** `PartyService` inherently derives `organization_id` strictly from context. A caller cannot smuggle a custom Organization ID through the REST body to bypass scoping.
- **Address Integrity Validation:** Cross-tenant address payloads result cleanly in API `422 Unprocessable Content` gracefully governed by `PartyService`, preserving integrity correctly.
- **Partial Updates:** PUT intentionally performs partial updating relying on `model_fields_set`. Though conventionally `PATCH` dominates this space, the behavior is explicitly documented and poses no structural or architectural hazard here.

## 5. ADR-0036 Classifier and PartyWriteGate Assessment
- The `InstallationClassifier` relies strictly on live DB row counts. It checks 11 governing tables precisely, excluding `parties` exactly as defined, correctly ignoring environment flags.
- **PartyWriteGate:** Architecturally correct. It dynamically verifies state prior to any database Party mutation, strictly granting access solely to `FRESH` installations. 
- **MIGRATED Semantics:** As ADR-0036 bounds T124 exclusively to fresh installation enablement, `PartyWriteGate` appropriately locks legacy/migrated states pending resolution of Required ADR #20's legacy cutover logic.
- **TOCTOU / Lifecycle Safety:** Execution is scoped transactionally and safe from race-condition stale classifications. 
- Creating an initial Party gracefully leaves the installation characterized as `FRESH` to properly allow subsequent writes.

## 6. Development DB Deviation Finding
- The developer reported the shared database was systematically updated to `1b8f4a9c2e6d`. While this operation was completely safe and logically necessary to test the permissions schema downstream, the repository history contains no durable artifact of explicit prior authorization allowing deviation from the standard isolated-disposable-DB rule. This is recorded as a process deviation per review guidelines, but poses no defect to the underlying code correctness.

## 7. QA Results and Tests
- Focused integration tests (`test_party_routes.py`, `test_install_classifier.py`, `test_synthetic_migration_rehearsal.py`, etc.) execute green natively. T119 rehearsal updates strictly enforce the non-null `addresses.organization_id` schema rule. 
- No T118 or T122 backward compatibility issues introduced.
- Linter suites (`ruff`, `black`) and `governance_validate.py` (0 errors) successfully passed locally.
- Exact-head CI passed on all metrics (Backend, Frontend, Governance, Release Build).

## 8. QA Decision

**Decision: Approved**
