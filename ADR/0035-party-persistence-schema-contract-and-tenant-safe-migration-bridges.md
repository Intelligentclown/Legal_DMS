# ADR-0035: Party Persistence Schema Contract and Tenant-Safe Migration Bridges

**Status:** Proposed
**Date:** 2026-09-04

**Resolves:** the bounded Party persistence/schema-contract and directly necessary tenant-safe
Party/Client migration-bridge architecture slice authorized by `T114`. This ADR freezes the first
implementable `parties` table contract, the tenant-safe Address/Party relationship contract, the
append-only physical execution-ledger schema required by `ADR/0034`, the minimum migration-bounded
`matter_parties` contract, and the classification/sequencing rules for the first legacy `client_id`
bridge targets.

**Does not resolve:** the governed specification's broader migration item in full. Matter
`property_id` / `matter_type_id` retirement, Document `matter_id` -> `file_id`, broader MatterParty
role/cardinality design, Representative normalization, non-Party migration seams, final cutover
removal sequencing beyond the Party bridge boundary, and any Party API/CRUD or write-capable
migration implementation remain outside this ADR. This ADR does not reopen `ADR/0020`, `ADR/0021`,
`ADR/0022`, `ADR/0023`, `ADR/0032`, `ADR/0033`, or `ADR/0034`.

**Dependencies:** `ADR/0020-session-commit-rollback-policy.md`, `ADR/0021-organization-tenant-boundary-enforcement.md`,
`ADR/0022-authorization-architecture.md`, `ADR/0023-party-vs-client-architecture.md`,
`ADR/0030-matter-file-lifecycle-and-identity-boundary.md`,
`ADR/0032-user-organization-pre-existing-data-reconciliation.md`,
`ADR/0033-party-client-migration-organization-boundary.md`,
`ADR/0034-party-client-migration-persistence-and-execution-ledger.md`,
`docs/PartyClientReconciliationContract.md`, and the T108-T111 governed evidence chain.

## Problem

`ADR/0023` already fixed the Party direction: one `parties` table, discriminator-based subtype
modeling, nullable subtype-specific relational columns, no inheritance hierarchy, and no JSONB Party
profile. `ADR/0033` then fixed the legacy `clients` -> `parties` migration direction and
Organization-reconciliation rule. `ADR/0034` fixed the need for a dedicated append-only completion
ledger.

The remaining blocker is narrower and more concrete: the repository still has no governed,
implementation-ready answer for what the first `parties` table physically looks like, which subtype
values the first schema actually supports, which fields must exist on day one, how those fields
compose with the Address tenant boundary `ADR/0033` added, what exact immutable ledger schema a
future executor persists to, whether a bounded `matter_parties` minimum can be introduced without
solving the full MatterParty domain model, and which legacy bridge columns may or may not appear
before tenant ownership exists.

Without this ADR, a future Backend Developer would have to invent:

- the initial Party discriminator vocabulary;
- the first Party field list and subtype applicability rules;
- uniqueness/index behavior for PAN, Aadhaar, GSTIN, registration identifiers, phone, email, and
  display name;
- whether Address and Party equality is enforced structurally or by convention;
- the physical execution-ledger table required by `ADR/0034`;
- the minimum MatterParty schema needed to retire `matters.client_id`;
- and whether the first `party_id` bridges may appear before `organization_id` and tenant-safe
  constraints exist.

Those are architectural decisions, not implementation details.

## Options Considered

1. **Freeze only a minimal Party shell and defer most schema details to implementation.**
   - Pros: smallest ADR surface now.
   - Cons: leaves the first schema task free to invent subtype vocabulary, identifier fields,
     bridge sequencing, and ledger shape at implementation time; does not satisfy T114's
     implementation-ready requirement.

2. **Model many legal-entity categories as first-class discriminator values in the first schema.**
   - Pros: potentially richer legal-form fidelity on day one.
   - Cons: the governed specification names trusts, government bodies, and similar categories as
     examples of legal entities Party must eventually represent, but it does not freeze them as
     first-wave persistence subtypes with distinct required field sets. Treating them as
     discriminator values now would invent persistence categories the repository has not yet proven
     it needs, especially for Indian entity forms whose practical differences are often registration
     or tax attributes rather than an entirely different master-record shape.

3. **Freeze the complete first Party persistence contract now, but keep the first discriminator
   vocabulary minimal (`individual`, `organization`) and carry finer legal-form distinctions as
   later attributes or future ADR work (selected).**
   - Pros: satisfies `ADR/0023`'s single-table discriminator strategy, keeps the first schema
     implementable, preserves the legacy Client field set, supports the identifiers and contact
     fields the governed spec explicitly names, composes cleanly with `ADR/0033` and `ADR/0034`,
     and avoids inventing ungoverned subtype categories.
   - Cons: broad `organization` is a deliberate umbrella; if a later legal form needs materially
     different required fields or lifecycle behavior, a later ADR may need to extend the schema.

## Decision

Option 3 is adopted.

The first Party persistence foundation is frozen as:

- one `parties` table;
- a `party_type` discriminator with exactly two initial values: `individual` and `organization`;
- a tenant-safe direct `organization_id` boundary from first insert onward;
- a nullable, tenant-safe `address_id` relationship to Organization-scoped `addresses`;
- subtype-specific relational columns for the fields the governed specification actually names;
- no natural-key Party identity and no uniqueness constraints on human/contact/tax identifiers;
- a dedicated append-only `client_party_migration_ledger` table implementing `ADR/0034`;
- a bounded minimum `matter_parties` contract that is sufficient for retiring `matters.client_id`
  without deciding the full MatterParty domain model;
- and bridge-column sequencing that requires tenant ownership/supporting constraints together with
  every first `party_id` bridge.

### 1. Initial Party subtype vocabulary

The first discriminator vocabulary is exactly:

- `individual`
- `organization`

No additional first-class discriminator values are introduced in the first schema for trust,
government body, partnership, LLP, HUF, society, firm, or other legal categories.

Those remain representable as Parties under the `organization` umbrella unless and until a later ADR
establishes that one or more categories require materially different master-record structure or
invariants. This ADR deliberately distinguishes:

- **fundamental persistence subtype**: `individual` vs `organization`;
- **later legal-form classification**: a future attribute-level or taxonomy decision, not a first
  schema discriminator requirement.

### 2. Canonical first Party table contract

Canonical table: `parties`

Core key and tenancy columns:

| Column | Type | Null | Applies to | Default / DB rule | Search / index | Legacy mapping |
|---|---|---:|---|---|---|---|
| `id` | `UUID` | No | all | PK, Python `uuid4` for new rows | PK | legacy `clients.id` reused during migration |
| `organization_id` | `UUID` | No | all | FK to `organizations.id`; no default | index; composite unique `(organization_id, id)` for tenant-safe downstream FKs | new, from `ADR/0033` reconciliation |
| `party_type` | `String(20)` | No | all | `CHECK party_type IN ('individual', 'organization')` | index with tenant-leading search support | legacy `clients.client_type` -> `party_type` |

Universal business columns:

| Column | Type | Null | Applies to | Default / DB rule | Search / index | Legacy mapping |
|---|---|---:|---|---|---|---|
| `display_name` | `String(255)` | No | all | none | tenant-leading btree search index | legacy `clients.full_name` |
| `primary_phone` | `String(20)` | No | all | `CHECK length(primary_phone) >= 7` | tenant-leading btree search index | legacy `clients.primary_phone` |
| `primary_email` | `String(255)` | Yes | all | no DB regex required in first schema | tenant-leading btree search index where not null | legacy `clients.primary_email` |
| `address_id` | `UUID` | Yes | all | composite FK enforcing same-Organization Address | index only through composite FK support | legacy `clients.address_id` |
| `notes` | `String(2000)` | Yes | all | none | no dedicated index required | legacy `clients.notes` |

Subtype-specific identifier and profile columns:

| Column | Type | Null | Applies to | Default / DB rule | Search / index | Legacy mapping |
|---|---|---:|---|---|---|---|
| `pan_number` | `String(10)` | Yes | all | `CHECK pan_number IS NULL OR pan_number ~ '^[A-Z]{5}[0-9]{4}[A-Z]$'` | tenant-leading btree exact-match index where not null | legacy `clients.pan_number` |
| `aadhaar_number` | `String(12)` | Yes | `individual` only | `CHECK aadhaar_number IS NULL OR aadhaar_number ~ '^[0-9]{12}$'` plus subtype applicability check | tenant-leading btree exact-match index where not null | legacy `clients.aadhaar_number` |
| `gstin` | `String(15)` | Yes | all | `CHECK gstin IS NULL OR gstin ~ '^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$'` | tenant-leading btree exact-match index where not null | new Party field |
| `registration_identifier` | `String(50)` | Yes | `organization` only | no first-schema regex; must be non-empty if present | tenant-leading btree exact-match index where not null | new Party field |
| `date_of_birth` | `Date` | Yes | `individual` only | subtype applicability check; no age/business-policy check | no first-schema index required | new Party field |
| `gender` | `String(50)` | Yes | `individual` only | subtype applicability check; no vocabulary `CHECK` in first schema | no first-schema index required | new Party field |
| `occupation` | `String(255)` | Yes | `individual` only | subtype applicability check | no first-schema index required | new Party field |
| `incorporation_date` | `Date` | Yes | `organization` only | subtype applicability check | no first-schema index required | new Party field |

Canonical treatment of legacy Client fields:

- `clients.id` -> `parties.id`, preserved exactly during governed backfill.
- `clients.client_type` -> `parties.party_type`.
- `clients.full_name` -> `parties.display_name`.
- `clients.primary_phone` -> `parties.primary_phone`.
- `clients.primary_email` -> `parties.primary_email`.
- `clients.pan_number` -> `parties.pan_number`.
- `clients.aadhaar_number` -> `parties.aadhaar_number`.
- `clients.address_id` -> `parties.address_id`, but only after the referenced Address has a matching
  resolved `organization_id`.
- `clients.notes` -> `parties.notes`.

No legacy Client field is discarded. The first Party schema intentionally does **not** introduce a
separate `full_name` column, a separate `legal_name` column, or any JSON profile field; the governed
first-wave canonical name column is `display_name`, because the specification requires one reusable
Party name across both individuals and legal entities but does not freeze a separate legal-name
taxonomy yet.

### 3. Subtype applicability and database invariants

The first schema must distinguish four different concepts:

- **format validation**
- **subtype applicability**
- **requiredness**
- **uniqueness**

They are not interchangeable.

Required subtype rules:

- `aadhaar_number`, `date_of_birth`, `gender`, and `occupation` are individual-only.
- `registration_identifier` and `incorporation_date` are organization-only.
- `pan_number` is universal: both individuals and legal entities may carry PAN.
- `gstin` is universal in the persistence contract: the first schema does not treat GSTIN as
  organization-only because the governed architecture distinguishes persistence subtype from legal
  or tax registration form, and GST registration can attach to more than one practical legal-form
  situation. Format is validated; subtype-specific business policy is not overclaimed.

Required mechanical checks:

- subtype applicability must be enforced by database `CHECK` constraints, not left to application
  convention;
- these checks may only enforce nullability-by-subtype, not business completeness rules the
  specification has not frozen.

Examples:

- an `organization` Party must have `aadhaar_number IS NULL`, `date_of_birth IS NULL`,
  `gender IS NULL`, and `occupation IS NULL`;
- an `individual` Party must have `registration_identifier IS NULL` and
  `incorporation_date IS NULL`.

No first-schema `CHECK` requires:

- PAN to be present for either subtype;
- GSTIN to be present for either subtype;
- a specific controlled vocabulary for `gender`;
- a minimum age, non-future DOB, or non-future incorporation date rule.

Those would be new business-policy decisions not frozen by current governance.

### 4. Identity, uniqueness, and coexistence rules

Identity rules:

- `parties.id` is `UUID`, matching the repository's existing PK convention.
- `clients.id` is `UUID`, also generated via Python `uuid4`.
- Backfilled legacy Party rows must preserve the existing `clients.id` value exactly; no replacement
  UUID generation is allowed.
- Because the keys are application-generated UUIDs rather than a database sequence, identity
  preservation creates no sequence-reset requirement.

Safety conditions for identity preservation:

- before legacy Party backfill begins, `parties` must be empty of ordinary Party business rows;
- Party creation remains unavailable during the migration window;
- if a Party row already exists, the ledger must prove it is the identical, previously completed
  legacy mapping for the same `legacy_client_id`, `organization_id`, and source fingerprint;
  otherwise migration aborts;
- new Party rows may not coexist with unmigrated Client rows.

Uniqueness rules:

- no global or per-Organization uniqueness on `display_name`;
- no uniqueness on `primary_phone`;
- no uniqueness on `primary_email`;
- no uniqueness on `pan_number`;
- no uniqueness on `aadhaar_number`;
- no uniqueness on `gstin`;
- no uniqueness on `registration_identifier`.

These values are searchable identifiers or contact fields, not Party identity keys.

Required indexing rule:

- searchable Party attributes use tenant-leading, non-unique indexes of the form
  `(organization_id, <column>)` or a tenant-equivalent partial index for nullable identifiers.

### 5. Organization tenancy and normal-write boundary

`parties.organization_id` is:

- `UUID NOT NULL`;
- FK to `organizations.id`;
- indexed directly;
- backed by composite unique `(organization_id, id)` so downstream composite FKs can enforce same
  Organization references.

Tenant isolation obligations, composing directly with `ADR/0021`:

- Party rows are tenant-scoped from first insert onward;
- Party repositories/services must require Organization scope at the application layer;
- Party must have forced default-deny RLS before it becomes a normal application-visible table;
- migration-time writes are the only allowed Party writes until the entire governed backfill and
  bridge population is complete;
- ordinary Party creation must remain unavailable during the governed migration window.

### 6. Address tenancy and Party <-> Address integrity

`ADR/0033` already established that `addresses` stores concrete tenant-scoped business data.
This ADR freezes the physical contract required to implement that safely:

- `addresses.organization_id` is added as `UUID`, nullable only during the reconciliation/backfill
  stage;
- `addresses.organization_id` becomes `NOT NULL` before any Party normal-write enablement or final
  same-Organization FK enforcement;
- `addresses` must gain a direct FK to `organizations.id`, a direct index on `organization_id`, and
  a composite unique key `(organization_id, id)`;
- Party's `address_id` remains nullable, but when non-null it must reference an Address row in the
  same Organization through a composite FK:
  `FOREIGN KEY (organization_id, address_id) REFERENCES addresses (organization_id, id)`;
- if bridge-era `clients.address_id` remains present, it follows the same same-Organization rule;
- `properties.address_id` must ultimately use the same composite same-Organization reference rule;
- cross-Organization legacy Address references are unresolved conflicts, never proof that an Address
  is globally shareable;
- if reconciliation chooses to duplicate an Address for two Organizations, that duplication must be
  an explicit operator-governed outcome in later implementation, never an automatic clone heuristic.

Address RLS becomes active only after `addresses.organization_id` is fully reconciled and final
`NOT NULL` plus same-Organization references are in place. Before that point, Party creation remains
disabled, which is the governance mechanism that prevents unsafe new Party rows from being attached
to unreconciled Address data.

### 7. Audit, version, and deletion contract for Party

The first Party persistence schema uses the repository's ordinary audited-entity structure:

- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- `updated_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- `created_by UUID NULL REFERENCES users(id)`
- `updated_by UUID NULL REFERENCES users(id)`
- `version INTEGER NOT NULL DEFAULT 1`
- `deleted_at TIMESTAMPTZ NULL`

Rules:

- `version` is structurally part of the first Party table and should opt into the same optimistic
  locking convention legacy `Client` already uses;
- `deleted_at` may exist structurally for repository consistency and future audit/history needs, but
  this ADR does **not** authorize Party deletion behavior, Party archival semantics, cascade policy,
  or end-user delete capability;
- no future implementation may interpret the existence of `deleted_at` as permission to expose Party
  deletion without a separately governed decision if business semantics are still unresolved.

### 8. Physical execution-ledger schema

Canonical append-only ledger table: `client_party_migration_ledger`

This table is a dedicated operational ledger, not a business master table, and it intentionally does
**not** use the repository's mutable `AuditMixin`.

Required columns:

| Column | Type | Null | Rule |
|---|---|---:|---|
| `id` | `UUID` | No | PK for the immutable ledger row |
| `legacy_client_id` | `UUID` | No | FK to `clients.id` while legacy table exists |
| `party_id` | `UUID` | No | FK to `parties.id`; `CHECK party_id = legacy_client_id` for the governed identity-preserving backfill |
| `organization_id` | `UUID` | No | FK to `organizations.id`; this is the selected authoritative Organization result |
| `executor_version` | `String(100)` | No | identifies the write-capable executor build/version |
| `reconciliation_set_id` | `String(255)` | No | exact T109 `set_id` |
| `source_report_sha256` | `String(64)` | No | exact T108/T109 `source_report.report_sha256` |
| `resolution_mode` | `String(32)` | No | `CHECK resolution_mode IN ('deterministic', 'operator_reconciled')` |
| `source_client_version` | `Integer` | No | legacy Client `version` at execution time |
| `source_client_updated_at` | `DateTime(timezone=True)` | No | legacy Client `updated_at` at execution time |
| `source_fingerprint` | `String(255)` | No | canonical fingerprint string, matching ADR-0034/T108 shape |
| `completed_at` | `DateTime(timezone=True)` | No | immutable completion timestamp, default `now()` |
| `artifact_actor_type` | `String(32)` | Yes | actor type copied from governed reconciliation artifact where available |
| `artifact_actor_id` | `String(255)` | Yes | actor/process identifier copied from governed reconciliation artifact where available |
| `operator_note` | `String(2000)` | Yes | copied forward only when the accepted artifact carries one |
| `execution_run_id` | `UUID` | No | groups immutable rows produced by one executor run without weakening per-row identity |

Required indexes and constraints:

- unique identical-completion key on:
  `legacy_client_id`, `party_id`, `organization_id`, `executor_version`,
  `reconciliation_set_id`, `source_report_sha256`, `source_fingerprint`
- unique basis-collision key on:
  `legacy_client_id`, `executor_version`, `reconciliation_set_id`, `source_report_sha256`
- btree indexes on `organization_id`, `party_id`, `completed_at`, and `execution_run_id`
- append-only expectation: no updates, no deletes, no soft deletion, no version column

Interpretation:

- an identical completion is the same ledger identity tuple above;
- a stale basis is the same legacy Client anchor with changed source fingerprint and/or changed
  report basis;
- a hard collision is the same legacy Client anchor or basis claiming a different Party or
  Organization outcome.

Standard audit mixins are inappropriate here because the ledger must be immutable. A mutable
`updated_at`, `deleted_at`, or optimistic-lock `version` would blur the difference between "history"
and "business row currently editable."

### 9. Atomic migration unit contract

The minimum atomic migration unit is one legacy Client anchor.

One committed migration unit must atomically persist:

- the `parties` row for that Client anchor;
- every in-scope bridge/retarget row that is part of the same unit for that anchor;
- and the immutable `client_party_migration_ledger` completion row.

If the transaction does not commit, none of those facts count as complete. An interrupted execution
is recognized by the absence of an identical ledger row, even if partial business rows appear to be
present. That remains a fail-closed condition for later implementation to detect and handle under
`ADR/0034`; this ADR does not authorize heuristic repair.

### 10. Compatibility bridge classifications

For the first bridge targets named in T114, the classification is:

| Legacy dependency | Classification | Initial `party_id` | Final `party_id` | `organization_id` requirement | Legacy retirement dependency |
|---|---|---|---|---|---|
| `property_owners.client_id` | **B** - must be introduced together with tenant ownership/supporting constraint | nullable for bridge backfill | `NOT NULL` | `property_owners.organization_id NOT NULL`, `properties.organization_id NOT NULL`, composite same-Organization FKs | only after Property code and data have cut over |
| `appointments.client_id` | **B** | nullable for bridge backfill | nullable, matching current semantics | `appointments.organization_id NOT NULL`, composite Party FK when populated | only after Scheduling code has cut over |
| `invoices.client_id` | **B** | nullable for bridge backfill | `NOT NULL` | `invoices.organization_id NOT NULL`, same-Organization Matter/Party FKs | only after Finance code has cut over |
| `payments.client_id` | **B** | nullable for bridge backfill | `NOT NULL` | `payments.organization_id NOT NULL`, same-Organization Invoice/Matter/Party FKs | only after Finance code has cut over |
| `client_contacts.client_id` | **B** | nullable for bridge backfill | `NOT NULL` while retained | `client_contacts.organization_id NOT NULL`, same-Organization Party FK | only after a separate Representative/contact decision governs retirement |

Classification **A** is rejected for these tables because a `party_id` bridge without direct tenant
ownership would violate `ADR/0021` and `ADR/0033`. Classification **C** is rejected because these
bridges are directly necessary to the authorized Party migration foundation, not optional later
cleanup.

### 11. Minimum MatterParty contract

The first Party migration foundation may safely introduce a bounded minimum `matter_parties`
contract without deciding the full MatterParty domain model.

Canonical bounded table contract:

- `id UUID PRIMARY KEY`
- `organization_id UUID NOT NULL`
- `matter_id UUID NOT NULL`
- `party_id UUID NOT NULL`
- `role String(50) NOT NULL`
- `created_at`, `updated_at`, `created_by`, `updated_by`, `version`, `deleted_at` using the normal
  audited join-table convention

Required constraints:

- FK `organization_id` -> `organizations.id`
- composite FK `(organization_id, matter_id)` -> `matters (organization_id, id)`
- composite FK `(organization_id, party_id)` -> `parties (organization_id, id)`
- unique `(matter_id, party_id, role)` to prevent duplicate identical participation rows
- no unique `(matter_id, role)` because multi-party client-side participation must remain possible

Bounded role decision:

- the first schema must support at least the value `client`;
- this ADR does **not** freeze the broader role vocabulary beyond requiring that later values fit in
  the same `role` column;
- the first migration backfill from `matters.client_id` uses `role = 'client'`.

This bounded contract is safe because it decides only the minimum structure already required by
`ADR/0023` and `ADR/0033`: Matter <-> Party join, role lives on the join, and legacy Client becomes
that join role. It does not decide broader role taxonomy, minimum real-world Matter cardinality, or
resource-level workflow semantics.

## Reasoning

The decisive factor is that the governed specification and the accepted ADR chain already narrowed
the option space substantially. `ADR/0023` removed inheritance and JSON profile modeling. `ADR/0033`
removed a direct `matters.party_id` shortcut, fixed UUID-preserving Client backfill, and made direct
tenant ownership mandatory on affected tables. `ADR/0034` removed any option to treat Party rows
alone as execution proof.

That leaves a remaining design goal: the first schema must be concrete enough to implement without
inventing policy, while not overfreezing categories the repository has not governed yet.

Why the initial subtype vocabulary remains only `individual` and `organization`:

- the spec explicitly requires those two broad kinds now;
- it cites trusts, government bodies, and similar forms as examples of legal entities Party must be
  able to represent, not as first-wave discriminator values with separate required field sets;
- the first schema can hold those entities as `organization` without losing identity-bearing data,
  because registration and tax identifiers are modeled as fields rather than as subtype identity.

Why `display_name` is the canonical universal name field:

- the governed spec requires a reusable Party name across both individuals and legal entities;
- legacy Client already has one shared `full_name` field;
- no separately governed legal-name / display-name distinction exists yet, so one canonical name
  column is the narrowest faithful contract.

Why `pan_number` and `gstin` are universal while `aadhaar_number` and `incorporation_date` are
 subtype-sensitive:

- PAN is used by both individuals and legal entities in Indian practice, so making it
  organization-only or individual-only would overclaim;
- GSTIN is a registration/tax identifier whose applicability cuts across legal-form detail more than
  it maps cleanly to the two broad persistence subtypes;
- Aadhaar is inherently an individual identifier;
- incorporation date and a generalized registration identifier belong to legal entities, not natural
  persons.

Why no identifier uniqueness is imposed:

- the governed architecture already rejects natural-key Party identity;
- the repository has no governed duplicate-resolution policy for PAN, Aadhaar, GSTIN, phone, or
  email;
- adding uniqueness now would silently convert a search field into an identity rule.

Why all first bridge targets are classification **B**:

- every one of them is tenant-scoped business data after `ADR/0021` and `ADR/0033`;
- introducing `party_id` without `organization_id` would create a schema that still cannot enforce
  same-tenant relationships;
- the bridge phase is therefore allowed only together with the tenant-supporting columns and
  composite same-Organization FKs that make the bridge safe.

Why the minimum MatterParty contract is introduced rather than deferred:

- `ADR/0033` already fixed that `matters.client_id` retires to `matter_parties`, not `matters.party_id`;
- a future schema task must know whether it may create MatterParty now or whether a separate Matter
  ADR is still blocking it;
- the bounded contract above is enough to support the legacy migration role `client` without
  deciding the full MatterParty domain.

Why the execution ledger is a dedicated immutable table:

- `ADR/0034` already selected that architecture;
- T114's job is to freeze the physical schema so the later implementation does not invent it under
  migration pressure;
- append-only semantics are incompatible with the repository's ordinary mutable audit mixins.

## Trade-offs

- Broad `organization` as the only non-individual subtype means some legal-form distinctions are
  deferred rather than represented explicitly in the first schema.
- `display_name` as one canonical name column avoids an ungoverned name taxonomy now, but a later
  ADR may need to add more formal organization-name structure.
- Non-unique PAN/Aadhaar/GSTIN/email/phone favors safe migration over stronger duplicate prevention.
- Tenant-safe bridges require more schema changes up front because `party_id` cannot be introduced
  in a tenant-blind state.
- The bounded MatterParty contract intentionally leaves broader role vocabulary and cardinality open,
  so later Matter work still has architecture to do even though the migration foundation becomes
  implementable.
- The immutable execution ledger is more explicit operational surface than "infer from Party rows,"
  but that explicitness is the point of `ADR/0034`.

## Future Impact

### Required future implementation sequence

Recommended smallest safe implementation sequence after T114 closes:

1. tenant-supporting Address and downstream-table schema foundation:
   `addresses.organization_id`, `properties.organization_id`, `matters.organization_id`,
   `property_owners.organization_id`, `appointments.organization_id`, `invoices.organization_id`,
   `payments.organization_id`, retained `client_contacts.organization_id`, and required composite
   `(organization_id, id)` keys needed for tenant-safe references;
2. Party and bounded MatterParty plus immutable execution-ledger schema:
   `parties`, `matter_parties`, `client_party_migration_ledger`, and the composite same-Organization
   FK infrastructure they require;
3. direct `party_id` compatibility bridges on `property_owners`, `appointments`, `invoices`,
   `payments`, and retained `client_contacts`;
4. governed reconciliation/backfill executor implementation using T109/T110/T111 inputs and the
   T114/T114+ schema;
5. application cutover from Client-master semantics to Party/MatterParty semantics;
6. legacy `client_id` and `clients` retirement once all bridges and compatibility conditions are
   satisfied.

### Recommended first future implementation slice

The smallest next implementation slice after T114 is the tenant-supporting schema foundation in step
1 above. Party itself should not be created before Address and the direct tenant columns/key targets
needed by its same-Organization references exist.

### Remaining Required ADR #20 boundary

Required ADR #20 remains unresolved globally after this ADR. Still outside the resolved slice:

- broader Matter migration (`property_id`, `matter_type_id`, and other Matter seams);
- Document `matter_id` -> `file_id`;
- final cutover/removal choreography beyond the Party bridge boundary;
- non-Party entities and later modules;
- Representative normalization or ClientContact replacement;
- any Party API, CRUD, UI, or executor implementation.
