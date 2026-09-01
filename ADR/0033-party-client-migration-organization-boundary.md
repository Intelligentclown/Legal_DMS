# ADR-0033: Party/Client Migration and Organization-Boundary Reconciliation

**Status:** Proposed
**Date:** 2026-09-01

**Resolves:** the Party/Client migration architecture slice currently blocking Party implementation:
how the legacy `clients` model transitions to `parties`, how existing client-linked references are
migrated, and how Organization ownership is introduced and reconciled for that legacy client graph.

**Does not resolve:** the full planning-list item covering overall migration strategy. The governed
specification's still-open migration item also includes Matter's `property_id`/`matter_type_id`
retirement, Document's `matter_id`→`file_id` redirect, and other downstream sequencing not decided
here. This ADR intentionally resolves only the Party/Client slice so Party can be governed without
falsely claiming the entire migration item is closed. Also does not reopen `ADR/0021`, `ADR/0022`,
`ADR/0023`, `ADR/0024`, `ADR/0028`, `ADR/0030`, `ADR/0031`, or `ADR/0032`.

**Dependencies:** `ADR/0021` (tenant-isolation mechanism; all tenant-scoped Party-side tables must
carry directly-enforced `organization_id`), `ADR/0023` (Party is the reusable master record; Client
is a Matter relationship/status, not a master entity), `ADR/0024` (Property remains independent of
Matter; `PropertyOwner` is the existing ownership-history structure whose client reference remains to
be retargeted), `ADR/0028` (Finance keeps `Invoice`/`Payment` as real tables and had already flagged
their `client_id`→Party redirect as part of this migration seam), `ADR/0031` (User↔Organization
cardinality and live tenant resolution), and `ADR/0032` (interactive reconciliation precedent for
legacy rows that predate Organization ownership).

## 1. Problem Statement

`ADR/0023` already settled the conceptual model: **Party is the reusable master record; Client is a
Matter role carried by `MatterParty`, not a separate master entity or Party subtype.** What remains
unsettled, and what the repository's live schema still blocks, is the migration architecture from the
legacy Stage-2 `clients` implementation to that finalized model.

This is not a rename. Direct repository inspection on `298fb3e02862f9bd426681beb2ac58b69171a233`
confirms that:

- `clients` is a real legacy master table (`client.py`, migration `ac077004afeb`) with its own
  address link and subtype discriminator.
- `matters.client_id` is a mandatory one-client FK, directly contradicting the finalized
  many-party-per-Matter model.
- Other live tables still depend directly on `clients.id`: `property_owners.client_id`,
  `appointments.client_id`, `invoices.client_id`, and `payments.client_id`.
- None of those legacy client-linked tables carries `organization_id` today, even though
  `ADR/0021` makes Organization the mandatory tenancy boundary for tenant-scoped data.
- The repository's current Organization work (`ADR/0031`/`ADR/0032`/`T105`) only introduced
  `organizations` plus `users.organization_id`; it did not reconcile the legacy client graph.

Without a governed migration decision here, a future implementer would have to invent:

- whether `matters.client_id` becomes `party_id` or is replaced by `matter_parties`,
- whether the other direct client FKs remain, dual-write, or are removed,
- how existing `clients` rows obtain `organization_id`,
- and what must happen when that Organization assignment is ambiguous.

That would be exactly the kind of silent architectural invention this repository's governance process
exists to prevent.

## 2. Current State

### 2.1 Repository facts established by inspection

- `backend/src/app/infrastructure/persistence/models/client.py`
  - `Client`: `id`, `client_type`, `full_name`, `primary_phone`, `primary_email`,
    `pan_number`, `aadhaar_number`, `address_id`, `notes`.
  - `ClientContact`: `client_id`, `contact_name`, `relationship_type`, `phone`, `email`,
    `is_primary`.
- `backend/src/app/infrastructure/persistence/models/matter.py`
  - `Matter.client_id` is non-nullable and directly points to `clients.id`.
- `backend/src/app/infrastructure/persistence/models/property.py`
  - `PropertyOwner.client_id` is non-nullable and directly points to `clients.id`.
- `backend/src/app/infrastructure/persistence/models/scheduling.py`
  - `Appointment.client_id` is nullable and directly points to `clients.id`.
- `backend/src/app/infrastructure/persistence/models/financial.py`
  - `Invoice.client_id` is non-nullable and directly points to `clients.id`.
  - `Payment.client_id` is non-nullable and directly points to `clients.id`.
- `backend/src/app/infrastructure/persistence/models/document.py` and
  `backend/src/app/infrastructure/persistence/models/storage.py`
  - no direct `client_id`, but many tests/factories create `Matter` by first creating `Client`,
    so Party migration affects them transitively.

### 2.2 Relevant governed constraints already established

- **Already decided by existing ADR/spec:** `ADR/0023` and spec §4 rules 8–14
  - Party is the reusable master record.
  - Client is a Matter relationship/status, not a master entity.
  - A Matter may have multiple parties/clients.
  - `MatterParty` is the target relationship shape.
- **Already decided by existing ADR/spec:** `ADR/0021`
  - tenant-scoped tables require directly-carried `organization_id`;
  - enforcement is fail-closed and must not rely on inference-through-joins alone.
- **Already decided by existing ADR/spec:** `ADR/0031` and `ADR/0032`
  - Organizations now exist;
  - users resolve to at most one Organization;
  - legacy rows that predate Organization ownership may require explicit operator reconciliation.
- **Already decided by existing ADR/spec:** `ADR/0028`
  - `Invoice` and `Payment` remain real finance entities;
  - their `client_id`→Party redirect belongs to this migration seam, not to a finance redesign.
- **Architectural gap discovered by inspection:** the prompt's example references
  `financial.charges.client_id` and `financial.expenses.client_id`, but the current repository has no
  `charges` or `expenses` tables or models yet. The live financial client references today are
  `invoices.client_id` and `payments.client_id`.

### 2.3 Additional legacy dependencies that must be accounted for

Beyond the minimum list named in the task, repository inspection found these client-linked structures
that this migration slice must explicitly classify:

- `client_contacts.client_id`
- `property_owners.client_id`
- tests and factories in:
  - `backend/tests/integration/test_client_models.py`
  - `backend/tests/integration/test_matter_and_workflow_models.py`
  - `backend/tests/integration/test_property_models.py`
  - `backend/tests/integration/test_financial_models.py`
  - `backend/tests/integration/test_scheduling_models.py`
  - `backend/tests/integration/test_document_models.py`
  - `backend/tests/integration/test_ocr_qr_backup_models.py`
- `docs/ERD.md` and `docs/Database.md`, which still document the pre-Party schema.

### 2.4 Definitive legacy-client dependency inventory

The following is the complete canonical inventory from a repository-wide search of production
models, Alembic history, seeds, tests, and current governed schema/specification documents. It
intentionally excludes incidental uses of the word "client" meaning HTTP/API client and historical
review/log prose that does not define a live dependency.

| Current dependency | Target dependency | Migration treatment | `organization_id` treatment | Retirement point |
|---|---|---|---|---|
| `clients` master table / `Client` ORM | `parties` / `Party` ORM | One legacy Client row becomes exactly one Party row; see §5.1 and §5.3. | `parties.organization_id` is populated by §6 and `NOT NULL` on insert. `clients.organization_id` is bridge-only. | Drop `clients` only after every row and dependency below has cut over. |
| `client_contacts.client_id` / `ClientContact` ORM | Retained legacy contact record with `party_id`; no Representative target is decided. | Add/backfill `party_id`; retain all contact fields read-only through the explicit compatibility period in §5.4. | Add, backfill from resolved Party/client ownership, then `NOT NULL`; enforce directly. | Only after a separately governed contact/Representative decision has made its information accessible elsewhere and the compatibility period has ended. |
| `matters.client_id` / `Matter` ORM | `matter_parties.party_id` with role `client` | Retain the old FK only as a bridge; create one `matter_parties` row per legacy Matter; then drop `matters.client_id`. | `matters` and `matter_parties` both receive a directly carried, resolved, final `NOT NULL` Organization FK. | After parity validation and all Matter code/tests use `matter_parties`. |
| `property_owners.client_id` / `PropertyOwner` ORM | `property_owners.party_id` | Add nullable bridge, backfill, cut code over, require Party FK, drop `client_id`. | `properties` and `property_owners` each receive directly carried, resolved, final `NOT NULL` Organization FKs. | After Property ownership code/tests and schema documentation use `party_id`. |
| `appointments.client_id` / `Appointment` ORM | `appointments.party_id` | Add nullable bridge and backfill where present; cut code over; drop `client_id`. | `appointments.organization_id` is directly carried, resolved, and final `NOT NULL`; Party link remains nullable because it is nullable today. | After Scheduling code/tests use `party_id`. |
| `invoices.client_id` / `Invoice` ORM | `invoices.party_id` | Add nullable bridge, backfill, cut code over, require Party FK, drop `client_id`. | `invoices.organization_id` is directly carried, resolved, and final `NOT NULL`. | After Finance code/tests use `party_id`. |
| `payments.client_id` / `Payment` ORM | `payments.party_id` | Add nullable bridge, backfill, cut code over, require Party FK, drop `client_id`. | `payments.organization_id` is directly carried, resolved, and final `NOT NULL`. | After Finance code/tests use `party_id`. |
| Historic schema migrations `ac077004afeb`, `7789f56da7f9`, `c52ee7c83023`, `07150e442816`, `cf6b0519b74c` | New forward-only Party migration(s) | Do not rewrite applied Alembic history. New migrations add, backfill, validate, and retire. | New forward migrations add tenant columns and RLS/enforcement. | Historic migrations remain immutable history. |
| Seeded `clients:read`, `clients:write`, `clients:delete` permissions in `9963e15f2752` and `224b650e5235`, plus `test_t66_role_permissions.py`, `test_auth.py`, and `test_jwt_service.py` | Party resource permission codes under ADR/0022's resource/action convention | Add the governed Party codes and migrate equivalent role grants before Party routes are enabled; retain `clients:*` only during read-only compatibility; then remove them and update the affected authorization/JWT tests. | Permissions are global lookup/authorization data, not tenant-scoped tables; no `organization_id` is added. | When no route, service, UI, or role requires the legacy resource codes. |
| Production model registration `models/__init__.py` and model module imports | Party model registration | Register Party-side models and remove Client as a live master model at final retirement. | Party-side mapped tables must meet the direct-tenancy rule before registration is used in production. | With `clients` table/ORM removal. |
| Model tests and test helpers: `test_client_models.py`, `test_matter_and_workflow_models.py`, `test_property_models.py`, `test_financial_models.py`, `test_scheduling_models.py`, `test_document_models.py`, `test_ocr_qr_backup_models.py` | Party/MatterParty and retargeted-reference tests | Replace Client-master setup and assertions; retain a narrowly scoped migration-compatibility test only during the bridge. | Tests must create Organization-scoped fixtures and prove cross-Organization denial for every target tenant table. | With bridge-column and legacy-table removal, except retained migration-history coverage. |
| `docs/ERD.md`, `docs/Database.md`, governed specification current-state mappings | Party-era ERD/schema documentation | Update as part of cutover; preserve historical migration explanation in ADRs rather than leaving current-state docs stale. | Document direct `organization_id` and tenant enforcement for each target table. | Same implementation release as final schema cutover. |

There are no current Client repositories/services, `/clients` API routes, Client request/response
schemas, production factories, or client-record seed data. `financial.charges.client_id` and
`financial.expenses.client_id` do not exist in the inspected schema, model set, migrations, tests, or
ERD; they are therefore not migration sources. Future Charge/Expense work is constrained by §5.2 and
§12 not to create them.

## 3. Decision

The migration architecture is **staged, compatibility-first, and backfill-before-cutover**. It is
not one atomic table rename and not a "create parties later and hope the code catches up" approach.

### 3.1 `clients` transitions to `parties` by 1:1 legacy-record migration

Each existing `clients` row is migrated into exactly one `parties` row.

- **Architectural decision made here:** for backfilled rows, `parties.id` reuses the legacy
  `clients.id` value.
  - This keeps the migration deterministic.
  - It turns direct legacy FK redirects (`client_id`→`party_id`) into structural retargeting rather
    than value remapping.
  - It lets `matter_parties.party_id` backfill directly from `matters.client_id`.
  - Both current Client and governed Party primary keys are UUIDs. They are generated with `uuid4`,
    not a database sequence, so this decision has no sequence/identity-counter adjustment.
  - Identity preservation is safe only under the controlled cutover invariant in §5.3: before
    legacy backfill begins, `parties` must be empty and Party creation must be unavailable. A
    non-empty Party table, any UUID collision, or a Party row not already recorded as the same
    completed legacy mapping is a hard preflight failure, not a condition to resolve by overwriting
    or silently remapping IDs.
- **Architectural decision made here:** Party carries a mandatory `organization_id` from the moment
  the row is inserted; there is no permanent `NULL` Party ownership state.
- **Architectural decision made here:** the migration must preserve an auditable mapping artifact from
  legacy client to Party. Because IDs are reused, that artifact may be as simple as a dedicated
  migration ledger table or equivalent recorded reconciliation output, but some durable audit record
  must exist and must capture at least `legacy_client_id`, `party_id`, `organization_id`, migration
  timestamp, and whether operator input was required.

### 3.2 `matters.client_id` does not become `matters.party_id`

`matters.client_id` is **retired in favor of `matter_parties`**, not renamed to `party_id`.

- **Already decided by existing ADR/spec:** Client is a role on a Matter relationship, not a master
  entity field on Matter itself.
- **Architectural decision made here:** a new `matter_parties` table is the target relationship
  model, carrying at minimum `matter_id`, `party_id`, `organization_id`, and a role field whose
  backfilled value for legacy `matters.client_id` rows is `client`.
- **Architectural decision made here:** `matters.client_id` exists only as a temporary compatibility
  column during migration and must be removed after code cutover and backfill validation.
- **Rejected here:** introducing a new long-lived `matters.party_id` would recreate the same
  one-party Matter bottleneck `ADR/0023` already rejected.

### 3.3 The other direct legacy client references are retargeted to Party

These references preserve their existing row-level meaning and become direct Party references:

- `property_owners.client_id` → `property_owners.party_id`
- `appointments.client_id` → `appointments.party_id`
- `invoices.client_id` → `invoices.party_id`
- `payments.client_id` → `payments.party_id`

For these tables, the migration is a **compatibility bridge followed by cutover**:

- add nullable `party_id`,
- backfill from the legacy `client_id` using the 1:1 migrated Party row,
- update code to read/write `party_id`,
- then make `party_id` the authoritative FK and remove `client_id`.

### 3.4 `client_contacts` preserves contact information but is not auto-promoted to `representatives`

`client_contacts` is explicitly **not** mapped directly into a future `representatives` model by this
ADR.

- **Already decided by existing ADR/spec:** `ADR/0023` identified `ClientContact` only as a partial
  precedent and explicitly distinguished generic contacts from legally-authorized representatives.
- **Repository fact:** each row stores `contact_name`, free-text `relationship_type`, optional
  `phone`/`email`, and `is_primary`; it is information attached to the legacy Client, not merely an
  expendable join row.
- **Architectural decision made here:** preserve every `client_contacts` row by retaining the table
  as a deprecated, read-only compatibility record during an explicit compatibility period. Add and
  backfill `party_id`, preserve the existing contact fields unchanged, and remove `client_id` before
  `clients` is dropped. This keeps the information accessible without treating it as canonical new
  Party functionality.
- **Architectural decision made here:** the compatibility period ends only when a separately governed
  contact/Representative design has made the legacy contact information available or has explicitly
  authorized its retirement. It has no calendar duration because none is governed today.
- **Requires a separate ADR / later governed design:** full `Representative` semantics, authorization
  basis, and whether/how `client_contacts` data is normalized into that model.

### 3.5 Organization ownership is introduced by a deterministic reconciliation algorithm

The Organization backfill rule is:

- **Architectural decision made here:** every row in the migrated Party/client graph must receive an
  explicit `organization_id`.
- **Architectural decision made here:** automatic propagation is allowed only where the algorithm in
  §6 yields exactly one consistent Organization assignment for a row.
- **Architectural decision made here:** when a row's Organization cannot be assigned uniquely and
  deterministically, the migration must stop for that row-set and require explicit operator
  reconciliation. No heuristic or silent default is allowed.

This follows `ADR/0032`'s principle: when legacy data predates tenancy and the repository contains no
authoritative tenant marker, operator-confirmed reconciliation is required rather than invented logic.

## 4. Migration Strategy

The migration is **staged, compatibility-first, and backfill-first**. The conceptual sequence is:

1. **Precondition gate**
   - `organizations` and `users.organization_id` already exist.
   - Any pre-existing `users.organization_id IS NULL` rows have already been reconciled per
     `ADR/0032`.
   - Party implementation must not begin on a database where the user/Organization reconciliation is
     still incomplete.

2. **Introduce Party-side target structures**
   - create `parties` with mandatory `organization_id`;
   - create `matter_parties` with mandatory `organization_id`;
   - add nullable `party_id` bridge columns to `property_owners`, `appointments`, `invoices`,
     `payments`, and `client_contacts`;
    - add nullable `organization_id` columns to every legacy tenant-scoped table in this slice that
      lacks one today: at minimum `clients`, `client_contacts`, `matters`, `property_owners`,
      `appointments`, `invoices`, `payments`, and any new Party-side tables created in this phase;
   - `properties` also requires `organization_id` before any Party-linked ownership row can become
     tenant-safe, because `property_owners` cannot be the only tenant-carrying property-side table.

3. **Reconcile Organization ownership for legacy data**
   - establish the Organization assignment for each legacy client anchor;
   - propagate that assignment to the directly dependent rows in this slice;
   - fail closed on any conflict or ambiguity.

4. **Backfill Parties and Party references**
   - insert one `parties` row per `clients` row, reusing `clients.id`;
   - backfill `matter_parties` from `matters.client_id` with role `client`;
    - backfill each new `party_id` bridge column from the matching `client_id`;
    - validate row counts, mappings, matching Organization ownership, and all required final-state
      `party_id` values before any application cutover.

5. **Cut over application code**
   - Matter logic reads/writes `matter_parties`, not `matters.client_id`;
   - Property ownership logic reads/writes `property_owners.party_id`;
   - Finance logic reads/writes `invoices.party_id` and `payments.party_id`;
   - Scheduling logic reads/writes `appointments.party_id`;
   - no code path may dual-write indefinitely.

6. **Tighten constraints after verified backfill**
   - convert authoritative Party-side FKs to `NOT NULL` where the legacy column was already required;
    - make every target tenant-scoped `organization_id` `NOT NULL`, add its FK to `organizations`,
      and add/enable `ADR/0021` application scoping plus forced default-deny RLS policies;
   - remove legacy `client_id` columns once code cutover is complete and validated.

7. **Retire legacy tables**
   - `clients` becomes deprecated/read-only during the bridge period;
   - `clients` is removed only after all canonical references have cut over and any retained
     `client_contacts` dependency has been detached from `clients`.

## 5. Data Mapping

### 5.1 `clients` → `parties`

The existing `Client` fields map as follows. `ADR/0023` fixed the Party storage mechanism but did
not fix the exact Party field vocabulary beyond universal fields and a discriminator, so the mapping
does not silently invent fields or subtype meanings.

| Legacy Client field | Party treatment | Governing status |
|---|---|---|
| `id` | Copy unchanged: `parties.id = clients.id`, subject to §5.3 preflight and rollback rules. | Architectural decision in this ADR; both types are UUID. |
| `client_type` | Copy to Party's discriminator for the currently valid values `individual` and `organization`. | Existing Client constraint plus ADR/0023's discriminator decision. The future subtype vocabulary is not expanded here. |
| `full_name` | Copy unchanged to Party's universal display/name field. | ADR/0023 universal identity field. |
| `primary_phone` | Copy unchanged to Party's universal primary-phone field; retain current format/length validation unless a later Party-field ADR changes it. | Existing Client constraint and ADR/0023 universal field. |
| `primary_email` | Copy unchanged to Party's universal primary-email field, including `NULL`. | ADR/0023 universal field. |
| `pan_number` | Copy unchanged into Party only if the accepted Party schema includes a corresponding Party attribute; preserve existing format validation. It must not be discarded. | ADR/0023 names PAN as a searchable, format-validated Party attribute but leaves exact subtype field lists open. The applicable subtype semantic is not governed here. |
| `aadhaar_number` | Copy unchanged into Party only if the accepted Party schema includes a corresponding Party attribute; preserve existing format validation. It must not be discarded. | ADR/0023 names Aadhaar as a searchable, format-validated Party attribute but leaves exact subtype field lists open. The applicable subtype semantic is not governed here. |
| `address_id` | Copy unchanged to Party's universal nullable address FK; do not clone or reassign `Address`. | ADR/0023 expressly reuses Address unchanged. |
| `notes` | Copy unchanged to Party's universal nullable notes field. | ADR/0023 universal field. |

`organization_id` is new, not a legacy Client field, and is assigned only through §6. Audit columns
and Client's optimistic-lock version are historical metadata, not Party identity fields: preserve
them in the migration audit ledger as source evidence; apply the standard Party audit columns to the
inserted Party row. Whether an exact legacy `version` value must be copied is not governed and is not
required for this identity migration.

### 5.2 Reference-by-reference migration

- **`matters.client_id`**
  - target: `matter_parties`
  - bridge: keep `matters.client_id` temporarily
  - backfill: create one `matter_parties` row per Matter with `party_id = matters.client_id`,
    `role = 'client'`, and matching `organization_id`
  - final state: drop `matters.client_id`; Matter no longer carries any direct client/party FK

- **`property_owners.client_id`**
  - target: `property_owners.party_id`
  - bridge: add nullable `party_id`
  - backfill: `party_id = client_id`
  - final state: `party_id NOT NULL`, FK retargeted to `parties.id`, `client_id` removed

- **`appointments.client_id`**
  - target: `appointments.party_id`
  - bridge: add nullable `party_id`
  - backfill: `party_id = client_id` where a client exists
  - final state: `party_id` remains nullable unless later Scheduling requirements prove every
    appointment must reference a Party; this ADR does not invent that stronger rule

- **`invoices.client_id`**
  - target: `invoices.party_id`
  - bridge: add nullable `party_id`
  - backfill: `party_id = client_id`
  - final state: `party_id NOT NULL`, `client_id` removed

- **`payments.client_id`**
  - target: `payments.party_id`
  - bridge: add nullable `party_id`
  - backfill: `party_id = client_id`
  - final state: `party_id NOT NULL`, `client_id` removed

- **`client_contacts.client_id`**
  - target: retained, read-only legacy contact compatibility via `client_contacts.party_id`
  - bridge: add nullable `party_id`
  - backfill: `party_id = client_id`
  - final state: `party_id NOT NULL`, direct Organization ownership, `client_id` removed; all existing
    contact data remains accessible for the explicit compatibility period in §3.4

### 5.2.1 Additional tables affected transitively

- `documents` still reference `matters`, so Matter factories/tests must migrate to create
  `matter_parties` rather than `Client`-anchored Matters.
- any future `charges`/`expenses` implementation must never introduce new `client_id` columns; they
  inherit Party and Organization directly if/when those tables are implemented.

### 5.3 Identity-preservation and staged-migration safety

`Client.id` is `UUID` with a Python `uuid4` default. `ADR/0023` specifies the Party PK as UUID with
the same repository convention. There is no numeric sequence to advance or reconcile.

The controlled sequence makes identity preservation safe:

1. The schema deployment creates `parties` but does not expose Party creation or writes.
2. A preflight locks the migration scope and requires `parties` to be empty. If a prior interrupted
   run left Party rows, the durable migration ledger must prove each is the same completed Client
   mapping with the same `party_id`, `organization_id`, and source-row fingerprint; otherwise abort.
3. The backfill inserts the Party row and its ledger row atomically per committed migration unit.
   A retry may skip only a ledger-proven identical mapping; it may never generate a replacement UUID.
4. New Party creation is enabled only after every legacy Client has a Party and every required bridge
   is populated. Therefore new Party records cannot coexist with unmigrated Client records.

Rollback before a committed backfill unit leaves no Party or ledger row for that unit. An interrupted
run after a committed unit is resumable only through the ledger validation above. The migration must
not delete a Party to force a retry, and it must not overwrite a pre-existing Party UUID collision.

### 5.4 `client_contacts` compatibility boundary

`client_contacts` is neither empty legacy clutter nor a governed Representative model. It holds
ordinary contact facts and an unconstrained relationship label; `is_primary` only identifies a primary
contact in that legacy collection. No authorization basis, authority scope, Party-to-person identity,
or multi-Party relationship rule exists in the current schema or accepted ADRs.

The migration therefore preserves its rows, fields, audit history, and accessibility through a
read-only `party_id`-based compatibility table. It does not write new contact records there after
Party cutover, does not label the rows Representatives, and does not remove them merely because
`clients` is retired. A later Representative/relationship ADR is required before normalizing,
replacing, or deleting this information.

## 6. Organization Backfill Strategy

### 6.1 What is already decided

- **Already decided by existing ADR/spec:** Organization is the tenant boundary (`ADR/0021`).
- **Already decided by existing ADR/spec:** a User belongs to at most one Organization
  (`ADR/0031`).
- **Already decided by existing ADR/spec:** legacy pre-tenant data may require explicit operator
  reconciliation rather than silent inference (`ADR/0032`).

### 6.2 Deterministic reconciliation algorithm

The reconciliation anchor is each legacy `clients.id`; every dependent record receives the anchor's
Organization unless it has an independently resolved Organization that must agree.

1. Build an evidence set for each Client from only these authoritative sources:
   - a non-null `created_by` or `updated_by` whose `users.organization_id` is already non-null and
     reconciled under ADR/0032;
   - a directly linked record in this migration slice whose `organization_id` was already resolved
     by this same algorithm and whose FK path is explicit: Matter, PropertyOwner/Property,
     Appointment, Invoice, Payment, or ClientContact;
   - an explicit, previously committed reconciliation-ledger assignment for the exact Client ID,
     source-row fingerprint, and migration version.
2. Discard null and un-reconciled user evidence. Collect distinct candidate Organization UUIDs from
   the remaining evidence; record each source row and path.
3. Exactly one candidate UUID is **deterministic**. Assign it to the Client/Party and propagate it to
   dependent rows that have no independently resolved value. If a dependent has an existing resolved
   value, it must equal the anchor's UUID.
4. Zero candidates is **unmappable**: current repository data provides no authoritative Organization
   fact for the Client. Two or more distinct candidates, or any anchor/dependent disagreement, is
   **ambiguous**. Creation time, record order, names, contact details, geography, inferred practice,
   and a database-wide single-Organization assumption are not evidence.
5. Every unmappable or ambiguous Client forms an unresolved reconciliation set with all directly
   dependent rows. No Party row, Party FK, final `organization_id`, or RLS-protected cutover is
   performed for that set until an explicit mapping exists.

### 6.3 Explicit operator reconciliation and unresolved records

Unresolved sets require an explicit operator-supplied mapping of `legacy_client_id` to an existing or
operator-created Organization. The architecture deliberately does not name a business approver; no
accepted governance document establishes one. The deployer must use the project’s governed
reconciliation mechanism, not an Alembic prompt or an application heuristic.

Each reconciliation decision must retain a durable audit record containing at least: migration run and
version; legacy Client ID; source-row fingerprint/version; selected Organization ID; all discovered
candidate IDs and evidence paths; classification (`deterministic`, `ambiguous`, `unmappable`, or
`operator-reconciled`); timestamp; and the operator identity/process reference available at runtime.

Unresolved records block cutover for the entire Party/client graph. Allowing a partial tenant cutover
would leave either tenant-scoped rows without direct ownership or a legacy master still writable,
which violates ADR/0021 and this ADR's single-master rule. The bridge schema may exist while
reconciliation is pending, but Party writes and removal of any legacy `client_id`/`clients` dependency
may not proceed.

### 6.4 Final tenant-boundary state

| Table | Required final `organization_id` | Population | Final enforcement |
|---|---|---|---|
| `parties` | Yes, `NOT NULL` | Client-anchor reconciliation. | FK to `organizations`; ADR/0021 scoped repository/service access and forced default-deny RLS. |
| `matter_parties` | Yes, `NOT NULL` | Resolved Matter/Party ownership, which must agree. | Same direct FK, scope, and RLS; no inference solely through joins. |
| `matters` | Yes, `NOT NULL` | Resolved legacy Matter/client graph. | Same direct FK, scope, and RLS. |
| `properties` | Yes, `NOT NULL` | Resolved property ownership graph; conflicts block reconciliation. | Same direct FK, scope, and RLS. |
| `property_owners` | Yes, `NOT NULL` | Matching resolved Property and Party ownership. | Same direct FK, scope, and RLS. |
| `appointments` | Yes, `NOT NULL` | Resolved legacy appointment graph; nullable Party does not make tenant ownership nullable. | Same direct FK, scope, and RLS. |
| `invoices` | Yes, `NOT NULL` | Matching resolved Matter and Party ownership. | Same direct FK, scope, and RLS. |
| `payments` | Yes, `NOT NULL` | Matching resolved Matter, Invoice where present, and Party ownership. | Same direct FK, scope, and RLS. |
| `client_contacts` during compatibility | Yes, `NOT NULL` | Resolved legacy Client/Party anchor. | Same direct FK, scope, and RLS while retained. |

`clients.organization_id` exists only during the bridge to make legacy reads fail closed; it too is
backfilled and made `NOT NULL` before any compatibility read is allowed. This directly preserves
ADR/0021's rule that tenant scope is carried and enforced on the table being accessed, not inferred
from a join.

## 7. Compatibility Strategy

### 7.1 During transition

- `clients` is retained as a **deprecated, read-only compatibility table**.
- direct-reference tables gain `party_id` bridge columns before `client_id` is removed.
- `matters.client_id` is retained only long enough to backfill and cut over to `matter_parties`.
- Party creation and Party writes remain disabled until all Client rows, required Party FKs, and
  Organization assignments have passed §5.3 and §6 validation; compatibility is read-only, not a
  two-master dual-write period.
- no new feature work may deepen dependency on `clients` once the bridge phase starts.

### 7.2 After cutover

- canonical reads/writes use `parties`, `matter_parties`, and the retargeted `party_id` FKs only;
- `clients` is removed after all canonical dependencies are gone;
- `client_contacts` remains as a Party-linked, read-only compatibility table until its separate
  governed retirement condition is met; it no longer depends on `clients`.
- legacy `clients:*` permission codes are removed only after Party permission grants and all canonical
  access checks have cut over.

### 7.3 What is explicitly not allowed

- no permanent dual-write regime;
- no permanent compatibility alias where `clients` and `parties` both act as live master records;
- no long-lived `matters.party_id` shortcut that bypasses `matter_parties`.

## 8. Constraints for Implementation

A future Backend Developer may not be authorized to implement Party until all of these constraints are
accepted and then followed:

- `parties.organization_id` must be mandatory, directly carried, and tenant-enforced per `ADR/0021`.
- `matter_parties.organization_id` must also be directly carried; tenant scope may not be inferred
  only by joining through `matters` or `parties`.
- `matters`, `properties`, `property_owners`, `appointments`, `invoices`, `payments`, and retained
  `client_contacts` must each end with their own `organization_id NOT NULL`, Organization FK, scoped
  data access, and forced default-deny RLS policy. Every linked row's Organization must match; a
  mismatched relationship is rejected rather than repaired by inference.
- `matters.client_id` must be migrated to `matter_parties`, not renamed to `party_id`.
- `property_owners`, `invoices`, and `payments` must end in a `party_id NOT NULL` state because the
  legacy schema already required a client there.
- `appointments.party_id` may remain nullable unless Scheduling is separately re-governed.
- no ambiguous Organization assignment may be auto-resolved by heuristic.
- migration runs must be auditable and fail closed.
- backfill identity reuse requires the §5.3 preflight/ledger invariant; no Party row may be created
  alongside unmigrated Client rows, and a collision or unproven prior Party row aborts the run.
- `client_contacts` contact facts must remain available read-only until a separate governing decision
  permits their replacement or retirement.
- existing `clients:*` role grants must be migrated to Party resource permissions before Party access
  is enabled; a future Charge or Expense must reference Party, never Client.
- code, tests, fixtures, ERD/schema docs, and tenant-enforcement migrations must be updated in the
  same governed implementation slice; Party is not implementation-complete while any canonical
  codepath still depends on `Client` as a live master entity.

## 9. Alternatives Considered

1. **Rename `clients` to `parties` and rename every `client_id` to `party_id`.**
   Rejected. It directly contradicts `ADR/0023` for Matter, leaves Client-as-Matter-role unresolved,
   and hides the Organization backfill problem.

2. **Keep `clients` as the master table and add `parties` later only for new features.**
   Rejected. This creates permanent compatibility debt and leaves two competing master-record models.

3. **Replace every client reference with `party_id`, including `matters.party_id`.**
   Rejected. It preserves the one-party Matter bottleneck the governed model explicitly rejected.

4. **One-shot atomic migration removing `clients` immediately.**
   Rejected. Too risky for a legacy graph with multiple dependent tables and no existing tenant
   ownership; it offers no safe verification window.

5. **Infer all legacy rows into one Organization automatically.**
   Rejected. `ADR/0032` already established that pre-tenant data cannot be silently grouped when the
   data model lacks authoritative tenant markers.

6. **Staged, compatibility-first migration with explicit ambiguity stop points.**
   Selected. It is the narrowest approach that satisfies `ADR/0021`, `ADR/0023`, and the repository's
   actual dependency graph simultaneously.

## 10. Risks

- **Migration-integrity risk:** if `party_id` and `client_id` diverge during the bridge phase, data
  can split. Mitigation: bridge period must be short and canonical write target must be explicit.
- **Tenancy risk:** incorrect Organization reconciliation would create cross-tenant leaks. Mitigation:
  fail closed on ambiguity; require explicit operator reconciliation.
- **Compatibility risk:** lingering code or tests may keep creating `Client` rows as masters after
  Party cutover. Mitigation: Party implementation is not complete until those call sites are removed.
- **Operational risk:** a partially applied migration could strand rows between old and new models.
  Mitigation: Party writes are disabled until complete backfill; stage boundaries are transactional
  within each migration step and ledger-verified across the full run.
- **Documentation drift risk:** current ERD/schema docs still describe the client-based model.
  Mitigation: governed implementation must update them alongside code/schema cutover.
- **Representative/contact risk:** `client_contacts` semantics are not the same as a governed
  Representative model. Mitigation: keep the table deprecated/read-only until that later design exists.

## 11. Open Owner Decisions

No Project Owner policy decision is required to govern this migration architecture. The real-world
Organization mapping for an ambiguous or unmappable deployment is migration input, not a policy the
architecture can infer; §6 requires it to be explicitly supplied and audited without naming an
unestablished business approver.

## 12. Downstream Impact

### Property

- `property_owners` is retained as the ownership-history structure.
- Its foreign key retargets from Client to Party.
- `properties.organization_id` must exist before Property ownership can be tenant-safe under
  `ADR/0021`.
- This ADR does not redesign Property↔Party ownership semantics beyond that retargeting.

### Matter

- Matter is the primary blocker this ADR removes.
- `matters.client_id` is temporary only; the canonical model is `matter_parties`.
- Party implementation cannot be considered complete until Matter is cut over to `matter_parties`.

### File and Document

- no direct client FK exists there today, but their factories/tests depend on Matter creation.
- they inherit the Matter-side migration and must stop assuming a `Client` master row is required to
  create a Matter.
- this ADR does not decide the later `documents.matter_id`→`file_id` migration, which remains a
  separate migration slice.

### Financial

- the live client-linked finance rows are `invoices` and `payments`, not `charges`/`expenses`.
- both retarget directly to `party_id`.
- future Finance implementation must treat Party as the counterparty model from the start; it must not
  introduce new `client_id` debt.

### Scheduling

- `appointments.client_id` becomes `appointments.party_id`.
- nullability stays as permissive as the current schema unless Scheduling is later tightened by a
  separate governed decision.

### Future modules

- Enquiry and Quotation should be Party-native from their first implementation; they must not be built
  on top of the deprecated `clients` table.
- Any future module attaching to an external person/legal-entity counterparty must reference Party and
  carry `organization_id` directly.

- Future Charge and Expense tables are not present today; when separately authorized, they must be
  Party-native and Organization-scoped from their first migration. They are not a reason to retain
  `clients` or to add speculative bridge columns now.

## 13. Future Impact

- This ADR gives the future Party implementation a fixed migration target and sequencing model; the
  implementer no longer needs to invent how `clients` exits.
- The overall migration-strategy planning item remains open for the non-Party slices
  (`matter_type_id`, `property_id`, `documents.matter_id`, and other later redirects).
- A future Representative ADR must decide the canonical replacement, if any, for `client_contacts`.
