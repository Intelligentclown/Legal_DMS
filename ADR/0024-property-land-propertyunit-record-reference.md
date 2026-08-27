# ADR-0024: Property / Land / Property-Unit Boundary and Property Record Reference Architecture

**Status:** Proposed
**Date:** 2026-08-27

**Resolves:** `docs/Legal_DMS — Domain Model & Functional Specification.md` §21 planning-list items
**#3** ("Property vs Matter independence" — the boundary/reference mechanism, not the already-frozen
independence itself), **#4** ("Land vs Property Unit" — representation strategy), and **#6**
("Property Record Reference architecture") — the same bundled unit §26 item 3 itself groups as one
decision.

**Assessed, not resolved:** Required ADR #5 ("Revenue vs City Survey" — exact field sets) and #7
("Flexible Scheme hierarchy," including the TP/FP↔Scheme conceptual boundary). This ADR's
"Relationship to Required ADR #5" and "Relationship to Required ADR #7" sections give the reasoned
dependency assessment T90's authorized scope requires; neither is decided here.

**Does not resolve:** Required ADR #1, #2, #18, or #19 (already resolved by `ADR/0021`/`ADR/0023`/
`ADR/0022`/`ADR/0021` respectively, not reopened here) or Required ADR #8–#17/#20 (untouched).

**Dependencies:** `ADR/0021-organization-tenant-boundary-enforcement.md` (tenant isolation — every
table this ADR's decision implies is Organization-scoped, composed with, not reopened).
`ADR/0022-authorization-architecture.md` (authorization — Property and its linked record entities
are governed by the existing resource+action permission model, composed with, not reopened).
`ADR/0023-party-vs-client-architecture.md` (Party — `PropertyOwner`'s eventual retargeting from
`client_id` to a Party reference is a disclosed, unresolved dependency, not decided here).

## Problem

The governed specification freezes, as Confirmed Business Rules, that Property is an independently-
identified subject of legal work, existing and participating in Matters independently of any one
Matter (§4 rule 15–17), and that Land and Property Unit — whatever those turn out to structurally
be — must never be conflated with each other (§4 rule 18). It further freezes, for the Gujarat
property-records domain specifically, that Revenue and City Survey are distinct record systems
(rule 19), that a Revenue Block/Survey Number belongs to "the Revenue/Land model" (rule 20), that a
City Survey Number may identify property *units* (rule 21) and is not merely another Revenue Survey
Number (rule 22), that TP/FP is independently represented (rule 23), and that the property-record-
system set must remain extensible — a fifth system must be addable without a schema rewrite (rule
24). None of these rules is reopened, reinterpreted, or narrowed by this ADR.

What is not frozen, and what §12/§26 both name as blocking correct schema design, is **how** these
concepts are structurally related: whether `Land` needs its own table at all or is better understood
as the same concept as `RevenueRecord`; whether "Property Unit" — a phrase the business rules use
but never formally define as an entity — needs its own table or is already realized by
`CitySurveyRecord`; and how `Property` connects to whichever record-system entities actually exist
(a generic linking table vs. direct foreign keys vs. some other mechanism), in a way that satisfies
rule 24's extensibility requirement without prematurely committing to those record entities' exact
field-level shape (Required ADR #5's job, not this one's).

### Repository baseline (direct inspection, `main` at the branch point of this session)

- **`properties` (`property.py`) exists**: `property_type` (`CHECK`'d
  `agricultural|residential|commercial|industrial|other`), a single generic `survey_number`/
  `sub_division_number` pair, `area_value`/`area_unit`, `address_id`, a denormalized `village_id`
  (a documented query-performance trade-off, `docs/CHANGELOG.md`), `registration_number`. No
  `matter_id` — confirmed the current schema does not violate Property/Matter independence in the
  Property→Matter direction (§25 invariant #4). `PropertyOwner` exists as a conventional (real-FK)
  join table to `clients`, carrying `ownership_share`/`ownership_type`/`from_date`/`to_date` — cited
  directly by §24.3 as the working precedent for the eventual Party-ownership relationship, once
  `client_id` is retargeted to Party (`ADR/0023`'s own domain, not decided here).
- **`Land`, `RevenueRecord`, `CitySurveyRecord`, `TP/FP` (any spelling), `PropertyUnit`, `Scheme`,
  and `PropertyRecordReference` do not exist anywhere in `backend/src/app`** — confirmed by a full
  grep of the application source tree. Zero migrations exist for any of them beyond the base
  `properties`/`property_owners` table (`7789f56da7f9_properties_properties_property_owners.py`).
- **A generic, typed, polymorphic reference pattern is already established, working, and documented
  in this codebase** — not a novel idiom this ADR would be introducing. `ActivityLog`
  (`entity_type`+`entity_id`), `AuditLog` (`resource_type`+`resource_id`), `WorkflowHistory`
  (`entity_type`+`entity_id`), `QrCodeRecord` (`entity_type`+`entity_id`), and `AiRequest`
  (`entity_type`+`entity_id`) all use the identical shape — a string discriminator plus a UUID with
  no enforced `ForeignKey`, each with its own composite index. `docs/ERD.md` documents this
  explicitly as a named, deliberate, repository-wide convention ("Polymorphic references (entity_type
  + entity_id, no FK)"), with the trade-off (no DB-level referential integrity on the id column)
  stated openly rather than hidden. One structural nuance is worth naming honestly, not glossed
  over: every existing instance of this pattern is a **fan-in** shape (many different source entity
  types referencing one generic log/history table); the mechanism this ADR needs is the **inverse**
  shape — one specific, known source (`Property`) referencing an extensible set of target record
  types. The referential-integrity trade-off is identical either way; only the direction of the
  "many" side differs, and that difference does not change which mechanism is the better fit — see
  "Options Considered" below.
- **`PropertyOwner` is the contrasting precedent** — a conventional join table with real, enforced
  foreign keys to both sides (`properties.id`, `clients.id`), used because both sides are single,
  fixed, known entity types. This codebase already uses *both* patterns (enforced-FK conventional
  join, and unenforced-FK polymorphic reference) for different, evidenced reasons — this ADR is not
  introducing a first-of-its-kind choice between them; it is picking the one this repository's own
  precedent already matches for the specific shape at hand.
- **"Property Unit" is never given its own §24 entity definition anywhere in the specification** —
  confirmed by a full search. It appears only as: the subject of rule 18's negative constraint
  ("must not be conflated" — a rule about two things staying distinct, not a definition of either
  thing); a candidate table name floated once in §16 (pre-§24 strategic planning, itself flagged
  there as unresolved — "must be specified before deciding whether these are separate tables... or
  another arrangement" — and superseded by §24's more careful, entity-by-entity treatment, which
  never gave it a section); a conditional ("if approved") scope item in an earlier task breakdown;
  and the title of Required ADR #4 itself. §24.4's own `CitySurveyRecord` purpose text — "the City
  Survey system's property-unit **identifier**" — uses "property-unit" descriptively, for what
  `CitySurveyRecord` *is*, not as a label for some other, competing entity. This absence is directly
  load-bearing for this ADR's Decision below.

## Business/Specification Inputs

Frozen (not reopened by this ADR):

- §4 rules 15–17 (Property independent of Matter; multi-Matter participation; shared-Property does
  not imply shared-Matter).
- §4 rule 18 (Land and Property Unit must not be conflated).
- §4 rules 19–24 (Revenue/City-Survey distinctness; Revenue Block/Survey Number belongs to the
  Revenue/Land model; City Survey Number may identify property units and is not another Revenue
  Survey Number; TP/FP independently represented; extensibility required).
- §24.3's already-established Property⟷Matter relationship: many-to-many through `MatterProperty`,
  never direct — the same pattern, and the same already-CBR status, `ADR/0023` already treated
  `MatterParty` as for Party⟷Matter. Not redesigned here, for the identical reason.
- §24.4's explicit assignment of the TP/FP↔Scheme conceptual-boundary question to Required ADR #7,
  not to #6 — this ADR preserves that assignment rather than absorbing it.

Genuinely open, and the actual subject of this ADR's Decision:

- §24.3's Land representation-strategy question (three named candidates).
- The unnamed-but-necessary "Property Unit" representation question Required ADR #4's own title
  requires this ADR to address, given no §24 entity definition exists for it.
- §24.4's Property Record Reference mechanism question (generic linking table vs. direct FKs vs.
  another approach).

Genuinely open, and explicitly **not** decided by this ADR (see "Explicitly Unresolved Items"):

- Exact field sets for `RevenueRecord`, `CitySurveyRecord`, and TP/FP records (Required ADR #5).
- Scheme's own hierarchy-storage mechanism and the TP/FP↔Scheme conceptual boundary (Required ADR
  #7).
- Property↔Scheme relationship's exact cardinality (§24.3's own open item, coupled to #7).
- Property↔Party ownership's exact shape, including `PropertyOwner`'s retargeting from `client_id`
  to Party (§24.3's own open item, coupled to `ADR/0023`).
- Whether a Property can hold more than one reference of the same `record_type` (cardinality detail
  of the mechanism this ADR does decide).
- Subdivision/combination semantics (whether subdividing a Property/Land record creates new
  identities) — not addressed anywhere in the frozen specification; not invented here.

## Definitions / Terminology

- **Property:** the Organization-scoped, Matter-independent master record for a subject of legal
  work (§4 rule 15). After this ADR, Property is confirmed as a **generic** record — it does not
  itself carry Revenue/City-Survey/TP-FP-specific identifying detail; that detail lives in the
  record entities it references.
- **Land:** per this ADR's Decision, **not a separate table** — the business concept "the Revenue-
  oriented land identity" (§24.3) is realized by `RevenueRecord`. Not a new entity; a naming
  clarification of an entity the specification already requires (§24.4).
- **Property Unit:** per this ADR's Decision, **not a separate table** — the business concept named
  in rule 18/21 is realized by `CitySurveyRecord`. Not a new entity; a naming clarification of an
  entity the specification already requires.
- **RevenueRecord:** the Gujarat Revenue-system property reference (Block/Survey Number lineage,
  §24.4). Its exact field set is Required ADR #5's job, not decided here.
- **CitySurveyRecord:** the City Survey system's property-unit identifier (§24.4), distinct from
  Revenue Survey Number (rule 21/22). Exact field set is Required ADR #5's job.
- **TP/FP Record:** the Town Planning / Final Plot reference (§24.4, rule 23). Exact field set and
  its relationship to whatever "Scheme" turns out to mean is Required ADR #5's and #7's job
  respectively, not decided here.
- **PropertyRecordReference:** the new linking entity this ADR establishes, connecting a `Property`
  to zero-or-more rows across the extensible set of record-system entities above.

## Options Considered

### Cluster A — Land / Property-Unit representation strategy (Required ADR #4)

**For Land**, §24.3 itself names three candidates:

1. **Land as its own table that Property references.** Would require Land to hold some
   distinguishing content Property and `RevenueRecord` don't already cover between them — nothing in
   §24.3's or §24.4's text identifies what that content would be; Land's own purpose statement
   ("the Revenue-oriented land identity") describes it entirely in terms of the Revenue system.
   Introducing this table would add an unevidenced extra join layer (`Property → Land →
   RevenueRecord`) with no demonstrated distinct responsibility. **Rejected** — not supported by any
   textual content requiring it, and this task's own governing instruction is not to invent entities
   the specification doesn't establish.
2. **Land as a specialization/subtype of Property** (Land-specific fields living directly on
   `Property` or a Property-subtype extension). Directly disfavored by §24.3's own "Gap vs. frozen
   architecture" note, which states the specification's own **working assumption** is that Property
   becomes generic and *links to* separate record entities, explicitly contrasted with "Property
   itself grows type-specific columns." Making Land a Property subtype would be exactly the
   type-specific-columns-on-Property approach the specification's own text leans away from.
   **Rejected.**
3. **Land folded into `RevenueRecord` directly** — i.e., "Land" is the business/domain name for the
   entity `RevenueRecord` already is at the engineering level; no separate `lands` table exists.
   Directly supported by: rule 20's own phrasing, "Revenue Block/Survey Number belongs to **the
   Revenue/Land model**" (a single, slash-joined model, not two separate models); Land's own purpose
   statement being defined entirely as "Revenue-oriented"; and the Gap note's own three-way
   link-target list for Property (Revenue/City-Survey/TP-FP) never naming Land as a fourth,
   independent target. **Selected.**

**For "Property Unit"** — the specification names no equivalent three-way menu (because, unlike
Land, it never gives Property Unit its own §24 entity treatment at all), so this ADR evaluates the
same structural options by analogy, on the same evidentiary standard:

1. **Property Unit as its own new table, separate from `CitySurveyRecord`.** No §24 text anywhere
   describes what distinct content such a table would hold beyond what `CitySurveyRecord` already
   is described as holding (a City Survey Number, ward/zone linkage). **Rejected** — an unevidenced,
   redundant entity.
2. **Property Unit as a specialization/subtype of Property.** Rejected for the identical Gap-note-
   based reasoning as Land option 2 above.
3. **Property Unit realized by `CitySurveyRecord`** — no separate table; the phrase "property unit"
   in rules 18/21 refers to what a City Survey Number identifies, which is exactly `CitySurveyRecord`'s
   own stated purpose. Directly supported by rule 21's own text — "City Survey Number **may identify
   property units**" — and by §24.4's own descriptive use of "property-unit identifier" for
   `CitySurveyRecord`. **Selected.**

| Criterion | Land: own table | Land: Property subtype | Land = RevenueRecord | Unit: own table | Unit: Property subtype | Unit = CitySurveyRecord |
|---|---|---|---|---|---|---|
| Textual support in §24 | None | Contradicted by Gap note's working assumption | Direct (rule 20 phrasing, purpose text) | None | Contradicted by Gap note | Direct (rule 21 phrasing, CitySurveyRecord purpose) |
| Avoids unevidenced entity invention | No | No | **Yes** | No | No | **Yes** |
| Consistent with Property staying generic (Gap note) | No | No | **Yes** | No | No | **Yes** |
| Schema/query simplicity | Extra join layer | No extra table, but conflates layers | Simplest (no extra layer) | Extra join layer | No extra table, but conflates layers | Simplest |

### Cluster B — Property Record Reference mechanism (Required ADR #6)

1. **Direct foreign keys on `Property`** (e.g. `revenue_record_id`, `city_survey_record_id`,
   `tp_fp_record_id` as nullable FK columns). Strong referential integrity, but **each new record
   system requires a schema migration** (a new nullable FK column) — a materially weaker
   satisfaction of rule 24's extensibility requirement ("must not... block adding a fifth [system]
   later") than a mechanism needing no schema change at all. **Rejected** as the primary mechanism.
2. **A typed, mutually-exclusive-FK link table** (one `property_record_links` table with several
   nullable, real-FK columns — one per record type — plus a `CHECK` constraint ensuring exactly one
   is set per row). Better referential integrity than the generic pattern, but inherits the same
   extensibility weakness as option 1 (a fifth record system still needs a new nullable FK column
   added to this table) while being materially more complex than either alternative. **Rejected** —
   worse trade-off position than both other options, not merely "not selected."
3. **A generic, typed, polymorphic linking table** — `property_record_references`
   (`property_id` FK, `record_type` discriminator string, `record_id` UUID, no enforced `ForeignKey`
   on `record_id` since its target table varies by `record_type`). A new record system is addable by
   inserting rows with a new `record_type` value — **zero schema change required**, the strongest
   available satisfaction of rule 24. Directly matches this codebase's own established, documented,
   five-times-precedented polymorphic-reference convention (`ActivityLog`, `AuditLog`,
   `WorkflowHistory`, `QrCodeRecord`, `AiRequest`), with the identical, already-accepted, already-
   documented referential-integrity trade-off this codebase has made consistently every other time
   this shape was needed. **Selected.**

| Criterion | Direct FKs | Typed mutually-exclusive-FK table | Generic polymorphic table |
|---|---|---|---|
| Referential integrity | Strongest (enforced FK) | Strong (enforced FK, CHECK-guarded) | Weakest (unenforced, app-layer discipline) |
| Extensibility (rule 24) | Weak (new column per system) | Weak (new column per system) | **Strongest (zero schema change)** |
| Repository consistency | No precedent for this exact shape | No precedent | **Direct precedent, 5x, documented** |
| Query complexity | Simple (plain columns) | Simple (plain columns) | Requires `record_type` in every query — matches existing `ActivityLog`/`AuditLog` query pattern already proven in this codebase |
| Implementation complexity | Low | Higher (CHECK constraint, more columns) | Low (matches existing pattern exactly) |
| Auditability | Direct | Direct | Same as `ActivityLog`/`AuditLog`'s own already-audited pattern |

## Decision

### Cluster A — Land and Property Unit

**No separate `Land` or `PropertyUnit` table is created.** "Land" is the business name for
`RevenueRecord`; "Property Unit" is the business name for `CitySurveyRecord`. Rule 18's requirement
that Land and Property Unit "must not be conflated" is satisfied precisely because rule 19 already
independently requires `RevenueRecord` and `CitySurveyRecord` to remain distinct, never-merged
record systems — no separate mechanism is needed to keep "Land" and "Property Unit" apart beyond
keeping the two record types they resolve to apart, which the specification already mandates
regardless of this ADR.

This resolves Required ADR #4 as a **naming/representation clarification**, not as a new pair of
entities: the specification's own text, read carefully, never actually requires two additional
tables beyond the Gujarat-record entities §24.4 already names — it requires that whatever
represents "Land" and whatever represents "Property Unit" stay distinct from each other, a
requirement `RevenueRecord`/`CitySurveyRecord`'s own already-frozen distinctness already satisfies.

### Cluster B — Property Record Reference mechanism (Required ADR #6)

A new `property_record_references` table: `id` (UUID PK), `property_id` (mandatory, real `FOREIGN
KEY` to `properties.id` — the one side of this relationship that is always a single, known type),
`record_type` (a discriminator string — at minimum `revenue_record`, `city_survey_record`, and a
TP/FP-record category per §24.4's own naming, extensible to a future fifth value with no schema
change), `record_id` (UUID, no enforced `ForeignKey` — the target table varies by `record_type`,
matching this codebase's own established polymorphic-reference convention exactly), plus the
standard `AuditMixin` fields every other tenant-scoped table in this codebase already carries. A
composite index on `(property_id, record_type)` (and, separately, on `(record_type, record_id)`),
mirroring `ActivityLog`'s/`AuditLog`'s existing indexing convention for the identical pattern shape.

This resolves Required ADR #6: the mechanism is a generic linking table, not direct FKs on
`Property`, justified by rule 24's extensibility requirement and this codebase's own five-times-
proven precedent for exactly this shape — not selected merely because "flexible" sounds appealing in
the abstract, but because it is the only option among those evaluated that satisfies rule 24 without
a schema change per new record system, and because this repository has already made and documented
this exact trade-off successfully five separate times.

### Cluster C — Property / Matter independence (Required ADR #3)

Not reopened as an independent design question — §4 rule 15's independence is frozen, and
§24.3's `MatterProperty` many-to-many join (mirroring `ADR/0023`'s treatment of `MatterParty`) is
already CBR, not redesigned here. What this ADR *does* resolve, as the "boundary/reference
mechanism" T90's own authorization text asks for: **`Property` stays generic** — after this
decision, no Revenue/City-Survey/TP-FP-specific column is added directly to `Property`; all
record-system-specific detail lives in the linked entities, reached only through
`property_record_references`. `Property`'s own boundary is therefore: the stable, Organization-
scoped, Matter-independent identity anchor that both `MatterProperty` (toward Matter) and
`property_record_references` (toward the Gujarat record systems) attach to — nothing more.

## Detailed Reasoning

The Land and Property-Unit decisions both follow the same evidentiary discipline this task's own
Frozen-Business-Rule Protection instructions require: rather than inventing two new entities because
their names appear in a business rule, this ADR asked what distinguishing content each would
actually hold, found none described anywhere in §24, and found direct textual support (rule 20's
"Revenue/Land model" phrasing; rule 21's "may identify property units" phrasing) for treating them
as the already-required Gujarat-record entities under different names instead. This mirrors
`ADR/0023`'s identical discipline for Party/Client — resolving an identity question by recognizing
what the frozen text already establishes, not by designing a new table because a term exists. The
record-reference mechanism decision follows `ADR/0021`'s and `ADR/0022`'s shared evidentiary
standard: favor the option this repository's own architecture already demonstrates working,
unless a concrete, evidenced gap requires otherwise. No such gap exists here — the polymorphic
reference pattern is not merely "precedented somewhere," it is a named, documented,
`docs/ERD.md`-recorded, five-instance convention this codebase has already committed to for exactly
this class of problem (a fixed source needing to reference an open-ended, extensible set of target
types), and rule 24's extensibility requirement makes the zero-schema-change property of that
pattern a genuine, not merely incidental, advantage over both FK-based alternatives.

## Data-Model Implications

- **`properties` (existing, `Modify`):** unchanged in shape by this ADR beyond what `ADR/0021`
  already requires (mandatory `organization_id`) — no new Revenue/City-Survey/TP-FP columns are
  added to it, consistent with the Gap note's working assumption this ADR adopts.
- **`revenue_records` (new):** realizes "Land." Its own field list is Required ADR #5's job; this
  ADR fixes only that it is the entity `property_record_references` rows of `record_type =
  'revenue_record'` point to.
- **`city_survey_records` (new):** realizes "Property Unit." Same scoping as above.
- **`tp_records`/`fp_records` (new):** whether TP and FP end up as one combined table or two related
  tables is a Required ADR #5-level structural detail this ADR does not decide — the `record_type`
  discriminator accommodates either shape (one value or two) without requiring this ADR to choose.
- **`property_record_references` (new):** the mechanism itself, per "Decision" above.
- **No `lands` or `property_units`/`PropertyUnit` table is created.**
- **`PropertyOwner` (existing):** unchanged by this ADR. Its eventual retargeting from `client_id`
  to a Party reference remains §24.3's own disclosed open item, coupled to `ADR/0023`, not decided
  here.

## API / Query Implications

- Property is exposed as **one resource**; its Revenue/City-Survey/TP-FP-linked detail is reached
  through `property_record_references`, not through type-specific Property sub-resources — avoiding
  the same permission-surface-fragmentation risk `ADR/0023` named for Party subtypes (see
  "Relationship to ADR-0022" below).
- Querying a Property's full record-reference set requires filtering
  `property_record_references` by `property_id` (and, to resolve a specific reference, joining
  against whichever table `record_type` names) — the identical query shape this codebase's existing
  `ActivityLog`/`AuditLog` consumers already use for their own polymorphic lookups, so no new query
  pattern is introduced.
- The existing `SearchQuery`/`FilterSpec` generic-repository framework applies to `Property`'s own
  fields (`survey_number`, `registration_number`, `village_id`) unchanged; searching *across*
  record-reference detail (e.g. "find the Property with Revenue Survey Number X") is a query-layer
  capability this ADR does not design — flagged as a real future need, not invented here.

## Tenant-Isolation Composition (ADR-0021)

`ADR/0021` is not modified, reopened, or reinterpreted. Every table this ADR's decision implies —
`revenue_records`, `city_survey_records`, `tp_records`/`fp_records`, and
`property_record_references` itself — is tenant-scoped and requires a mandatory `organization_id`
column under `ADR/0021`'s already-decided rule, enforced by the same two independent layers
`ADR/0021` established (mandatory application-layer scoping, `FORCE`d default-deny RLS backstop).
Stated explicitly, because it is easy to miss for a linking table specifically: **`property_record_references`
must carry its own `organization_id`**, not merely inherit tenant scope by joining to `properties` —
`ADR/0021`'s own requirement is that tenant scope be an explicit, independently-enforceable value on
every tenant-scoped table, not implicitly derived through a join, so that the RLS backstop applies
to the linking table directly and does not depend on a correct join always being present in every
query that touches it.

## Authorization Composition (ADR-0022)

`ADR/0022` is not modified, reopened, or reinterpreted. Property and its linked record entities are
governed by `ADR/0022`'s existing resource+action permission model — the seeded permission set
already includes `properties:read`/`properties:write`/`properties:delete` (confirmed existing,
seeded infrastructure this ADR's entities plug into, not new). Consistent with `ADR/0023`'s
identical reasoning for Party subtypes: `revenue_records`, `city_survey_records`, and TP/FP records
are accessed only *through* Property (they are Property's own linked detail, not independently
user-facing top-level resources), so they are governed by the same `properties:*` permission codes
as Property itself — not fragmented into per-record-type permission codes, which would risk the
same permission-surface drift `ADR/0022`'s resource+action model is designed to avoid. If a future
decision ever needs record-type-specific authorization (e.g. a Revenue-record-specific permission
distinct from City-Survey), that is a new decision for whoever authorizes it, not implied here.

## Relationship to ADR-0023 — Party vs Client

`ADR/0023` is not modified, reopened, or reinterpreted. The only touchpoint between the two domains
is `PropertyOwner`, already cited by §24.3 as the precedent for Property↔Party ownership once
`client_id` is retargeted to Party — that retargeting is **not** decided by this ADR; it remains
§24.3's own disclosed open item ("Property ⟷ Party ownership is ED in exact shape"), coupled to
`ADR/0023`'s own domain, and is left exactly as open as it was before this ADR.

## Consequences

- `Property`, `RevenueRecord`, `CitySurveyRecord`, and TP/FP records can each be created with a
  shape directly informed by this decision once a future implementation task is authorized — this
  ADR itself creates no schema.
- Required ADR #5, once authorized, has a fixed, stable interface to populate: the `record_type`
  discriminator's value set and each target table's mere existence (with its own UUID PK) — #5 need
  only decide each table's internal field list, not whether it exists or how Property reaches it.
- Required ADR #7, once authorized, is unaffected by this ADR's TP/FP-record treatment: TP/FP
  Record is simply one more `record_type` value in `property_record_references`, regardless of what
  #7 eventually decides "Scheme" conceptually is or whether a TP Scheme counts as this
  specification's Scheme.
- The `village_id`/`survey_number` denormalization already on `properties` is unaffected —
  `properties`'s own existing fields are not restructured by this ADR, only left generic (no new
  record-system columns added to it).

## Trade-offs

- **No DB-level referential integrity on `property_record_references.record_id`** — the same
  accepted trade-off this codebase has already made, and documented, five separate times. Correct
  `record_type`↔`record_id` pairing becomes an application-layer discipline requirement, not a
  database-enforced one — named explicitly, not hidden, matching `docs/ERD.md`'s own existing
  disclosure for the identical pattern elsewhere.
- **Resolving "Land" and "Property Unit" as names for already-required entities, rather than as new
  tables, is a stronger textual-interpretation claim than a from-scratch design would be** — this
  ADR names the specific rule text (20, 21) and the Gap note's working assumption supporting it, but
  a future architect revisiting this decision should re-verify that reading against the frozen text
  directly, not merely cite this ADR's conclusion.
- **A fifth (or later) record system is addable with zero schema change**, the direct benefit of the
  generic-linking-table choice — but every query touching `property_record_references` must
  correctly filter by `record_type`, a discipline requirement rather than a structural guarantee,
  matching the exact trade-off already accepted for `ActivityLog`/`AuditLog`/`WorkflowHistory`.
- **`property_record_references` requires its own `organization_id`** (see "Tenant-Isolation
  Composition"), a real, additional column this ADR's mechanism requires beyond what a purely
  join-derived approach might have assumed sufficient — named explicitly rather than left implicit.

## Migration Implications

No migration is created by this ADR. Architecturally: `properties` is not restructured — no
Revenue/City-Survey/TP-FP columns are added to or removed from it, so no data migration of existing
`properties` rows is implied by this decision specifically. The new tables
(`revenue_records`/`city_survey_records`/`tp_records`/`fp_records`/`property_record_references`)
are net-new, requiring no backfill from existing data (none of the source data — Revenue Survey
Numbers, City Survey Numbers, TP/FP references — exists in the current schema to migrate from,
confirmed: `properties.survey_number` is the only, generic, insufficient current analogue). Whether
existing `properties.survey_number` values should be backfilled into a `revenue_records` row per
existing Property, and the sequencing of that backfill, is Required ADR #20's (general migration
strategy) job, not decided here.

## Testing / Verification Obligations

Named here as obligations for whichever future implementation task carries this decision out — not
performed by this ADR, mirroring `ADR/0021`/`ADR/0022`/`ADR/0023`'s identical convention:

- A test proving a `property_record_references` row's `organization_id` matches its `property_id`'s
  own `organization_id` — the concrete regression test for this ADR's tenant-isolation composition
  requirement.
- A test proving a new `record_type` value can be introduced (e.g. a future fifth system) without
  any schema migration — the concrete regression test for rule 24's extensibility requirement.
- A test proving `RevenueRecord`/`CitySurveyRecord` remain genuinely distinct, never-merged tables —
  the concrete regression test realizing rule 18/19 through this ADR's Land/Property-Unit resolution.
- A test proving `Property` itself gains no Revenue/City-Survey/TP-FP-specific column — a structural
  guard against a future implementer silently reverting to the type-specific-columns-on-Property
  approach this ADR rejected.

## Dependencies / Other Unresolved Related ADRs

- **#1 Organization as tenant boundary** — already resolved by `ADR/0021`.
- **#2 Party vs Client** — already resolved by `ADR/0023`.
- **#3 Property vs Matter independence** — resolved by this ADR, as the boundary/reference
  mechanism (independence itself was already frozen).
- **#4 Land vs Property Unit** — resolved by this ADR: both realized by already-required Gujarat-
  record entities, no new tables.
- **#5 Revenue vs City Survey** — **assessed, not resolved.** See "Relationship to Required ADR #5"
  below.
- **#6 Property Record Reference architecture** — resolved by this ADR: generic polymorphic linking
  table.
- **#7 Flexible Scheme hierarchy** — **assessed, not resolved.** See "Relationship to Required ADR
  #7" below.
- **#18 Authorization architecture** — already resolved by `ADR/0022`.
- **#19 Tenant isolation enforcement** — already resolved by `ADR/0021`.
- **#8–#17, #20** — untouched.

## Relationship to Required ADR #5 — Revenue / City Survey / TP-FP Representation

**Can #3/#4/#6 be resolved without prematurely deciding #5? Yes.** This ADR's decisions — that
`RevenueRecord` and `CitySurveyRecord` realize "Land"/"Property Unit" respectively, and that
`Property` reaches them (and TP/FP records) through a generic `property_record_references` table —
require knowing only that these entities **exist**, are **distinct**, and each have a **stable UUID
identity** to be referenced by. None of this ADR's reasoning depended on knowing `RevenueRecord`'s or
`CitySurveyRecord`'s actual column list, their validation rules, or their exact relationship to
`Land`/`Address`/`geography.py` beyond what §24.4 already states at the concept level. The stable
abstraction/interface #5 will populate is exactly: the `record_type` discriminator's defined value
set (at minimum `revenue_record`, `city_survey_record`, and a TP/FP category), and each named
target table's bare existence with a UUID primary key — #5's job is to decide each table's internal
field list, format-validation rules, and any additional relationships (e.g. to `geography.py`'s
village/taluka/district hierarchy), none of which this ADR constrains or presupposes. What
deliberately remains unresolved for #5 to decide: the exact field sets themselves; whether TP and FP
are one table or two; and any record-type-specific validation or search requirements beyond what
`property_record_references`'s generic mechanism already provides.

## Relationship to Required ADR #7 — Scheme Hierarchy / TP-FP↔Scheme Boundary

**Do Cluster A/B's decisions require any decision about Scheme? No.** TP/FP Record is treated by
this ADR as simply one more `record_type` value in `property_record_references` — its internal
relationship to whatever "Scheme" conceptually turns out to be (per §24.4's own explicit assignment
of that exact boundary question to Required ADR #7, not to #6) is entirely orthogonal to the
mechanism decided here. Nothing in this ADR requires knowing whether a Town Planning Scheme *is*
this specification's Scheme, a TP/FP-Record-only concept, or both — the record-reference mechanism
works identically regardless of that answer. §24.3's own separately-flagged "Property↔Scheme
relationship" open item (plausible but not frozen as required) is likewise left exactly as open as
before — this ADR neither assumes nor forecloses a direct `Property`↔`Scheme` relationship; if one
is ever needed, it would most plausibly be represented as a further `record_type`-like reference or
a dedicated join, a decision for whichever future ADR resolves #7 and the Property↔Scheme question
together, not invented here.

## Future Impact

- Required ADR #5, once authorized, populates the field-level detail of `revenue_records`,
  `city_survey_records`, and TP/FP records — the interface this ADR fixes for it (existence,
  distinctness, UUID identity, `record_type` discriminator values) does not need to change.
- Required ADR #7, once authorized, decides Scheme's own structure and the TP/FP↔Scheme boundary
  without needing to revisit this ADR's Property-side mechanism.
- Required ADR #20 (migration strategy) inherits the disclosed `properties.survey_number`→
  `revenue_records` backfill-sequencing question named above.
- `ADR/0023`'s own domain inherits the disclosed `PropertyOwner.client_id`→Party-reference
  retargeting question, unaffected by and unresolved by this ADR.
- If a future record system is added, it requires only a new target table and a new `record_type`
  value — no change to `Property`, `property_record_references`'s schema, or this ADR's decision.
- If cardinality evidence later shows a Property genuinely needs more than one reference of the same
  `record_type` (e.g. a subdivided Property with two Revenue Survey Numbers), that is a data-level
  question this ADR's mechanism already accommodates (nothing here assumes uniqueness per
  `record_type`) — but the business semantics of *why* that would happen (subdivision) remain
  unresolved, per "Explicitly Unresolved Items."

## Explicitly Unresolved Items

After this ADR, the Required ADR status is:

- **Required ADR #1** — already resolved by `ADR/0021`. Not reopened.
- **Required ADR #2** — already resolved by `ADR/0023`. Not reopened.
- **Required ADR #3** — **resolved by this ADR**, as the boundary/reference mechanism; independence
  itself remains the pre-existing frozen rule 15, not this ADR's decision.
- **Required ADR #4** — **resolved by this ADR**: Land and Property Unit are realized by
  `RevenueRecord` and `CitySurveyRecord` respectively; no separate tables. Exact field sets for
  either remain #5's job, not decided here.
- **Required ADR #5** — **not resolved; assessed only.** Genuinely separable from #3/#4/#6, per the
  dependency assessment above. Remains fully open.
- **Required ADR #6** — **resolved by this ADR**: a generic, typed, polymorphic linking table,
  `property_record_references`, following this codebase's own established convention.
- **Required ADR #7** — **not resolved; assessed only.** Genuinely separable from #3/#4/#6, per the
  dependency assessment above. Remains fully open, including the TP/FP↔Scheme conceptual boundary
  question §24.4 explicitly assigns to it.
- **Required ADR #18, #19** — already resolved by `ADR/0022`/`ADR/0021`. Not reopened.
- **Required ADR #8–#17, #20** — remain fully unresolved. Nothing in this ADR decides, narrows, or
  implies a position on any of them beyond the disclosed migration-sequencing dependency (#20) named
  above.

Also explicitly unresolved, named rather than silently decided: whether a Property can hold multiple
`property_record_references` rows of the same `record_type`; subdivision/combination identity
semantics; Property↔Scheme's exact cardinality; `PropertyOwner`'s retargeting to Party; and any
record-type-specific search/query capability beyond what the generic mechanism provides.

No Required ADR other than #3, #4, and #6 is resolved, reinterpreted, or narrowed by this document.
`ADR/0021`, `ADR/0022`, and `ADR/0023` are not modified, reopened, or reinterpreted by this
document. No §4 business rule and no part of §23's frozen concept list is changed, invented, or
silently altered by this document.
