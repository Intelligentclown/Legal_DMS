# T122 QA Review

**Task:** T122 -- Address Tenant Finalization and RLS Foundation
**Role:** QA Reviewer, per `docs/prompts/QAReviewer.md`
**Artifacts under review:** PR #213

## 1. Verified Baseline and Authorization Ancestry
- Evaluated against base `1d4db1460ccb251dce06cb769200786fa2b38e61`.
- Reviewed exact PR HEAD `443655fc899b19abee76e9fd12e29bc4eb9be146`.
- Confirmed authorization commit `5ec972177606517788b92feea8b9861e84d845b0` is a genuine ancestor.

## 2. Independent Governance Checks
- T122 is the latest authorized task.
- T123+ remains unauthorized.
- Required ADR #20 remains unresolved. ADR-0036 remains Proposed (not silently finalized here).
- No Party CRUD/RLS, Party permission, or Client/legacy retirement implementation was included. Scope exactly fits T122.

## 3. Scope and Implementation Validation
- Verified changed files: `backend/alembic/versions/9c4a7e2d1b5f_address_tenant_finalization_rls.py`, `backend/src/app/infrastructure/persistence/models/client.py`, `Phase20.md`, and tests.
- **Migration `9c4a7e2d1b5f`:** 
    - Correctly specifies `f3b7c9d1e2a4` as parent.
    - `addresses.organization_id` cleanly transitioned to `NOT NULL`.
    - No implicit ownership inferences, deletions, or data resets were attempted.
    - Existing `(organization_id, id)` support key and foreign keys remain preserved.
    - `ENABLE ROW LEVEL SECURITY` and `FORCE ROW LEVEL SECURITY` were applied successfully.
    - Select, Insert, Update, Delete policies were accurately established using `NULLIF(current_setting('app.current_organization_id', true), '')::uuid` to ensure safe GUC fallbacks.
    - `WITH CHECK` clauses correctly block a session acting on behalf of Organization A from writing or moving an Address into Organization B.
- **Downgrade verification:** Safely removes the policies, removes `FORCE`/`ENABLE RLS`, and restores the column to nullable, cleanly recovering the T120 state.

## 4. Disposable Database Fail-Closed Validation
- Successfully ran the fail-closed sequence. An `addresses` row instantiated on `f3b7c9d1e2a4` with `organization_id = NULL` unequivocally and cleanly fails the Alembic upgrade to `9c4a7e2d1b5f` with PostgreSQL returning a `contains null values` error. It correctly failed closed instead of proceeding silently or wiping data.

## 5. RLS and Same-Organization Behavioral Results
- `test_address_tenant_finalization_and_rls.py` explicitly tests the `legal_dms_app` runtime role under concurrent conditions, confirming:
    - RLS is fully forced in the catalog.
    - Empty or unset GUC defaults to deny.
    - Read/write access strictly adheres to the provided `current_organization_id`.
    - Cross-tenant mutations (moves) are aborted.
- Same-Organization FK regression was confirmed unharmed. The composite integrity previously established continues to defend Party, Client, and Property address assignments.
- Tenant GUC scoping mechanisms passed stress coverage for commits, rollbacks, and connection reuse, preventing cross-leakage.

## 6. Test-Support Adjustments & T119 / T115 Verification
- **Test Support (`provision_disposable_database_with`):** Parameterizing the target revision logically supports the T119 rehearsal pinning to `f3b7c9d1e2a4`. This accurately preserves the rehearsal's required "pre-T122 legacy database" environment without blocking future head tests. 
- **T122 Current-Head Coverage:** Assured via the `test_address_tenant_finalization_and_rls.py` suite, which explicitly boots disposable databases directly to `head` and exercises the current behavior. No regression coverage was lost.
- **T115 Test Exclusion:** The exclusion of `addresses` from `STAGED_NULLABLE_TABLES` in `test_tenant_schema_foundation.py` is semantically correct. As of T122, `addresses` is explicitly no longer a staged-nullable tenant table.
- **Offline Alembic Verification:** Re-verifying `alembic upgrade f3b7c9d1e2a4:9c4a7e2d1b5f --sql` successfully generates standard SQL. The noted full-history JSONB literal-rendering limitation fails in `9963e15f2752_seed_lookup_data.py` — it is indeed pre-existing and does not block range-scoped upgrades.

## 7. CI and Regression Tools
- Exact-head CI run: Backend, Frontend, and Governance checks are cleanly passing.
- Local executions: 33 localized tests passed safely within 11.6 seconds. `governance_validate.py` returned 0 errors.

## 8. QA Decision

**Decision: Approved**
