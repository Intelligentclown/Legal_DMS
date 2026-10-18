# T157 Independent QA Review — Matter–Property Association Application Surface

**Task:** T157 — Matter–Property Association Application Surface  
**Implementation Candidate Reviewed:** `89bed9272f8cdd9d2909a0f195ca942fa4278ec5`  
**Protected Base Commit:** `202a2099a130e7e205b0f8e650291834cd13781e` (`origin/main`, merge PR #295)  
**Pull Request:** [#296 — `feat(matters): add canonical property associations`](https://github.com/Intelligentclown/Legal_DMS/pull/296)  
**Branch:** `feature/t157-matter-property-application`  
**Lifecycle Stage:** `PROJECT_WORKFLOW.md §3` — Implementation + Independent QA  
**Architecture Authority:** `ADR/0044-party-canonical-matter-property-association-architecture.md`  
**Reviewer:** Independent QA Reviewer (Antigravity)  
**Date:** 2026-10-18  

---

## 1. Executive Summary & Formal QA Decision

- **Formal QA Decision:** **Approved with comments**
- **Exact Candidate SHA Evaluated:** `89bed9272f8cdd9d2909a0f195ca942fa4278ec5`
- **Scope Audit:** Exactly six (6) files changed (+863 / −3 lines). Zero database migrations, zero schema modifications, zero product frontend code, and zero ADR resolutions.
- **Summary Assessment:** The implementation adheres strictly to ADR-0044 and T157 authorization. It provides canonical Matter-scoped endpoints for listing, associating, and unlinking Properties backed solely by `matter_properties`. Multi-tenant non-enumeration, permission boundaries (`matters:read`/`matters:write`/`properties:read`), request-scoped transaction ownership, and structured audit events were independently verified with real PostgreSQL. A real two-session concurrent race test proved that duplicate creations resolve deterministically to exactly one persisted row without leaking database exceptions or poisoning outer transactions.
- **Blocking Findings:** Zero (0).
- **Non-Blocking Observations:**
  1. *Constraint-Name Discrimination Advisory:* `add_if_absent` catches SQLSTATE `23505` to map duplicate creations to `created=False`. Because `id` is generated as a random UUIDv4 and no other business uniqueness constraints exist on `matter_properties`, this is mathematically safe. Stricter discrimination checking `getattr(exc.orig, "constraint_name", None) == "uq_matter_properties_organization_id_matter_id_property_id"` is documented as an advisory hardening recommendation.
  2. *Implementation Log Commit SHA Notation:* `Phase42.md` notes an earlier local hash (`fe38f7287dcb6e51f703952da83f2dbff81772b2`) prior to PR candidate commit creation (`89bed9272f8cdd9d2909a0f195ca942fa4278ec5`). Cosmetic only.

---

## 2. Baseline & Provenance Verification

- **Protected `main` Baseline:** `202a2099a130e7e205b0f8e650291834cd13781e` (Merge PR #295 — T157 authorization).
- **PR #296 State:** `OPEN`, `isDraft: false`, `mergeable: MERGEABLE`, targeting `main`.
- **Ancestry Chain:**
  ```
  202a2099a130e7e205b0f8e650291834cd13781e (origin/main baseline)
    └─ 89bed9272f8cdd9d2909a0f195ca942fa4278ec5 (PR #296 candidate head)
  ```
  - Ahead by: 1 commit.
  - Behind by: 0 commits.
  - Merge base: `202a2099a130e7e205b0f8e650291834cd13781e`.

---

## 3. Scope & Changed Files Audit

The frozen candidate touches exactly six (6) files:

1. `backend/src/app/application/interfaces/matter_property_repository.py` (+31 lines) — Narrow repository port.
2. `backend/src/app/application/matter_property_service.py` (+106 lines) — Matter-scoped coordination service.
3. `backend/src/app/infrastructure/persistence/sqlalchemy_matter_property_repository.py` (+61 lines) — SQLAlchemy implementation with savepoint duplicate handling.
4. `backend/src/app/presentation/api/v1/matters.py` (+150 / −3 lines) — Three canonical association endpoints + schemas.
5. `backend/tests/integration/test_matter_property_routes.py` (+421 lines) — Comprehensive integration & concurrency test suite.
6. `docs/ImplementationLog/Stage3/Phase42.md` (+97 lines) — Phase implementation log.

**Prohibited Scope Confirmed Absent:**
- Zero frontend modifications.
- Zero Alembic migrations or schema changes (Alembic head remains `b155caa6d4e1`).
- Zero modifications to models `matter_properties.py`, `matter.py`, `property.py`, or `party.py`.
- Zero changes to legacy `Matter.property_id` semantics (no dual-writing, clearing, or backfill).
- Zero Party/Client manufacture or mutation of `PropertyOwner` / `MatterParty`.
- Zero new RBAC permission codes or permission families.
- Zero ADR resolutions: Required ADRs `[12, 15, 16, 17, 20]` remain unresolved; ADR-0044 remains Proposed.
- Zero T158+ selection or authorization.

---

## 4. HTTP API Contract & Response Compatibility

### Verified Routes

1. **List Associated Properties:**
   - `GET /api/v1/matters/{matter_id}/properties`
   - **Status:** `200 OK`
   - **Permissions:** `matters:read` AND `properties:read`
   - **Behavior:** Returns `ApiResponse[list[AssociatedPropertyRead]]`. Obeys tenant boundaries (404 on cross-tenant or missing Matter). Lists zero, one, or multiple canonical Properties.
2. **Associate Existing Property:**
   - `POST /api/v1/matters/{matter_id}/properties`
   - **Body:** `{"property_id": "UUID"}`
   - **Status:** `201 Created` for a newly persisted link; `200 OK` for an already-associated pair.
   - **Permissions:** `matters:write` AND `properties:read`
   - **Behavior:** Resolves both Matter and Property under caller's Organization; inserts `matter_properties` row; records audit event on 201; returns `AssociatedPropertyRead`.
3. **Unlink Property:**
   - `DELETE /api/v1/matters/{matter_id}/properties/{property_id}`
   - **Status:** `204 No Content`
   - **Permissions:** `matters:write` AND `properties:read`
   - **Behavior:** Removes association row if present; returns 204 idempotently whether row was present or already absent; non-enumerating 404 if Matter or Property does not exist in caller's Organization.

### Response Schema Compatibility

`AssociatedPropertyRead` and `AssociatedPropertyOwnerRead` were compared field-by-field against canonical `PropertyRead` and `PropertyOwnerRead` in [properties.py](file:///d:/Code/Legal_DMS_Clean/backend/src/app/presentation/api/v1/properties.py#L97-L140):
- **Property Fields:** `id`, `property_type`, `survey_number`, `sub_division_number`, `area_value`, `area_unit`, `address_id`, `village_id`, `registration_number`, `owners`.
- **Owner Fields:** `party_id`, `legacy_client_id`, `ownership_share`, `ownership_type`, `from_date`, `to_date`.
- **Classification:** 100% field, nullability, type, and Party-canonical owner compatibility. Zero schema drift.

---

## 5. Tenant Isolation & Authorization Matrix

Independent testing against real PostgreSQL verified:
- **Same-Tenant Execution:** Same-Organization Matter + Property associations succeed cleanly.
- **Cross-Tenant Non-Enumeration:**
  - `GET /matters/{other_org_matter_id}/properties` → `404 Not Found`.
  - `POST /matters/{other_org_matter_id}/properties` with own property → `404 Not Found`.
  - `POST /matters/{own_matter_id}/properties` with `other_org_property_id` → `404 Not Found`.
  - `DELETE /matters/{other_org_matter_id}/properties/{prop_id}` → `404 Not Found`.
  - `DELETE /matters/{matter_id}/properties/{other_org_prop_id}` → `404 Not Found`.
  Cross-tenant identifiers never leak resource existence.
- **Unscoped Callers:** Requests lacking authenticated Organization context return `403 Forbidden` (`_require_organization()`).
- **Authorization Enforcement:** Each required permission was tested independently:
  - `GET /matters/{id}/properties` without `matters:read` → `403 Forbidden`.
  - `GET /matters/{id}/properties` without `properties:read` → `403 Forbidden`.
  - `POST /matters/{id}/properties` without `matters:write` → `403 Forbidden`.
  - `POST /matters/{id}/properties` without `properties:read` → `403 Forbidden`.
  - `DELETE /matters/{id}/properties/{prop_id}` without `matters:write` → `403 Forbidden`.
  - `DELETE /matters/{id}/properties/{prop_id}` without `properties:read` → `403 Forbidden`.
- **ADR-0044 Authorization Alignment:** Requiring `matters:write` + `properties:read` for both mutation endpoints strictly satisfies ADR-0044 lines 33–34 ("Creating or removing an association is a Matter-scoped change requiring existing matters:write and appropriate Property visibility/authorization checks; it must not become an indirect way to mutate a Property or bypass its read boundary"). No new permissions were introduced.

---

## 6. Canonical vs Legacy Data Boundary

Independent testing proved that `Matter.property_id` is completely decoupled from T157 canonical operations:
- A Matter having only a populated legacy `property_id` returns an empty array `[]` from `GET /matters/{matter_id}/properties`.
- Creating a canonical association does not mutate, backfill, or overwrite `Matter.property_id`.
- Unlinking a canonical association does not clear or alter `Matter.property_id`.
- Legacy `Matter.property_id` is never read as canonical relationship evidence.
- Required ADR #20 remains unresolved.

---

## 7. Neighbor Aggregate Isolation

Testing confirmed that T157 operations never mutate neighboring entities:
- **`MatterParty`:** Row count and contents remain strictly unchanged before and after association and unlink.
- **`PropertyOwner`:** Owner records remain unchanged before and after association and unlink.
- **`Party` / `Client`:** No Party or Client records are manufactured or updated.
- **Matter / Property Entities:** Primary scalar fields remain unaffected; deleting an association leaves both Matter and Property records intact in the database.

---

## 8. Integrity, Concurrency & Constraint Discrimination

### Real PostgreSQL Concurrent Race Verification

In `test_concurrent_duplicate_repository_attempts_create_exactly_one_row`, two concurrent sessions raced via `asyncio.gather` to insert the same `(organization_id, matter_id, property_id)` pair:
- **Result:** Exactly one call returned `created=True` and the competing call returned `created=False`.
- **Database Row Count:** Exactly one canonical row survived in `matter_properties`.
- **No Exception Leak:** No database exception surfaced to the caller.

### Savepoint & Outer Transaction Semantics

`SqlAlchemyMatterPropertyRepository.add_if_absent` uses `async with self._session.begin_nested():` around `self._session.add()` and `flush()`.
- **Savepoint Isolation:** When PostgreSQL triggers a collision on `uq_matter_properties_organization_id_matter_id_property_id`, the savepoint rolls back only the subtransaction (`ROLLBACK TO SAVEPOINT`).
- **Outer Transaction State:** Verified via dedicated test that the outer session remains clean and usable; subsequent queries, inserts, and commits in the same session complete without transaction poisoning.
- **No Premature Commits:** Neither the repository nor the service invokes `commit()`. Request transaction ownership remains strictly with the FastAPI dependency lifecycle (ADR-0020).

### Constraint-Specific Discrimination Analysis

`add_if_absent` catches `IntegrityError` and checks `getattr(exc.orig, "sqlstate", None) == "23505"`.
- **Database Unique Constraints on `matter_properties`:**
  1. `matter_properties_pkey` — Primary key on `(id)`.
  2. `uq_matter_properties_organization_id_id` — Unique on `(organization_id, id)`.
  3. `uq_matter_properties_organization_id_matter_id_property_id` — Business unique pair on `(organization_id, matter_id, property_id)`.
- **Analysis:**
  The `id` column is populated with a fresh `uuid4()` on each instantiation in `MatterPropertyService.associate`. The probability of a UUID collision on the primary key is negligible (~$10^{-37}$). There are **zero other business unique constraints** on `matter_properties` (a Matter can have multiple Properties; a Property can have multiple Matters). Foreign key violations raise SQLSTATE `23503`, check constraints raise `23514`, and not-null violations raise `23502`.
- **Conclusion:** Any reachable `23505` during `add_if_absent` is mathematically guaranteed to be the canonical pair constraint. Foreign key violations (e.g. invalid endpoint ID) were verified to raise `23503` and are NOT masked as duplicates. Stricter discrimination checking `exc.orig.constraint_name` is noted as an advisory non-blocking comment.

---

## 9. Audit Behavior

Reusing the existing `AuditLogger` port, audit logging was verified:
- **Association Creation (201):** Records exactly one `matter_property_associated` event (`resource_type="matter_property"`, `resource_id=str(matter_id)`, metadata `{"property_id": str(property_id)}`).
- **Duplicate Association (200):** Emits zero (0) additional audit records.
- **Unlink (204, row removed):** Records exactly one `matter_property_unlinked` event (`resource_type="matter_property"`, `resource_id=str(matter_id)`, metadata `{"property_id": str(property_id)}`).
- **Repeated Unlink (204, row already absent):** Emits zero (0) additional audit records.
- **Privacy:** No sensitive tenant data is logged.

---

## 10. Regression Evidence & Full-Suite Classification

### Focused Regression Suites Executed

| Test Suite / Command | Scope | Result |
| :--- | :--- | :--- |
| `uv run pytest tests/integration/test_matter_property_routes.py -v` | T157 HTTP, auth, legacy, & concurrency | **3 passed** in 7.51s |
| `uv run pytest tests/integration/test_matter_property_tenant_integrity_foundation.py -q` | T155 schema, RLS, & downgrade | **5 passed** in 41.07s |
| `uv run pytest tests/integration/test_matter_routes.py tests/integration/test_property_routes.py -q` | Matter & Property route regressions | **6 passed** in 12.81s |
| `uv run pytest tests/unit/test_matter_service.py tests/unit/test_property_service.py tests/unit/test_audit_logger.py -q` | Core domain service & audit unit tests | **15 passed** in 0.17s |
| `uv run pytest tests/integration/test_auth_login.py -v` | Authentication & login auditing (isolated) | **10 passed** in 2.66s |
| `uv run pytest tests/integration/test_operational_fresh_provenance.py -q` | Operational-fresh bootstrap & provenance | **7 passed** in 29.05s |
| `uv run pytest tests/unit -q` | Complete backend unit test suite | **342 passed** in 6.74s |
| `uv run ruff check src tests alembic` | Python linting | **All checks passed** |
| `uv run black --check src tests alembic` | Code formatting check | **329 files clean** |
| `python scripts/governance_validate.py --report` | Governance consistency validation | **0 warnings, 0 errors** |
| `python scripts/tests/test_governance_validate.py -v` | Governance validation unit suite | **60 passed** in 0.164s |

### Baseline vs Candidate Full-Suite Classification

Running the broad integration test suite (`tests/integration`) reveals failures:
1. `tests/integration/test_client_migration_executor.py`:
   - *Failure:* `null value in column "organization_id" of relation "properties" violates not-null constraint`.
   - *Classification:* **COMMON / Pre-existing.** This test file was last modified in commit `2ae0dbf` (T124, 2026-09-15), prior to T133 making `properties.organization_id` mandatory. The file is untouched in PR #296 (`git diff origin/main..HEAD` is empty).
2. `tests/integration/test_auth_login.py` (when run combined with other integration files):
   - *Failure:* `assert len(audit_records) == 1` fails due to pytest `caplog` capture clearing when executed alongside certain session-level loggers.
   - *Classification:* **Environmental / Cross-suite fixture interaction.** When executed in its normal isolated test run, `test_auth_login.py` passes 10/10 tests cleanly.
3. *Candidate-Only Failures:* **Zero (0).**

---

## 11. Exact-Head CI Status

All four workflows completed with success on candidate `89bed9272f8cdd9d2909a0f195ca942fa4278ec5`:

| Workflow | Event | Run ID | Conclusion | Duration |
| :--- | :--- | :--- | :--- | :--- |
| **Governance** | `pull_request` | [39110590085](https://github.com/Intelligentclown/Legal_DMS/actions/runs/39110590085) | **Success** | 9s |
| **Backend** | `pull_request` | [39110590152](https://github.com/Intelligentclown/Legal_DMS/actions/runs/39110590152) | **Success** | 24s |
| **Frontend** | `pull_request` | [39110590084](https://github.com/Intelligentclown/Legal_DMS/actions/runs/39110590084) | **Success** | 42s |
| **Release** | `pull_request` | [39110590112](https://github.com/Intelligentclown/Legal_DMS/actions/runs/39110590112) | **Success** | 29s |

---

## 12. Delivery Calendar Schedule Boundary

- **Task Planning Parameters (docs/delivery_calendar.json):**
  - Planned Start: `2026-10-18`
  - Reported Actual Implementation Start: `2026-10-18`
  - Planned Finish: `2026-10-21`
  - Planned Duration: `4` inclusive calendar days
  - Milestone: `M1`
  - Lane: `matter`
  - Critical Path: `true`
  - Slack: `0`
- **Assessment:**
  No implementation defects or regression blockers were identified that threaten completion within the 4-day window. In accordance with T156 calendar rules, Independent QA does not mark completion or compute final variance.

---

## 13. Findings

### Blocking Findings
- **None (0).**

### Non-Blocking Observations
1. **Advisory — Constraint-Name-Specific Discrimination:**
   In [sqlalchemy_matter_property_repository.py](file:///d:/Code/Legal_DMS_Clean/backend/src/app/infrastructure/persistence/sqlalchemy_matter_property_repository.py#L41-L47), `add_if_absent` checks `getattr(exc.orig, "sqlstate", None) == "23505"`. While sound for this entity because `id` is a random UUIDv4 and no other business uniqueness constraints exist on `matter_properties`, checking `getattr(exc.orig, "constraint_name", None) == "uq_matter_properties_organization_id_matter_id_property_id"` provides even stricter defense-in-depth against unexpected future schema evolutions.
2. **Cosmetic — Implementation Log Commit Hash:**
   `docs/ImplementationLog/Stage3/Phase42.md` records commit hash `fe38f7287dcb6e51f703952da83f2dbff81772b2`, reflecting a local commit created prior to candidate finalization (`89bed9272f8cdd9d2909a0f195ca942fa4278ec5`). Can be aligned during Documentation Manager closeout.

---

## 14. QA Publication Provenance

- **QA Review Artifact Path:** `docs/reviews/T157_QA_Review.md`
- **Reviewed Candidate SHA:** `89bed9272f8cdd9d2909a0f195ca942fa4278ec5`
- **Publication Commit:** Published directly descending from `89bed9272f8cdd9d2909a0f195ca942fa4278ec5`.
- **Files Modified in Publication:** Strictly `docs/reviews/T157_QA_Review.md`.

---

## 15. Next Lifecycle Action

PR #296 is **Approved with comments**.

Under `PROJECT_WORKFLOW.md §3`:
1. Control Tower independently verifies QA provenance and formal decision.
2. Documentation Manager synchronizes governance documentation and closes out T157.
3. PR #296 is merged to `main`.
4. Next task in `IMPLEMENTATION_QUEUE.md` is selected and authorized.
