# T175 Implementation Evidence — Operational Reacceptance and Conversion Verification

**Task:** T175 — M1 Operational Reacceptance & M2-V3 Conversion Verification  
**Issue / authorization:** #363 / PR #364 (merged)  
**Protected baseline and candidate base:** `cc5a9ef20929c5723df9b4320d44bdc76bc02400` (PR #368, T176 closeout)  
**Execution date:** 2026-10-24 (Asia/Kolkata)  
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
| A9.2 | **Blocked** | T175 freshly verified packaged Windows cold start and unauthenticated restart at `file:///…/index.html#/login`; the visible Sign in form disproves the prior blank-renderer defect. Login, protected navigation, logout, and authenticated session restoration require a human operator to enter credentials and were not automated. |
| A10.1–A10.4, A10.6–A10.7 | Verified (valid reuse) | T166 tenant/RBAC evidence; T169/T176 did not alter RLS, roles, permission grants, or these routes. |
| A10.5 | Verified (valid reuse of fresh pass) | T166 Read Only Party-create denial (403). |
| A11.1–A11.2 | Verified (valid reuse) | T166 validation/not-found evidence; no intersecting change. |
| A11.3 | Verified (valid reuse of fresh pass) | T166 exact constraint, atomicity, recovery, nondisclosure and RBAC evidence; conversion/Matter uniqueness behavior was not changed by T169/T176. |

**Scenario tally:** 34 verified through source-traceable current reuse or prior fresh execution; 1 blocked (A9.2 authentication-dependent subflow); 0 failed; 0 not executed outside that blocked subflow. This is evidence status, not M1 acceptance.

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

Workstream A is **not ready for Independent QA approval as full operational reacceptance** because the changed native packaged path lacks a human-authenticated login/navigation/logout/restart walkthrough. It is ready for Independent QA inspection as an evidence package with that explicit blocker. No full M1 operational acceptance is declared or recommended.

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
| Rollback with no orphan records under simulated conversion fault | Not executed | No existing acceptance-specific fault-injection protocol was executed in T175. The generic request transaction contract is not substituted for direct evidence. |
| Tenant isolation and RBAC | Verified | Cross-tenant acceptance is `404`; missing `matters:write` is `403`; focused test uses actual authenticated permission grants. |
| Prospect-only rejection | Verified | Party-less Enquiry acceptance returns `422`; no automatic Party creation is observed or inferred. |
| Duplicate Matter-number collision recovery | Verified (valid reuse) | T166 A11.3’s exact PostgreSQL `23505` / `uq_matters_matter_number`, structured `409`, zero residue and subsequent-success evidence remains applicable; T169/T176 do not change the Matter conversion/uniqueness path. |
| Lost response / uncertain commit retry | Not executed | No controlled response-loss harness was run; idempotent replay is verified but is not treated as a substitute. |
| Native Windows UI completion and authenticated restart | Blocked | Packaged cold start/restart is verified, but authentication input and resulting protected navigation require a human operator. |
| Operator error recovery | Not executed | T176's reviewed CDP evidence covers credential-submission error handling, but T175 did not run an operator interaction; no broader claim is made. |

### 3.2 Workstream B conclusion

Workstream B is **not ready for Independent QA approval as complete conversion operational verification**. The existing backend contract is freshly verified for the core acceptance, idempotency, tenant/RBAC and concurrency cases, and the duplicate-number recovery evidence is validly reused. Direct evidence is still missing for acceptance-specific rollback/no-orphan fault injection, uncertain-commit retry, authenticated native UI completion/restart, and operator error recovery. No conversion redesign, automatic Party creation, existing-Matter linking, or numbering change is proposed.

## 4. Changed-file inventory

This PR-2 candidate changes only this evidence record and its companion Phase 53 implementation log. It intentionally does not modify application code, tests, migrations, schemas, ADRs, governance ledgers, delivery-calendar fields, or milestone acceptance state.

## 5. Required next action

Independent QA may review this candidate's evidence and exact commands. A human operator must perform the remaining authenticated Windows Electron walkthrough before either workstream can be recommended as operationally complete. If rollback or uncertain-commit verification exposes a product defect, stop Workstream B and seek separate authorization rather than changing conversion behavior in T175.
