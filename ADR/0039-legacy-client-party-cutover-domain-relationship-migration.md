# ADR-0039: Legacy Client-to-Party Cutover and Domain-Relationship Migration Architecture

**Status:** Proposed  
**Date:** 2026-09-22

**Related task:** T131 — Legacy Client-to-Party Cutover and Domain-Relationship Migration Architecture.

**Advances but does not resolve:** Required ADR #20, “Migration strategy from the current schema.” T131 closes the remaining Client-as-master cutover decision, but Required ADR #20 also governs migration seams outside T131 authorization, including Matter `property_id` / `matter_type_id` transition and Document/File migration. Those remain unresolved.

**Does not resolve:** Required ADRs #10, #11, #12, #15, #16, #17, or any other Required ADR.

**Composes with:** ADR-0021, ADR-0022, ADR-0023, ADR-0024, ADR-0028, ADR-0030, ADR-0033, ADR-0034, ADR-0035, ADR-0036, ADR-0037.

## Problem

The governed target model is already fixed: Party is the reusable person/legal-entity master; “Client” is a role a Party holds in a Matter through MatterParty. The current schema still contains a real legacy `clients` master and direct Client foreign keys. T108–T118 built a governed migration path and T124–T127 made ordinary Party writes safe for proven operational-fresh installations, but normal downstream domain work still faces a split model.

Fresh inspection at T131 authorization baseline `0933dc765693a62499be78d68256e8ea70988f71` confirms these material dependencies:

- `matters.client_id` is mandatory.
- `property_owners.client_id` is mandatory and `party_id` is a nullable compatibility bridge.
- `client_contacts.client_id` is mandatory and `party_id` is a nullable compatibility bridge.
- `appointments.client_id` is nullable and `party_id` is a nullable compatibility bridge.
- `invoices.client_id` and `payments.client_id` are mandatory and both have nullable `party_id` bridges.
- `client_party_migration_ledger.legacy_client_id` deliberately retains a Client FK as immutable migration evidence.
- the T118 executor already creates identity-preserving Party rows, bounded MatterParty rows with `role='client'`, direct Party bridge values, Organization staging, and immutable ledger completion.
- PartyWriteGate permits ordinary Party writes only for OPERATIONAL_FRESH; MIGRATED remains denied.
- Matter, Property, PropertyOwner, Appointment, Invoice, Payment, ClientContact and Client retain nullable transitional `organization_id` in current ORM shapes, while Party and Address have finalized mandatory tenant ownership.

Without a cutover contract, fresh installations would eventually have to manufacture legacy Client rows to create Matter/ownership records, or implementers would invent dual-write behavior. Conversely, deleting Client columns immediately would destroy the migration evidence and compatibility path already governed by ADR-0033–0035.

## Options Considered

### 1. Immediate destructive cutover

Drop Client dependencies, make Party/MatterParty canonical everywhere, and migrate all rows in one release.

Rejected. It collapses reconciliation, backfill, tenant finalization, application cutover, RLS and retirement into one irreversible event; it also removes evidence needed by the current migration ledger before all consumers have crossed the seam.

### 2. Indefinite dual-master / dual-write

Keep Client and Party as co-equal writable masters and mirror every write.

Rejected. It contradicts ADR-0023, creates two identity authorities, makes divergence a normal state, and forces clean installations to continue creating legacy identity.

### 3. Staged canonical switch with compatibility shadows

Selected. Party is canonical identity for new domain composition. Legacy Client remains source/evidence only where required during migration. Target relationships become canonical one bounded aggregate at a time. Old Client columns may temporarily coexist as compatibility shadows, but they are never co-equal authorities and are not dual-written from new-business operations.

## Decision

### 1. Canonical identity by installation state

**OPERATIONAL_FRESH:** Party is immediately the only reusable person/legal-entity master for new business. New domain workflows MUST NOT create a Client row merely to satisfy transitional schema. A future Matter surface must therefore wait until schema/application work permits Party + MatterParty creation without mandatory `Matter.client_id`. New Property ownership likewise uses Party once its target schema is enabled. Physically retained Client columns are compatibility-only and may be null/unused only after separately authorized schema changes make that possible.

**LEGACY_WITH_BUSINESS_DATA / UNPROVEN:** no new Party-based domain write surface is enabled by this ADR. Existing legacy data remains readable only through already-governed paths; migration/reconciliation uses T108–T118. Ambiguous, stale, contradictory or unsupported evidence fails closed.

**MIGRATED:** the classification proves all legacy Client anchors are covered by governed migration ledger evidence; it does not by itself prove every downstream application has cut over, nor does it automatically enable ordinary Party writes. Target-domain write eligibility requires the later cutover implementation plus explicit PartyWriteGate evolution where separately authorized.

### 2. Client-to-Party mapping

For governed legacy migration the canonical mapping remains exactly one legacy Client anchor to exactly one Party, preserving UUID identity (`party_id = legacy_client_id`) and one resolved Organization. Deterministic and operator-reconciled mappings are the only executable resolution modes.

The immutable ledger is authoritative execution evidence for completion of that anchor under its recorded basis. A Party row without matching ledger completion is not proof of migration. Duplicate/conflicting ledger bases, Party-without-ledger, Organization disagreement, stale source fingerprint, or cross-Organization mapping fail closed.

The Client row is not deleted by migration. It becomes a compatibility/source shadow after successful migration and remains until all direct consumers and evidence requirements have retired. The ledger may outlive application Client semantics; if the Client table is eventually removed, preservation/retargeting of immutable migration evidence must be explicitly implemented before the FK can disappear.

### 3. Compatibility-window invariant

There is one canonical write representation per concept.

- Identity: Party is canonical after an anchor is migrated; Client is frozen compatibility/source data.
- Matter client participation: MatterParty(`role='client'`) becomes canonical when the Matter cutover slice lands.
- Property ownership: `PropertyOwner.party_id` becomes canonical when its cutover slice lands.
- Appointment/Invoice/Payment direct party bridges become canonical only in their separately authorized domain cutovers.
- ClientContact is legacy/transitional information; `party_id` identifies the migrated Party, but this ADR does not redesign contacts/Representatives.

No normal application dual-write from Party back into Client is permitted. Legacy columns may be retained for reads, verification and rollback before their retirement gate. If canonical and compatibility representations disagree, writes fail closed and remediation must use a governed migration/reconciliation path rather than heuristic repair.

### 4. Matter transition

Target new-business shape is Matter + one-or-more MatterParty rows; Client is a role value, not a Matter master FK.

A later Matter foundation must:
1. finalize direct Organization ownership and same-Organization constraints/RLS before normal writes;
2. make `matters.client_id` non-required for operational-fresh creation;
3. make MatterParty the canonical client-participation relationship;
4. preserve legacy `client_id` only as a read/verification shadow during compatibility;
5. for migrated legacy Matters, require the ledger-backed Client→Party mapping and the corresponding same-Organization MatterParty(`role='client'`) backfill;
6. allow multiple client-role Parties and other later role values; never impose unique `(matter_id, role)`;
7. eventually remove `matters.client_id` only after all reads/writes/tests no longer depend on it and migration evidence proves all legacy Matters have canonical MatterParty representation.

This ADR does not decide MatterProperty, MatterClassification or MatterWorkType field-level implementation, and does not resolve retirement of `matter_type_id` or `property_id`.

### 5. PropertyOwner transition

Property remains independent of Matter. Ownership target is Party.

A later ownership foundation must finalize `properties.organization_id` and `property_owners.organization_id`, same-Organization constraints and RLS before normal writes. Operational-fresh ownership must use `PropertyOwner.party_id` without creating Client. Legacy owners are backfilled only from a valid ledger-backed Client→Party mapping. Multiple owners remain supported.

During compatibility, `client_id` is a frozen legacy shadow; `party_id` is canonical after the ownership cutover. Disagreement fails closed. `client_id` retires only after every retained owner has a valid Party representation and all application consumers use it.

Gujarat Revenue/City Survey/TP-FP modeling is outside this ADR.

### 6. ClientContact and other Client dependencies

`ClientContact` remains a transitional legacy contact record. Its `party_id` bridge identifies the migrated Party, but retirement requires a later contact/Representative decision so contact information is not silently lost. No new ClientContact-based domain design is authorized.

Appointments, Invoices and Payments are also real Client dependencies discovered by repository inspection. Their existing nullable `party_id` bridges are migration compatibility infrastructure. T131 does not redesign Scheduling or Finance; each later domain cutover must switch canonical reads/writes to Party while preserving its own governed invariants. Mandatory legacy `client_id` columns cannot retire before that domain cutover.

### 7. PartyWriteGate

PartyWriteGate currently consumes InstallationClassifier and allows ordinary Party writes only for OPERATIONAL_FRESH. That remains unchanged.

A later migrated-write-enablement task may permit MIGRATED only when it can prove both:
- governed Client→Party migration completion under the immutable ledger/classifier contract; and
- the required compatibility/cutover invariants for the application surface being written.

MIGRATED alone is not sufficient. Classification/read failure remains fail closed. PartyWriteGate is not generalized to Address, Matter, Property or other domains.

### 8. Tenant/RLS sequencing

Every target tenant-scoped aggregate must reach this sequence before normal writes:
1. direct Organization value reconciled/backfilled where legacy data exists;
2. `organization_id NOT NULL`;
3. Organization FK and `(organization_id,id)` support key where composite references require it;
4. same-Organization composite FKs;
5. application-level Organization scoping and permissions;
6. forced default-deny RLS using the existing Organization GUC pattern;
7. non-owning, non-superuser, NOBYPASSRLS runtime role verified.

Migration/executor writes remain an explicit owning/admin path and do not weaken runtime RLS. Cross-Organization mappings are invalid, never repaired by copying/inference.

### 9. Provenance and schema-revision evolution

ADR-0037 provenance remains sufficient. Later Alembic revisions that preserve operational-fresh semantics must explicitly advance the supported schema revision using the T130 precedent: recreate/advance the guarded provenance functions and update runtime classifier support in the same governed migration slice.

A schema upgrade does not create migration completion evidence. Client migration state continues to derive from legacy rows plus immutable ledger coverage; operational-fresh derives from provenance. Contradictory operational-fresh and migration evidence remains an error.

### 10. Rollback and irreversibility

Before a legacy column/table is retired, additive tenant finalization, bridge population and canonical-read switching may be rolled back only if rollback can restore the prior executable schema without discarding authoritative migration evidence. The immutable migration ledger is never rolled back as an ordinary business edit.

The irreversible boundary is the first destructive retirement that removes a legacy source/compatibility column or table after all retirement gates pass. After that point, rollback is forward-repair or restore-from-backup/migration procedure; a downgrade must not fabricate Client identity from Party data.

Each destructive retirement is a separately authorized implementation slice with explicit backup/recovery and QA evidence.

### 11. Required ADR #20 boundary

T131 does **not** fully resolve Required ADR #20.

It settles the remaining Client→Party identity and direct Client-dependency cutover strategy, including Matter client participation and PropertyOwner ownership. However the canonical specification and ADR-0033 explicitly leave additional current-schema migration seams under #20, including Matter `property_id`/`matter_type_id` transition, Document `matter_id`→File migration, and other downstream backfill sequencing. Resolving those here would cross T131's explicit exclusions and, for Document/File, collide with unresolved Required ADR #10.

Therefore this ADR intentionally has no `Resolves: Required ADR #20` claim. Governance must keep #20 unresolved after T131.

## Scenario Proofs

1. Empty operational-fresh: create Party/Address normally; no Client manufactured. Matter/ownership wait for their target cutover surface.
2. Operational-fresh Party/Address growth: provenance remains OPERATIONAL_FRESH; Client count remains zero.
3. Future fresh Matter: Party + MatterParty is canonical; no mandatory Client once later schema slice lands.
4. Future fresh ownership: PropertyOwner points to Party after later tenant/cutover slice.
5. Existing Client: remains legacy source until reconciled/executed.
6. Deterministic migration: one UUID-preserving Party + bridges + ledger atomically.
7. Operator reconciliation: same result, selected Organization recorded by governed artifact/ledger.
8. Partial migration: not MIGRATED; ordinary migrated Party writes remain denied.
9. Stale artifact: executor/preflight rejects; no canonical cutover inference.
10. Legacy Matter: retains client_id until ledger-backed MatterParty exists and cutover gate passes.
11. Legacy PropertyOwner: retains client_id until ledger-backed party_id exists and ownership cutover passes.
12. Multiple Matter Parties: allowed; no unique role-per-Matter rule.
13. Same Party, different Matter roles: allowed because role lives on MatterParty.
14. Cross-Organization mapping: rejected by reconciliation/executor and later composite FKs/RLS.
15. Compatibility reads: canonical target preferred after surface cutover; legacy shadow may support verification only.
16. Compatibility writes: single-write to canonical target; no Party→Client dual-write.
17. Retirement: only after zero live consumers, complete canonical representation and explicit destructive migration authorization.
18. Rerun: identical ledger basis is no-op; changed basis/fingerprint fails closed.
19. Unsupported/contradictory evidence: no migration/canonical-write promotion.
20. Schema head beyond 5d8a3f2e9c6b: supported revision advanced explicitly in the same later migration.
21. Rollback before retirement: may revert additive/canonical-read steps if authoritative ledger evidence is preserved.
22. After destructive retirement: no automatic downgrade reconstruction; forward repair/restore procedure required.
23. Clean install with zero Clients: remains valid; legacy identity is not synthesized.
24. Development/test Client data: processed as legacy rows if retained, but its existence is not evidence of production-customer migration requirements.

## Successor Decomposition

No task numbers or authorization are created here.

1. **Matter/Property tenant-and-canonical-relationship schema foundation.** Finalize direct Organization ownership/RLS prerequisites and make operational-fresh target relationships representable without Client. High-risk cross-layer migration/security work: Codex-level implementation; independent QA focuses on migration upgrade/downgrade, RLS, same-tenant FKs, provenance revision advancement and zero fake Client creation.
2. **Canonical MatterParty / PropertyOwner application cutover.** Switch target reads/writes to Party relationships while legacy shadows remain. Medium/high risk; OpenCode first only if the prior schema slice leaves a tightly specified surface, otherwise Codex. QA focuses on compatibility discrepancies and tenant isolation.
3. **Migrated Party-write eligibility.** Evolve PartyWriteGate only with explicit evidence contract. High-risk security/migration work: Codex; QA focuses on fail-closed classification and concurrency.
4. **Scheduling/Finance/ClientContact consumer cutovers.** Separate bounded domain slices; do not bundle unrelated business redesign.
5. **Legacy Client/direct-column retirement.** Destructive, last. Codex; explicit recovery evidence and independent QA required.

The **first dependency-safe implementation slice** after T131 is slice 1: a bounded tenant/canonical-relationship schema foundation sufficient for operational-fresh MatterParty and Party-based PropertyOwner composition without creating Client rows. It must remain schema/security foundation only; no Matter/Property CRUD.

## Consequences

- Clean installations can progress toward the final domain without ever treating Client as a new-business master.
- Legacy migration remains evidence-driven and fail-closed.
- Compatibility is staged without dual-master semantics.
- Matter and ownership can be implemented in dependency order.
- Required ADR #20 remains honestly open for migration seams outside T131.

## Implementation Boundary

This ADR is architecture only. It creates no schema, migration, runtime behavior, database mutation, CRUD surface, permission, RLS policy or task authorization.
