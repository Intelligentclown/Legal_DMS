# T177 Implementation Evidence — Post-Conversion Office Journey

**Task:** T177 — M2 Post-Conversion Office Journey Verification & Gap Disposition  
**Authorization:** Issue #373; protected authorization PR #374  
**Protected implementation baseline:** `0cba800f1c01c4156059d076874dca88e921ef79`  
**Candidate:** pending implementation commit on `codex/t177-office-journey-verification`  
**Execution date:** 2026-10-25 (Asia/Kolkata)  
**Scope:** targeted verification test and evidence only; no production route, schema, migration, ADR, authorization, forecast, or milestone-state change.

## 1. Environment and isolation

| Item | Evidence |
| --- | --- |
| Repository baseline | Branch was created directly from protected `origin/main` `0cba800f1c01c4156059d076874dca88e921ef79`; the T177 authorization and its QA publication commits are ancestors. |
| PostgreSQL | Docker `postgres:16-alpine`, server `16.15`; test fixture created a fresh, randomly named `legal_dms_t177_journey_*` database, ran the repository fresh-install/bootstrap path, then dropped it in fixture teardown. The shared `legal_dms_dev` database was used only as the maintenance connection that creates/drops the disposable database. |
| Application path | FastAPI production ASGI app, production route/services/repositories/transaction dependency, SQLAlchemy and PostgreSQL. The external `FileStorage` port is an in-memory test substitute, so content bytes can be asserted without external filesystem residue. |
| Native package | Windows 10.0.26300; Node 24.15.0; npm 11.12.1; Electron 43.3.0; electron-builder 26.15.3. `electron-builder --win --dir` created `release/t177-win/win-unpacked`. |

## 2. Reproducible execution

From `backend/`, with local-only credentials and URLs supplied only to the process:

```text
$env:DATABASE_URL=<local PostgreSQL 16 maintenance URL>
$env:APP_DATABASE_URL=<local PostgreSQL 16 app-role URL>
$env:JWT_SECRET_KEY=<non-production secret>
$env:PYTHONPATH=src
uv run pytest tests/integration/test_t177_post_conversion_office_journey.py -q
1 passed, 1 warning
```

Focused regression execution also passed:

```text
uv run pytest tests/integration/test_t149_enquiry_quotation_routes.py -q
6 passed, 1 warning
uv run pytest tests/integration/test_matter_property_routes.py -q
3 passed, 1 warning
uv run pytest tests/integration/test_document_routes.py tests/integration/test_t142_document_version_routes.py -q
16 passed, 1 warning
```

The warning in each run is the pre-existing Starlette `TestClient`/HTTPX deprecation warning. A full backend-suite attempt exceeded this execution environment's 30-second command observation limit and is **not** represented as a pass.

Frontend/package checks:

```text
npm --prefix frontend run test -- --run
21 files / 187 tests passed
npm run build
passed; packaged-renderer-assets: OK (3 local references, all relative and present)
npx electron-builder --win --dir --config.directories.output=release/t177-win
passed; Windows x64 unpacked package produced
```

Governance checks on the candidate worktree baseline passed: `python scripts/governance_validate.py` (0 warnings, 0 errors), `python scripts/delivery_calendar.py`, `python scripts/current_context_manifest.py` (no discrepancies; `latest_authorized=T177`, `latest_done=T176`), and `git diff --check`.

## 3. Acceptance-criteria matrix

| AC | Result | Reproducible evidence |
| --- | --- | --- |
| AC-01 | Pass | `test_t177_operator_completes_post_conversion_office_journey` creates an Enquiry with the canonical Party, a Quotation and exact issued Revision, then `POST /api/v1/enquiries/{enquiry}/quotations/{quotation}/revisions/{revision}/accept`. First call is 201; same key/payload replay is 200 and returns the same aggregate. |
| AC-02 | Pass | The conversion response's `matter_id` is immediately used with `GET /api/v1/matters/{matter_id}`; the operator path needs no copied/re-entered Matter identifier. |
| AC-03 | Pass | The reopened Matter response contains only `{party_id: <seeded canonical Party>, role: "client"}`. The focused T149 regression additionally proves the persisted `Matter.client_id` remains null and conversion creates no legacy Client. |
| AC-04 | Pass | A pre-existing same-tenant Property fixture is associated via `POST /api/v1/matters/{matter}/properties`; the first result is 201, a repeat is 200, and `GET` returns exactly one association. T157 route tests add canonical tenant/race coverage. |
| AC-05 | Pass | `POST /api/v1/matters/{matter}/files` creates the File; `GET /api/v1/matters/{matter}/files/{file}` reopens it and confirms the Matter ID. |
| AC-06 | Pass | `POST /api/v1/matters/{matter}/files/{file}/documents` creates a typed Document; its canonical nested `GET` reopens it. T139 regression coverage confirms unfiled legacy Documents are not surfaced. |
| AC-07 | Pass | Raw bytes are posted to the nested Version route with filename, MIME type and idempotency key. `GET .../versions/{version}/content` returns byte-identical content, `text/plain`, and the original filename. T142 regression coverage adds version idempotency, ordinal and cross-tenant checks. |
| AC-08 | Pass | A separate tenant with all relevant permissions receives 404 for both the Matter and Version-content routes; an authenticated caller lacking `files:read` receives 403. No payload content is asserted or exposed in the denials. |
| AC-09 | Pass by valid protected-evidence reuse; not freshly authenticated in this run | The newly built unpacked Windows package was observed at `file:///.../index.html#/login` with accessible Sign in/email/password controls, confirming current packaged cold-start/login rendering. Authenticated session restoration, logout, and logged-out restart are unchanged code paths and retain the protected T175 human-operated evidence (PR #369 / closeout #370). This run did not use or invent a local operator credential; that limitation is explicit. |
| AC-10 | Ready for independent QA | This evidence file, the single journey test, exact commands/results, and the gap register below are committed for a separate Comprehensive / Risk Tier 1 QA review. This executor does not render a QA decision. |

## 4. Native packaged-Electron observation

The T177 candidate package launched a native window titled **Legal Document & Matter Management System**. Its accessibility tree exposed:

```text
file:///D:/code/legal_dms_t177/release/t177-win/win-unpacked/resources/app.asar/frontend/dist/index.html#/login
heading: Sign in
controls: Email, Password, Sign in
```

This is direct native evidence for the packaged asset/router boundary and unauthenticated operator entry point. It is not misrepresented as a fresh authenticated end-to-end UI run.

## 5. Gap disposition register

| ID | Classification | Finding | Impact | Recommended disposition |
| --- | --- | --- | --- | --- |
| T177-LIM-01 | Verification limitation | This run did not replay the authenticated packaged-Electron workflow because no dedicated fresh local operator account/session was provisioned. | The native login renderer is fresh; authenticated restart relies on the protected T175 human-operated proof. | QA should verify the code/path-reuse analysis and may request a separately provisioned operator replay if it identifies a material reason. No product change is indicated. |
| T177-LIM-02 | Verification limitation | Binary-content integration uses a deterministic in-memory implementation of the existing external `FileStorage` port. | The HTTP/service/transaction/content-integrity contract is proven; this is not a filesystem durability or antivirus/OS-download test. | Retain as an explicit boundary. Any production-storage durability investigation needs separate authorization. |
| T177-ADV-01 | Usability improvement | The sequence remains route-driven; no new Party-detail page or server-side Property search is present. | Operators need a known existing Property identifier/selection source. | Preserve the stated exclusion. Consider only as a separately authorized usability task. |
| T177-ADV-02 | Historical test-environment limitation | Full backend suite could not be observed to completion in this session because the command runner truncates/ends after 30 seconds. | No false full-suite certification is made. | Independent QA should run the full suite in its supported environment if its risk assessment requires it. |

No confirmed production defect, security regression, schema issue, or missing mandatory API feature was identified. No substantive remediation is proposed or performed.

## 6. Independent QA handoff

Review the exact candidate commit and verify the evidence matrix against:

- `backend/tests/integration/test_t177_post_conversion_office_journey.py`
- `backend/tests/integration/test_t149_enquiry_quotation_routes.py`
- `backend/tests/integration/test_matter_property_routes.py`
- `backend/tests/integration/test_document_routes.py`
- `backend/tests/integration/test_t142_document_version_routes.py`
- `docs/ImplementationLog/Stage3/Phase54.md`

Requested review tier: **Comprehensive / Risk Tier 1 Independent QA**. The QA reviewer must independently classify any limitation, publish its decision to this PR branch, and re-read it from the remote head. T177 remains Authorized/not Done pending that review, protected implementation merge, and a separately commissioned closeout PR.
