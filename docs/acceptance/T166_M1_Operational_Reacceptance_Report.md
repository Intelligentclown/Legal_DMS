# T166 Operational Reacceptance Report — Initial Execution

**Task:** T166 — M1 Final Remediation & Operational Reacceptance  
**Role:** Operational Acceptance Executor  
**Execution date:** 2026-10-19 (Asia/Kolkata)  
**Status:** STOPPED — material operational-fresh security/provenance gate failure; no readiness claim

## Exact identities and provenance

| Item | Verified identity | Result |
|---|---|---|
| Protected authorization baseline | `f93a664624e5f3ac45ec7fb0279f88e1faaebf5c` — PR #323 merge | Verified locally after `git fetch origin --prune`; equals `origin/main` |
| T166 local implementation candidate | `a8fd172c710da6cfcef216502bcc1b2ab624910b` implementation; `dde7fdf` log | Descends from the baseline, but no `origin/feature/t166-matter-conflict` ref exists. It is **not a remotely verified candidate**. |
| Isolated runtime | New disposable Docker container `legal-dms-t166-acceptance-pg16`, `postgres:16-alpine`, loopback port 55466 | Used only for this execution; pre-existing `legal_dms_postgres` was not used. |
| Database | New `t166_acceptance` database | Fresh-install procedure used; no production or unidentified database was used. |
| Alembic | `b155caa6d4e1` | Sole `alembic heads` output and one `public.alembic_version` row. |
| Matter uniqueness | `uq_matters_matter_number` = `UNIQUE (matter_number)` | Verified directly from PostgreSQL catalog; this is a global (not Organization-scoped) uniqueness constraint. |

The runtime role `legal_dms_app` was created as `LOGIN`, non-superuser, non-`BYPASSRLS`, non-`CREATEROLE`, and non-`CREATEDB`. The owner and application URLs, JWT secret, passwords, installation ID, event IDs, and bearer tokens are deliberately omitted from this report.

## Environment gate outcome

Fresh-install provenance successfully created the schema and immutable fresh-birth event at `b155caa6d4e1`. The required restricted-role operational-fresh bootstrap then failed closed.

| Check | Observation | Outcome |
|---|---|---|
| Application-role privilege | `legal_dms_app` has no superuser or `BYPASSRLS` privileges | Pass |
| Provenance schema access | `legal_dms_app` has `USAGE` | Pass |
| Bootstrap function authorization | `has_function_privilege('legal_dms_app', 'legal_dms_provenance.enter_operational_fresh(uuid)', 'EXECUTE') = false`; direct restricted-role invocation returned `permission denied for function enter_operational_fresh` | **Fail / material blocker** |
| Bypass attempt | Not attempted: invoking the bootstrap with the owner role would not establish the required restricted-role operational-fresh evidence | Preserved fail-closed boundary |

This prevents a supported operational-fresh Party write. It is a security/provenance deployment defect or incompatible setup contract, not evidence that Party creation is operationally accepted. It requires Backend/architecture ownership to determine the approved grant/provisioning remedy; it must not be silently worked around in acceptance.

## Required reacceptance workstreams

### B — Party A3.2 / DEF-T163-01

**Blocked.** Authenticated Party creation, committed persistence, independent retrieval, tenant isolation, and RBAC retest were not executed because the required supported operational-fresh state cannot be established with the restricted runtime role. `DEF-T163-01` is therefore **not resolved operationally**.

T165 QA evidence remains a valid implementation-level source, but it is not substituted for this fresh operational acceptance requirement.

### A — Matter A11.3 / DEF-T163-02

**Blocked before execution.** The local candidate is ancestrally correct but is not a remote GitHub candidate: no `origin/feature/t166-matter-conflict` ref was found after fetch. Its claimed change is `a8fd172`, with documentation commit `dde7fdf`; its observed scope includes Matter service/tests and Phase47. Per T166, no A11.3 execution was performed against this unverified candidate.

The protected baseline does retain the database constraint, but it does not contain the candidate's HTTP-409 translation. No conclusion is made about the HTTP response, atomic Matter/MatterParty rollback, post-conflict transaction usability, tenant nondisclosure, or non-target integrity failures.

### C — Native Electron A9.2 / BLK-T163-01

**Blocked / pending separate Windows Electron verification executor and Project Owner operator.** No browser-only, headless, static, or substitute result is claimed. The required native termination/relaunch restoration and logout non-restoration evidence has not been supplied to this executor.

## T163 scenario evidence reconciliation

The table uses the exact original T163 source `docs/acceptance/T163_M1_Acceptance_Report.md` and `docs/acceptance/evidence/acceptance_results.json` (candidate `fd97356ff717cd7f772c8ef2ad01dc110e393656`, independent QA publication `a894d7bada5dfd66201fd7729f310d9641740058`). Reuse is limited to scenarios not changed by the T165 classifier remediation or the unverified T166 Matter candidate. It establishes historical coverage, not a new end-to-end pass.

| Scenarios | Current evidence state | Exact source / rationale |
|---|---|---|
| A1.1–A2.2 | Validly reused | T163 acceptance evidence; no intervening authenticated API/product change in the protected T165 diff. |
| A3.1, A3.3–A3.4 | Validly reused | T163 acceptance evidence; T165 classifier surface is Party-write admission, not listing or Matter creation/retrieval. |
| A3.2 | Blocked | Fresh reexecution required by T166; restricted-role operational-fresh bootstrap denied. |
| A4.1–A8.2 | Validly reused | T163 acceptance evidence; protected T165 diff changes only schema compatibility/classifier and related tests. |
| A9.1 | Validly reused | T163 browser evidence; no Electron result inferred. |
| A9.2 | Blocked | Native Windows execution remains outstanding; original T163 `BLK-T163-01` cannot be reused as a pass. |
| A10.1–A10.7 | Validly reused | T163 tenant/RBAC evidence; no protected T165 change to RLS, roles, permissions, or Matter route authorization. A10.5 was not re-run because A3.2 gate blocked the intended Party operational path. |
| A11.1–A11.2 | Validly reused | T163 validation/not-found evidence; no verified T166 candidate is available. |
| A11.3 | Blocked | Fresh candidate-specific execution required; candidate is only local/unverified. Original T163 failure is superseded as the defect target, not converted to a pass. |

Count: **32 validly reused; 0 freshly passed; 3 blocked; 0 failed in this execution.** This is not a 35-scenario operational reacceptance pass.

## Defect and gap disposition

| Item | Disposition |
|---|---|
| DEF-T163-01 | Open operationally. T165 implementation evidence exists, but A3.2 cannot be executed under supported restricted-role operational-fresh provenance. |
| DEF-T163-02 | Pending remote candidate verification and fresh A11.3 execution. |
| BLK-T163-01 | Pending native Windows Electron operator evidence. |
| New blocker: T166-OBS-01 | Restricted app role lacks execute permission on `legal_dms_provenance.enter_operational_fresh(uuid)`, preventing required operational-fresh bootstrap. Treat as material security/provenance deployment defect until independently triaged. |
| Full suite | Not passed. A supported background `uv run pytest tests -q` execution was started in this isolated PostgreSQL 16 environment after the foreground 30-second runner cut off. It reached 23% in 195 seconds and reported multiple failures. Because it was not a fail-fast invocation, it was then stopped: continuing could not change the failed full-suite result. No final collected/pass/fail total is available. Developer-reported focused tests and 348-unit result remain unverified implementation claims. |

## Independent QA handoff

1. Verify this report against `f93a664…`, the container/database evidence, and the PostgreSQL grant query.
2. Do not approve an operational-fresh Party pass until the restricted-role bootstrap is repaired through an authorized, security-reviewed route and A3.2 is freshly executed.
3. Require remote GitHub verification of the exact T166 Matter candidate and its ancestry before running A11.3; then verify 409 shape, no Matter/MatterParty persistence, transaction reuse, non-enumeration, and unrelated-integrity fail-closed behavior.
4. Obtain separately executed native Windows Electron A9.2 evidence; browser/headless evidence is insufficient.
5. Arrange a longer-running full-suite execution or record its exact time/platform limitation. Do not report the 941-test suite as passed.

**M1 remains NOT READY.** This report does not self-approve, merge, mark T166 Done, or change protected governance state.
