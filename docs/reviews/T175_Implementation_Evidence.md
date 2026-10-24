# T175 Implementation Evidence — Operational Reacceptance and Conversion Verification

**Task:** T175 — M1 Operational Reacceptance & M2-V3 Conversion Verification  
**Issue / authorization:** #363 / PR #364 (merged)  
**Protected baseline and candidate base:** `cc5a9ef20929c5723df9b4320d44bdc76bc02400` (PR #368, T176 closeout)  
**Execution dates:** 2026-10-24 and 2026-10-25 (Asia/Kolkata)
**Scope:** Verification and evidence publication only. No application, schema, migration, ADR, forecast, queue, or acceptance-state change was made.

## 1. Preflight and evidence environment

| Item | Result |
| --- | --- |
| Protected `main` | `origin/main = cc5a9ef20929c5723df9b4320d44bdc76bc02400`; verified after `git fetch origin --prune`. |
| T175 authorization | Issue #363 is open; authorization PR #364 merged as `7a5077af940c4e31c2c3cf36a73083240ff4845f`. |
| T176 dependency | Implementation PR #367 merged as `e7ccd7ce5333eaabb48c4d06fa12fa69cefc177b`; closeout PR #368 merged as the protected baseline. |
| Database | Disposable Docker container `legal-dms-t175-pg16`, `postgres:16-alpine`, PostgreSQL `16.15`, bound only to `127.0.0.1:55475`. The pre-existing shared `legal_dms_postgres` container was not used. |
| Runtime roles | The repository-supported `provision-app-role` command created `legal_dms_app` in the disposable container; PostgreSQL confirmed it is neither superuser nor `BYPASSRLS`. |
| Migration frontier | `uv run alembic upgrade head`, `alembic heads`, and `alembic current` each confirmed the sole head `b155caa6d4e1`. |
| Native package | `npm run dist` built a Windows x64 unpacked package and NSIS installer. The packaged-renderer verifier passed: three local references, all relative and present. |

The first focused conversion-test attempt stopped before execution because the disposable server had not yet had the required `legal_dms_app` role provisioned. That was an environment preflight failure, not an application result; the role was provisioned with the repository's supported CLI and the test was rerun from a fresh disposable database.

## 2. Workstream A — M1 operational reacceptance

### 2.1 T166 scenario disposition

`docs/acceptance/T166_M1_Operational_Reacceptance_Report.md` remains the source for the original 35-scenario execution: 31 valid evidence reuses and four fresh passes. T175 revalidated the changed packaged-Electron path. Every non-Electron scenario has no intervening application-path change in T169 or T176; reuse is therefore identified explicitly below rather than represented as a new execution.

| T166 scenarios | Current disposition | Evidence / rationale |
| --- | --- | --- |
| A1.1–A2.2 | Verified (valid reuse) | T166 report, T163 evidence; no intersecting path in T169/T176. |
| A3.1, A3.3–A3.4 | Verified (valid reuse) | T166 report; T165 classifier remediation did not alter these routes after its reviewed evidence. |
| A3.2 | Verified (valid reuse of fresh pass) | T166 supported-bootstrap execution: authenticated Party create/retrieve, tenant 404, and RBAC 403. |
| A4.1–A8.2 | Verified (valid reuse) | T166 report; no intersecting application change. |
| A9.1 | Verified (valid reuse) | T166 browser evidence; it is not used as Electron evidence. |
| A9.2 | **Verified (human-operated, 2026-10-25)** | Packaged Electron login reached Status and protected Matter navigation; a full restart restored the session; logout followed by another restart returned to Sign in. Screenshots retained under `docs/acceptance/evidence/T175/`. |
| A10.1–A10.4, A10.6–A10.7 | Verified (valid reuse) | T166 tenant/RBAC evidence; T169/T176 did not alter RLS, roles, permission grants, or these routes. |
| A10.5 | Verified (valid reuse of fresh pass) | T166 Read Only Party-create denial (403). |
| A11.1–A11.2 | Verified (valid reuse) | T166 validation/not-found evidence; no intersecting change. |
| A11.3 | Verified (valid reuse of fresh pass) | T166 exact constraint, atomicity, recovery, nondisclosure and RBAC evidence; conversion/Matter uniqueness behavior was not changed by T169/T176. |

**Scenario tally:** 35 verified through source-traceable current reuse, prior fresh execution, or the documented human-operated packaged-Electron session; 0 blocked; 0 failed. This is evidence status, not M1 acceptance.

### 2.2 Backend-suite and advisory reconciliation

Command run from `backend/` against the isolated PostgreSQL 16.15 target:

```text
uv run pytest -q
942 passed, 87 warnings in 799.60s (0:13:19)
```

This independently corroborates T169's two recorded clean runs of `942 passed, 87 warnings, 0 failed, 0 errors`. The 87 warnings remain visible (Starlette/HTTPX deprecations and test-fixture short-secret warnings); none were suppressed.

`QA-T166-NB-01` was specifically rechecked. Its historical failure mode was an in-process Alembic `fileConfig` disabling `app.audit`. T169's reviewed `disable_existing_loggers=False` remediation is present; the formerly affected `tests/integration/test_activity_models.py` passed `6 passed, 1 warning` after the isolated database was migrated. The advisory's durable historical record is not altered by this task, but its reported failure was not reproduced.

### 2.3 Native package observations

The unpacked executable was launched through native Windows automation. It opened one native window titled **Legal Document & Matter Management System**. Its accessibility tree and visible renderer showed:

- `file:///.../resources/app.asar/frontend/dist/index.html#/login`;
- heading **Sign in**, email and password controls, and Sign in button;
- no blank renderer and no React Router 404 page.

After a complete application exit, a fresh launch again showed the same unauthenticated `#/login` page. This verifies packaged cold start and unauthenticated restart only. It does not establish authenticated persistence, logout clearing, protected navigation, or operator error recovery.

Local frontend regression checks on the candidate also passed: `npm --prefix frontend run test -- --run` reported **21 files / 187 tests passed**; lint reported **0 errors and 4 pre-existing Fast Refresh warnings**; and `format:check` passed.

### 2.4 Workstream A conclusion

The required packaged-Electron authentication/navigation/logout/restart walkthrough is complete. This supplies evidence for Independent QA review; no full M1 operational acceptance is declared or recommended.

## 3. Workstream B — M2-V3 conversion verification

### 3.1 Fresh PostgreSQL/API execution

Command run from `backend/` after isolated preflight:

```text
uv run pytest tests/integration/test_t149_enquiry_quotation_routes.py -q
4 passed, 1 warning in 6.82s
```

The test uses fresh disposable databases below the isolated PostgreSQL 16 server and exercises the actual FastAPI route, application service, SQLAlchemy persistence, PostgreSQL constraints, and row locks. It is separate from the full-suite result above.

| Required verification | Result | Source / observation |
| --- | --- | --- |
| Party-linked Enquiry conversion | Verified | `test_t152_accepts_exact_issued_revision_creates_party_canonical_matter_and_replays`. |
| Exact issued-revision eligibility | Verified | The test issues the exact revision before acceptance; T149 issuance test also rejects re-issuance. |
| Exactly one Matter and Acceptance | Verified | Fresh route test asserts one Acceptance and one Matter for the converted Enquiry. |
| `MatterParty(role="client")` | Verified | Fresh route test reads persisted `MatterParty` and asserts the linked Enquiry Party with `client` role; `Matter.client_id is None`. |
| Same key / same payload replay | Verified | First response `201`; repeat response `200` with `replayed=true` and same aggregate identity. |
| Changed-payload conflict | Verified | Same idempotency key with changed title returns `409`. |
| Distinct-key duplicate prevention | Verified | Distinct key after a completed conversion returns `409`. |
| Two-session PostgreSQL concurrency / row lock | Verified | Parallel `asyncio.gather` route requests return one `201` and one `409`; persisted Acceptance count is exactly one. The repository implementation locks the Enquiry with `SELECT … FOR UPDATE`. |
| Rollback with no orphan records under simulated conversion fault | **Verified (2026-10-25)** | A test-only hook raised immediately after the Acceptance flush and before request commit. The production ASGI/service/persistence path rolled back; direct counts were `Matter=0`, `Acceptance=0`, and `MatterParty=0` for the conversion Organization. |
| Tenant isolation and RBAC | Verified | Cross-tenant acceptance is `404`; missing `matters:write` is `403`; focused test uses actual authenticated permission grants. |
| Prospect-only rejection | Verified | Party-less Enquiry acceptance returns `422`; no automatic Party creation is observed or inferred. |
| Duplicate Matter-number collision recovery | Verified (valid reuse) | T166 A11.3’s exact PostgreSQL `23505` / `uq_matters_matter_number`, structured `409`, zero residue and subsequent-success evidence remains applicable; T169/T176 do not change the Matter conversion/uniqueness path. |
| Lost response / uncertain commit retry | **Verified (2026-10-25)** | The first production-ASGI request committed its conversion, then a test transport discarded its `http.response.start`. Retrying the original payload and `Idempotency-Key` returned HTTP `200`, `replayed=true`, and the persisted Acceptance/Matter IDs; direct counts confirmed one Matter, Acceptance, and MatterParty. |
| Native Windows UI completion and authenticated restart | **Verified (human-operated, 2026-10-25)** | The operator signed in, navigated protected views, completed the full workflow, then confirmed session restoration after a full application restart. See `T175_electron_authenticated_dashboard.png`, `T175_electron_converted_matter.png`, and `T175_electron_session_restored.png`. |
| Operator error recovery | **Verified (human-operated, 2026-10-25)** | Party creation was denied by the existing ADR-0037 installation-state guard with a visible, specific message; the form stayed usable and no Party was persisted. The operator safely continued by linking the existing canonical Party and completed conversion. See `T175_electron_party_write_denial.png`. |

### 3.2 Workstream B conclusion

All four mandatory verification gates are now evidenced. The existing backend contract is freshly verified for core acceptance, idempotency, tenant/RBAC and concurrency; rollback/no-orphan and uncertain-commit recovery are direct isolated PostgreSQL evidence; and the packaged-Electron human session verified the workflow and safe UI recovery. No conversion redesign, automatic Party creation, existing-Matter linking, or numbering change is proposed.

### 3.3 Isolated PostgreSQL 16 fault and uncertain-commit protocol (2026-10-25)

This ran only against an ephemeral `postgres:16-alpine` container exposed on `127.0.0.1:55476` and removed after the run. The repository-supported `provision-app-role` provisioned the required non-owning role before fresh-install migration. The shared `legal_dms_postgres` instance was not used. No human credential, access token, or customer data was used or captured.

```text
# from backend/; values supplied only to the local process
$env:DATABASE_URL=<isolated-postgresql-16-admin-url>
$env:APP_DATABASE_URL=<isolated-postgresql-16-app-role-url>
$env:JWT_SECRET_KEY=<non-production-test-secret>
$env:PYTHONPATH=src
uv run provision-app-role
uv run pytest tests/integration/test_t149_enquiry_quotation_routes.py -q

6 passed, 1 warning in 9.43s
```

`test_t175_acceptance_fault_rolls_back_entire_conversion_and_leaves_no_orphans` injects a `RuntimeError` immediately after the Acceptance flush; direct post-fault counts are all zero. `test_t175_lost_response_after_commit_replays_existing_conversion_once` raises only at `http.response.start` after `get_db()` commits, then retries the original key/payload and asserts `200`/`replayed=true` plus exactly one persisted aggregate. Both are test-only additions; no production source, schema, or conversion semantic changed.

### 3.4 Human-operated packaged Electron evidence (2026-10-25)

The operator used the clearly named local-only Advocate account. The first login attempt failed because an unrelated AnyCommand service occupied port 8000; after the operator removed it and the local Legal DMS API was started on the package's documented default origin, the same account logged in successfully. This was a local host conflict, not an application defect and required no application, schema, or package change. The session then demonstrated protected Status and Matter navigation, existing Party linking, Enquiry → Quotation → issued revision → Acceptance → Matter completion (`T175-M-001`), authenticated restart persistence, logout, and logged-out restart persistence. Screenshots: `T175_electron_authenticated_dashboard.png`, `T175_electron_party_write_denial.png`, `T175_electron_converted_matter.png`, `T175_electron_session_restored.png`, `T175_electron_logout_persisted.png`.

## 4. Changed-file inventory

This PR-2 candidate adds the two test-only T175 integration scenarios, this evidence record, its Phase 53 log update, and the five operator screenshots. It does not modify production application code, migrations, schemas, ADRs, governance ledgers, delivery-calendar fields, or milestone acceptance state.

## 5. Required next action

Independent QA must perform a fresh review of this substantive evidence; the decision at `e41c8e5` does not cover it. No M1 or M2 acceptance claim is permitted before that independent review and the remaining lifecycle gates.
