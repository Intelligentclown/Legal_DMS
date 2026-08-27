# T91 Software Architect Report

**Task:** T91 — Draft and resolve Required ADR #5 ("Revenue vs City Survey," read per §26 item 5's
fuller framing as "Revenue/City-Survey/TP-FP exact field sets"), while explicitly not resolving
Required ADR #7 ("Flexible Scheme hierarchy" / TP-FP↔Scheme boundary). Per
`docs/Legal_DMS — Domain Model & Functional Specification.md` §21's planning-list terminology. Full
authorized-scope text: `IMPLEMENTATION_QUEUE.md`'s T91 row.

**Role:** Software Architect, per `docs/prompts/SoftwareArchitect.md` (formally adopted, merged
`b5b3126`). This report follows that prompt's Required Output (§8) and Reviewer Checklist (§7 item
7) structure, and this task's own §14 requirements.

---

## 1. Repository Baseline Verification

- `git status`: clean working tree, on `main`, before any edit.
- `git fetch origin`: local `main` was **behind** `origin/main` by 2 commits at session start
  (local HEAD `503be1a`, `origin/main` at `25c845d`). Fast-forwarded via `git merge --ff-only
  origin/main` — a clean fast-forward, no divergent local commits.
- Post-fast-forward: `main == origin/main` at `25c845d7ea1629ef90dc2751240494f3d15618c8`.
- Starting SHA recorded: `25c845d7ea1629ef90dc2751240494f3d15618c8`.

## 2. Authorization Verification

- `git merge-base --is-ancestor 2554ad3b6429297bc1b14480ac6470b1108eaaa2 HEAD` → **YES** (the T91
  authorization commit "docs(governance): authorize T91" is an ancestor of `main`, confirmed
  post-fast-forward).
- `git log --oneline`: T91's authorization (`2554ad3`, merged via PR #126, merge `25c845d`)
  immediately follows T90's post-merge closeout (`052ddea`/PR #125, merge `503be1a`) — no
  implementation commit of any kind appears between T90's closeout and the T91 authorization merge.
- `IMPLEMENTATION_QUEUE.md`'s T91 row, read in full directly from the file (not from the task
  prompt), confirms: Required ADR #5 scope, framed exactly as the task prompt states; the explicit
  "must treat as already established" list (`ADR/0021`/`ADR/0022`/`ADR/0023`/`ADR/0024` all frozen);
  the explicit must-decide list (field-level architecture for the three record types, identifiers/
  format, geography linkage, composition with `ADR/0024`'s reference mechanism) and must-NOT-decide
  list (Scheme hierarchy, TP/FP↔Scheme boundary, Property↔Scheme cardinality, migration strategy,
  Matter/File/Document/financial/workflow architecture, anything already frozen); the **explicit QA
  watch item** naming the #5↔#7 tension and requiring it "remain visible, not silently resolved for
  field-model convenience" — quoting §24.4's own TP/FP text verbatim; the required-QA-before-merge
  statement; and the three-PR governance lifecycle this report follows steps (1)–(2) of. The task
  prompt's own framing matches this queue row precisely.
- `T90 is now Done` — confirmed present in `IMPLEMENTATION_QUEUE.md`'s T90 row text.
- `ADR/0021`, `ADR/0022`, `ADR/0023`, `ADR/0024` all exist (confirmed via `ls ADR/`).
- `ADR/0025` did **not** exist prior to this pass (confirmed via `ls ADR/0025*` failing before
  drafting).
- No `T92` reference exists anywhere in the repository — confirmed via a full-repository filename
  search (`find . -iname "*T92*"`, excluding `node_modules`/`.git`, zero matches) and a content grep
  of `IMPLEMENTATION_QUEUE.md` (zero matches outside the T91 row's own "does not create T92"
  exclusion clause) and `PROJECT_STATE.json` (not separately re-checked this session; no mechanism
  exists for `T92` to have entered it without an `IMPLEMENTATION_QUEUE.md` row first, and none
  exists there).
- `businessFeatures` remains `[]`; `currentStage` remains `stage-3`/`in_progress` — confirmed via
  direct JSON read, unchanged.
- No unauthorized T91 implementation had already occurred: confirmed by the git log sequence above
  and by `git status`'s clean working tree at session start.

## 3. Specification Evidence

Read directly from `docs/Legal_DMS — Domain Model & Functional Specification.md`, in full where
cited, via a dedicated background investigation pass whose findings were independently reasoned
about before drafting, not taken on faith:

- §4 rules 19–24 verbatim.
- §24.4's cross-cutting note and the full RevenueRecord, CitySurveyRecord, and TP/FP Record entity
  blocks — every field-level candidate quoted verbatim (Block Number, Survey Number, Sub-division,
  village/taluka/district linkage, "7/12 extract fields" for RevenueRecord; City Survey Number,
  ward/zone linkage for CitySurveyRecord; TP scheme number, FP number for TP/FP Record) — confirmed
  each block is explicitly labeled `Fields (ED — unresolved)`, not frozen content.
- §24.4's TP/FP Record block's own explicit assignment of the TP/FP↔Scheme boundary question to
  Required ADR #7, not to #5 or #6 — read and quoted verbatim, the direct textual source of this
  task's QA watch item.
- §26's "must resolve before implementation" list, confirming item 5 ("Revenue/City-Survey/TP-FP
  exact field sets... Required ADR #5") is textually distinct from item 4 (#7, Scheme hierarchy) and
  item 3 (#3/#4/#6, already resolved by `ADR/0024`).
- §27's "Dependency ordering coherence" self-check — read and quoted verbatim: the specification's
  own assertion that §24's group presentation order (Gujarat Records before Scheme) creates no
  forward dependency, and that mentions like the TP/FP↔Scheme note are "flagged as context, not
  depended upon." This is the direct textual basis for T91 (and this ADR) proceeding without #7.
- An exhaustive search for "TP scheme number," "FP number," "ward," "zone," "Block Number," "Survey
  Number," "Sub-division" across the full 3858-line document — confirmed each phrase appears
  exactly once, entirely within the §24.4 field bullets already quoted, with no elaboration
  anywhere else.
- An exhaustive search for format/regex/pattern rules applicable to Gujarat identifiers — confirmed
  **none exists**. The only regex-format precedent in the entire specification (PAN/Aadhaar) is
  scoped to Party/Client (§24.2) and is never extended, analogized, or referenced in connection with
  Revenue/City-Survey/TP-FP identifiers anywhere in the document.

## 4. Existing ADRs Examined

- `ADR/template.md` — structure precedent.
- `ADR/0021`, `ADR/0022`, `ADR/0023`, `ADR/0024` — re-confirmed (all authored by this same role in
  prior sessions; content unchanged, re-verified against the current files, not re-derived from
  memory). `ADR/0024`'s "stable UUID identity," `record_type` discriminator, and mandatory-
  `organization_id`-on-every-implied-table requirements are the direct interface this ADR populates
  without redesigning.
- None of the four was modified — confirmed via `git diff --stat main` (below): none appears in
  this branch's diff.

## 5. Repository Investigation

Direct inspection, read-only, via the same background investigation pass:

- `backend/src/app/infrastructure/persistence/models/geography.py` (full file) — confirmed the
  complete, working `Country → State → District → Taluka → Village` hierarchy: each level FK'd to
  its parent, `UniqueConstraint(parent_id, name)` at each level, **no `organization_id`, no
  `AuditMixin`** (global reference data, matching `matter_types`/`document_types`'s treatment
  elsewhere).
- `backend/src/app/infrastructure/persistence/models/property.py` (full file, re-confirmed) —
  `Property.village_id` already FKs into this hierarchy today (nullable, indexed) — the direct,
  working precedent this ADR extends to `RevenueRecord`. `survey_number`/`sub_division_number`
  confirmed as plain `String` columns with zero format `CHECK` constraints — today's "generic,
  insufficient" analogue per `ADR/0024`.
- `backend/src/app/infrastructure/persistence/models/client.py` — `pan_number`/`aadhaar_number`'s
  exact regex `CHECK` constraints confirmed (`^[A-Z]{5}[0-9]{4}[A-Z]$`, `^[0-9]{12}$`), cited as the
  mechanism precedent for format validation, explicitly **not** claimed as spec-mandated for Gujarat
  identifiers.
- A full grep of `backend/src/app` confirmed zero implementation exists for `Revenue`, `CitySurvey`/
  `City Survey`, TP/FP (any spelling), `ward`, or `zone`.
- `backend/alembic/versions/` — confirmed only one geography-related migration
  (`198cbb4bbeb6_geography_countries_states_districts_.py`), matching `geography.py` exactly; zero
  migrations exist for any Gujarat-record target entity.
- `docs/ERD.md` — confirmed the `ck_<table>_<name>` CHECK-constraint naming convention and the
  documented geography-hierarchy ER relationships; confirmed no section mentions Revenue, City
  Survey, TP, FP, ward, or zone anywhere.

## 6. Architectural Reasoning

The specification's field-level content for this cluster is genuinely sparse — each of the three
record types' `Fields` bullets is explicitly labeled ED, offering only a short, non-binding
candidate list. This ADR's approach was to take exactly what the specification names as candidates
and formalize them as the field-level architecture (since T91's own authorization requires deciding
"the field-level architecture," and the specification's candidate lists are the only textual content
available to ground that decision in), while explicitly declining to invent anything beyond what is
named — most visibly, no format/validation rule is decided for any Gujarat identifier, and "7/12
extract fields" is named as a deferred, undesigned future field group rather than guessed at.
Geography linkage was extended to `RevenueRecord` (matching the specification's own explicit
suggestion and the existing `Property.village_id` precedent) but deliberately **not** extended to
`CitySurveyRecord`'s ward/zone, because the specification's own text draws that exact distinction
(RevenueRecord's bullet mentions `geography.py` reuse; CitySurveyRecord's does not) and no
repository infrastructure exists for ward/zone modeling to reuse.

## 7. Field-Level Decisions

Full field-classification tables (Entity/Field/Required?/Source/Purpose/Type/Validation/Deferred?)
for `RevenueRecord`, `CitySurveyRecord`, `TPRecord`, and `FPRecord` are recorded in `ADR/0025`'s own
"Entity / Field Architecture" section — not duplicated here in full; summarized:

- **RevenueRecord:** `id`, `organization_id`, `block_number` (nullable), `survey_number` (required,
  the record's defining identifier), `sub_division_number` (nullable), `village_id`/`taluka_id`/
  `district_id` (nullable FKs into `geography.py`), audit + optimistic-lock fields. "7/12 extract
  fields" explicitly not designed — no column created.
- **CitySurveyRecord:** `id`, `organization_id`, `city_survey_number` (required), `ward`/`zone`
  (nullable plain strings, explicitly not FK'd into any new lookup entity), audit + optimistic-lock
  fields.
- **TPRecord:** `id`, `organization_id`, `tp_scheme_number` (required, a plain string — explicitly
  **not** an FK to any Scheme entity), audit + optimistic-lock fields.
- **FPRecord:** `id`, `organization_id`, `fp_number` (required), audit + optimistic-lock fields.

All business-identifier fields are `String`, never numeric (to avoid leading-zero corruption); each
record's own defining identifier is `NOT NULL`; auxiliary fields remain nullable, matching
`Property.sub_division_number`'s existing precedent. No format/regex `CHECK` constraint is defined
for any Gujarat identifier — disclosed as an open gap, with the `Client.pan_number`-style mechanism
named as the pattern a future format decision should use.

## 8. Alternatives Considered

Three clusters, each with genuine, non-strawman alternatives scored against relevant criteria in
`ADR/0025`'s own "Alternatives Considered" section:

- **RevenueRecord geography linkage:** embedded strings (rejected — discards existing normalized
  infrastructure); normalized FK reuse (**selected** — matches existing `Property.village_id`
  precedent and the spec's own suggestion); hybrid FK+denormalized (not selected now — no
  query-performance evidence justifies it yet, unlike `Property`'s own documented trade-off).
- **CitySurvey ward/zone representation:** plain strings (**selected** — no evidence justifies
  more); new lookup entities (rejected — unevidenced infrastructure invention); composite field
  (rejected — collapses two concepts the spec names distinctly).
- **TP/FP table structure:** one combined table (rejected — contradicts the spec's own explicit
  `tp_records`/`fp_records` two-table naming); two separate tables (**selected** — matches spec
  naming exactly); generic renamed combined table (rejected — same reason as the first).

## 9. #5 ↔ #7 Dependency Analysis

`ADR/0025` contains a dedicated "Explicit #7 Deferral" section, directly responding to this task's
QA watch item, drawing the mandatory distinction verbatim: `TPRecord.tp_scheme_number`'s mere
existence as a plain, human-facing string field is decided (a #5 question); its structural
relationship to any future `Scheme` entity — whether it should ever become a real `scheme_id` FK,
whether a Town Planning Scheme *is* this specification's Scheme — is entirely undecided and left to
Required ADR #7 (a #7 question), citing §24.4's own explicit assignment of that boundary verbatim.
The section also cites §27's "Dependency ordering coherence" self-check directly as the
specification's own textual confirmation that this forward mention does not create a blocking
sequencing dependency — this ADR does not merely assert separability, it grounds the assertion in
the specification's own explicit self-check.

## 10. #20 Migration Dependency

`ADR/0025`'s "Dependency Analysis" section discloses, without designing: the
`properties.survey_number`/`sub_division_number`→`revenue_records` backfill question (per `ADR/0024`'s
Land = RevenueRecord decision); `Property.village_id`'s possible role as a backfill input for
`RevenueRecord.village_id`; and the confirmed absence of any existing data to migrate into
`city_survey_records`, `tp_records`, or `fp_records` (none of their source concepts exists in any
current table). None of this is sequenced or designed — named as inputs for whichever future task
resolves Required ADR #20.

## 11. Unresolved / Deferred Items

- Required ADR #7 (Scheme hierarchy, TP/FP↔Scheme boundary) — fully deferred.
- Required ADR #20 (migration/backfill mechanics) — disclosed dependencies named, not designed.
- "7/12 extract fields" — named once in the specification, never elaborated; no column created.
- Whether `ward`/`zone` should ever become normalized lookup entities.
- Official format/validation rules for any Gujarat business identifier — none specified; the
  mechanism to apply them (once known) is named, not populated.
- Uniqueness and whitespace/case-normalization rules for any business identifier.
- Property↔Scheme cardinality (`ADR/0024`'s own open item — unaffected).
- `PropertyOwner`'s `client_id`→Party retargeting (`ADR/0023`'s own open item — unaffected).
- Whether a Property may hold multiple `property_record_references` rows of the same `record_type`
  (`ADR/0024`'s own open item — unaffected).

## 12. Frozen-Business-Rule Verification

```
[x] S4 rules 19-24 (Gujarat records distinctness and extensibility) -- cited as already-settled
    inputs, directly informing every field-level decision; none reinterpreted.
[x] ADR/0021, ADR/0022, ADR/0023, ADR/0024 composed with, not modified -- confirmed via
    git diff --stat (below): none appears in this branch's diff.
[x] No new business rule invented merely because a modeling choice would be convenient -- every
    field named in ADR/0025 traces directly to a specification-named candidate or to necessary
    architectural representation (UUID PK, organization_id, audit fields); "7/12 extract fields"
    explicitly left undesigned rather than guessed at.
[x] Genuinely unresolved business questions identified, not silently decided -- format rules,
    ward/zone structure, "7/12 extract" contents, and the #7/#20 dependencies are all explicitly
    named as unresolved in ADR/0025's own "Unresolved Questions" section.
[x] The #5 <-> #7 QA watch item specifically addressed -- a dedicated "Explicit #7 Deferral"
    section draws the "field required to store a value" vs "architectural relationship to Scheme"
    distinction verbatim, as this task's authorization required.
```

## 13. Exact Files Changed

```
$ git status
On branch docs/t91-adr-0025-revenue-citysurvey-tpfp-field-architecture
Untracked files:
  ADR/0025-revenue-city-survey-tpfp-field-architecture.md
  docs/reviews/T91_Software_Architect_Report.md

$ git diff --stat main
(empty prior to this commit -- both files are new, untracked)
```

Exactly two new files, both documentation. No existing file was modified — confirmed `ADR/0021`,
`ADR/0022`, `ADR/0023`, `ADR/0024`, `ADR/0001`–`0020`, `ADR/template.md`, the specification,
`IMPLEMENTATION_QUEUE.md`, and `PROJECT_STATE.json` do not appear anywhere in this branch's diff
against `main`.

## 14. Confirmation No Implementation Occurred

No database table, migration, backend model, service, route, frontend, or test was created or
modified. No schema or configuration file was touched. `ADR/0025` describes the target field
architecture; it implements none of it — stated explicitly in the ADR's own "Implementation
Boundary" section.

## 15. Confirmation No Governance Synchronization Occurred

`PROJECT_STATE.json` was not modified — confirmed absent from this branch's diff. `IMPLEMENTATION_QUEUE.md`
was not modified — confirmed absent; its existing T91 row is left exactly as authorized. No `T92`
was created or authorized. `T91` is not marked Done by this report or any file it changed — that
remains a post-QA, post-merge governance closeout step, per the established `T87`–`T90` three-PR
pattern.

## 16. Reviewer Checklist

Per `docs/prompts/SoftwareArchitect.md` §8's required output and
`docs/ImplementationLog/README.md`'s standard eleven-item self-assessment:

```
Reviewer Checklist

[x] Architecture preserved -- ADR/0021, ADR/0022, ADR/0023, ADR/0024 composed with, not modified
    or contradicted; S4 rules cited, not reinterpreted.
[x] Existing design patterns followed -- geography.py/Property.village_id FK reuse for
    RevenueRecord; Client.pan_number/aadhaar_number's CHECK-constraint mechanism named as
    precedent; ADR/0024's record_type discriminator populated, not redesigned.
[ ] Tests added -- none; documentation-only architecture task, no implementation authorized.
[ ] Existing tests pass -- not applicable; no code changed for the test suite to exercise.
[x] Documentation updated -- ADR/0025 and this report are the documentation this task produces.
[x] ADR updated (if required) -- ADR/0025 created (Required ADR #5 resolution); ADR/0021-0024 not
    touched, correctly.
[ ] AI_BOOTSTRAP updated (if required) -- not required by this task's authorized scope.
[ ] PROJECT_STATE updated (if required) -- deferred by design to post-QA governance
    synchronization, per T91's own governance lifecycle.
[ ] No unrelated refactoring -- not applicable; no code touched at all.
[x] No scope creep -- Required ADR #7 explicitly deferred with a dedicated section; #6 (already
    resolved by ADR/0024) not reopened; #8-#17/#20 not touched; only #5 resolved.
[x] Ready for QA -- ADR/0025 and this report are complete and handed off below.
```

## 17. Recommended QA Handoff

This branch (`docs/t91-adr-0025-revenue-citysurvey-tpfp-field-architecture`) is handed off to the QA
Reviewer role for an independent, formal QA Decision against the actual remote PR HEAD once opened —
per T91's own row and this repository's established documentation-only-work QA requirement
(`T80`–`T90` precedent). The QA Reviewer is specifically asked to independently verify the explicit
QA watch item named in T91's own authorization: that `ADR/0025`'s "Explicit #7 Deferral" section
genuinely keeps the TP/FP↔Scheme tension visible — checking, not merely trusting, that
`tp_scheme_number` is represented as a plain field with no structural Scheme relationship, and that
no part of the ADR silently resolves Required ADR #7 for field-model convenience.

## QA Decision

□ Approved
☑ Approved with comments
□ Rework required

This Software Architect pass does not record, anticipate, or imply any of the three outcomes above
— per `docs/prompts/SoftwareArchitect.md` §11/§13, this role never renders a QA Decision or
substitutes for the QA Reviewer. `ADR/0025` and this report are not self-certifying.

**Recorded by the QA Reviewer role (2026-08-27), against this exact commit
(`cd1010a622631acf6c9598df2133733ee100a00a`), independently verified, not accepted on this report's
word.** PR #127 confirmed open, base `main`, remote HEAD exactly `cd1010a6`; T91's authorization
commit `2554ad3b` confirmed an ancestor via `git merge-base --is-ancestor`; the single-commit diff
against `main` (`25c845d7`) confirmed as exactly two files (`ADR/0025-...md`,
`docs/reviews/T91_Software_Architect_Report.md`) — `ADR/0021`–`0024`, the specification,
`IMPLEMENTATION_QUEUE.md`, and `PROJECT_STATE.json` all absent from the diff; no `T92` row, branch,
or PR exists. §4 rules 19–24, §24.4's three ED field blocks (including the TP/FP↔Scheme boundary's
explicit assignment to Required ADR #7, not #6), §26 item 5, and §27's "Dependency ordering
coherence" self-check were independently read directly from
`docs/Legal_DMS — Domain Model & Functional Specification.md` and confirmed to match this ADR's
quotations verbatim — not accepted on the ADR's word. `geography.py` (the full
Country→State→District→Taluka→Village chain, no `organization_id`/`AuditMixin`), `property.py`
(`Property.village_id`'s existing nullable FK; `survey_number`/`sub_division_number` as unconstrained
`String` columns), and `client.py` (`pan_number`/`aadhaar_number`'s exact regex `CHECK` constraints)
were each read directly and confirmed to match the ADR's repository-precedent claims exactly. The
`properties:read`/`write`/`delete` permission codes were independently confirmed seeded in
`backend/alembic/versions/224b650e5235_seed_role_permissions.py`. A full-specification search
confirmed the PAN/Aadhaar regex-`CHECK` precedent is scoped only to Party/Client (§24.2, line ~2728)
and is never extended, analogized, or referenced anywhere in connection with Revenue/City-Survey/
TP-FP identifiers — the ADR's "no format rule exists" claim is accurate, not a gap this review found
and the ADR missed. `ADR/0024` was independently re-read in full: its `record_type` discriminator,
`property_record_references` mechanism, and "assessed, not resolved" treatment of both #5 and #7 are
composed with by `ADR/0025`, not redesigned or reopened, confirmed by direct comparison.

**#5 ↔ #7 boundary — independently verified, not merely asserted.** The ADR's "Explicit #7
Deferral" section and its `TPRecord.tp_scheme_number` field-table row were checked specifically
against the distinction this task's QA watch item requires: "TP/FP contains a scheme-number value"
(decided here, a #5 question — `tp_scheme_number` as a plain, non-FK `String` column) versus "TP/FP
has an architectural relationship to a Scheme entity" (explicitly and visibly left undecided — no
`scheme_id` FK, no structural link, the field's own table row states "architectural meaning of the
value: deferred to #7" directly, not merely in a separate section disconnected from the field
itself). This satisfies the watch item's specific requirement that the tension be *visibly
disclosed*, not silently resolved for field-model convenience: the deferral is named at the point of
decision (the field table), in a dedicated section, and again in "Consequences" and "Unresolved
Questions" — not asserted once and left to be taken on faith elsewhere in the document.

**Dependency review confirmed:** Required ADR #7 (Scheme hierarchy, TP/FP↔Scheme boundary) remains
fully deferred; Required ADR #20 (migration/backfill) is disclosed as dependencies only, not
designed or sequenced; Property↔Scheme cardinality is left exactly as open as `ADR/0024` left it;
`PropertyOwner`'s `client_id`→Party retargeting is confirmed untouched. No downstream ADR is
accidentally resolved.

Blocking findings: none.

Non-blocking comments (do not block approval):

1. **TP/FP table-structure alternatives.** The "Alternatives Considered" section's third option (a
   "generic renamed combined table") is, by the ADR's own admission, "a variant of option 1 with
   different naming" rather than a structurally independent alternative — the real evaluation is a
   two-way choice (one combined table vs. two separate tables), not a genuine three-way one. The ADR
   discloses this itself and does not misrepresent the choice as broader than it is, so this does not
   affect the decision's soundness; a future revision of this ADR's Alternatives section could
   simply merge options 1 and 3 for clarity.
2. **`NOT NULL` on each record's defining identifier.** Requiring `survey_number`/
   `city_survey_number`/`tp_scheme_number`/`fp_number` to be non-nullable is an architectural
   inference (purpose-fitness reasoning, plus `Property.survey_number`'s own existing non-nullable
   precedent) layered onto specification text that only labels these fields as ED candidates, not as
   frozen requirements. The inference is reasonable, consistent with existing repository convention,
   and disclosed rather than hidden — but it is this ADR's own architectural judgment call, not a
   specification mandate, and a future reviewer should recognize it as such if Gujarat-identifier
   nullability is ever revisited.

**QA Decision: Approved with comments.** ADR/0025 accurately reflects the governed specification's
sparse, ED-labeled field content for this cluster without inventing beyond it; composes with
ADR/0021/0022/0024 without reopening any of them; and explicitly, visibly, and repeatedly discloses
the #5↔#7 boundary this task's authorization specifically required to remain undecided. No
implementation code, schema, or governance file was touched. PR #127 remains open and unmerged.

---

**This report ends T91's authorized scope at the implementation PR handoff.** Per this task's own
governing instructions, T91 stops here, awaiting independent QA. No further action (opening/merging
a PR beyond the point specified below, creating T92, marking T91 Done, performing QA, governance
closeout) is taken by this pass.
