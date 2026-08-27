# ADR-0025: Revenue / City-Survey / TP-FP Record Field Architecture

**Status:** Proposed
**Date:** 2026-08-27

**Resolves:** `docs/Legal_DMS — Domain Model & Functional Specification.md` §21 planning-list item
**#5** ("Revenue vs City Survey" — read, per §26 item 5's own fuller framing, as "Revenue/City-
Survey/TP-FP exact field sets").

**Explicitly not resolved:** Required ADR #7 ("Flexible Scheme hierarchy," including the TP/FP↔
Scheme conceptual boundary §24.4 itself assigns there) and Required ADR #6 (the
`property_record_references` linking mechanism — already resolved by `ADR/0024`, not reopened
here). See "Explicit #7 Deferral" below — this section exists specifically because T91's own
authorization names the #5↔#7 boundary as a QA watch item.

**Does not resolve:** Required ADR #1, #2, #3, #4, #18, or #19 (already resolved by `ADR/0021`/
`ADR/0023`/`ADR/0024`/`ADR/0022`/`ADR/0021` respectively, not reopened here) or Required ADR #8–
#17/#20 (untouched).

**Dependencies:** `ADR/0021` (tenant isolation — every table this ADR names is Organization-scoped,
composed with, not reopened). `ADR/0022` (authorization — governed by the existing `properties:*`
permission codes, per `ADR/0024`'s own reasoning, composed with, not reopened). `ADR/0024` (Property/
Land/Property-Unit boundary and the `property_record_references` mechanism this ADR's entities
populate — frozen, not reopened).

## Context

`ADR/0024` decided that "Land" and "Property Unit" are realized by `RevenueRecord` and
`CitySurveyRecord` respectively (not separate tables), and that `Property` reaches these — plus a
TP/FP record category — through a generic, typed `property_record_references` linking table
(`property_id`, `record_type`, `record_id`). What `ADR/0024` deliberately left open, because it
required only that these entities *exist* with a *stable UUID identity*, is what fields each entity
actually carries. §12 and §26 (item 5) both classify "Revenue/City-Survey/TP-FP exact field sets" as
blocking correct schema design — this ADR resolves that.

The governed specification is unusually sparse at the field level for this cluster, and this ADR
treats that sparseness honestly rather than filling it with invented detail. §24.4's RevenueRecord,
CitySurveyRecord, and TP/FP Record blocks are each explicitly labeled `**Fields (ED — unresolved)**`
— the specification states the field lists below only as **candidates**, not as frozen requirements,
and this ADR's job is to turn those candidates into an actual architectural decision, not to invent
beyond them.

### Repository baseline (direct inspection)

- **No `RevenueRecord`, `CitySurveyRecord`, `TP/FP` (any spelling), `ward`, or `zone` implementation
  exists anywhere in `backend/src/app`** — confirmed by a full grep. No migration creates any of
  these tables — confirmed by inspecting all 14 files in `backend/alembic/versions/`.
- **`properties.survey_number`/`sub_division_number`** are today's only, generic, insufficient
  analogue: `String(50)`, no `CHECK` constraint, no format validation of any kind. `survey_number`
  is non-nullable and indexed; `sub_division_number` is nullable, unindexed.
- **A complete, working geography hierarchy already exists**: `geography.py`'s
  `Country → State → District → Taluka → Village` chain (`countries`, `states`, `districts`,
  `talukas`, `villages`), each level FK'd to its parent, each with a `UniqueConstraint` on
  `(parent_id, name)`. This hierarchy carries **no `organization_id`, no `AuditMixin`** — it is
  global, Organization-agnostic reference/lookup data (matching this codebase's treatment of
  `matter_types`/`document_types` elsewhere), not tenant-scoped business data.
- **`Property.village_id`** already FKs into this hierarchy today (nullable, indexed) — confirming
  the pattern this ADR extends to `RevenueRecord` is already proven, working code, not a new idiom.
- **A working format-validation precedent exists**: `Client.pan_number`/`aadhaar_number`, each a
  nullable `String` column with a Postgres regex `CHECK` constraint (`pan_number_format`,
  `aadhaar_number_format`), documented in `docs/ERD.md`'s `ck_<table>_<name>` naming convention.
  **The specification itself never extends this precedent to Gujarat property identifiers** — that
  analogy, where this ADR draws it, is this ADR's own architectural inference from repository
  precedent, not a specification requirement, and this ADR is careful throughout not to
  misattribute it.
- **No format/regex/length/leading-zero/case rule is specified anywhere in the governed
  specification** for Revenue Survey Number, City Survey Number, TP scheme number, or FP number —
  confirmed by an exhaustive search. This absence is treated as a genuine gap to disclose, not an
  invitation to invent official-looking rules.

## Decision

Four new tables — `revenue_records`, `city_survey_records`, `tp_records`, `fp_records` — each
carrying the specification's own named candidate fields (§24.4), plus the architecturally-necessary
identity/tenant/audit scaffolding every tenant-scoped table in this codebase already carries, plus
nullable geography linkage for `revenue_records` specifically (direct reuse of the existing
`geography.py` hierarchy, per §24.4's own RC/IC-labeled suggestion). No format validation is decided
for any Gujarat-specific identifier field, because none is specified in the governed text — this is
disclosed as an open gap, not filled by invention. TP and FP remain two separate tables, matching
§24.4's own explicit `tp_records`/`fp_records` naming, not merged into one. Neither table gains any
structural relationship to a `Scheme` entity — TP/FP's own scheme-number field is a plain, unlinked
string, and the question of whether/how it should ever become a real relationship is left entirely
to Required ADR #7, per "Explicit #7 Deferral" below.

## Scope

**In scope (T91's authorized decision surface):** field-level architecture for `RevenueRecord`,
`CitySurveyRecord`, and TP/FP records; identity and tenant-boundary representation; whatever
validation the specification actually justifies; geography linkage where the specification suggests
it; population of `ADR/0024`'s `record_type` discriminator value set.

**Out of scope (explicitly not decided here):** the `property_record_references` mechanism itself
(`ADR/0024`, frozen); Scheme's own architecture and the TP/FP↔Scheme conceptual boundary (Required
ADR #7); Property↔Scheme cardinality (§24.3's own open item, coupled to #7); migration/backfill
mechanics (Required ADR #20); any decision already frozen by `ADR/0021`–`ADR/0024`; any Required ADR
#8–#17.

## Specification Evidence

§4 rules 19–24, verbatim:

> 19. Revenue and City Survey are distinct record systems.
> 20. Revenue Block/Survey Number belongs to the Revenue/Land model.
> 21. City Survey Number may identify property units.
> 22. City Survey Number is not merely another Revenue Survey Number.
> 23. TP/FP is independently represented.
> 24. Other property-record systems must remain extensible.

§24.4's field-level candidates, verbatim and in full — the entirety of what the governed
specification says at the field level for this cluster:

> **RevenueRecord** Fields (ED — unresolved): "the exact Revenue-record field set (7/12 extract
> fields, Block Number, Survey Number, Sub-division, village/taluka/district linkage — the existing
> `geography.py` hierarchy is directly reusable, RC/IC) is not specified in the frozen architecture
> at the field level; only the *concept's* existence and independence from City Survey is frozen."
>
> **CitySurveyRecord** Fields (ED — unresolved): "City Survey Number, ward/zone linkage, and its
> relationship to a Property/Property-Unit are not specified at the field level."
>
> **TP/FP Record** Fields (ED — unresolved): "TP scheme number, FP number, and their relationship
> to Property/Scheme are not specified at the field level."

"7/12 extract fields" appears exactly once in the entire specification, as an unexplained
parenthetical example — this ADR does not invent what a "7/12 extract" contains; it is named below
as a deliberately deferred future field group, not designed here.

§27's "Dependency ordering coherence" self-check, verbatim — the direct textual basis for this ADR
proceeding without #7:

> "§24's group ordering... matches the dependency order given for this task and is internally
> consistent: no group's specification depends on an entity from a *later* group... where a later
> concept is mentioned, as with the Party/Property/Scheme overlap notes, it is flagged as context,
> not depended upon."

The "Party/Property/Scheme overlap notes" this passage refers to directly includes §24.4's own
TP/FP↔Scheme note — the specification itself classifies that mention as non-blocking context, the
same conclusion T91's authorization and this ADR both reach independently.

## Entity / Field Architecture

Field-classification discipline, applied to every field below:

| Column | Meaning |
|---|---|
| **Required?** | Whether the field is non-nullable in this ADR's decision |
| **Source** | Specification / Existing ADR / Repository convention / Necessary architectural representation / Deferred |
| **Deferred?** | Whether this ADR declines to decide the field's content, format, or existence |

### RevenueRecord

| Entity | Field | Required? | Source | Purpose | Type/representation | Validation | Deferred? |
|---|---|---|---|---|---|---|---|
| RevenueRecord | `id` | Yes | Necessary architectural representation (`ADR/0024`'s stable-UUID-identity requirement) | Stable system identity | UUID | PK | No |
| RevenueRecord | `organization_id` | Yes | Existing ADR (`ADR/0021`) | Tenant scope | UUID, FK to `organizations.id` | Mandatory, RLS-backed per `ADR/0021` | No |
| RevenueRecord | `block_number` | No | Specification (§24.4, ED-labeled candidate) | Revenue Block Number | String, length TBD | None specified in spec — not invented here | Format: yes |
| RevenueRecord | `survey_number` | Yes | Specification (§24.4, ED-labeled candidate) | Revenue Survey Number — this record's defining identifier | String (never numeric — see "Validation Rules") | None specified in spec — not invented here | Format: yes |
| RevenueRecord | `sub_division_number` | No | Specification (§24.4, ED-labeled candidate) | Sub-division of the Survey Number | String | None specified — not invented here | Format: yes |
| RevenueRecord | `village_id` | No | Specification (§24.4, RC/IC-labeled suggestion) + Repository convention (`geography.py` reuse, `Property.village_id` precedent) | Geographic linkage | UUID, FK to `villages.id` | FK integrity only | No (mechanism decided; population/backfill is #20's job) |
| RevenueRecord | `taluka_id` | No | Same as `village_id` | Geographic linkage | UUID, FK to `talukas.id` | FK integrity only | No |
| RevenueRecord | `district_id` | No | Same as `village_id` | Geographic linkage | UUID, FK to `districts.id` | FK integrity only | No |
| RevenueRecord | "7/12 extract fields" | — | Specification (named, undefined) | Unknown — spec names the term once, never elaborates | Not designed | Not designed | **Yes — entirely deferred, no column created** |
| RevenueRecord | Audit fields (`created_at`/`updated_at`/etc.) | Yes | Repository convention (`AuditMixin`, universal) | Audit trail, §4 rule 42 | Per `AuditMixin` | Standard | No |
| RevenueRecord | Optimistic-lock version | Yes | Repository convention (`OptimisticLockMixin`, matches `Property`'s own treatment) | Concurrency safety | Per `OptimisticLockMixin` | Standard | No |

**Why `village_id`/`taluka_id`/`district_id` are separate FKs rather than a single denormalized
string:** matches the existing, working `Property.village_id` pattern exactly, keeps each level
independently queryable/indexable, and reuses infrastructure the specification itself names as
"directly reusable" for this exact purpose — see "Alternatives Considered" for the rejected
denormalized and hybrid options.

### CitySurveyRecord

| Entity | Field | Required? | Source | Purpose | Type/representation | Validation | Deferred? |
|---|---|---|---|---|---|---|---|
| CitySurveyRecord | `id` | Yes | Necessary architectural representation | Stable system identity | UUID | PK | No |
| CitySurveyRecord | `organization_id` | Yes | Existing ADR (`ADR/0021`) | Tenant scope | UUID, FK | Mandatory, RLS-backed | No |
| CitySurveyRecord | `city_survey_number` | Yes | Specification (§24.4, ED-labeled candidate) | City Survey Number — this record's defining identifier, distinct from Revenue Survey Number per §4 rule 22 | String (never numeric) | None specified — not invented here | Format: yes |
| CitySurveyRecord | `ward` | No | Specification (§24.4, ED-labeled candidate) | Ward linkage | String, plain field | None specified | Whether this should become a lookup entity (like `Village`): **yes, deferred** — no evidence justifies inventing a `Ward` table |
| CitySurveyRecord | `zone` | No | Specification (§24.4, ED-labeled candidate) | Zone linkage | String, plain field | None specified | Same as `ward` — deferred |
| CitySurveyRecord | Audit fields | Yes | Repository convention | Audit trail | Per `AuditMixin` | Standard | No |
| CitySurveyRecord | Optimistic-lock version | Yes | Repository convention | Concurrency safety | Per `OptimisticLockMixin` | Standard | No |

**Why `ward`/`zone` are plain strings, not FKs into a new lookup hierarchy**, unlike
`RevenueRecord`'s village/taluka/district treatment: the specification's own CitySurveyRecord field
bullet never mentions `geography.py` reuse (confirmed by direct comparison — RevenueRecord's bullet
does, CitySurveyRecord's does not), and `geography.py`'s existing hierarchy stops at `Village` —
it does not model urban wards or zones at all. Inventing a `Ward`/`Zone` lookup hierarchy with no
textual or repository basis would violate this task's own instruction against inventing domain
infrastructure the specification doesn't establish. Plain strings are the more conservative,
better-evidenced choice; whether ward/zone later deserve their own lookup entities is named
explicitly as a deferred question, not silently foreclosed.

### TP Record and FP Record

Kept as **two separate tables**, matching §24.4's own explicit repository-mapping text
("`tp_records`/`fp_records`" — two distinct plural table names, not one), not merged into a single
combined table.

| Entity | Field | Required? | Source | Purpose | Type/representation | Validation | Deferred? |
|---|---|---|---|---|---|---|---|
| TPRecord | `id` | Yes | Necessary architectural representation | Stable system identity | UUID | PK | No |
| TPRecord | `organization_id` | Yes | Existing ADR (`ADR/0021`) | Tenant scope | UUID, FK | Mandatory, RLS-backed | No |
| TPRecord | `tp_scheme_number` | Yes | Specification (§24.4, ED-labeled candidate) | Town Planning scheme number, as a plain identifying value — **not** a structural relationship to any Scheme entity, see "Explicit #7 Deferral" | String (never numeric) | None specified | Format: yes; architectural meaning of the value: deferred to #7 |
| TPRecord | Audit fields | Yes | Repository convention | Audit trail | Per `AuditMixin` | Standard | No |
| TPRecord | Optimistic-lock version | Yes | Repository convention | Concurrency safety | Per `OptimisticLockMixin` | Standard | No |
| FPRecord | `id` | Yes | Necessary architectural representation | Stable system identity | UUID | PK | No |
| FPRecord | `organization_id` | Yes | Existing ADR (`ADR/0021`) | Tenant scope | UUID, FK | Mandatory, RLS-backed | No |
| FPRecord | `fp_number` | Yes | Specification (§24.4, ED-labeled candidate) | Final Plot number | String (never numeric) | None specified | Format: yes |
| FPRecord | Audit fields | Yes | Repository convention | Audit trail | Per `AuditMixin` | Standard | No |
| FPRecord | Optimistic-lock version | Yes | Repository convention | Concurrency safety | Per `OptimisticLockMixin` | Standard | No |

Neither `TPRecord` nor `FPRecord` gains a `scheme_id` foreign key or any other structural link to a
`Scheme` table — see "Explicit #7 Deferral."

## Identity and Tenant Boundary

Every table this ADR decides has a UUID primary key as its sole system identity — matching this
codebase's universal convention and `ADR/0024`'s own "stable UUID identity" requirement for
`property_record_references`'s targets. Business identifiers (Survey Number, City Survey Number, TP
scheme number, FP number) are **never** used as primary keys — they are searchable, human-facing
values, following the identical principle `ADR/0023` already established for Party ("no natural key...
is sufficiently universal or stable to serve as identity"), extended here to Gujarat property
identifiers for the same reason: none of them is guaranteed globally unique or immutable enough to
serve as a system identity.

Every table this ADR decides carries a mandatory `organization_id`, per `ADR/0021`'s already-decided
rule — application-layer scoping as the primary mechanism, `FORCE`d default-deny RLS as the backstop.
This is not a new requirement this ADR invents; it is `ADR/0024`'s own explicit requirement ("every
new table this ADR implies... requires mandatory `organization_id`") now applied to the four
concretely-named tables. `geography.py`'s hierarchy (`villages`/`talukas`/`districts`) is correctly
**not** given an `organization_id` by this ADR — it remains global, Organization-agnostic reference
data, exactly as it already is today; a `RevenueRecord`'s FK into that hierarchy does not create any
cross-tenant data-leak risk, since the referenced geography rows carry no Organization-specific
content.

## Validation Rules

**No format (regex/length/leading-zero/case) rule is decided for any Gujarat-specific identifier
field** — Block Number, Survey Number, Sub-division, City Survey Number, TP scheme number, FP
number — because none is specified anywhere in the governed text, confirmed by exhaustive search.
This is a disclosed gap, not an implementation detail glossed over. If and when an official format
specification becomes available, the architecturally-correct mechanism to apply it is the one this
codebase already uses successfully for `Client.pan_number`/`aadhaar_number`: a Postgres regex `CHECK`
constraint following the `ck_<table>_<name>` naming convention — named here as the mechanism a
future task should reach for, not as a constraint this ADR itself defines.

Two validation-adjacent decisions **are** made, on architectural (not business-rule) grounds:

- **Every business-identifier field is a `String` column, never a numeric type.** Gujarat
  administrative identifiers commonly carry significant leading zeros and non-numeric characters;
  storing them as a numeric type would silently corrupt data on the first leading-zero value. This
  is a data-integrity decision this ADR is authorized to make (necessary architectural
  representation), not a business rule.
- **Each record's own defining identifier is required (`NOT NULL`)** — `RevenueRecord.survey_number`,
  `CitySurveyRecord.city_survey_number`, `TPRecord.tp_scheme_number`, `FPRecord.fp_number` — because
  a record with no identifying value at all would not serve the purpose §24.4 defines for it.
  Auxiliary fields (`block_number`, `sub_division_number`, `ward`, `zone`) remain nullable, matching
  `Property.sub_division_number`'s own existing nullable precedent, since the specification does not
  establish these as universally present on every record.

Explicitly left open, not decided here: whitespace-trimming/normalization; case-sensitivity;
uniqueness (per-Organization or otherwise) of any business identifier — a Revenue Survey Number
recurring across sub-divisions of the same base survey is a realistic, unaddressed possibility this
ADR does not foreclose by adding an unjustified uniqueness constraint.

## Property Record Reference Integration

This ADR populates, without redesigning, `ADR/0024`'s `record_type` discriminator: four values —
`revenue_record`, `city_survey_record`, `tp_record`, `fp_record` — one per table this ADR decides,
each `property_record_references.record_id` row pointing at the corresponding table's UUID PK with
no enforced `ForeignKey` (matching `ADR/0024`'s own polymorphic-reference mechanism exactly). No
change to `property_record_references`'s own shape, columns, or `organization_id` requirement is
made or implied — that mechanism remains exactly as `ADR/0024` decided it. Whether a `Property` may
hold more than one `property_record_references` row of the same `record_type` remains `ADR/0024`'s
own already-disclosed open cardinality question, not reopened or narrowed here.

## Repository Conventions

Direct precedent cited and followed, not invented:

- **UUID PK + `AuditMixin` + `OptimisticLockMixin`**: the exact shape `Property` itself already
  uses — followed identically for consistency across the same domain cluster.
- **Regex `CHECK`-constraint format validation**: `Client.pan_number`/`aadhaar_number`'s precedent,
  named as the mechanism a future format decision should use — not applied here, since no format
  rule exists to enforce yet.
- **Geography-hierarchy FK reuse**: `Property.village_id`'s existing, working precedent, extended to
  `RevenueRecord` per the specification's own suggestion; explicitly **not** extended to
  `CitySurveyRecord`'s ward/zone, for which no equivalent repository infrastructure exists.
- **Polymorphic reference discriminator values**: consistent with `ADR/0024`'s own adoption of this
  codebase's `entity_type`/`entity_id`-style convention (`ActivityLog`, `AuditLog`, `WorkflowHistory`,
  `QrCodeRecord`, `AiRequest`) — this ADR's four `record_type` values are the concrete population of
  that already-decided mechanism.
- **`ck_<table>_<name>` CHECK-constraint naming**, per `docs/ERD.md` — named as the convention any
  future format-validation constraint on these tables should follow.

No repository precedent exists for ward/zone geographic modeling, for TP/FP structure, or for any
Gujarat-identifier format — stated explicitly rather than assumed.

## Alternatives Considered

### RevenueRecord geography linkage

1. **Fully embedded geographic hierarchy** (village/taluka/district names stored as plain strings
   directly on `RevenueRecord`, no FK). Simpler, no join required — but discards the existing,
   working, spec-endorsed `geography.py` hierarchy entirely, reintroducing free-text geography data
   this codebase has already normalized once. **Rejected.**
2. **Normalized FK references to `geography.py`** (`village_id`/`taluka_id`/`district_id`, this
   ADR's selection). Matches the existing `Property.village_id` precedent exactly and the
   specification's own "directly reusable" suggestion.
3. **Hybrid** (FK plus a denormalized display string, mirroring `Property`'s own
   `village_id`-denormalized-for-search-performance trade-off). A reasonable future optimization if
   search-performance evidence justifies it, but no such evidence exists yet for `RevenueRecord`
   specifically — `Property`'s own denormalization was a documented, deliberate trade-off for a
   proven query pattern, not a default to copy without justification. **Not selected now**; named as
   a legitimate future option if query-performance evidence later warrants it.

| Criterion | Embedded strings | Normalized FK | Hybrid |
|---|---|---|---|
| Spec fidelity | Low (discards the reuse suggestion) | **High** | High |
| Referential integrity | None | **Enforced** | Enforced |
| Repository consistency | None | **Direct precedent** | Partial precedent |
| Query simplicity | Simple (no join) | Requires join | Simple + join available |
| Implementation complexity | Low | **Low** | Higher |

### City Survey ward/zone representation

1. **Plain string fields** (this ADR's selection) — no repository or specification basis for
   anything more structured.
2. **Ward/Zone as new lookup entities**, mirroring `Village`. Rejected — no evidence anywhere (spec
   or repository) that wards/zones need normalization, shared referencing, or hierarchy; inventing
   this would be exactly the "domain infrastructure the specification doesn't establish" this task
   instructs against.
3. **A single composite `ward_zone` string**. Rejected — the specification names "ward" and "zone"
   as two distinct concepts (rule 21's context, §24.4's field bullet), and collapsing them loses
   independent queryability with no offsetting benefit.

| Criterion | Plain strings | New lookup entities | Composite field |
|---|---|---|---|
| Spec fidelity | High (names two distinct concepts) | Overreach — invents structure not evidenced | Loses the two-concept distinction |
| Repository consistency | Consistent (no infrastructure to misuse) | No precedent | No precedent |
| Implementation complexity | **Lowest** | Highest | Low |
| Extensibility if evidence later emerges | Convertible later without data loss | N/A (already there) | Harder to split later |

### TP/FP table structure

1. **One combined TP/FP table** with a type discriminator. Rejected — contradicted directly by
   §24.4's own repository-mapping text, which names two separate plural tables
   (`tp_records`/`fp_records`), not one.
2. **Two separate tables, `TPRecord`/`FPRecord`** (this ADR's selection) — matches the specification's
   own naming exactly.
3. **A single generic "TownPlanningRecord" table covering both**, with `record_subtype`. A variant of
   option 1 with different naming; rejected for the identical reason — the specification's own text
   already commits to two distinct table names, and no evidence suggests conflating them.

| Criterion | Combined table | Two tables (selected) | Generic renamed combined |
|---|---|---|---|
| Spec fidelity | Contradicts explicit two-table naming | **Matches exactly** | Contradicts naming |
| Domain clarity | Conflates two administratively distinct record types the spec treats separately | **Clear, matches spec's own separation** | Conflates |
| Extensibility | N/A | Each evolves independently | N/A |

## Dependency Analysis

### Required ADR #7 (Scheme hierarchy / TP-FP↔Scheme boundary) — see "Explicit #7 Deferral" below.

### Required ADR #20 (migration strategy)

Not decided here; disclosed dependencies for whichever future task resolves #20:

- `properties.survey_number`/`sub_division_number` are today's only, generic, insufficient analogue
  to `RevenueRecord`'s fields (per `ADR/0024`'s Land = RevenueRecord decision). Whether and how
  existing `Property` rows' values should backfill into new `revenue_records` rows is a migration-
  sequencing question this ADR does not design.
- `Property.village_id`'s existing FK could plausibly inform a `RevenueRecord.village_id` backfill —
  named as a plausible input to a future migration, not decided or sequenced here.
- No existing data exists anywhere to migrate into `city_survey_records`, `tp_records`, or
  `fp_records` — confirmed, none of the source concepts (City Survey Number, ward, zone, TP scheme
  number, FP number) appears in any current table.

### Property integration

Property↔Scheme cardinality remains exactly as open as `ADR/0024` left it — not decided, narrowed,
or assumed by this ADR.

### Existing `PropertyOwner`

Unaffected by this ADR. Its own `client_id`→Party-retargeting question (§24.3, coupled to
`ADR/0023`) is unrelated to Gujarat-record field architecture and is not touched here.

## Explicit #7 Deferral

This section exists because T91's own authorization names the #5↔#7 boundary as a specific QA watch
item, and because §24.4's own text states the tension directly: "TP scheme number, FP number, and
their relationship to Property/Scheme are not specified at the field level... This boundary question
is explicitly assigned to Required ADR #7."

This ADR draws the distinction the authorizing task requires, explicitly:

- **Decided by this ADR (a #5 question):** `TPRecord` needs a field to store a Town Planning scheme
  number as a plain, human-facing identifying value (`tp_scheme_number`). This is "a TP/FP field
  required to store a scheme number" — the field's mere existence and type, nothing more.
- **Not decided by this ADR (a #7 question):** `tp_scheme_number` is **not** a foreign key. It is
  not linked, structurally or by convention, to any `Scheme` entity, table, or future architecture.
  Whether a Town Planning Scheme *is* this specification's `Scheme` (§24.5), a TP/FP-Record-only
  concept, or both; whether `TPRecord` should ever gain a real `scheme_id` FK; and Scheme's own
  hierarchy-storage mechanism are all **entirely deferred to Required ADR #7**, exactly as §24.4
  itself already assigns them.

This ADR proceeds without resolving #7 because §27's own "Dependency ordering coherence" self-check
states directly that the TP/FP↔Scheme mention is "flagged as context, not depended upon" — the
specification itself asserts these are not sequenced. Nothing in this ADR's field-level decisions —
for `RevenueRecord`, `CitySurveyRecord`, `TPRecord`, or `FPRecord` — requires knowing what "Scheme"
turns out to mean.

## Migration Implications / #20 Deferral

No migration is created by this ADR. See "Dependency Analysis" above for the disclosed
`properties.survey_number`→`revenue_records` backfill question and `Property.village_id`'s possible
role — sequencing and mechanics remain Required ADR #20's job, not designed here.

## Unresolved Questions

- Required ADR #7 — Scheme hierarchy, TP/FP↔Scheme conceptual boundary. Fully deferred, per above.
- Required ADR #20 — migration/backfill mechanics. Disclosed dependencies named, not designed.
- The contents of "7/12 extract fields" — named once in the specification, never elaborated; no
  column created for it by this ADR.
- Whether `ward`/`zone` should ever become normalized lookup entities.
- Official format/validation rules for any Gujarat business identifier — none specified; the
  `CHECK`-constraint mechanism to apply them, once known, is named but not populated.
- Uniqueness of any business identifier, per-Organization or otherwise.
- Whitespace/case normalization for business identifiers.
- Property↔Scheme cardinality (§24.3, coupled to #7 — unaffected by this ADR).
- `PropertyOwner`'s `client_id`→Party retargeting (§24.3, coupled to `ADR/0023` — unaffected by this
  ADR).
- Whether a Property may hold multiple `property_record_references` rows of the same `record_type`
  (`ADR/0024`'s own open item — unaffected).

## Consequences

- `RevenueRecord`, `CitySurveyRecord`, `TPRecord`, and `FPRecord` can each be created with a shape
  directly informed by this decision once a future implementation task is authorized — this ADR
  itself creates no schema.
- `ADR/0024`'s `property_record_references` mechanism now has a concrete, fixed `record_type` value
  set to populate.
- Required ADR #7, once authorized, can proceed knowing exactly what field-level commitment already
  exists on the TP/FP side (`tp_scheme_number` as a plain string) and exactly what remains for it to
  decide (the field's structural meaning).
- A future format-validation decision (if official Gujarat identifier formats ever become available)
  has a named, proven mechanism (`CHECK`-constraint, `ck_<table>_<name>` convention) to apply without
  needing to invent one.

## Implementation Boundary

This ADR is an architecture decision, not implementation. No database table, migration, model,
service, repository, route, frontend, or test is created or modified by this document. Every field,
table, and mechanism named above describes what a future, separately-authorized implementation task
must build — none of it exists in code as a result of this ADR.

## References

- `docs/Legal_DMS — Domain Model & Functional Specification.md` §4 rules 19–24, §24.4, §26 item 5,
  §27's "Dependency ordering coherence."
- `ADR/0021-organization-tenant-boundary-enforcement.md`
- `ADR/0022-authorization-architecture.md`
- `ADR/0023-party-vs-client-architecture.md`
- `ADR/0024-property-land-propertyunit-record-reference.md`
- `backend/src/app/infrastructure/persistence/models/geography.py`
- `backend/src/app/infrastructure/persistence/models/property.py`
- `backend/src/app/infrastructure/persistence/models/client.py`
- `docs/ERD.md`
