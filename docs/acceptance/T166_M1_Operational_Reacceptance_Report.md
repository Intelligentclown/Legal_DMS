# T166 Operational Reacceptance Report — Resumed Execution

**Task:** T166 — M1 Final Remediation & Operational Reacceptance  
**Role:** Operational Acceptance Executor  
**Execution date:** 2026-10-19 (Asia/Kolkata)  
**Status:** In progress — A3.2 and A11.3 freshly passed on independently isolated supported-role environments; A9.2 remains blocked; no readiness claim

## Preserved initial STOP history

The initial execution correctly stopped at `T166-OBS-01` after trying the operational-fresh transition with `legal_dms_app`. The subsequent architecture/security investigation established this is the deliberately denied normal runtime role, not a product defect. This report preserves that evidence below and adds the supported-role reexecution; no grant was added to `legal_dms_app`.

## Exact identities and provenance

| Item | Verified identity | Result |
|---|---|---|
| Protected authorization baseline | `f93a664624e5f3ac45ec7fb0279f88e1faaebf5c` — PR #323 merge | Verified locally after `git fetch origin --prune`; equals `origin/main` |
| T166 Matter implementation candidate | PR [#325](https://github.com/Intelligentclown/Legal_DMS/pull/325) head `dde7fdf9e011bd61677c4b0edc4dde875daba7f0`; implementation parent `a8fd172c710da6cfcef216502bcc1b2ab624910b` | Remote `refs/pull/325/head` verified after fetch; candidate and implementation both descend from `f93a664…`. |
| Isolated runtime | New disposable Docker container `legal-dms-t166-acceptance-pg16`, `postgres:16-alpine`, loopback port 55466 | Used only for this execution; pre-existing `legal_dms_postgres` was not used. |
| Database | New `t166_acceptance` database | Fresh-install procedure used; no production or unidentified database was used. |
| Alembic | `b155caa6d4e1` | Sole `alembic heads` output and one `public.alembic_version` row. |
| Matter uniqueness | `uq_matters_matter_number` = `UNIQUE (matter_number)` | Verified directly from PostgreSQL catalog; this is a global (not Organization-scoped) uniqueness constraint. |

The runtime role `legal_dms_app` was created as `LOGIN`, non-superuser, non-`BYPASSRLS`, non-`CREATEROLE`, and non-`CREATEDB`. The owner and application URLs, JWT secret, passwords, installation ID, event IDs, and bearer tokens are deliberately omitted from this report.

For the fresh A11.3 execution, a third independently disposable PostgreSQL 16 environment was used: Docker container `legal-dms-t166-a11-pg16`, image `postgres:16-alpine`, loopback port 55468, and database `t166_a11`. It was created blank, used only for this run, and was not a production or pre-existing database. Its guarded install produced the sole `b155caa6d4e1` head plus immutable `FRESH_BIRTH` sequence 1 and `OPERATIONAL_FRESH_ENTERED` sequence 2 records at that revision. The ordinary application and dedicated bootstrap roles were each non-superuser, non-`BYPASSRLS`, non-`CREATEROLE`, and non-`CREATEDB`; `enter_operational_fresh(uuid)` execute was false for the application role and true for the bootstrap role. The bootstrap-role connection, not an owner or application connection, executed the operational transition.

## Initial environment gate outcome

Fresh-install provenance successfully created the schema and immutable fresh-birth event at `b155caa6d4e1`. The required restricted-role operational-fresh bootstrap then failed closed.

| Check | Observation | Outcome |
|---|---|---|
| Application-role privilege | `legal_dms_app` has no superuser or `BYPASSRLS` privileges | Pass |
| Provenance schema access | `legal_dms_app` has `USAGE` | Pass |
| Bootstrap function authorization | `has_function_privilege('legal_dms_app', 'legal_dms_provenance.enter_operational_fresh(uuid)', 'EXECUTE') = false`; direct restricted-role invocation returned `permission denied for function enter_operational_fresh` | **Fail / material blocker** |
| Bypass attempt | Not attempted: invoking the bootstrap with the owner role would not establish the required restricted-role operational-fresh evidence | Preserved fail-closed boundary |

This correctly prevented an unsupported operational-fresh Party write. It was subsequently classified as a test-setup error: the protected repository provides `provision-bootstrap-role` and requires `legal_dms_bootstrap` for this transition.

## Resumed supported bootstrap evidence

A second disposable PostgreSQL 16 container/database was created independently from the initial one. Before any acceptance identities or business fixtures, the following supported sequence completed:

1. provisioned non-privileged `legal_dms_app`;
2. provisioned non-privileged `legal_dms_bootstrap` with routine-only access;
3. ran guarded `fresh-install-provenance` on a blank database;
4. confirmed sole Alembic head `b155caa6d4e1` and immutable `FRESH_BIRTH` event;
5. ran `operational-fresh-bootstrap` using only the bootstrap-role connection; and
6. confirmed the committed `OPERATIONAL_FRESH_ENTERED` event at the same revision.

Both application and bootstrap roles were `LOGIN`, non-superuser, non-`BYPASSRLS`, non-`CREATEROLE`, and non-`CREATEDB`. PostgreSQL confirmed bootstrap-function `EXECUTE=false` for `legal_dms_app` and `true` for `legal_dms_bootstrap`. No administrator, owner, or application-role invocation of the transition occurred.

## Required reacceptance workstreams

### B — Party A3.2 / DEF-T163-01

**Freshly passed.** After supported bootstrap, normal authenticated `legal_dms_app` runtime requests produced: Advocate login `200`; Party create `201`; independent Party retrieval `200`; cross-tenant Party retrieval `404`; and Read Only Party-create denial `403`. A separate owner-session database query found exactly one Party row with the authenticated Organization A identifier, proving committed persistence after the HTTP request. The successful ordinary API request demonstrates PartyWriteGate admission under the production classifier.

`DEF-T163-01` is **operationally resolved for A3.2** on this supported fresh-install evidence. This is not a general M1 readiness decision.

### A — Matter A11.3 / DEF-T163-02

**Freshly passed against PR #325 frozen head `dde7fdf9e011bd61677c4b0edc4dde875daba7f0`.** The HTTP API was served from that exact detached candidate checkout in testing mode. Normal authenticated Advocate identities in two distinct Organizations created and attempted to duplicate a single Matter number:

| Check | Fresh result |
|---|---|
| Initial Organization A Matter create | `201 Created` |
| Organization B duplicate of the same global Matter number | Structured `409`, exactly `{"error":{"code":"conflict","message":"Matter number is already in use"}}` |
| PostgreSQL targeting | Direct controlled duplicate probe exited non-zero with SQLSTATE `23505` and constraint name `uq_matters_matter_number`; PostgreSQL catalog identifies it as a unique constraint. |
| Atomicity | Owner-session query for the conflicting number returned exactly one Matter and exactly one MatterParty, belonging to Organization A. No Organization B aggregate residue was present. The direct probe also left the count at one. |
| Transaction/savepoint usability | Organization B successfully created a different Matter after the conflict (`201`). |
| Tenant isolation / nondisclosure | Organization B retrieval of Organization A's Matter returned `404`; the conflict body contained neither Organization identifier. |
| RBAC anti-probe | Organization A Read Only identity received `403` for the duplicate POST, ahead of conflict handling. |
| Non-target integrity handling | Targeted candidate unit test `test_non_target_integrity_error_remains_untranslated` passed; it proves a distinct `23505` constraint remains an `IntegrityError`, not a translated conflict. |

The remotely published PR #325 checks were independently queried after execution: Backend validation, Frontend validation, Governance consistency validation, and Release build verification each report passing runs (the two GitHub run batches visible for the PR were all green). These CI results support, but do not replace, the fresh operational evidence.

`DEF-T163-02` is **operationally resolved for A11.3** on this exact candidate only. It is not an M1 readiness decision.

### C — Native Electron A9.2 / BLK-T163-01

**Blocked / pending separate Windows Electron verification executor and Project Owner operator.** No browser-only, headless, static, or substitute result is claimed. The required native termination/relaunch restoration and logout non-restoration evidence has not been supplied to this executor.

## T163 scenario evidence reconciliation

The table uses the exact original T163 source `docs/acceptance/T163_M1_Acceptance_Report.md` and `docs/acceptance/evidence/acceptance_results.json` (candidate `fd97356ff717cd7f772c8ef2ad01dc110e393656`, independent QA publication `a894d7bada5dfd66201fd7729f310d9641740058`). Reuse is limited to scenarios not changed by the T165 classifier remediation or the unverified T166 Matter candidate. It establishes historical coverage, not a new end-to-end pass.

| Scenarios | Current evidence state | Exact source / rationale |
|---|---|---|
| A1.1–A2.2 | Validly reused | T163 acceptance evidence; no intervening authenticated API/product change in the protected T165 diff. |
| A3.1, A3.3–A3.4 | Validly reused | T163 acceptance evidence; T165 classifier surface is Party-write admission, not listing or Matter creation/retrieval. |
| A3.2 | Freshly executed — Passed | Supported `legal_dms_bootstrap` transition completed before fixtures; normal application runtime returned 201, then independent API retrieval 200 and separate committed-row verification. Cross-tenant 404 and Read Only 403 passed. |
| A4.1–A8.2 | Validly reused | T163 acceptance evidence; protected T165 diff changes only schema compatibility/classifier and related tests. |
| A9.1 | Validly reused | T163 browser evidence; no Electron result inferred. |
| A9.2 | Blocked | Native Windows execution remains outstanding; original T163 `BLK-T163-01` cannot be reused as a pass. |
| A10.1–A10.4, A10.6–A10.7 | Validly reused | T163 tenant/RBAC evidence; no protected T165 change to RLS, roles, permissions, or Matter route authorization. |
| A10.5 | Freshly executed — Passed | Read Only identity received 403 on Party create; existing `parties:write` RBAC boundary remained enforced. |
| A11.1–A11.2 | Validly reused | T163 validation/not-found evidence; PR #325 changes only duplicate-constraint translation/aggregate savepoint behavior. |
| A11.3 | Freshly executed — Passed | Exact PR #325 head was served from an isolated supported-role installation. Global duplicate returned structured 409; direct PostgreSQL probe proved `23505`/`uq_matters_matter_number`; persistence, recovery, tenant/RBAC and fail-closed checks passed. Original T163 failure is superseded by this fresh evidence. |

Count: **31 validly reused; 3 freshly passed; 1 blocked; 0 failed in the resumed execution.** This is not a 35-scenario operational reacceptance pass because native A9.2 remains blocked.

## Defect and gap disposition

| Item | Disposition |
|---|---|
| DEF-T163-01 | Resolved operationally for A3.2. Fresh supported-role, authenticated, persistence, retrieval, tenant-isolation, RBAC and PartyWriteGate-admission evidence passed. |
| DEF-T163-02 | Resolved operationally for A11.3 against exact PR #325 head `dde7fdf9e011bd61677c4b0edc4dde875daba7f0`. Structured global-number 409, exact constraint targeting, atomicity, recovery, nondisclosure, RBAC and non-target fail-closed behavior passed. |
| BLK-T163-01 | Pending native Windows Electron operator evidence. |
| T166-OBS-01 | Closed as an acceptance setup error, not a product defect. `legal_dms_app` correctly lacks bootstrap execution; `legal_dms_bootstrap` is the supported role. |
| Full suite | Not passed. The initial marker-only run remains unclassified. A fresh controlled, captured `uv run pytest tests -q --maxfail=1` run against protected baseline completed without orphaned workers: **82 passed, 1 failed, 10 warnings in 66.07s**. The first failure was `tests/integration/test_auth_login.py::TestLoginAuditing::test_successful_login_records_exactly_one_login_success_event`, which expected one `app.audit` log record but observed zero. Its sanitized identifier, assertion context and warnings are preserved in `docs/acceptance/evidence/T166_full_suite_failfast_sanitized.txt`. It is a protected-baseline failure, not candidate-specific; no historical-baseline comparison was run, so its root cause and age remain unclassified. |

## Independent QA handoff

1. Verify this report against `f93a664…`, the separate disposable-environment evidence, and the PostgreSQL privilege/provenance queries.
2. Independently reproduce the supported bootstrap-role A3.2 result; do not substitute owner-role bootstrap or expand application-role privileges.
3. Reproduce A11.3 from PR #325 head, independently checking the HTTP 409 shape, `23505`/`uq_matters_matter_number`, no Matter/MatterParty residue, recovery, non-enumeration, RBAC and non-target integrity behavior. The sanitized procedure/results are in `docs/acceptance/evidence/T166_A11_3_sanitized.txt`.
4. Obtain separately executed native Windows Electron A9.2 evidence; browser/headless evidence is insufficient.
5. Arrange a longer-running full-suite execution or record its exact time/platform limitation. Do not report the 941-test suite as passed.

**M1 remains NOT READY.** This report does not self-approve, merge, mark T166 Done, or change protected governance state.
