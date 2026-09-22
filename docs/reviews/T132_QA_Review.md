# QA Reviewer — Independent QA of T132 PR #236 Verification Report

1. **Reviewed PR Number:** 236
2. **Exact Reviewed Remote Head:** `93b4d7e6791f7a9b9042b1ebfd1a57ffd70386fc`
3. **Base SHA:** `c25cf58b17fd586e110d57d52540db16a7b4e341`
4. **Authorization Verification:** Verified. `latestTaskAuthorized = T132`, `latestTaskDone = T131`, `inProgressTransitions = []`. PR implements exactly the T132 scope without overreach.
5. **Changed-file Verification:** Verified. The exact expected 12 files were changed. The corrections `f655ef34` and `93b4d7e6` legitimately updated historical test fixtures to correctly align with the new schema contracts without concealing real application defects.
6. **Architecture Assessment:** Passed. Safely maintains Client as a legacy compatibility shadow. No destructive retirement occurred. Required ADR #20 and Matter `property_id` logic remain untouched.
7. **Migration Assessment:** Passed. `Matter.organization_id` cleanly upgraded to `NOT NULL`. Ownership derivation exclusively cascades from `Matter.client_id -> Client.organization_id`. `MatterParty`, `Party`, and `Property` were properly avoided as alternative synthetic backfill sources.
8. **Retained-data Scenario Results:** Passed. The migration successfully fails closed rather than synthesizing missing organizational context.
9. **Matter/client Compatibility Assessment:** Passed. `Matter.client_id` remains an intact FK for compatibility. 
10. **Party-canonical Operational-fresh Result:** Passed. An operational-fresh Matter can legally instantiate with a `NULL` `client_id` without fabricating a phantom `Client` record.
11. **Same-organization Integrity Result:** Passed. Same-tenant schema integrity flawlessly enforced for `Matter <-> Client`, `MatterParty <-> Matter`, and `MatterParty <-> Party` using composite Postgres FKs.
12. **RLS Result:** Passed. Both `matters` and `matter_parties` enforce Row Level Security utilizing the correct `app.current_organization_id` GUC pattern across SELECT, INSERT, UPDATE, and DELETE.
13. **Runtime-role Result:** Passed. Verified `legal_dms_app` acts strictly as `NOBYPASSRLS` and respects cross-tenant isolations under the active GUC boundaries.
14. **Provenance-function Result:** Passed. Explicitly advanced schema revision literal from `5d8a3f2e9c6b` to `7f1b9c3d4a2e` via identical function replacement logic.
15. **Classifier Result:** Passed. The SQLAlchemy installation classifier strictly relies upon the new `7f1b9c3d4a2e` boundary.
16. **Upgrade Result:** Passed. Schema strictly conforms.
17. **Downgrade Result:** Passed. Evaluated via direct scratch testing. By attempting to reset `client_id` to `NOT NULL`, downgrades against a database containing an operational-fresh Matter (where `client_id` is genuinely `NULL`) will fail transactionally in PostgreSQL, ensuring `Client` identity is never nefariously synthesized to facilitate a downgrade.
18. **Focused Test Counts:** 3 new integration tests written.
19. **Full-suite Count:** `test_matter_tenant_party_foundation.py`, `test_tenant_schema_foundation.py` + 4 other integration suites ran. Found exactly **4 failing tests** in `test_operational_fresh_provenance.py`.
20. **Ruff Result:** Clean (`0` errors).
21. **Black Result:** Clean.
22. **Diff-check Result:** Clean.
23. **Exact-head CI Result:** Corroborated green via GitHub Actions (Backend, Frontend, Governance, Release). *Note: The CI backend workflow limits scope to `tests/unit`, masking the integration suite failures observed in QA.*
24. **Scope/exclusion Verification:** Verified. No T133+ work included.
25. **Required ADR #20 Status:** Verified as safely Unresolved.
26. **ADR-0039 Status:** Verified as Proposed.
27. **T132 Governance Status:** Authorized / Not Done.
28. **T133+ Authorization Status:** Unauthorized.
29. **Blocking Findings:**
   - **Defect (Test configuration drift):** `backend/tests/integration/test_operational_fresh_provenance.py` unconditionally asserts against the old schema revision (`HEAD = "5d8a3f2e9c6b"`) inside its tests, which results in `AssertionError: assert [('FRESH_BIRT...f1b9c3d4a2e')] == [('FRESH_BIRT...d8a3f2e9c6b')]` upon execution. The developer successfully updated the literal inside the `test_install_classifier.py` and `synthetic_migration.py` but missed this suite.
30. **Non-blocking Observations:** The underlying migration and schema implementation are flawless. CI passed due to its limitation to unit tests, demonstrating the necessity of full independent integration QA.
31. **Formal QA Verdict:** **Rework required**.

**Required Rework:**
Please correct the `HEAD` variable inside `backend/tests/integration/test_operational_fresh_provenance.py` to `7f1b9c3d4a2e` to match the newly established schema boundary. No application or migration code changes are required.
