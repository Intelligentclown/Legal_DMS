# ADR-0026: Scheme Hierarchy Storage Mechanism and TP/FP↔Scheme Conceptual Boundary

**Status:** Proposed
**Date:** 2026-08-27

**Resolves:** `docs/Legal_DMS — Domain Model & Functional Specification.md` §21 planning-list item
**#7** ("Flexible Scheme hierarchy"), including the TP/FP-Record ↔ Scheme conceptual boundary §21
item 7 itself explicitly bundles into this same decision.

**Does not resolve:** Required ADR #1, #2, #3, #4, #5, #6, #18, or #19 (already resolved by
`ADR/0021`/`ADR/0023`/`ADR/0024`/`ADR/0024`/`ADR/0025`/`ADR/0024`/`ADR/0022`/`ADR/0021` respectively,
not reopened here) or Required ADR #8–#17/#20 (untouched, and #9/#10/#13/#20 specifically excluded
by T92's own authorized scope).

**Dependencies:** `ADR/0021` (tenant isolation — every table this ADR decides is Organization-scoped,
composed with, not reopened). `ADR/0022` (authorization — Scheme entities are governed by the
existing resource+action permission model, composed with, not reopened). `ADR/0024` (Property/Land/
Property-Unit boundary — left Property↔Scheme cardinality as an open downstream concern, assessed
but not resolved here). `ADR/0025` (Revenue/City-Survey/TP-FP field architecture — froze
`TPRecord.tp_scheme_number` as a plain, unlinked string field; this ADR decides only that field's
*structural meaning*, not its existence or format, per `ADR/0025`'s own "Explicit #7 Deferral"
section).

## Context

`ADR/0025` resolved the field-level architecture for `RevenueRecord`, `CitySurveyRecord`,
`TPRecord`, and `FPRecord`, and deliberately deferred one question to this ADR: whether
`TPRecord.tp_scheme_number` has any structural relationship to a `Scheme` entity. That deferral
exists because §24.4 itself names the tension directly — "a Town Planning Scheme is conceptually
adjacent to but not necessarily the same thing as this specification's 'Scheme' (development/
project structure)" — and assigns resolving it to Required ADR #7, not to #6 or #5.

Separately, and the larger part of this ADR's scope, §4 rules 25–28 freeze that Scheme is a
Matter-independent, Organization-owned development/project structure, but leave its internal
hierarchy storage mechanism entirely open. §12 and §26 (item 4) both classify "Scheme hierarchy
storage mechanism" as blocking correct schema design — this ADR resolves that, and, per its bundled
mandate, the TP/FP boundary question alongside it.

### #5 ↔ #7 Traceability (mandatory, per T92's authorization and the T91 QA watch item)

1. **What `ADR/0025` already decided:** `TPRecord` has a `tp_scheme_number` field — a required,
   plain `String` column, never a foreign key, storing a Town Planning scheme number as a
   human-facing identifying value only. `ADR/0025` explicitly stated this decision is about the
   field's *mere existence and type*, nothing more.
2. **What `ADR/0025` deliberately deferred to #7:** whether `tp_scheme_number` — or `TPRecord` more
   generally — has any *structural* relationship to a `Scheme` entity; whether a Town Planning
   Scheme *is* this specification's `Scheme`, a TP/FP-Record-only concept, or both; and Scheme's own
   hierarchy-storage mechanism, which did not yet exist as a decided architecture for #5 to compose
   against.
3. **What T92 (this ADR) now resolves:** Scheme's hierarchy storage mechanism (below); the TP/FP↔
   Scheme conceptual boundary — concluding, with reasoning given in "TP/FP↔Scheme Boundary Decision"
   below, that they are **distinct concepts, not linked by any database relationship** — a Town
   Planning Scheme number remains exactly what `ADR/0025` already made it, a plain field, and this
   ADR adds no `scheme_id` or other structural reference to `TPRecord`.
4. **What remains unresolved after #7:** Property↔Scheme's exact cardinality (assessed, not
   resolved — see "Relationship to Required ADR #24.3 — Property↔Scheme" below); whether/how a
   Scheme-owning Organization's specific Building/Block/Section/Unit vocabulary is configured
   (business/config content, not architecture, per §6.2's general pattern); Required ADR #9, #10,
   #13, #20 (explicitly out of this task's scope); any decision already frozen by `ADR/0021`–`0025`.

### Repository baseline (direct inspection, `main` at this ADR's authoring baseline)

- **No `Scheme`, `SchemeNode`, `scheme_id`, `scheme_node`, `TPRecord`, or `FPRecord` implementation
  exists anywhere in `backend/src/app`** — confirmed by a full-repository, case-insensitive grep.
  The only unrelated match for "scheme" is `deps.py`'s `_bearer_scheme` (an HTTP authentication
  concept, `HTTPBearer`, structurally unconnected to the business `Scheme` entity).
- **No self-referencing, adjacency-list, materialized-path, `lft`/`rgt`, or nested-set pattern
  exists anywhere in `backend/src/app/infrastructure/persistence/models/`** — confirmed by a full
  grep for `parent_id`, self-referencing `ForeignKey`, and nested-set column names. A variable-depth
  self-referencing hierarchy would be a **genuinely new idiom** for this codebase, unlike
  `ADR/0024`'s polymorphic-reference choice, which had five direct precedents.
- **`geography.py` is this codebase's only existing hierarchy-shaped precedent**, and it is
  structurally the *opposite* of what Scheme needs: `Country → State → District → Taluka → Village`
  is implemented as **five separate, fixed-level tables**, each with a single non-nullable `ForeignKey`
  to its immediate parent's table. This works precisely because that hierarchy's depth and level
  names are genuinely fixed in reality (a village always has a taluka, a taluka always has a
  district, and there is never a sixth level) — the opposite of what §4 rule 27/28 requires for
  Scheme, where "Building/Block/Section are standard concepts, not mandatory hierarchy
  requirements" and a shallower structure must be supported as a first-class case, not an edge case.
  `geography.py` is cited here as relevant negative precedent — proof this codebase already commits
  to a fixed-level-per-table pattern successfully, and exactly why that pattern is the wrong fit for
  a business-variable hierarchy like Scheme's.
- **`docs/ERD.md` contains no mention of Scheme, `scheme_nodes`, or any related table** — confirmed
  by direct search. No prior design work exists to build on beyond §9.4/§10.A's own candidate naming
  in the governed specification.

## Business/Specification Inputs

Frozen (not reopened by this ADR):

- §4 rule 25 (Scheme is independent of Matter — same independence pattern as Property).
- §4 rule 26 (one Organization may own/control multiple Schemes).
- §4 rule 27/28 (Scheme structure is flexible; Building/Block/Section are standard, not mandatory,
  concepts; shallower structures must be a first-class case).
- §24.4's explicit assignment of the TP/FP↔Scheme conceptual-boundary question to Required ADR #7,
  not to #6 (preserved, not absorbed elsewhere).
- `ADR/0025`'s freezing of `TPRecord.tp_scheme_number` as a plain, unlinked `String` field.

Genuinely open, and the actual subject of this ADR's Decision:

- §24.5's hierarchy-storage-mechanism question (four named candidates).
- §24.4's TP/FP↔Scheme conceptual-boundary question.

Genuinely open, and explicitly **not** decided by this ADR (assessed only, per "Explicitly
Unresolved Items"):

- Property↔Scheme's exact cardinality and whether it is mediated by a structure/join table (§24.3's
  own open item).
- Which concrete Building/Block/Section/Unit vocabulary an Organization actually needs (business/
  config content, per §6.2's general configurability pattern).
- Required ADR #9, #10, #13, #20 — explicitly out of scope per T92's authorization.

## Decision Drivers

Ranked in the order this ADR actually weighs them, consistent with the evidentiary discipline
`ADR/0021`–`0025` already established (specification mandate first, then repository consistency,
then implementation simplicity, never novelty for its own sake):

1. **§4 rule 27/28's explicit variable-depth requirement** — any mechanism that bakes in a maximum
   or fixed set of named levels is disqualified outright, regardless of its other merits.
2. **Concurrency safety** — this specification's own established discipline (§17.5's mandatory
   concurrent-creation test for File Numbering, and this project's general "concurrency-critical, not
   cosmetic" treatment of structural mechanisms) applies by extension to any mechanism whose
   correctness depends on serialized writes across many rows.
3. **Repository consistency** — prefer a mechanism this codebase's existing patterns and
   infrastructure (SQLAlchemy, Postgres, the generic repository/service layering) support cleanly,
   over one requiring novel infrastructure.
4. **Implementation and query complexity** — prefer the option that is simplest to implement and
   query correctly, once the first three drivers are satisfied, not before.

## Alternatives Considered — Scheme Hierarchy Storage Mechanism

### 1. Adjacency List

A single `scheme_nodes` table; each row carries a nullable, self-referencing `parent_id` (`NULL` for
a top-level node under a Scheme) and a `scheme_id` grouping all nodes under one `Scheme`.

| Criterion | Assessment |
|---|---|
| Variable-depth support | **Full** — a node simply points to its immediate parent; no depth limit, no schema change to go deeper or shallower |
| Parent/child representation | Single FK column — the simplest possible representation |
| Insertion/update complexity | **Low** — inserting a node is one `INSERT` with `parent_id` set; no other row is touched |
| Subtree queries | Requires a recursive query (Postgres `WITH RECURSIVE` CTE) — not a single flat `SELECT`, but a well-supported, standard SQL/Postgres capability |
| Ancestor/descendant queries | Same recursive-CTE mechanism, both directions |
| Integrity constraints | A `CHECK` can prevent a node being its own direct parent trivially; preventing a deeper cycle (a node becoming an ancestor of itself several levels up) requires either a recursive validation at write time or a trigger — named honestly as a real, if minor, gap below |
| Concurrency implications | **Low risk** — a single-row `INSERT`/`UPDATE` per operation; no cascading renumbering of other rows is ever required, so ordinary row-level locking is sufficient |
| Future hierarchy changes (re-parenting) | **Cheap** — moving a subtree is a single `UPDATE` of the moved node's own `parent_id`; every descendant's own `parent_id` chain is unaffected and still resolves correctly |
| Tenant isolation | Direct — `organization_id` sits on `scheme_nodes` exactly like any other tenant-scoped table under `ADR/0021`, no special interaction with the parent/child structure |
| ORM/repository implementation complexity | **Low-to-medium** — ordinary CRUD via the existing generic repository pattern for creating/reading a single node; subtree/ancestor traversal needs a bespoke repository method issuing a recursive CTE, the same kind of departure from purely-generic CRUD this codebase already accepts elsewhere (e.g. `SqlAlchemyUserRepository.assign_role()`) |
| Suitability for Legal_DMS's expected usage | Schemes are created and restructured by ordinary Organization staff as business need arises (not built once and left static) — an adjacency list's cheap, single-row writes fit this pattern; a write-heavy, rarely-restructured-in-bulk usage pattern is exactly what this option is best suited for |

### 2. Materialized Path

Each `scheme_nodes` row stores a string path (e.g. `/<root-id>/<child-id>/<grandchild-id>/`)
encoding its full ancestry in one indexed column.

| Criterion | Assessment |
|---|---|
| Variable-depth support | Full |
| Subtree queries | Efficient — a `LIKE 'path/%'` prefix match, indexable |
| Ancestor queries | Requires parsing the path string, or maintaining a separate ancestor list — messier than adjacency list's direct recursive traversal |
| Insertion complexity | Requires reading the parent's current path before computing the new row's path — one extra read every insert, not present in the adjacency-list option |
| Re-parenting cost | **Expensive and error-prone** — moving a subtree requires rewriting the path string on the moved node *and every one of its descendants*, since each descendant's path literally embeds the moved node's ID. For a Scheme that may be restructured as a real project evolves, this is a genuine, evidenced downside, not a theoretical one. |
| Integrity | No natural database-level constraint validates path well-formedness; correctness depends entirely on application-layer discipline |
| Repository precedent | None in this codebase |

**Rejected** — the re-parenting cost is a concrete, disqualifying weakness given Scheme structures
are expected to be edited by ordinary staff, not fixed at creation time, and this codebase has no
existing precedent to offset the added complexity.

### 3. Nested Set

Each `scheme_nodes` row stores `lft`/`rgt` integers encoding tree position via interval nesting.

| Criterion | Assessment |
|---|---|
| Variable-depth support | Full |
| Subtree/descendant queries | Very efficient — a single range comparison, no recursion needed |
| Insertion/update complexity | **Worst of the four options** — inserting or moving any node requires renumbering the `lft`/`rgt` values of every other node positioned after the insertion point, potentially touching a large number of unrelated rows for one logical change |
| Concurrency implications | **Genuine risk** — two concurrent inserts into the same Scheme's tree can conflict on the exact same renumbering range unless serialized by an explicit lock covering the whole tree (not just the affected rows), which itself becomes a throughput bottleneck for any Organization actively restructuring a Scheme. This is precisely the class of concurrency risk this specification treats as a first-order concern elsewhere (§17.5's mandatory concurrent-creation test for File Numbering) — deciding a hierarchy mechanism carrying an equivalent, undisclosed concurrency risk would be inconsistent with that discipline. |
| Repository precedent | None in this codebase |

**Rejected** — the write-amplification and concurrency risk are structurally the worst of the four
candidates, for a use case (staff-editable project structures) that does not need nested set's
query-side advantage badly enough to justify its write-side cost.

### 4. Fixed/Optional Levels

A fixed, nullable set of level columns (or one table per level, mirroring `geography.py`) — e.g.
`building_id`, `block_id`, `section_id`, `unit_id` — each optional, to approximate variable depth by
leaving unused levels `NULL`.

| Criterion | Assessment |
|---|---|
| Variable-depth support | **Bounded, not general** — supports any depth up to however many level-columns are defined in advance, and no more; a Scheme genuinely needing a depth beyond the anticipated set cannot be represented without a schema migration |
| Direct textual conflict | §4 rule 27/28 explicitly states Building/Block/Section "are standard concepts, not mandatory hierarchy requirements" — a fixed level set, even nullable, still bakes in an assumed *maximum* structure and a fixed vocabulary of level names, which is the exact pattern rule 27/28 warns against treating as a requirement |
| Repository precedent | **Direct** — this is exactly `geography.py`'s own pattern, proven and working, but for a genuinely fixed-depth real-world hierarchy (administrative levels), a materially different situation from Scheme's business-variable structure |

**Rejected** — disqualified primarily on direct specification-textual grounds (Decision Driver 1),
not on implementation merit; `geography.py`'s own success with this pattern is exactly why the
distinction matters — this codebase already knows this pattern works well for a genuinely
fixed-depth hierarchy, which is precisely why applying it to a hierarchy the specification requires
to stay variable would be reusing the wrong precedent.

## Decision — Scheme Hierarchy Storage Mechanism

**Adjacency list is adopted.** Two new tables:

- **`schemes`** — the stable, top-level identity for one development/project (§4 rule 25/26): `id`
  (UUID PK), `organization_id` (mandatory, per `ADR/0021`), `name`, plus the standard `AuditMixin`/
  `OptimisticLockMixin` scaffolding every tenant-scoped table in this codebase already carries. This
  is the entity a future Property↔Scheme or Matter-adjacent relationship would most plausibly
  reference, per §24.5's own text (Scheme ⟷ Property "plausible... exact cardinality... is ED") —
  not decided here, see "Relationship to Required ADR (Property↔Scheme)" below.
- **`scheme_nodes`** — the variable-depth internal structure within one Scheme: `id` (UUID PK),
  `scheme_id` (mandatory FK to `schemes.id`, grouping every node under its owning Scheme),
  `parent_id` (nullable, self-referencing FK to `scheme_nodes.id` — `NULL` for a top-level node
  directly under the Scheme), `node_type` (a plain string label — "Building," "Block," "Section,"
  "Unit," or any other value an Organization's own configuration names, per §6.2's general
  vocabulary-configurability pattern; not `CHECK`-constrained to a fixed value set, consistent with
  rule 27/28's flexibility requirement), `name`, `organization_id` (mandatory, per `ADR/0021` — see
  "Tenant-Isolation Composition" below for why this is required directly on `scheme_nodes`, not
  merely inherited via `scheme_id`), plus the standard `AuditMixin`/`OptimisticLockMixin`
  scaffolding.

This directly matches §9.4/§10.A's own two-name suggestion ("`schemes`, `scheme_nodes`/structure")
rather than inventing a different shape, and cleanly separates the stable Scheme identity (what a
future cross-domain relationship would reference) from the purely-internal variable-depth structure
beneath it.

## TP/FP↔Scheme Boundary Decision

**A Town Planning Scheme and this specification's `Scheme` entity are distinct concepts, not linked
by any database relationship.** `TPRecord.tp_scheme_number` remains exactly as `ADR/0025` already
decided it — a plain, required `String` field, never a foreign key, never structurally connected to
`schemes`/`scheme_nodes`.

**Reasoning, labeled explicitly as an architectural interpretation grounded in indirect textual
signals, not an explicit specification statement** (per this task's own instruction against
converting an inference into a specification requirement):

- §4 rule 26 describes an Organization as "own[ing]/control[ling] multiple Schemes" — language that
  reads naturally as the *firm's own client's* development/project structure (a builder's
  residential project, for instance), something the Organization (via its client) genuinely owns and
  organizes internally.
- A Town Planning Scheme, in the real-world administrative sense §24.4's own naming invokes, is a
  statutory land-development mechanism created and administered by a government town-planning
  authority over a geographic area — not something a private firm's client "owns or controls" in the
  sense rule 26 describes. The two concepts share a name-fragment ("Scheme") but describe
  categorically different kinds of things: one is the firm's internal project-organization tool, the
  other is a government administrative reference the firm merely records.
- No CBR text anywhere in §4 or §24 states or implies that a TP Scheme and this specification's
  `Scheme` are, or must be treated as, the same entity — the closest textual signal (§24.4's own
  overlap note) explicitly frames this as an open *question*, not a settled equivalence, and assigns
  answering it to this ADR.
- Absent any textual basis for asserting equivalence, and consistent with `ADR/0024`'s own discipline
  (reject an entity or relationship the specification's text does not actually require, rather than
  inventing one because two names sound related), the more conservative, better-evidenced conclusion
  is to keep them structurally separate.

**What this decision does and does not foreclose:** if concrete business evidence later shows a
genuine need to relate a specific `TPRecord` to a specific `Scheme` or `SchemeNode` (e.g., a
Scheme built entirely within the footprint of one Town Planning Scheme), that would be a new,
separately authorized decision — most plausibly a further `record_type`-style reference or a
dedicated join, mirroring `ADR/0024`'s own extensibility mechanism — not a silent reinterpretation of
this ADR's conclusion. This ADR neither assumes nor forecloses that possibility; it declines to
invent the relationship without present evidence.

## Data-Model Consequences

- **`schemes` (new):** top-level Scheme identity, per "Decision" above.
- **`scheme_nodes` (new):** self-referencing variable-depth structure, per "Decision" above.
- **`TPRecord` (existing, `ADR/0025`):** **unchanged by this ADR.** No `scheme_id` or other
  structural column is added to it. `tp_scheme_number` remains a plain string, exactly as `ADR/0025`
  froze it.
- **No other table is created, modified, or renamed by this ADR.**

## Tenant-Isolation Composition (ADR-0021)

`ADR/0021` is not modified, reopened, or reinterpreted. Both `schemes` and `scheme_nodes` are
tenant-scoped and require a mandatory `organization_id` column under `ADR/0021`'s already-decided
rule (mandatory application-layer scoping as the primary mechanism, `FORCE`d default-deny RLS as the
backstop). Stated explicitly, mirroring `ADR/0024`'s own identical discipline for
`property_record_references`: **`scheme_nodes` must carry its own `organization_id`, not merely
inherit tenant scope by joining to `schemes`** — `ADR/0021`'s own requirement is that tenant scope be
an explicit, independently-enforceable value on every tenant-scoped table, so that the RLS backstop
applies directly to `scheme_nodes` and does not depend on a correct join to `schemes` always being
present in every query that touches it (a real risk specifically for a self-referencing recursive
query, where a bug in the recursive traversal could otherwise silently omit the join).

## Authorization Composition (ADR-0022)

`ADR/0022` is not modified, reopened, or reinterpreted. `schemes` and `scheme_nodes` are governed by
`ADR/0022`'s existing resource+action permission model — a future `schemes:read`/`schemes:write`
permission pair, checked once at the service/use-case boundary, exactly like every other resource
`ADR/0022` already governs. Consistent with `ADR/0023`'s and `ADR/0024`'s identical reasoning for
their own sub-entities: `scheme_nodes` are accessed only *through* their owning `Scheme` (they are a
Scheme's own internal structure, not an independently user-facing top-level resource), so they are
governed by the same `schemes:*` permission codes as `Scheme` itself, not fragmented into a separate
`scheme_nodes:*` permission surface — avoiding the exact permission-surface drift `ADR/0022`'s
resource+action model is designed to prevent.

## Relationship to Property↔Scheme Cardinality (§24.3)

**Assessed, not resolved**, per T92's own explicit instruction that this remains an assessment
unless #7's scope genuinely requires deciding it — it does not. §24.3 itself frames the relationship
as "plausible... but not frozen as a required relationship." This ADR's hierarchy-mechanism decision
does not constrain that future decision in either direction: whichever cardinality is eventually
chosen (a Property referencing one `Scheme`, one `SchemeNode`, or neither), the target entity already
has a stable UUID identity under this ADR's decision, the same "existence, distinctness, stable
identity" interface `ADR/0024` fixed for the Gujarat-record entities. Whether that future relationship
is represented via `ADR/0024`'s own `property_record_references` mechanism (a further `record_type`
value), a dedicated FK, or another mechanism is not decided or narrowed here.

## Consequences

- `Scheme`/`SchemeNode` can each be created with a shape directly informed by this decision once a
  future implementation task is authorized — this ADR itself creates no schema.
- A future Property↔Scheme decision has a fixed, stable target identity to reference (`schemes.id`
  and/or `scheme_nodes.id`), without needing to revisit this ADR's hierarchy mechanism.
- `TPRecord`'s field-level architecture (`ADR/0025`) is confirmed final with respect to Scheme — no
  further change to it is implied by this ADR, closing the #5↔#7 traceability loop the T91 QA watch
  item required to remain visible.
- Whichever concrete Building/Block/Section/Unit vocabulary an Organization needs is seed/config
  data under `scheme_nodes.node_type`, not a schema decision — consistent with §6.2's general
  pattern already applied throughout §24.

## Risks

- **Cycle prevention is not database-enforced.** A `CHECK` constraint can prevent a node listing
  itself as its own direct parent, but a deeper cycle (node A → node B → node A) requires
  application-layer validation or a database trigger — named here as a genuine, disclosed gap, not
  hidden. A future implementation task must decide which mechanism to use; this ADR does not design
  it.
- **Recursive-query performance** for very deep or very wide Scheme structures is not benchmarked
  here — no real Scheme data exists yet to measure against. If evidence later shows recursive CTEs
  are a genuine performance bottleneck for a specific Organization's usage pattern, a supplementary
  denormalization (e.g., a cached depth or ancestor-count column) would be a future ADR amendment,
  not a reason to have chosen nested set or materialized path preemptively without evidence.
- **This is the first self-referencing hierarchy pattern in this codebase.** Unlike `ADR/0024`'s
  polymorphic-reference choice (five direct precedents), this ADR introduces a genuinely new idiom.
  This is disclosed explicitly, not minimized — the decision is made on the specification's own
  variable-depth requirement and general SQL/Postgres best practice, not on existing repository
  precedent, since none exists for this specific shape.

## Explicitly Unresolved Items

After this ADR, the Required ADR status is:

- **Required ADR #1, #2, #3, #4, #5, #6, #18, #19** — already resolved by their respective ADRs. Not
  reopened.
- **Required ADR #7** — **resolved by this ADR**: adjacency-list hierarchy mechanism (`schemes` +
  `scheme_nodes`); TP/FP↔Scheme conceptual boundary (distinct concepts, no database relationship).
- **Required ADR #8–#17, #20** — remain fully unresolved. Nothing in this ADR decides, narrows, or
  implies a position on any of them.

Also explicitly unresolved, named rather than silently decided:

- Property↔Scheme's exact cardinality and mechanism (§24.3 — assessed above, not resolved).
- Cycle-prevention mechanism for `scheme_nodes` (application-layer validation vs. database trigger).
- The concrete Building/Block/Section/Unit vocabulary any given Organization needs (business/config
  content).
- Whether a future denormalization (cached depth/ancestor data) is ever warranted — no evidence
  exists yet to decide this.

## Implementation Boundary

This ADR is an architecture decision, not implementation. No database table, migration, model,
service, repository, route, frontend, or test is created or modified by this document. Every table
and mechanism named above describes what a future, separately-authorized implementation task must
build — none of it exists in code as a result of this ADR.

## References

- `docs/Legal_DMS — Domain Model & Functional Specification.md` §4 rules 25–28, §24.3, §24.4, §24.5,
  §26 item 4, §27's "Dependency ordering coherence."
- `ADR/0021-organization-tenant-boundary-enforcement.md`
- `ADR/0022-authorization-architecture.md`
- `ADR/0024-property-land-propertyunit-record-reference.md`
- `ADR/0025-revenue-city-survey-tpfp-field-architecture.md`
- `backend/src/app/infrastructure/persistence/models/geography.py`
- `docs/ERD.md`
