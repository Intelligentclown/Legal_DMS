# T116 QA Review

**Task:** T116 -- Party migration foundation
**Role:** QA Reviewer, per `docs/prompts/QAReviewer.md`
**Artifacts under review:** PR #203

## 1. Verified Baseline and Authorization Ancestry
- Evaluated against base `9d326263188e919e0c76dd969610c55560d65775`.
- Reviewed exact PR HEAD `4ab657dc860c716438f5b58872ec7aa284efd37c`.
- Confirmed authorization commit `45ffe353c521245ed9db1fd7e24689394c59f53f` is a genuine ancestor.

## 2. Independent Governance Checks
- `PROJECT_STATE.json` correctly declares `latestTaskAuthorized = T116` and `latestTaskDone = T115`.
- T117+ remains unauthorized.
- Required ADR #20 remains unresolved globally.
- `python scripts/governance_validate.py` returned 0 errors.

## 3. Scope and Implementation Validation
- **Party**: Correctly implements the exact field contract, UUID PK, mandatory `organization_id`, and `(organization_id, id)` uniqueness constraint. Tenant-leading indices and specific CHECK constraints (PAN, Aadhaar, GSTIN format, etc.) are accurately reflected. No accidental natural-key identity exists on search identifiers.
- **Party → Address tenant integrity**: Correctly enforced via `(organization_id, address_id) -> addresses(organization_id, id)`.
- **MatterParty**: Correctly implements the bounded MatterParty schema with exact roles and composite FKs to both `parties` and `matters`, along with `(matter_id, party_id, role)` uniqueness.
- **Migration & ORM parity**: Exclusions are correctly verified. No Party bridges, no Client->Party migration execution, no downstream data backfills, no `NOT NULL` on T115 staging columns. ORM exactly matches the Alembic migration scripts.
- **Local testing:** `pytest` regression checks passed on SQLite. `git diff --check`, `ruff`, and `black` reported no errors for the tracked files. PostgreSQL live verification was omitted due to local environment constraints (Docker unavailable).

## 4. Execution-Ledger Tenant Integrity Defect
While verifying the implementation of `client_party_migration_ledger`, a critical architectural defect was found.

According to ADR-0035 ("Required future implementation sequence", Step 2), the implementation must introduce:
> `parties`, `matter_parties`, `client_party_migration_ledger`, and the composite same-Organization FK infrastructure they require

The ledger represents the authoritative Organization identity for a migrated legacy Client. However, the current migration script and ORM model define independent foreign keys:
- `party_id -> parties.id`
- `organization_id -> organizations.id`

This fails to enforce structural equality between the ledger's `organization_id` and the referenced Party's `organization_id`. To be tenant-safe, the ledger must enforce a composite same-Organization foreign key:
`(organization_id, party_id) REFERENCES parties (organization_id, id)`

## 5. QA Decision
The omission of the composite same-Organization foreign key on the execution ledger is a severe tenant boundary flaw that violates the repository's strict structural-integrity rules (ADR-0021/ADR-0035). 

**Decision: Rework required**

### Required Remediation
1. Update `backend/alembic/versions/e6a2d4c8f1b7_party_matterparty_ledger_foundation.py` to replace `fk_client_party_migration_ledger_party_id_parties` with a composite constraint on `(organization_id, party_id)` referencing `parties (organization_id, id)`.
2. Update the SQLAlchemy `ClientPartyMigrationLedger` model to reflect this composite FK.
3. Push the fix to the branch and request another QA pass.
