# T182 Implementation Evidence — Physical Document Storage Durability and Restart Recovery

**Task:** T182 — M2 Document Physical Storage Durability, Restart Recovery and Current-Head Backend Certification
**Authorization:** Issue #393; protected authorization PR [#394](https://github.com/Intelligentclown/Legal_DMS/pull/394)
**Original protected baseline:** `6720bcd281533ec2badc3ee3e7b92a0c12c52cb2`
**Reconciled protected baseline:** `012796947b33a11d4085f94804ca090fe7ef3b03`
**Implementation branch:** `codex/t182-storage-durability`
**Execution date:** 2026-10-28 (Asia/Kolkata)
**Status:** READY FOR INDEPENDENT QA — reconciled with the protected T183 allocator remediation and certified at the final implementation candidate.

## Environment and isolation

| Item | Evidence |
| --- | --- |
| Database | Dedicated disposable Docker PostgreSQL `16.15`, database `legal_dms_t182`; recreated and migrated to sole Alembic head `b155caa6d4e1` before final certification. |
| Filesystem | Per-test temporary physical roots for API/integration fault injection; native Electron root `C:\\Users\\Dhimant Patel\\AppData\\Local\\Temp\\legal_dms_t182_electron_storage`. |
| Backend | Python `3.14.4`; FastAPI backend `0.2.0`. |
| Native application | Windows Electron development application `legal-dms` `0.1.0`, connected to the isolated backend/database. |
| Candidate scope | Atomic `LocalFileStorage` write correction plus focused storage unit/integration tests only. No schema, migration, route, ADR, forecast, or governance-state changes. |
| Reconciliation | The preserved T182 worktree fast-forwarded cleanly from `6720bcd` to `0127969`; no local T182 path overlapped the completed T183 allocator change. T183 PRs [#396](https://github.com/Intelligentclown/Legal_DMS/pull/396), [#397](https://github.com/Intelligentclown/Legal_DMS/pull/397), and [#398](https://github.com/Intelligentclown/Legal_DMS/pull/398) are merged. |

## Acceptance-criteria matrix

| AC | Result | Reproducible evidence |
| --- | --- | --- |
| AC-01 | Pass | `test_t182_physical_upload_download_integrity_and_idempotency` uses real `LocalFileStorage` through the production ASGI routes. It compares physical and downloaded bytes, SHA-256, size, MIME type, and `Content-Disposition` filename. |
| AC-02 | Pass | `test_t182_physical_document_survives_fresh_backend_process_restart` starts one Uvicorn OS process, uploads to PostgreSQL/physical storage, terminates it, starts a distinct process against the same root/database, then authenticates and reads the same bytes/metadata with one version/blob. |
| AC-03 | Pass | The AC-01 test verifies same-key/same-payload replay returns the same version without a second blob/record; same key with different payload returns HTTP 409 and preserves the original bytes and counts. |
| AC-04 | Pass | `test_t182_post_write_database_failure_compensates_physical_blob` injects `SqlAlchemyDocumentVersionRepository.add()` failure after real save and before commit. HTTP 500, unchanged database counts, and empty disposable physical root prove compensation. |
| AC-05 | Pass | `test_t182_physical_write_failure_has_no_api_or_database_residue` injects real `os.fsync` failure in the atomic write path. HTTP 500, no target/temp files, and unchanged Version/Storage/Idempotency counts prove safe cleanup. `test_local_file_storage.py` contains 11 atomic-write/cleanup regressions. |
| AC-06 | Pass | `test_t182_physical_corruption_fails_closed` alters the committed physical file; download returns HTTP 500 and never returns corrupted bytes. |
| AC-07 | Pass | Tenant, RBAC, missing/invalid authentication-context, and traversal tests use production API dependencies and physical roots: cross-tenant access is 404; missing `documents:write`/`documents:read` is 403 with no mutation/disclosure; absent/malformed authorization is 401; `..` and absolute keys are rejected before I/O. |
| AC-08 | Pass | Native Windows Electron upload/download/restart smoke passed (below). Reconciled candidate full backend certification passed: `958 passed, 87 warnings in 483.11s`, exit `0`, on isolated PostgreSQL 16.15. |

## Focused regression results

With disposable PostgreSQL 16.15 and the ephemeral `JWT_SECRET_KEY` only in process environment:

```text
uv run pytest tests/integration/test_t182_physical_document_storage.py tests/unit/test_local_file_storage.py tests/integration/test_t183_file_number_allocator_concurrency.py tests/integration/test_t138_file_migration_and_allocator.py -q
23 passed, 1 warning in 34.89s

uv run pytest tests/integration/test_t142_document_version_routes.py tests/integration/test_t177_post_conversion_office_journey.py -q
15 passed, 1 warning in 15.04s
```

The focused warnings are the existing Starlette/TestClient deprecation warning. The full suite's 87 warnings are existing Starlette deprecations and JWT fixture `InsecureKeyLengthWarning` advisories; no T182 authentication behavior changed. Ruff and Black were re-run on the final working tree and passed (`ruff check src tests`; `black --check src tests`, 301 files unchanged). `git diff --check` passed.

## Native Windows Electron smoke

An authorized disposable operator used the real native Document Version UI to upload `README.md` (4,018 bytes) into the isolated root. The physical file and first native download both matched:

```text
SHA-256  96510b473aa5544edecb4e06cdc12104f6008e0758d52e133da9cae72c596aee
size     4018
```

The Electron window was closed and the backend process stopped. A fresh backend process and fresh Electron process were launched against the same PostgreSQL database and storage root. The operator reopened the same Matter/File/Document, observed version `1`, downloaded `README-restart.md`, and verified the identical size and SHA-256. The post-restart database/filesystem check showed one DocumentVersion, one FileStorageRecord, and one physical `content` blob.

The test operator lacked `properties:read`, which displayed unrelated property-panel errors on the Matter page. The Matter/File/Document navigation, upload, version retrieval, download, storage checksum, and restart path were all observed successfully; the advisory neither blocked nor altered the tested Document Version path.

## Final-suite certification

Final command, from `backend/`:

```text
uv run pytest -q
```

The historical first run used the native-smoke database after that disposable operator was seeded and failed with 16 bootstrap/seed assertions (`941 passed, 16 failed, 87 warnings, 611.03s`). Database inspection proved contamination (`users=1`, `organizations=1`, `document_versions=1`, `file_storage_records=1`, and seven roles). This was corrected as a test-environment lifecycle issue: only `legal_dms_t182` was dropped/recreated and migrated to `b155caa6d4e1`.

The next clean run produced `956 passed, 1 failed, 87 warnings in 537.12s` (exit 1), exposing the unrelated T138 concurrent allocator defect. T183 separately remediated that defect and completed its full three-PR lifecycle on protected main. After the T182 worktree fast-forwarded to `0127969`, this final clean run was executed from `backend/`:

```text
uv run pytest -q
```

Result: `958 passed, 87 warnings in 483.11s (0:08:03)`, exit `0`. The candidate includes the protected T183 allocator regression coverage and retains the sole migration head `b155caa6d4e1`.

## Governance and context validation

- `python scripts/governance_validate.py --report` — pass; unresolved Required ADRs remain `[12, 15, 16, 17, 20]` and no governance errors were reported.
- `python -m unittest scripts.tests.test_governance_validate -q` — `88 passed`.
- `python scripts/current_context_manifest.py` — pass; mechanically-derived frontier is `latest_done=T183`, `latest_authorized=T183`, with no discrepancies.
- `python -m unittest scripts.tests.test_current_context_manifest -q` — known historical hardcoded-frontier test debt: `6 passed, 1 failed`, because the test still asserts `T170/T171`. This does not invalidate the generator or governance state and remains separately tracked.

## Handoff

The implementation candidate is ready for Comprehensive / Risk Tier 1 Independent QA. The implementation executor must not self-approve, merge, create T182 closeout PR 3, mark T182 Done, or authorize a successor.
