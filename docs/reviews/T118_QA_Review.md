# T118 QA Review

**Task:** T118 -- Party/Client Backfill Executor
**Role:** QA Reviewer, per `docs/prompts/QAReviewer.md`
**Artifacts under review:** PR #205

## 1. Verified Baseline and Authorization Ancestry
- Evaluated against base `32e5ea960f2d0a614d0e5867704d3cb1cfeab559`.
- Reviewed exact PR HEAD `090c0d26c1dbc83e63de673751c4002efa8e1a03`.
- Confirmed authorization commit `8e32d9625d3f1e4eaa0138fa42d9b34fa9714753` is a genuine ancestor.

## 2. Independent Governance Checks
- `PROJECT_STATE.json` correctly declares `latestTaskAuthorized = T118` and `latestTaskDone = T117`.
- Required ADR #20 remains unresolved globally.
- T119+ remains unauthorized.
- **Authorization Wording Assessment:** Evaluated the exclusion of "Party business rows and Party CRUD/API/services". This is confirmed to mean standard application-level Party creation. The executor's creation of Party rows explicitly for migration complies with the first paragraph of the authorization and does not pose an authorization contradiction.

## 3. Scope and Implementation Validation
- Verified changed files: `IMPLEMENTATION_QUEUE.md`, `PROJECT_STATE.json`, `pyproject.toml`, `client_migration_executor.py`, and `test_client_migration_executor.py`. No extraneous files were modified.
- No schema/Alembic changes, no API route generation, no RLS/permission updates, no Client retirement, and no schema hardening occurred.

## 4. Executor Architecture and Safety
- **T110/T111 Gating:** The executor properly calls `run_live_reconciliation_staleness_preflight` and explicitly blocks any writes if the artifact is stale, invalid, or non-executable. Organization existence is also verified prior to anchor commit.
- **Dry-run/Write Safety:** The default behavior is a dry-run (transaction rollback). Explicit `--write` is required for persistence. Logging does not bleed sensitive Aadhaar/PAN data.
- **Atomic Anchor Transaction:** Each anchor execution commits atomically with Party, staging, MatterParty, bridges, and ledger entry, or rolls back entirely.

## 5. Migration Business Logic
- `Party.id` correctly equals legacy `Client.id`.
- MatterParty is bounded correctly to `role = 'client'`.
- The 5 direct Party bridge targets correctly receive the mapped identity without losing `client_id`.
- Organization staging populates properties, matters, appointments, invoices, payments, client contacts, and addresses consistently based purely on the exact artifact decision.

## 6. CRITICAL: Source Fingerprint Contract Defect
A severe defect exists in how `source_fingerprint` and identical-completion are verified, violating ADR-0034.

**Finding:** The executor computes `fingerprint` using only the frozen snapshot from the T108 JSON artifact (`hashlib.sha256(canonical_json(snapshot)...)`). It completely ignores the LIVE database `Client` row's current `version` or `updated_at`. When a retry runs, the executor fetches the ledger and only checks if `ledger.source_fingerprint == fingerprint`. 

Because both values stem from the static artifact, modifying the live `Client` row (incrementing its version or updating its timestamp) does *not* alter the computed fingerprint. A subsequent execution run will incorrectly classify the modified legacy Client as `already_completed` rather than correctly rejecting it as a hard collision/stale input.

**Requirement (ADR-0034):** The source fingerprint string must be dynamically derived from the *live* legacy row's `version` and `updated_at` (or they must participate structurally in the ledger unique key and the identical-completion equality check) so that any change in the execution-time anchor basis forces a fail-closed basis collision.

## 7. QA Decision
Due to the failure to bind the ledger's identical-completion logic to the live anchor's version/timestamp, the migration executor cannot guarantee idempotency against mutating legacy data.

**Decision: Rework required**

### Required Remediation
1. Update `backend/src/app/infrastructure/cli/client_migration_executor.py` so that the ledger's `source_fingerprint` or `already_completed` equality check binds tightly to the live `Client.version` and `Client.updated_at` (not just the artifact's frozen snapshot representation).
2. Ensure that a change to the live `Client` row's version/timestamp correctly causes a fail-closed rejection on retry rather than returning an `already_completed` no-op.
3. Update tests to cover this mutation scenario.
4. Push the fix to the PR branch and request a re-review.


---
## 8. QA Re-Review

**Date:** 2026-09-08
**Re-Review Target:** PR #205 at `090c0d26c1dbc83e63de673751c4002efa8e1a03`
**Prior Blocking Defect:** Replay could be incorrectly classified as `already_completed` after the live legacy Client row changed, because the old fingerprint came only from the frozen T108 snapshot.

### Remediation Verification
- **Ancestry:** The remediation commits `93c2f51` and `090c0d2` correctly descend from the previous QA evidence commit `b65f5b9...`.
- **Scope:** Changes were strictly limited to the executor file, its test file, and the Stage3/Phase17 implementation log.
- **Source Fingerprint Fix:** Verified. `client_source_fingerprint()` now derives the canonical fingerprint dynamically from the *live* legacy row (`client.id`, `client.version`, `_canonical_updated_at(client.updated_at)`). The executor uses this live fingerprint for both the execution-time ledger entry and the identical-completion check.
- **Timestamp Canonicalization:** Verified `_canonical_updated_at()`. It accurately converts timezone-aware objects to UTC and sets naive datetimes to UTC before formatting to a deterministic `YYYY-MM-DDTHH:MM:SS.ffffffZ` string, preventing false basis-collisions from mere timezone representation differences.
- **Mutation Replay Check:** A change to the live `Client` row (`version` increment or `updated_at` mutation) forces a new live fingerprint, guaranteeing that the identical-completion check fails closed (`basis_collision`). A regression test `test_changed_live_anchor_state_rejects_as_basis_collision` was added to assert this explicitly.
- **Regressions:** Re-running full `pytest`, Ruff, Black, and Governance checks confirms 0 regressions. T110/T111 gating, missing organization checks, dry-run rollbacks, and atomic transaction behaviors remain sound. CI reports all green.

**Final Decision: Approved**
