# T114 Software Architect Report

**Task:** T114 -- Party Persistence Schema Contract and Tenant-Safe Migration Bridge Architecture.

**Role:** Software Architect, per `docs/prompts/SoftwareArchitect.md`.

**Artifact under review:** `ADR/0035-party-persistence-schema-contract-and-tenant-safe-migration-bridges.md`.

**Status:** Initial architecture draft for PR 2 of T114's three-PR lifecycle. This report does not
perform independent QA, merge, governance closeout, or implementation.

## 1. Verified Baseline and Authorization Ancestry

- Fresh `git fetch origin` completed before any work.
- `origin/main` was verified at `ff9deacfbb7125ed47866a1e564442bfe5edb98b`, exactly the expected
  merge commit for PR #199, `docs(governance): authorize T114 party persistence schema architecture`.
- `git show` on `ff9deacfbb7125ed47866a1e564442bfe5edb98b` confirmed it is the merge of PR #199 and
  that it directly includes authorization commit `855aec1afb07f56ac26c18f5804191f49bfe494f`.
- `git merge-base --is-ancestor 855aec1afb07f56ac26c18f5804191f49bfe494f HEAD` must hold on this
  branch; the Architecture branch was created directly from `origin/main`, so the authorization is
  in ancestry by construction.
- Governance state was rechecked from repository artifacts before drafting:
  - `latestTaskAuthorized = T114`
  - `latestTaskDone = T113`
  - `inProgressTransitions = []`
  - Required ADR #20 remains unresolved globally
  - T114 exists and is authorized, but is not Done
  - T115+ remains unauthorized
- Remote-branch inspection found only the T114 authorization branch
  `origin/docs/t114-authorization-party-persistence-schema-contract`; no T114 Architecture branch
  existed before this branch was created.
- ADR numbering was rechecked from repository contents. `ADR/0034` was the highest existing ADR on
  `origin/main`, so this task correctly uses `ADR/0035`.

## 2. Sources Inspected

Read directly during this bounded architecture pass:

- `AI_BOOTSTRAP.md`
- `docs/AI_EXECUTION_ROUTING.md`
- `PROJECT_WORKFLOW.md`
- `PROJECT_STATE.json`
- T114's exact row in `IMPLEMENTATION_QUEUE.md`
- `docs/prompts/SoftwareArchitect.md`
- `docs/ImplementationLog/README.md`
- `ADR/template.md`
- `ADR/0020`, `ADR/0021`, `ADR/0022`, `ADR/0023`, `ADR/0030`, `ADR/0032`, `ADR/0033`, `ADR/0034`
- `docs/Legal_DMS — Domain Model & Functional Specification.md`
- `docs/PartyClientReconciliationContract.md`
- `backend/src/app/infrastructure/cli/client_migration_preflight.py`
- `backend/src/app/infrastructure/cli/client_reconciliation_staleness_preflight.py`
- `backend/src/app/infrastructure/database/base.py`
- `backend/src/app/infrastructure/persistence/models/__init__.py`
- `backend/src/app/infrastructure/persistence/models/client.py`
- `backend/src/app/infrastructure/persistence/models/matter.py`
- `backend/src/app/infrastructure/persistence/models/property.py`
- `backend/src/app/infrastructure/persistence/models/financial.py`
- `backend/src/app/infrastructure/persistence/models/scheduling.py`
- `backend/src/app/infrastructure/persistence/models/mixins.py`
- Alembic revisions:
  - `ac077004afeb_clients_addresses_clients_client_.py`
  - `7789f56da7f9_properties_properties_property_owners.py`
  - `c52ee7c83023_matters_and_workflow_matter_types_.py`
  - `cf6b0519b74c_financial_payment_methods_invoices_.py`
  - `07150e442816_scheduling_and_tags.py`
- relevant tests and docs via repository search:
  `test_client_models.py`, `test_client_migration_preflight.py`, `test_matter_and_workflow_models.py`,
  `test_property_models.py`, `test_financial_models.py`, `test_scheduling_models.py`,
  `test_document_models.py`, `test_ocr_qr_backup_models.py`, `docs/ERD.md`, and `docs/Database.md`

## 3. Architecture Decisions Frozen by ADR-0035

ADR-0035 makes the following implementation-ready decisions:

- initial Party discriminator vocabulary is exactly `individual` and `organization`;
- finer legal-form categories are not first-wave discriminator values;
- the first `parties` table uses `party_type`, `display_name`, `primary_phone`, `primary_email`,
  `address_id`, `notes`, `pan_number`, `aadhaar_number`, `gstin`, `registration_identifier`,
  `date_of_birth`, `gender`, `occupation`, `incorporation_date`, direct `organization_id`, and the
  standard audited/versioned columns;
- legacy Client UUIDs are preserved exactly as Party UUIDs during governed backfill;
- no PAN, Aadhaar, GSTIN, registration identifier, email, phone, or display-name uniqueness rule is
  introduced;
- subtype applicability is enforced by database `CHECK` constraints, but non-frozen business
  requiredness rules are not invented;
- `addresses.organization_id` is required and becomes final `NOT NULL` before normal Party writes;
- Party <-> Address and Property <-> Address relationships must enforce same-Organization equality by
  composite FK or equivalently strong declarative constraint;
- `client_party_migration_ledger` is the canonical immutable execution-ledger table implementing
  `ADR/0034`;
- every first legacy `party_id` bridge target is classification **B**, meaning it must be introduced
  together with tenant ownership/supporting constraints;
- a bounded minimum `matter_parties` contract is safe and required for the Party migration
  foundation;
- the minimum atomic migration unit is one legacy Client anchor, committing Party row, in-scope
  bridge writes, and immutable ledger row together.

## 4. Exact Party Contract Summary

The first Party table is one Organization-scoped master record per Party with:

- key/tenancy: `id`, `organization_id`, `party_type`
- universal fields: `display_name`, `primary_phone`, `primary_email`, `address_id`, `notes`
- universal searchable identifiers: `pan_number`, `gstin`
- individual-only fields: `aadhaar_number`, `date_of_birth`, `gender`, `occupation`
- organization-only fields: `registration_identifier`, `incorporation_date`
- standard audited/versioned columns: `created_at`, `updated_at`, `created_by`, `updated_by`,
  `version`, `deleted_at`

Legacy Client field treatment is explicit:

- `id` preserved
- `client_type` -> `party_type`
- `full_name` -> `display_name`
- `primary_phone` / `primary_email` / `pan_number` / `aadhaar_number` / `notes` preserved
- `address_id` preserved only when the referenced Address resolves to the same Organization

## 5. Address Tenancy Decision

`addresses` remains the concrete business-address table, not reference data. T114 freezes the
physical tenant-safe contract required by `ADR/0033`:

- add `addresses.organization_id` as a staged nullable column for reconciliation/backfill only;
- make it final `NOT NULL` before Party normal-write enablement;
- add direct Organization FK, direct index, and composite unique `(organization_id, id)`;
- enforce Party/Address and Property/Address Organization equality through composite FKs;
- treat cross-Organization legacy Address sharing as unresolved conflict, never implicit global
  reuse;
- keep Party creation disabled during the migration window so no new unsafe Party rows can attach to
  unreconciled Address data.

## 6. Execution-Ledger Physical Schema Decision

ADR-0035 freezes `client_party_migration_ledger` as the append-only durable completion record
required by `ADR/0034`.

The ledger stores at minimum:

- `legacy_client_id`
- `party_id`
- `organization_id`
- `executor_version`
- exact T109 `reconciliation_set_id`
- exact T108/T109 `source_report_sha256`
- `resolution_mode`
- `source_client_version`
- `source_client_updated_at`
- canonical `source_fingerprint`
- `completed_at`
- minimal artifact provenance fields
- `execution_run_id`

It is immutable, does not use `AuditMixin`, and relies on explicit unique keys for identical
completion and collision detection rather than on mutable updates.

## 7. Bridge Sequencing Decision

The first legacy Client bridge targets all require classification **B**:

- `property_owners.client_id`
- `appointments.client_id`
- `invoices.client_id`
- `payments.client_id`
- `client_contacts.client_id`

That means the future implementation may not add `party_id` alone as a schema-only convenience.
Each bridge must appear together with the direct `organization_id` support and same-Organization FK
structure that makes the bridge tenant-safe under `ADR/0021` and `ADR/0033`.

Final nullability is also frozen:

- `property_owners.party_id`: `NOT NULL`
- `appointments.party_id`: nullable
- `invoices.party_id`: `NOT NULL`
- `payments.party_id`: `NOT NULL`
- retained `client_contacts.party_id`: `NOT NULL`

## 8. MatterParty Decision

The ADR concludes that a bounded minimum `matter_parties` contract can be introduced safely now.

What is frozen:

- `matter_parties` exists as the Matter <-> Party join required by `ADR/0023`
- it carries `organization_id`, `matter_id`, `party_id`, and `role`
- it enforces same-Organization references by composite FK
- backfill from legacy `matters.client_id` uses `role = 'client'`
- unique `(matter_id, party_id, role)` prevents identical duplicate participation rows

What remains deliberately open:

- broader role vocabulary beyond support for `client`
- wider MatterParty cardinality/business semantics not needed to retire `matters.client_id`

## 9. Alternatives Considered

The ADR evaluates and rejects:

1. a minimal shell ADR that leaves concrete Party fields and ledger shape for implementation;
2. a broad first-wave discriminator vocabulary covering many legal forms as separate Party subtypes.

The selected approach freezes the first full schema contract but keeps the first subtype vocabulary
minimal and attribute-driven where the current governance does not justify more.

## 10. Explicitly Deferred / Not Resolved

Still outside T114 and deliberately left unresolved:

- broader Matter migration beyond the bounded MatterParty foundation
- Matter `property_id` / `matter_type_id` retirement
- Document `matter_id` -> `file_id`
- final global cutover/removal choreography
- Representative normalization and `client_contacts` replacement
- legal-form taxonomy beyond the two initial Party discriminator values
- Party API/CRUD/UI
- any write-capable executor or schema implementation

Required ADR #20 therefore remains unresolved globally after this ADR.

## 11. Recommended Future Implementation Sequence

ADR-0035 ends with the recommended smallest safe implementation order:

1. tenant-supporting Address and downstream-table schema foundation;
2. Party + bounded MatterParty + immutable execution-ledger schema;
3. direct `party_id` compatibility bridges;
4. governed reconciliation/backfill executor implementation;
5. code cutover;
6. legacy removal.

The recommended smallest next implementation slice after T114 is step 1: the tenant-supporting
schema foundation required before Party can safely reference Address and before the first bridge
columns can be tenant-safe.

## 12. Exact Files Changed

Exactly two architecture artifacts are added by this T114 Software Architect pass:

- `ADR/0035-party-persistence-schema-contract-and-tenant-safe-migration-bridges.md`
- `docs/reviews/T114_Software_Architect_Report.md`

No application code, schema implementation, migration script, test, workflow, queue row, or
`PROJECT_STATE.json` change was made.

## 13. Validation

The required validation set for this architecture draft is:

- `python scripts/governance_validate.py`
- `python -m unittest scripts.tests.test_governance_validate -v`
- `git diff --check`
- final diff inspection confirming no unauthorized implementation/schema/data mutation occurred

This report does not render the independent QA decision.

## 14. Confirmation No Unauthorized Implementation Occurred

This branch does **not** implement:

- SQLAlchemy Party model
- `parties` table
- `matter_parties` table
- Address schema changes
- `client_party_migration_ledger` table
- bridge columns
- Alembic migrations
- RLS policies
- data migration or reconciliation execution
- Party API/CRUD/frontend work
- QA approval
- merge or governance closeout
- T115 or later authorization

## Reviewer Checklist

```text
Reviewer Checklist

☑ Architecture preserved
☑ Existing design patterns followed
□ Tests added
□ Existing tests pass
☑ Documentation updated
☑ ADR updated (if required)
□ AI_BOOTSTRAP updated (if required)
□ PROJECT_STATE updated (if required)
☑ No unrelated refactoring
☑ No scope creep
☑ Ready for QA
```

`Tests added` and `Existing tests pass` remain correctly unchecked because this is an
architecture-only PR-2 deliverable. `AI_BOOTSTRAP.md` and `PROJECT_STATE.json` are correctly
untouched because no standing process changed and T114 has not reached governance closeout.

## QA Decision

```text
□ Approved
□ Approved with comments
□ Rework required
```

The next required role is the independent QA Reviewer, after this branch is validated, pushed, and
opened as the T114 Architecture+QA PR.
