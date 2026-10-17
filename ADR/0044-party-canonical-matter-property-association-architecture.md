# ADR-0044: Party-Canonical Matter–Property Association Architecture

**Status:** Proposed  
**Date:** 2026-10-17  
**Related task:** T154 — Party-Canonical Matter–Property Association Architecture.

**Resolves:** None.

**Does not resolve:** Required ADR #12 (Workflow vs Government Status), #15 (Core vs configurable vocabulary), #16 (UUID vs human-readable identifiers), #17 (Soft deletion/history), or #20 (Migration strategy from the current schema). Required ADR #20 is a specification planning-list item, distinct from repository ADR-0020 (Session Commit/Rollback Policy).

**Composes with:** ADR-0020 request transaction ownership; ADR-0021 Organization tenant isolation; ADR-0022 authorization; ADR-0023 Party vs Client; ADR-0029 Activity vs Audit; ADR-0030 Matter/File lifecycle; ADR-0031 trusted User→Organization context; ADR-0037 operational-fresh provenance; ADR-0039 Party-canonical Matter/Property cutover; ADR-0043 Enquiry/Quotation/Acceptance/Matter conversion; T132/T133/T134/T135/T145 foundations.

## Problem and authoritative domain basis

The governed domain specification, `docs/Legal_DMS — Domain Model & Functional Specification.md`, §24.7 MatterProperty and §24 Property Relationships, requires a many-to-many Matter–Property relationship. A Matter can involve several Properties; a Property can participate in several Matters independently of its ownership. Existing nullable `Matter.property_id` is only a legacy one-Property analogue. T132 established Party-canonical Matter participation; T133 established Party-canonical Property ownership; T135 added Property application CRUD while expressly excluding MatterProperty. T145 provides the Party→Matter→File→Document→DocumentVersion frontend slice but intentionally omits Property association.

The specification marks relationship-nature vocabulary as an unresolved engineering decision, not a business requirement. It also assigns historical migration/retirement of direct legacy FKs to Required ADR #20. This ADR defines the canonical target and narrow coexistence boundary only.

## Decision

### Canonical representation and cardinality

The canonical association is `Matter ↔ MatterProperty ↔ Property`. A Matter may have zero or more associated Properties; a Property may participate in zero or more Matters. The same pair is represented at most once, regardless of how many Parties own the Property or participate in the Matter. Neither entity's existence depends on an association.

A future `matter_properties` association table has a stable opaque association identity (`id`, following existing UUID identity patterns), trusted `organization_id`, mandatory `matter_id` and `property_id`, and a unique constraint on the Matter/Property pair within Organization. Database-level same-Organization referential integrity must cover both referenced entities, not merely application validation. Association identity is distinct from either business record's identity and must not be exposed as an alternative tenant authorization token. Implementation must confirm the repository's existing ID, composite-FK, audit and RLS conventions before writing schema; no new business-readable numbering decision is made here.

No relationship-nature/type/status qualifier is introduced. No business invariant currently demands it; adding organization-configurable vocabulary would cross Required ADR #15. Future distinct relationship semantics require separately authorized architecture rather than speculative columns.

### Tenant integrity and authorization

Both endpoints must be resolved under the authenticated current user's trusted Organization context. Future `MatterProperty` is Organization-owned, with ENABLE and FORCE row-level security, default-deny behavior if Organization context is missing, and non-enumerating cross-tenant or nonexistent endpoint failures. Composite tenant-aware foreign keys (or equivalent existing database-enforced same-Organization constraints) prevent a row from joining endpoints of different Organizations. The API may never accept client-supplied Organization as authoritative. Transaction/session ownership continues under ADR-0020; do not add a second transaction owner.

Read operations require the existing relevant Matter/Property read authority. Creating or removing an association is a Matter-scoped change requiring existing `matters:write` and appropriate Property visibility/authorization checks; it must not become an indirect way to mutate a Property or bypass its read boundary. No new RBAC permission family, permission seed or per-Matter access architecture is authorized. If actual permission definitions cannot safely express these operations, STOP for a separate security decision.

### Party-canonical separation

`MatterParty` records a Party's role in a Matter. `PropertyOwner` records a Party's ownership of Property. `MatterProperty` records Property participation in Matter. None implies either of the others. Association creation/removal must not manufacture or change a Party, Client, MatterParty or PropertyOwner, and must not derive a Matter client from Property ownership or infer ownership from Matter participation.

### Association lifecycle and audit

Creating an association requires an existing same-Organization Matter and Property and is atomic with the request transaction. Duplicate attempts must not produce duplicate rows: a unique constraint is the final concurrency backstop. A repeated request for an already-associated pair is handled deterministically without creating another row; implementation must define a stable HTTP response contract and test concurrent duplicates.

Removing an association removes only that participation link, never the Matter, Property, PropertyOwner, MatterParty, File or Document. Missing/repeated removals must be deterministic and tenant-safe. Relationship additions/removals are audit-significant and must use existing audit patterns. This decision does not specify generalized soft deletion, historical preservation, archive, purge, legal hold or cascading deletion. If endpoint deletion behavior cannot be kept safe without Required ADR #17, STOP at that boundary rather than inventing policy.

### Application ownership and future API

The Matter is the primary association-editing aggregate: future authenticated Matter-scoped operations conceptually list linked Properties, associate an existing Property, and remove an association. A read-only Property-scoped reverse lookup of associated Matters is permitted when useful and authorized, but duplicate writable relationship ownership is not. Future frontend Matter detail may select an existing tenant-visible Property, list associated Properties, and remove a link; Property views may navigate associated Matters. Neither frontend nor Acceptance conversion may auto-create Property or infer an association.

### Legacy compatibility boundary — Required ADR #20

For new associations after the future canonical schema/application implementation, `MatterProperty` rows are the sole canonical writable relationship. Existing nullable `Matter.property_id` remains a legacy compatibility/evidence shadow; it must not be dual-written as a substitute for a canonical association. New operational-fresh Matter creation may continue to leave that shadow NULL.

Historical Matters may have a legacy `property_id` without a canonical association. A separately authorized implementation may expose a clearly distinguished, read-only compatibility projection for such historical records, provided it does not silently materialize canonical associations, imply migration completion, or treat conflicting legacy/canonical evidence as one unambiguous link. Canonical rows take precedence for canonical operations; conflicting evidence is flagged for later reconciliation, not silently merged, discarded or overwritten. Compatibility projections cannot be mutated through canonical association endpoints.

This ADR does **not** decide historical backfill, backfill eligibility, old-to-new reconciliation, dual-source conflict repair, legacy column removal timing, `matter_type_id` retirement, Client retirement, or unrelated File/Document convergence. Those remain under Required ADR #20. If a future implementation discovers that safe canonical creation is impossible without these decisions, it must STOP and escalate.

## Options considered

1. **Retain single `Matter.property_id`: rejected.** Violates governed multi-property Matter and Property reuse invariants.
2. **Use PropertyOwner or MatterParty as implicit join: rejected.** Confuses ownership/party roles with the subject of legal work.
3. **Canonical many-to-many join with mandatory relationship-type vocabulary: rejected for now.** The specification labels qualifier semantics unresolved; no business invariant justifies crossing Required ADR #15.
4. **Canonical minimal join, retain legacy shadow for bounded compatibility: selected.** Supports new operational-fresh work without silently deciding historical convergence.

## Future implementation sequencing

1. Separately authorize a bounded schema/tenant-integrity foundation for `matter_properties`, with tenant-aware references, uniqueness, RLS, migration/provenance advancement, and database-level tests. The current T154 architecture phase creates **no** migration.
2. Separately authorize Matter-scoped application operations, RBAC/audit/idempotency and concurrency tests, and any carefully defined read-only legacy compatibility projection. No historical backfill is implied.
3. Separately authorize frontend Matter/Property association controls and navigation, with integration/interaction tests.
4. Address historical migration/retirement only under separately governed Required ADR #20 work.

The historical migration/provenance frontier at T154 authorization is `8d77007b9d7f` (parent `e148c0f5a8b2`); this ADR does not advance it.

## Verification invariants for subsequent implementation/QA

- Zero-to-many in both directions; one canonical row per Organization/Matter/Property pair.
- Existing Matter and Property remain independent, Organization-scoped and Party-canonical.
- Same-Organization association enforced at database and application boundaries.
- Default-deny FORCE RLS and non-enumerating cross-tenant behavior.
- No Party, Client, MatterParty or PropertyOwner manufactured or mutated by association operations.
- Duplicate/concurrent association requests cannot create duplicate rows.
- Removal changes only the association; audit records relationship changes.
- Legacy `Matter.property_id` is not dual-written, removed or silently backfilled.
- No new relationship qualifier, RBAC family, generalized lifecycle policy or Required ADR resolution.

## Consequences and explicit exclusions

The model adds an explicit tenant-owned relationship and a future schema/application/frontend implementation sequence. It avoids a false one-Property-per-Matter constraint and keeps ownership and participation separate. Historical legacy records remain a consciously unresolved compatibility/migration concern.

T154 authorizes no production code, schema, Alembic migration, seed, historical backfill, `Matter.property_id` removal, Client or `matter_type_id` retirement, ownership redesign, automatic Property/Party/File creation, File/Document/DocumentVersion redesign, generalized Workflow/Government Status, configurable vocabulary, business-readable numbering, retention/archive/purge/legal hold, commercial accounting, T153 hardening, or T155+ authorization. Required ADRs #12/#15/#16/#17/#20 remain unresolved.
