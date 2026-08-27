# ADR-0023: Party vs Client — Party Subtype-Modeling Strategy

**Status:** Proposed
**Date:** 2026-08-27

**Resolves:** `docs/Legal_DMS — Domain Model & Functional Specification.md` §21 planning-list item
**#2** ("Party vs Client"). Per §24.2's own text, the substance of this planning-list item, once
analyzed, is the **Party subtype-modeling strategy** — see "Problem" below for why the label
("Party vs Client") and the actual open decision are not the same question, and why that is not a
discrepancy this ADR needs to resolve, only correctly identify.

**Does not resolve:** Required ADR #1, #18, or #19 (already resolved by `ADR/0021`/`ADR/0022`, not
reopened here) or Required ADR #3–#17/#20 (untouched; see "Explicitly Unresolved Items" below).

**Dependencies:** `ADR/0021-organization-tenant-boundary-enforcement.md` (tenant isolation — Party
is Organization-scoped, composed with, not reopened). `ADR/0022-authorization-architecture.md`
(authorization architecture — Party access is governed by its resource+action model, composed with,
not reopened).

## Problem

`docs/Legal_DMS — Domain Model & Functional Specification.md` §21 labels its second required
architectural decision "Party vs Client" — a label that, read in isolation, could suggest an open
question about whether `Client` is a subtype of `Party`, a separate entity, or something else. It
is not. **That identity question is already frozen**, settled independently in three places in the
governed specification, not by this ADR:

- **§4 rule 8:** "Party is the reusable master record."
- **§4 rule 9:** "Client is a Matter relationship/status, not a master entity" — and §24.2 restates
  this explicitly: "'Client' is not a Party subtype or a separate table; it is what a Party *is* on
  a given Matter."
- **§23 ("Final Executive Decision")**, the specification's own frozen-concept list, names `Party`
  and **`Client-as-relationship`** as two separate frozen line items — not `Client` as its own
  entity alongside `Party`. The wording is deliberate, not incidental.
- **§1.6 "Highest risks," item 2:** "Treating `Client` as the equivalent of `Party`" is named as one
  of the specification's ten highest-risk implementation mistakes — restated again in the business-
  discovery document's own highest-risk list (item 1: "Current `Client` model vs finalized Party
  architecture").

The mechanism that *realizes* rule 9 is also already specified, not left to this ADR: `MatterParty`
(§24.7) is the many-to-many join between `Matter` and `Party` that carries a `role` field as an
attribute of the join itself — "'Client' is a *value* this role field can take, not a separate
table" (§24.7, verbatim). This is a Confirmed Business Rule this ADR treats as already established,
exactly per this task's own governing instruction to compose with, not reopen, already-frozen
decisions. `MatterParty`'s own remaining open questions (the full role vocabulary beyond "Client,"
minimum cardinality) are `MatterParty`'s own unresolved engineering decisions (§24.7's own "Open
engineering decisions" list) — not part of Required ADR #2 and not decided here.

**What Required ADR #2 actually requires, per §24.2's own direct statement**, is a different, still
genuinely open question: `Party` itself must represent both individuals and legal entities
("companies, trusts, government bodies, etc." — broader than the current `Client.client_type`'s
`individual|organization` pair), and **how that subtype distinction is modeled at the schema level
is unresolved** — §24.2 names three candidates (single-table with a discriminator column,
class-table inheritance, or a JSONB profile blob) and cites this exact question as "Required ADR #2
('Party vs Client')." §12's "Remaining Engineering Decisions" table and §26 item 1 both confirm the
same framing ("Exact Party subtype strategy... must decide before implementation" /
"Party subtype-modeling strategy (§24.2; Required ADR #2)"). This ADR resolves that question — the
subtype-modeling strategy — not the identity question, which was never actually open.

### Repository baseline (direct inspection, `main` at `b5b3126`)

- **No `Party`, `MatterParty`, `PartyRelationship`, `Representative`, `Enquiry`, `Quotation`, or
  `Communication` table exists anywhere in the schema** — confirmed by a full read of
  `backend/src/app/infrastructure/persistence/models/*.py`. None of these are partial
  implementations; all are net-new per the specification's own "Repository mapping" bullets for
  each.
- **A `Client` implementation exists today** (`infrastructure/persistence/models/client.py`):
  `Client` (`client_type` — `CHECK (client_type IN ('individual', 'organization'))`, `full_name`,
  `primary_phone`, `primary_email`, `pan_number`/`aadhaar_number` with format-validating `CHECK`
  constraints, `address_id`, `notes`), `ClientContact` (`client_id`, `contact_name`,
  `relationship_type` as a free string, `phone`, `email`, `is_primary` — a **partial** precedent
  for `Representative`, per §24.2's own assessment: "conflates 'any contact person' with 'a person
  legally authorized to act for the Party'"), and `Address` (already village-aware, directly
  reusable per §24.2 — no change proposed here). `matters.client_id`/`matters.property_id` are
  today's single-valued foreign keys — the concrete manifestation of the "one-client Matter"
  limitation §25 invariant #1/#2 both name as currently violated.
- **This `Client` table is not a rename target for `Party`** — confirmed directly, and already
  stated by the specification itself (§24.2, §11.1): it is `individual|organization`-only, carries
  client-specific fields directly rather than through a general subtype mechanism, has no
  `organization_id` (consistent with `ADR/0021`'s identical finding that no Organization concept
  exists in code today), and has no Representative or PartyRelationship concept at all. Its
  repository-mapping classification is **New/Modify**, not **Rename**.
- **No SQLAlchemy inheritance mapping (joined-table or single-table polymorphic identity) exists
  anywhere in this codebase** — confirmed by a full grep of every model file: every one of the
  twelve model modules is a flat `Base`/`AuditMixin`/`OptimisticLockMixin` class with plain columns
  and `ForeignKey` constraints only, matching `ADR/0021`'s identical finding that "no SQLAlchemy
  `relationship()` is declared anywhere, by deliberate original design." Wherever this codebase
  already models a subtype-like distinction, it does so with a `CHECK`-constrained discriminator
  column on a single table — `Client.client_type`, `Address.address_type`, `Role.is_system_role`,
  `Permission.category` — never a base-plus-extension-table pattern.
- **JSONB is already used elsewhere in this codebase** (`activity_logs.details`,
  `system.py`'s `config`/`payload`/`result` columns) — but exclusively for genuinely free-form,
  unvalidated, non-searched metadata (audit annotations, background-job configuration), never for
  identity-bearing, format-validated, individually-searchable business fields of the kind Party's
  subtype-specific fields (PAN, Aadhaar, GSTIN) require.

## Business/Specification Inputs

Frozen (not reopened by this ADR):

- §4 rule 8 (Party is the reusable master record), rule 9 (Client is a Matter relationship/status,
  not a master entity), rules 10–14 (multi-party Matters, a Party's many-Matter participation,
  role-varies-per-Matter, multiple Representatives, joint Representative authorization).
- §23's frozen-concept list: `Party` and `Client-as-relationship` as distinct line items.
- §1.6/business-discovery's shared highest-risk warning against treating `Client` as equivalent to
  `Party`.
- §24.7 MatterParty's existence and purpose (the join entity realizing rule 9) — its own unresolved
  field-level details are not decided here.
- §4 rule 43 (Organization is the tenant/security boundary, applying transitively to Party per
  `ADR/0021`).

Genuinely open, and the actual subject of this ADR's Decision:

- §24.2's Party subtype-modeling strategy — the three named candidates.

Genuinely open, and explicitly **not** decided by this ADR (see "Explicitly Unresolved Items"):

- Exact field list per subtype (§24.2, excluded by T89's own authorized scope).
- Party-merge/deduplication (§24.2, excluded).
- Party-level confidentiality (§24.2's Authorization bullet, §4 rule 45's applicability to Party,
  excluded).
- `MatterParty`'s role vocabulary and minimum cardinality (§24.7, a different entity's own open
  items, not part of Required ADR #2).
- `PartyRelationship`'s relationship-type vocabulary and directionality (§24.2, a different open
  item).
- `Representative`'s authorization-basis vocabulary and Document-evidence requirement (§24.2, a
  different open item).

## Definitions / Terminology

- **Party:** the Organization-scoped, reusable master record for any person or legal entity the
  firm deals with (§4 rule 8). Exists independently of any Matter. Has a subtype (individual,
  organization, and potentially others per §24.2's "companies, trusts, government bodies, etc.").
- **Client:** not an entity, not a Party subtype, not a separate table. A *role value* a Party holds
  on a specific `MatterParty` row (§4 rule 9, §24.7). A single Party can be "Client" on one Matter
  and hold a different role (e.g. "Opposing Party," "Represented Third Party") on another, per §4
  rule 12.
- **MatterParty:** the many-to-many join entity between `Matter` and `Party`, carrying `role` as an
  attribute of the join (§24.7). Already specified as CBR; not redesigned by this ADR.
- **PartyRelationship:** a self-referential Party↔Party relationship (director-of, family-of, etc.),
  distinct from a Party's role on a Matter (§24.2). Not redesigned by this ADR.
- **Representative:** a person authorized to act *for* a Party (§4 rule 13/14), distinct from
  `PartyRelationship`. Not redesigned by this ADR.
- **Subtype-modeling strategy:** the schema-level technique for representing that a single `Party`
  table must hold rows of meaningfully different shapes (an individual's PAN/Aadhaar/date-of-birth
  versus an organization's CIN/GSTIN/incorporation-date) — this ADR's actual subject.

## Options Considered

### Tier 1 — Party/Client identity relationship (already frozen; evaluated here only for
traceability, per this task's own instruction to consider these alternatives explicitly, and to
show why each is or isn't available as a live choice)

1. **Client as a Party subtype or separate inheritance branch** (e.g. a `client_parties` extension
   table, or a `Client(Party)` polymorphic identity). **Not available as a choice this ADR can
   make** — directly contradicted by §4 rule 9 and §23's "Client-as-relationship" line item, and is
   the exact mistake §1.6's highest-risk item 2 names by description. Rejected on frozen-business-
   rule grounds, not architectural-quality grounds — no scoring against this ADR's criteria would
   change this outcome, because the specification has already removed it from the option space.
2. **Client as a role/capability associated with Party.** **This is the already-frozen
   architecture**, not a choice being made by this ADR — realized by `MatterParty.role` per §24.7,
   confirmed by §4 rule 9's own text. This ADR's "Decision" below treats this as a settled
   precondition, not as one of three options it is scoring.
3. **Party and Client as separate entities with an explicit relationship** (e.g. a `Party` table
   and a distinct `Client` table, FK-linked). **Not available as a choice** for the same reason as
   option 1 — §23 explicitly frozen `Party` and `Client-as-relationship` as two different *kinds* of
   thing (a master entity and a relationship-attribute value), not two entities of the same kind
   linked by a foreign key. Rejected on frozen-business-rule grounds.

### Tier 2 — Party subtype-modeling strategy (the actual open decision this ADR resolves)

1. **Single-table with a discriminator column and nullable subtype-specific fields.** One `parties`
   table; a `CHECK`-constrained discriminator column (extending, not reinventing,
   `Client.client_type`'s exact pattern); subtype-specific fields as nullable columns, each
   individually format-validated via `CHECK` constraints where applicable (PAN/Aadhaar, following
   the already-proven `Client.pan_number`/`aadhaar_number` regex-`CHECK` pattern verbatim).
   - **Domain fidelity:** matches today — Party's "individual vs organization" split is exactly what
     `Client.client_type` already models; extending to additional subtypes (trust, government body)
     is an additive discriminator-value change, not a structural one.
   - **Repository consistency:** the only option with a direct, working, already-tested precedent
     in this exact codebase (`Client.client_type`) and the only option consistent with this
     codebase's confirmed zero-ORM-inheritance convention across all twelve existing model files.
   - **Schema/query simplicity:** a single `SELECT`/`session.get()` retrieves a complete Party row —
     no join required, matching `AbstractRepository.get_by_id()`'s existing bare-`session.get()`
     shape with no specialization needed.
   - **Field-level integrity:** preserves the proven, working `CHECK`-constraint format-validation
     pattern for PAN/Aadhaar/GSTIN-style fields — a real, tested mechanism this codebase already
     has, unlike the other two options.
   - **Searchability:** subtype-specific fields remain ordinary indexed relational columns, directly
     compatible with the existing `SearchQuery`/`FilterSpec` generic-repository framework §24.2
     itself names as "directly reusable" for Party search — no query-layer extension needed.
   - **Downside, named honestly:** nullable-column sprawl as subtype diversity grows beyond
     individual/organization; `CHECK`-constraint expressions enforcing "only fields belonging to
     this row's own subtype may be non-null" grow more complex with each additional subtype. See
     Trade-offs and Future Impact.
2. **Class-table inheritance** (a `parties` base table plus `individual_parties`/
   `organization_parties` extension tables, SQLAlchemy joined-table polymorphism).
   - **Domain fidelity/normalization:** the strongest of the three — individual-only and
     organization-only fields live in genuinely separate tables with real `NOT NULL` constraints,
     no nullable-sprawl, cleanest extension story for additional subtypes.
   - **Repository consistency:** **zero precedent anywhere in this codebase** — confirmed by full
     inspection of all twelve existing model files; would introduce SQLAlchemy's joined-table
     polymorphic mapping (`polymorphic_on`/`polymorphic_identity`) as a first-of-its-kind pattern,
     requiring new ORM/repository infrastructure this ADR is not authorized to design (this is a
     schema/architecture decision, not an implementation task).
   - **Schema/query complexity:** loading a complete Party row requires a join across base and
     extension tables — `AbstractRepository.get_by_id()`'s current bare-`session.get()` shape would
     need real rework to support polymorphic loading correctly, a repository-layer change with no
     currently-authorized task to perform it.
   - **Migration cost:** each new subtype requires a new extension table and its own migration —
     higher operational cost than adding nullable columns to an existing table.
   - Rejected as the primary mechanism, on repository-consistency and unauthorized-infrastructure-
     scope grounds — not because it is architecturally unsound in the abstract.
3. **JSONB profile blob keyed by subtype.** A `parties` table with universal columns plus one
   `profile: JSONB` column holding subtype-specific fields as a schemaless document.
   - **Flexibility:** highest of the three — a new subtype needs no migration, only a different JSON
     shape.
   - **Repository consistency:** JSONB itself has precedent in this codebase (`activity_logs`,
     `system.py`), but never for identity-bearing, format-validated, individually-searchable fields
     of the kind PAN/Aadhaar/GSTIN are — every existing JSONB use is genuinely free-form,
     non-validated, non-searched metadata, a materially different use case.
   - **Field-level integrity:** the working `CHECK`-constraint regex-validation pattern already
     proven for `Client.pan_number`/`aadhaar_number` does not transfer cleanly to JSONB-embedded
     values — Postgres can express JSONB-path `CHECK` constraints, but this codebase has never done
     so, and it is a markedly less-proven mechanism here than the plain-column pattern already
     working today.
   - **Searchability:** §24.2 explicitly requires PAN/Aadhaar/registration-number search via the
     existing `SearchQuery`/`FilterSpec` framework; that framework operates over typed relational
     columns through the generic repository, not JSONB-path queries — adopting this option would
     require extending that framework in a way nothing in this codebase currently proves out for
     structured, filterable fields (as opposed to the opaque metadata JSONB is used for today).
   - Rejected as the primary mechanism for identity-bearing structured fields, on integrity and
     searchability grounds specific to the fields Party's subtype dimension actually needs to carry
     — not a rejection of JSONB as a technology in general (see Future Impact for a narrower,
     legitimate future use).

| Criterion | (1) Single-table + discriminator | (2) Class-table inheritance | (3) JSONB profile blob |
|---|---|---|---|
| Domain fidelity | Adequate (matches today's 2-subtype reality) | Highest | Adequate |
| Identity semantics | Clear (one row = one Party) | Clear (base row = one Party) | Clear (one row = one Party) |
| Lifecycle flexibility | Adequate | Adequate | Highest |
| Schema/query simplicity | Highest (no join) | Lowest (join required) | High (no join, but path queries) |
| Field-level integrity (CHECK constraints) | Highest (proven, working) | High (real NOT NULL) | Lowest (unproven in this codebase) |
| Searchability via existing `SearchQuery` | Highest (direct fit) | High (direct fit, needs joins) | Lowest (framework doesn't support JSONB paths) |
| Migration cost per new subtype | Low (add columns) | Higher (new table) | Lowest (no migration) |
| Consistency with existing Legal_DMS architecture | **Highest** (direct precedent, zero-ORM-inheritance convention) | Lowest (first-of-its-kind pattern) | Medium (JSONB precedented, but not for this use) |
| Authorization compatibility (`ADR/0022`) | Highest (one resource, one permission surface) | Medium (risks per-subtype-table permission drift) | Highest |
| Tenant-isolation compatibility (`ADR/0021`) | Equivalent across all three — `organization_id` is an ordinary mandatory column regardless of subtype strategy | Equivalent | Equivalent |

## Decision

**Tier 1 is not decided here — it is already frozen**, and this ADR states it explicitly rather
than silently assuming it: Client is a role value on `MatterParty`, never a Party subtype or
separate entity, per §4 rule 9 and §23.

**Tier 2, Option 1 is adopted**: Party's subtype dimension is modeled as a **single table with a
`CHECK`-constrained discriminator column and nullable subtype-specific fields**, directly extending
the pattern this codebase's own existing `Client.client_type` already proves out, rather than
introducing class-table inheritance or a JSONB profile blob. This is a schema-shape decision, not an
implementation — no migration, table, or column is created by this ADR.

### What this decides, precisely

- One `parties` table (§9.4/§10.A naming convention), not a rename of `clients` (per §24.2's own
  explicit "a direct rename is insufficient" — see Migration Implications).
- A discriminator column analogous to `Client.client_type`, `CHECK`-constrained to a defined value
  set. The exact expanded value set beyond `individual`/`organization` (trust, government body,
  etc.) is **not decided here** — excluded from T89's authorized scope ("exact field list per
  subtype").
- Universal fields (display name, subtype discriminator, primary phone, primary email, notes, an
  `address_id` FK reusing the existing `Address` table unchanged) apply to every row regardless of
  subtype.
- Subtype-specific fields are nullable columns scoped to the rows whose discriminator value they
  apply to, format-validated via `CHECK` constraints following the exact pattern already proven for
  `Client.pan_number`/`Client.aadhaar_number`. Their exact list is **not decided here**.
- No natural-key uniqueness constraint on Party identity (matching `Client`'s existing behavior and
  §24.2's own statement that "no natural key... is sufficiently universal or stable to serve as
  identity") — PAN/Aadhaar/registration-number remain searchable attributes, not unique identifiers.

### Why this is the correct decision, not merely the simplest one

The deciding factors are repository-grounded, not a preference for simplicity in the abstract: (a)
this codebase has a real, working, tested precedent for exactly this pattern
(`Client.client_type`), (b) this codebase has zero precedent anywhere for ORM-level inheritance
mapping, confirmed by inspecting every existing model file, making class-table inheritance a
genuinely novel pattern this decision would be introducing rather than extending, (c) the format-
validation and searchability requirements §24.2 itself names as required for Party (PAN/Aadhaar/
registration-number `CHECK`-validated and searchable) are only cleanly satisfied, with a proven
mechanism, by plain relational columns — not by JSONB-embedded values, which this codebase has never
format-validated or made searchable through its existing `SearchQuery` framework. This mirrors the
same evidence-based reasoning `ADR/0021` and `ADR/0022` both used: favor the option this repository's
own actual architecture already demonstrates working, unless a concrete, evidenced gap requires
otherwise.

## Detailed Reasoning

Rejecting Tier 1's alternatives is a frozen-business-rule matter, not an architectural-quality
judgment — §4 rule 9 and §23's "Client-as-relationship" line item leave no scoring exercise capable
of overriding them, and this ADR does not attempt one. Selecting Tier 2 Option 1 follows directly
from this repository's own evidenced conventions: every existing subtype-like distinction in this
codebase (`Client.client_type`, `Address.address_type`, `Role.is_system_role`) already uses a flat
discriminator column, and zero existing model uses ORM-level inheritance — the same
"favor what this repository already demonstrates working" principle `ADR/0021` applied when
choosing application-layer scoping as the primary tenant-isolation mechanism (because it is what a
developer already reads and tests directly) and `ADR/0022` applied when formalizing the existing
`RbacAuthorizationService` rather than replacing it. Class-table inheritance's normalization
advantage is real but is not evidenced as *needed* yet — §24.2 names only two subtypes with concrete
field examples (individual: PAN/Aadhaar/DOB/gender/occupation; organization: CIN/GSTIN/incorporation
date), a scale the discriminator-column approach handles cleanly, with the class-table-inheritance
alternative available later (see Future Impact) if a specific future subtype's field-count genuinely
outgrows the nullable-column approach's comfort zone. JSONB's rejection is narrower and more
specific: it is not rejected as a technology (this codebase already uses it appropriately elsewhere)
but as the wrong fit for *this specific field set* — identity-bearing, individually format-validated,
individually searchable fields, which is exactly the category JSONB's existing uses in this
codebase (`activity_logs.details`, `system.py`'s config/payload columns) deliberately are not.

## Data-Model Implications

- **New table:** `parties` — id (UUID PK, matching this repository's established convention),
  `organization_id` (mandatory, per `ADR/0021` — see "Relationship to ADR-0021"), a discriminator
  column, universal fields, subtype-specific nullable fields (exact lists excluded from this ADR's
  scope).
- **Not a rename:** `clients`/`client_contacts` are not renamed or restructured into `parties` by
  this ADR — they remain the pre-finalized-architecture implementation until a future migration
  task (Required ADR #20's own scope) decides the data-migration mechanics.
- **Reused unchanged:** `Address` — already Organization-agnostic geography data, no interaction
  with the subtype-modeling decision.
- **Downstream new tables not redesigned here, only confirmed as Party's consumers:**
  `MatterParty` (Matter↔Party join, carries role), `PartyRelationship` (Party↔Party self-join),
  `Representative` (Party↔person-authorized-to-act join). Each references `parties.id`; none of
  their own internal shape is decided by this ADR.
- **Uniqueness:** none beyond the primary key, matching `Client`'s existing behavior — PAN/Aadhaar/
  registration-number remain searchable, not unique-constrained.
- **Normalization:** the chosen approach is less normalized than class-table inheritance (nullable
  columns for fields that don't apply to every row) — an accepted, named trade-off, not an
  oversight (see Trade-offs).

## API / Query Implications

- Party is exposed as **one resource type**, with the discriminator as an ordinary field in its DTO
  — not a family of subtype-specific endpoints or resource types. This avoids a failure mode
  class-table inheritance would tempt (a `/individual-parties` vs `/organization-parties` API
  split, which would fragment the single `parties:read`/`parties:write`-style permission surface
  `ADR/0022`'s model expects — see "Relationship to ADR-0022").
- The existing generic `SearchQuery`/`FilterSpec` framework, already wired through the generic
  repository (`T4`–`T6`), applies to Party's subtype-specific fields directly, the same way it
  already applies to `Client.client_type` today — no new query mechanism is required by this
  decision.
- Filtering/joining: no join is required to retrieve a complete Party record (unlike class-table
  inheritance), keeping `AbstractRepository.get_by_id()`'s existing shape usable without
  specialization — consistent with `ADR/0022`'s decision that repositories stay generic and
  permission-agnostic; nothing about this subtype-modeling choice requires or invites adding
  Party-specific logic into the repository layer.
- Authorization checks (per `ADR/0022`) apply once, to the Party resource as a whole, at the
  service/use-case boundary — not fragmented per subtype.

## Tenant-Isolation Composition

See "Relationship to ADR-0021" below for the dedicated section. Summary: `parties.organization_id`
is mandatory per `ADR/0021`'s already-decided rule, applying identically regardless of which
subtype-modeling option had been chosen — the subtype-modeling decision and the tenant-isolation
mechanism are orthogonal, and this ADR does not alter, weaken, or duplicate `ADR/0021`'s mechanism
in any way.

## Authorization Composition

See "Relationship to ADR-0022" below for the dedicated section. Summary: Party access is governed
by `ADR/0022`'s existing resource+action permission model (e.g. a future `parties:read`/
`parties:write`-style permission code, following the established convention), checked once at the
service/use-case boundary, exactly like every other resource. The single-table approach keeps this
a single permission surface; Party-level or subtype-level confidentiality, if ever decided, is a
consumer of `ADR/0022`'s already-established resource-instance-authorization extension point, not a
new mechanism.

## Consequences

- A `parties` table can be created with a shape directly informed by this decision once a future
  implementation task is authorized — this ADR itself creates no schema.
- Future entities (`MatterParty`, `PartyRelationship`, `Representative`) have a stable target
  (`parties.id`) to reference once their own architectural questions are resolved.
- The existing `Client`/`ClientContact` implementation is unaffected by this ADR — no code, schema,
  or test changes result from this decision being recorded.
- A future Party-level confidentiality decision (if the business model is ever extended to require
  one) has a known, already-established place to plug into (`ADR/0022`'s extension point), reducing
  the risk of that future decision inventing a parallel authorization mechanism.

## Trade-offs

- **Nullable-column sprawl** as subtype diversity grows beyond individual/organization — accepted
  because §24.2 names only two subtypes with concrete field detail today, and the discriminator
  approach handles that scale cleanly; a materially larger subtype set is a Future Impact
  consideration, not a present cost.
- **`CHECK`-constraint complexity grows with each additional subtype** ("only fields belonging to
  this row's own subtype may be non-null" becomes a longer expression per added subtype) — a real,
  named cost versus class-table inheritance's cleaner `NOT NULL`-per-table story, accepted for the
  repository-consistency and query-simplicity gains described in Detailed Reasoning.
- **Lower normalization than class-table inheritance** — accepted deliberately; this repository's
  own conventions and the specification's currently-evidenced subtype scale do not yet justify the
  first-of-its-kind ORM-inheritance infrastructure the higher-normalization option would require.
- **The exact subtype vocabulary and field lists remain open** — this ADR decides the *mechanism*
  (discriminator column), not the *content* (which fields, which subtype values), per T89's own
  scope boundary; a real, named limitation of this ADR's scope, not an oversight.

## Migration Implications

No migration is created by this ADR. Architecturally: `clients`/`client_contacts` are not
retargeted or renamed by this decision — the data-migration mechanics (whether existing `Client`
rows backfill into `parties`, whether a dual-write/compatibility window is needed, how
`matters.client_id` is retired in favor of `MatterParty`) belong to Required ADR #20 (the general
migration-strategy ADR, §26 item 10), not to this ADR. This ADR only fixes the *target* shape
Required ADR #20 will need to migrate toward for Party's subtype dimension specifically.

## Testing / Verification Obligations

Named here as obligations for whichever future implementation task carries this decision out — not
performed by this ADR, mirroring `ADR/0021`'s and `ADR/0022`'s identical convention:

- A `CHECK`-constraint regression test proving subtype-inappropriate fields (e.g. an organization-
  subtype row with a non-null PAN field, if PAN remains individual-only) are rejected, mirroring
  the existing pattern already proven for `Client.pan_number`/`aadhaar_number`'s format `CHECK`s.
- A test proving a single Party can hold different `MatterParty.role` values (including "Client")
  across different Matters without any change to the Party row itself — the concrete regression
  test for §4 rule 12 being correctly realized entirely at `MatterParty`, not at `Party`.
- A test proving `parties.organization_id` is mandatory and enforced per `ADR/0021`'s existing
  fail-closed requirements — extending, not duplicating, that ADR's own testing obligations.
- A search/filter test proving PAN/Aadhaar/registration-number search continues to work through the
  existing `SearchQuery`/`FilterSpec` framework for the new `parties` table, the same way it already
  works for `clients` today.

## Dependencies / Other Unresolved Related ADRs

- **#1 Organization as tenant boundary** — already resolved by `ADR/0021`.
- **#2 Party vs Client** — resolved by this ADR (`ADR/0023`): Party subtype-modeling strategy.
- **#18 Authorization architecture** — already resolved by `ADR/0022`.
- **#19 Tenant isolation enforcement** — already resolved by `ADR/0021`.
- **#3–#17, #20** — untouched. In particular, #20 (migration strategy) now inherits a concrete,
  disclosed dependency from this ADR: the `clients`→`parties` migration mechanics, per "Migration
  Implications" above.

## Relationship to ADR-0021 — Tenant Isolation

`ADR/0021` is not modified, reopened, or reinterpreted by this ADR. `Party` is Organization-scoped
per §4 rule 43 applying transitively (§24.2's own "Identity & tenant ownership" bullet states this
directly) — `parties.organization_id` is mandatory, exactly as `ADR/0021` already requires for every
tenant-scoped table, enforced by the same two independent layers `ADR/0021` established: mandatory
application-layer scoping as the primary mechanism, and a `FORCE`d, default-deny Row-Level Security
policy as the backstop. This ADR's subtype-modeling decision has **no interaction** with tenant
scoping at all — `organization_id` sits alongside the discriminator column as an ordinary mandatory
column, under exactly the same rule regardless of which of Tier 2's three options had been chosen.
Stated explicitly so a future reader does not need to re-derive it: **an authorized Party record
belonging to one Organization must never be visible to, or modifiable by, a caller scoped to a
different Organization, and this ADR's subtype-modeling choice does not create, weaken, or bypass
that guarantee in any way.** `MatterParty`, `PartyRelationship`, and `Representative` — none
redesigned here — each independently inherit the identical mandatory-`organization_id` requirement
once their own architectural questions are resolved; this ADR does not decide their shape, only
confirms they are equally bound by `ADR/0021`.

## Relationship to ADR-0022 — Authorization Architecture

`ADR/0022` is not modified, reopened, or reinterpreted by this ADR. Party access is authorized
through `ADR/0022`'s existing resource+action, role-indirected permission model — a future
`parties:read`/`parties:write`-style permission code, checked once at the service/use-case boundary,
exactly like every other resource `ADR/0022` already governs (`matters:read`, `users:manage`, etc.).
This ADR's single-table subtype-modeling decision **reinforces** `ADR/0022`'s compatibility criteria
rather than complicating them: because Party is one table with one resource identity regardless of
subtype, there is exactly one permission surface to check, not a risk of per-subtype-table
permission drift that class-table inheritance could have invited (e.g. a future implementer adding
separate `individual_parties:read`/`organization_parties:read` codes, which would fragment
`ADR/0022`'s resource+action model at exactly the layer it was designed to keep coherent).

§24.2's own Authorization bullet leaves Party-level (and, by extension, subtype-level)
confidentiality **explicitly unresolved** — "the frozen architecture names Matters/Files/Documents
explicitly for finer-grained access, not Party, so the default assumption is Organization-level
visibility only unless a future decision extends it." This ADR does not decide that question,
consistent with T89's own authorized-scope exclusion. If and when a future ADR does decide it, per
this task's own instruction, that decision is a **consumer of the resource-instance-authorization
extension point `ADR/0022` already establishes** — "a second, independent filter alongside
`ADR/0021`'s tenant-scope filter, applied at the same data-access layer" (`ADR/0022`'s own
"Extension point for resource-instance authorization" section) — not a new authorization
architecture invented for Party specifically. This ADR names that composition path explicitly so a
future Party-confidentiality decision does not need to re-derive it.

## Future Impact

- If a future subtype (a trust, a government body, or another category §24.2 names as plausible)
  turns out to need a substantially larger, mostly-required field set of its own, this ADR's
  discriminator-column approach may need supplementing — e.g. a single dedicated extension table
  for just that one heavy subtype, without necessarily abandoning the discriminator approach for
  the lighter subtypes — a decision for a future ADR amendment or superseding ADR, per this
  repository's established convention (`ADR-0018`) for handling decisions that later need to
  change, not a silent implementation deviation.
- A narrow, legitimate future use for JSONB on the `parties` table remains available without
  reopening this ADR: genuinely free-form, non-searched, non-validated per-Party notes or
  attributes (the same category `activity_logs.details` already serves) — this ADR rejects JSONB
  only for the identity-bearing, format-validated, searchable subtype-specific fields it actually
  evaluated, not as a blanket prohibition on JSONB columns anywhere on `parties`.
- Required ADR #20 (migration strategy) inherits the disclosed `clients`→`parties` migration
  dependency named above.
- A future Party-level confidentiality ADR, if authorized, inherits the composition path with
  `ADR/0022`'s extension point named above.
- `MatterParty`, `PartyRelationship`, and `Representative` each remain open architectural questions
  in their own right — this ADR fixes the table they reference, not their own field lists,
  vocabularies, or cardinality rules.

## Explicitly Unresolved Items

After this ADR, the Required ADR status is:

- **Required ADR #1** ("Organization as tenant boundary") — already resolved by `ADR/0021`. Not
  reopened.
- **Required ADR #2** ("Party vs Client") — **resolved by this ADR (`ADR/0023`).** The identity
  question (Client is a `MatterParty.role` value, never a Party subtype or separate entity) was
  already frozen by §4 rule 9/§23 before this ADR and is restated, not newly decided, here. The
  genuinely open question this ADR resolves is the Party subtype-modeling strategy: single-table
  with a `CHECK`-constrained discriminator column. Exact subtype vocabulary, exact field lists per
  subtype, Party-merge/deduplication, and Party-level confidentiality are **explicitly not resolved
  by this ADR** — named limitations of its scope, matching T89's own authorized-scope exclusions,
  not silently decided by omission.
- **Required ADR #18** ("Authorization architecture") — already resolved by `ADR/0022`. Not
  reopened.
- **Required ADR #19** ("Tenant isolation enforcement") — already resolved by `ADR/0021`. Not
  reopened.
- **Required ADR #3–#17 and #20** — remain fully unresolved. Nothing in this ADR decides, narrows,
  or implies a position on any of them beyond the disclosed migration dependency (#20) named in
  "Future Impact."

No Required ADR other than #2 is resolved, reinterpreted, or narrowed by this document. `ADR/0021`
and `ADR/0022` are not modified, reopened, or reinterpreted by this document. No §4 business rule
and no part of §23's frozen concept list is changed, invented, or silently altered by this document.
