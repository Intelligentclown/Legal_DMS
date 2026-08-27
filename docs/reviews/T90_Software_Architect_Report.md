# T90 Software Architect Report

**Task:** T90 — Draft and resolve Required ADR #3 ("Property vs Matter independence" — boundary/
reference mechanism), #4 ("Land vs Property Unit"), and #6 ("Property Record Reference
architecture"), while assessing (not resolving) the dependency relationship with Required ADR #5
("Revenue vs City Survey") and #7 ("Flexible Scheme hierarchy"). Per
`docs/Legal_DMS — Domain Model & Functional Specification.md` §21's planning-list terminology. Full
authorized-scope text: `IMPLEMENTATION_QUEUE.md`'s T90 row.

**Role:** Software Architect, per `docs/prompts/SoftwareArchitect.md` (formally adopted, merged
`b5b3126`). This report follows that prompt's Required Output (§8) and Reviewer Checklist (§7 item
7) structure, and this task's own §13 requirements.

---

## 1. Repository Baseline Verification

- `git status`: clean working tree, on `main`, before any edit.
- `git fetch origin`: local `main` was **behind** `origin/main` by 2 commits at session start
  (local HEAD `ec68ac4`, `origin/main` at `fc5c116`). Fast-forwarded via `git merge --ff-only
  origin/main` — a clean fast-forward, no divergent local commits.
- Post-fast-forward: `main == origin/main` at `fc5c116092431e58249220dbc770be9c158c1d50`.
- Starting SHA recorded: `fc5c116092431e58249220dbc770be9c158c1d50`.

## 2. Authorization Verification

- `git merge-base --is-ancestor 26d092e HEAD` → **YES** (the T90 authorization commit
  "docs(governance): authorize T90" is an ancestor of `main`, confirmed post-fast-forward).
- `git log --oneline`: T90's authorization (`26d092e`, merged via PR #123, merge `fc5c116`)
  immediately follows T89's post-merge closeout (`6b9768a`/PR #122, merge `ec68ac4`) — no
  implementation commit of any kind appears between T89's closeout and the T90 authorization merge.
- `IMPLEMENTATION_QUEUE.md`'s T90 row, read in full directly from the file (not from the task
  prompt), confirms: Required ADR #3/#4/#6 bundled scope, matching §26 item 3's own bundling; the
  explicit "must treat as already established" list (`ADR/0021`/`ADR/0022`/`ADR/0023` all frozen,
  none to be reopened); the explicit statement that Property's independence from Matter (§4 rule
  15) is itself already frozen — this task decides the mechanism, not the independence; the
  explicit instruction that #5 and #7 must be *assessed*, not resolved, with reasoning grounded in
  the specification; the informal-role-turned-formal-role disclosure; the required-QA-before-merge
  statement; and the three-PR governance lifecycle this report follows steps (1)–(2) of. The task
  prompt's own framing matches this queue row precisely — no discrepancy of the kind found during
  T89 (where the task prompt's narrative framing diverged from the actual authorized scope).
- `T89 is now Done` — confirmed present in `IMPLEMENTATION_QUEUE.md`'s T89 row text.
- `ADR/0021`, `ADR/0022`, `ADR/0023` all exist (confirmed via `ls ADR/`).
- `ADR/0024` did **not** exist prior to this pass (confirmed via `ls ADR/0024*` failing before
  drafting).
- No `T91` reference exists anywhere in the repository — confirmed via a full-repository filename
  search (`find . -iname "*T91*"`, excluding `node_modules`/`.git`, zero matches) and a content grep
  of `IMPLEMENTATION_QUEUE.md` (the one match is T90's own "Explicitly outside scope" clause naming
  `T91` as something this authorization does *not* create — not an actual `T91` row) and
  `PROJECT_STATE.json` (zero matches).
- `businessFeatures` remains `[]`; `currentStage` remains `stage-3`/`in_progress` — confirmed via
  direct JSON read, unchanged.
- No unauthorized T90 implementation had already occurred: confirmed by the git log sequence above
  and by `git status`'s clean working tree at session start.

## 3. Authoritative Evidence Inspected

**Specification** (`docs/Legal_DMS — Domain Model & Functional Specification.md`), read in full
where cited:

- §4 rules 15–28 verbatim (Property, Gujarat Property Records, Scheme subsections).
- §24.3 Property & Land in full — Property's purpose, repository constraint, the "Gap vs. frozen
  architecture" note (the direct source of Required ADR #6's own framing), relationships, repository
  mapping, open engineering decisions; Land's purpose, repository constraint, and its own explicit
  three-option representation-strategy menu.
- §24.4 Gujarat Property Records in full — the cross-cutting rules-19–24 note; RevenueRecord,
  CitySurveyRecord, and TP/FP Record entity blocks; the TP/FP block's explicit assignment of the
  TP/FP↔Scheme boundary question to Required ADR #7, not #6; the PropertyRecordReference discussion
  naming the generic-linking-table-vs-direct-FK question as #6's to resolve.
- §24.5 Scheme in full — purpose, repository constraint, the rule-27/28-driven hierarchy-storage
  question (Required ADR #7), relationships (explicitly: no direct Scheme⟷Matter relationship).
- §9.4/§10.A's entity-to-repository-status mapping table and "New entities" list — confirmed
  `lands`, `schemes`, `scheme_nodes`/structure, `property_record_references`, `revenue_records`,
  `city_survey_records`, `tp_records`, `fp_records` are all named candidate tables, none yet
  implemented.
- §21's Required ADR items #3–#7 verbatim, including item #7's own explicit text assigning the
  TP/FP↔Scheme boundary to itself, not to #6.
- §12 and §26's "must resolve before implementation" tables, confirming all six Property/Land/
  Gujarat-records/Scheme items are blocking, and that §26 item 3 textually bundles #3/#4/#6 as one
  decision while listing #5 (item 5) and #7 (item 4) as separate, adjacent bullets — direct textual
  support for T90's own bundling and for #5/#7 being genuinely separable.
- §25 cross-domain invariant rows 5 and 6 — Revenue/City-Survey distinctness (fully preserved) and
  Land/Property-Unit non-conflation (only "Partially" preserved — the weakest confirmation status in
  the table, directly motivating this ADR).
- A full-document search for "PropertyUnit"/"Property Unit" — confirmed it is never given a §24
  entity definition anywhere; appears only in rule 18's constraint phrasing, a superseded §16
  pre-planning candidate-table list (itself flagged there as unresolved), a conditional scope item,
  and Required ADR #4's own title. This absence is the direct evidentiary basis for this ADR's
  Cluster A decision.

**Existing ADRs:**

- `ADR/template.md` — structure precedent.
- `ADR/0021-organization-tenant-boundary-enforcement.md` — re-confirmed (already read in full during
  T88/T89 sessions of this same role; content unchanged). Its mandatory-`organization_id`/
  application-layer-primary/RLS-backstop mechanism is composed with, not reopened.
- `ADR/0022-authorization-architecture.md` — re-confirmed (authored by this same role in the T88
  session). Its resource+action permission model, and its named concern about permission-surface
  fragmentation, are composed with, not reopened.
- `ADR/0023-party-vs-client-architecture.md` — re-confirmed (authored by this same role in the T89
  session). Its `MatterParty`-as-already-CBR treatment is the direct precedent this ADR mirrors for
  `MatterProperty`; its `PropertyOwner`/Party-retargeting touchpoint is cited as a disclosed,
  unresolved dependency, not decided here.
- Neither `ADR/0021`, `ADR/0022`, nor `ADR/0023` was modified — confirmed via `git diff --stat main`
  (below): none appears in this branch's diff.

**Repository implementation**, direct inspection, read-only:

- `backend/src/app/infrastructure/persistence/models/property.py` (full file) — `Property`
  (`property_type` discriminator, generic `survey_number`/`sub_division_number`, `area_value`/
  `area_unit`, `address_id`, denormalized `village_id`, `registration_number`), `PropertyOwner`
  (conventional real-FK join to `clients`).
- A full grep of `backend/src/app` confirmed zero implementation exists for `Land`, `PropertyUnit`,
  `RevenueRecord`, `CitySurveyRecord`, TP/FP (any spelling), `Scheme`, or `PropertyRecordReference`.
- `backend/alembic/versions/` — confirmed only one property-related migration
  (`7789f56da7f9_properties_properties_property_owners.py`), matching `property.py` 1:1; zero
  migrations exist for any target entity.
- The codebase's existing polymorphic-reference convention — `ActivityLog`, `AuditLog`,
  `WorkflowHistory`, `QrCodeRecord`, `AiRequest` — confirmed as five separate, already-shipped,
  already-`docs/ERD.md`-documented instances of the `entity_type`+`entity_id`-shaped pattern,
  including the explicitly-disclosed no-enforced-FK trade-off. `PropertyOwner` confirmed as the
  contrasting conventional-join-table precedent (real FKs both sides).
- `docs/CHANGELOG.md` and `docs/ERD.md` — confirmed the actual documented rationale for
  `properties.village_id`'s denormalization (the `property.py` docstring's own claimed location,
  "`docs/Database.md`'s Risks section," does not exist as written — a minor pre-existing doc-drift
  point, noted for completeness, not something this ADR needed to or did correct, since
  `docs/Database.md` is not this task's file to modify).

## 4. Decisions Made

- **Required ADR #3** (Property vs Matter independence, boundary/reference mechanism): resolved by
  confirming `Property` stays fully generic — no Revenue/City-Survey/TP-FP-specific column is added
  to it; all record-system detail lives in linked entities reached via `property_record_references`.
  Independence itself (rule 15) is not reopened; `MatterProperty` (already CBR per §24.3) is not
  redesigned, mirroring `ADR/0023`'s identical treatment of `MatterParty`.
- **Required ADR #4** (Land vs Property Unit): resolved as a naming/representation clarification,
  not new entities — "Land" is realized by `RevenueRecord` (directly supported by rule 20's "Revenue/
  Land model" phrasing and Land's own "Revenue-oriented" purpose text); "Property Unit" is realized
  by `CitySurveyRecord` (directly supported by rule 21's "may identify property units" phrasing and
  `CitySurveyRecord`'s own purpose text). No `lands` or `property_units` table is created. Rule 18's
  non-conflation requirement is satisfied because rule 19 already independently requires
  `RevenueRecord`/`CitySurveyRecord` to stay distinct.
- **Required ADR #6** (Property Record Reference architecture): resolved as a generic, typed,
  polymorphic linking table (`property_record_references`: `property_id` real-FK, `record_type`
  discriminator, `record_id` unenforced-FK) — following this codebase's own five-times-precedented,
  `docs/ERD.md`-documented convention, selected specifically because it satisfies rule 24's
  extensibility requirement (a fifth record system needs zero schema change) more strongly than
  either FK-based alternative evaluated.

## 5. Alternatives Considered

**Cluster A (Land):** own table (rejected — no distinguishing content evidenced anywhere in §24);
Property subtype (rejected — contradicted by the Gap note's own working assumption that Property
stays generic); folded into `RevenueRecord` (**selected**). **Cluster A (Property Unit):** own
table (rejected — same reasoning); Property subtype (rejected — same reasoning); realized by
`CitySurveyRecord` (**selected**). Both selections scored against 5 criteria in a comparison table
(textual support, unevidenced-entity avoidance, consistency with the Gap note, schema/query
simplicity).

**Cluster B (record-reference mechanism):** direct FKs on `Property` (rejected — weak extensibility,
new column per record system); a typed mutually-exclusive-FK link table (rejected — same
extensibility weakness as direct FKs, higher complexity, "not merely not selected" but scored worse
than both alternatives); a generic polymorphic linking table (**selected** — strongest extensibility,
direct repository precedent 5x, matches this codebase's own already-accepted referential-integrity
trade-off). Scored against 6 criteria (referential integrity, extensibility, repository consistency,
query complexity, implementation complexity, auditability).

## 6. Dependency Analysis — Required ADR #5 and #7

**Required ADR #5 (Revenue/City-Survey/TP-FP exact field sets): assessed, not resolved.** This
ADR's own "Relationship to Required ADR #5" section states the reasoning directly: Cluster A/B's
decisions require only that `RevenueRecord`/`CitySurveyRecord`/TP-FP records *exist*, are
*distinct*, and have a *stable UUID identity* — never their actual column lists, format-validation
rules, or geography-hierarchy relationships. The stable interface #5 will later populate (the
`record_type` value set and each target table's bare existence) is named explicitly in the ADR, so
a future architect resolving #5 has a fixed contract to build against without needing to revisit
this ADR.

**Required ADR #7 (Scheme hierarchy / TP-FP↔Scheme boundary): assessed, not resolved.** TP/FP
Record is treated as one more `record_type` value in `property_record_references` — its eventual
relationship to whatever "Scheme" turns out to mean is orthogonal to the mechanism this ADR decides,
and §24.4 itself already assigns that specific boundary question to #7, not #6. This ADR's own
"Relationship to Required ADR #7" section preserves that assignment explicitly and states neither
Cluster A nor Cluster B required any decision about Scheme to reach coherence.

Both dependency assessments conclude **"yes, #3/#4/#6 are resolvable now without prematurely
deciding #5 or #7"** — consistent with §26 item 3's own textual bundling of #3/#4/#6 as one decision,
separate from item 4 (#7) and item 5 (#5).

## 7. Frozen-Business-Rule Protection

```
[x] S4 rules 15-17 (Property independence from Matter) -- cited as already-settled input, not
    reopened; this ADR resolves the mechanism/boundary, not the independence itself.
[x] S4 rule 18 (Land/Property-Unit non-conflation) -- cited as already-settled input; satisfied by
    this ADR's decision via rule 19's independent RevenueRecord/CitySurveyRecord distinctness
    requirement, not reinterpreted.
[x] S4 rules 19-24 (Gujarat records distinctness and extensibility) -- cited as already-settled
    inputs, directly informing Cluster A/B's decisions; none reinterpreted.
[x] S4 rules 25-28 (Scheme independence, multi-Scheme ownership, flexible/non-mandatory hierarchy)
    -- cited only for context in the #7 dependency assessment; not decided or reinterpreted.
[x] ADR/0021, ADR/0022, ADR/0023 composed with, not modified -- confirmed via git diff --stat
    (below): none appears in this branch's diff.
[x] No new business rule invented merely because a modeling choice would be convenient -- the
    Land=RevenueRecord and PropertyUnit=CitySurveyRecord decisions are schema-shape/naming
    clarifications justified by direct textual citation (rule 20, rule 21), not business-rule
    restatements.
[x] Genuinely unresolved business questions identified, not silently decided -- exact field sets
    (#5), Scheme hierarchy/TP-FP boundary (#7), Property<->Scheme cardinality, PropertyOwner's
    Party retargeting, multi-reference-per-record-type cardinality, and subdivision/combination
    semantics are all explicitly named as unresolved in ADR/0024's own "Explicitly Unresolved
    Items" section.
```

## 8. ADR Composition

- **`ADR/0021`:** every new table this ADR implies (`revenue_records`, `city_survey_records`,
  `tp_records`/`fp_records`, `property_record_references`) requires mandatory `organization_id`
  under `ADR/0021`'s existing rule; `ADR/0024` states explicitly that the linking table itself must
  carry its own `organization_id` rather than relying on an implicit join-derived scope, consistent
  with `ADR/0021`'s own explicit-value-threading requirement.
- **`ADR/0022`:** Property and its linked record entities are governed by the existing
  `properties:read`/`write`/`delete` permission codes (confirmed already seeded) rather than
  fragmented per record type, mirroring `ADR/0023`'s identical reasoning for Party subtypes —
  reinforcing, not complicating, `ADR/0022`'s resource+action model.
- **`ADR/0023`:** the only touchpoint is `PropertyOwner`'s eventual retargeting from `client_id` to
  Party, explicitly named as unresolved and left exactly as open as before.

## 9. Unresolved Questions (Named, Not Silently Dropped)

- Required ADR #5 (exact field sets for Revenue/City-Survey/TP-FP records) — assessed as separable,
  not resolved.
- Required ADR #7 (Scheme hierarchy storage mechanism; TP/FP↔Scheme conceptual boundary) — assessed
  as separable, not resolved.
- Whether TP and FP end up as one table or two — left to #5.
- Property↔Scheme's exact cardinality — §24.3's own open item, coupled to #7, not decided here.
- `PropertyOwner`'s retargeting from `client_id` to a Party reference — §24.3's own open item,
  coupled to `ADR/0023`, not decided here.
- Whether a Property may hold multiple `property_record_references` rows of the same `record_type`
  — a cardinality detail of the mechanism this ADR does decide, left open.
- Subdivision/combination identity semantics — not addressed anywhere in the frozen specification;
  not invented here.
- Required ADR #8–#17 and #20 — fully open, unaffected by this ADR beyond the disclosed
  `properties.survey_number`→`revenue_records` migration-sequencing dependency now recorded against
  #20.

## 10. Exact Files Changed

```
$ git status
On branch docs/t90-adr-0024-property-land-record-reference
Untracked files:
  ADR/0024-property-land-propertyunit-record-reference.md
  docs/reviews/T90_Software_Architect_Report.md

$ git diff --stat main
(empty prior to this commit -- both files are new, untracked)
```

Exactly two new files, both documentation. No existing file was modified — confirmed `ADR/0021`,
`ADR/0022`, `ADR/0023`, `ADR/0001`–`0020`, `ADR/template.md`, the specification,
`IMPLEMENTATION_QUEUE.md`, and `PROJECT_STATE.json` do not appear anywhere in this branch's diff
against `main`.

## 11. Confirmation No Implementation Occurred

No database table, migration, backend model, service, route, frontend, or Electron code was
created or modified. No test was added or modified. No schema or configuration file was touched.
`ADR/0024` describes the target architecture; it implements none of it.

## 12. Confirmation No Governance Synchronization Occurred

`PROJECT_STATE.json` was not modified — confirmed absent from this branch's diff. `IMPLEMENTATION_QUEUE.md`
was not modified — confirmed absent; its existing T90 row is left exactly as authorized. No `T91`
was created or authorized. `T90` is not marked Done by this report or by any file it changed — that
remains a post-QA, post-merge governance closeout step performed by a different role, per the
established `T87`/`T88`/`T89` three-PR pattern.

## 13. Reviewer Checklist

Per `docs/prompts/SoftwareArchitect.md` §8's required output and `docs/ImplementationLog/README.md`'s
standard eleven-item self-assessment:

```
Reviewer Checklist

[x] Architecture preserved -- ADR/0021, ADR/0022, ADR/0023 composed with, not modified or
    contradicted; S4/S23 frozen rules cited, not reinterpreted.
[x] Existing design patterns followed -- extends the codebase's own five-times-precedented
    polymorphic-reference convention (ActivityLog/AuditLog/WorkflowHistory/QrCodeRecord/AiRequest);
    mirrors ADR/0023's already-established MatterParty-as-CBR treatment for MatterProperty.
[ ] Tests added -- none; documentation-only architecture task, no implementation authorized.
[ ] Existing tests pass -- not applicable; no code changed for the test suite to exercise.
[x] Documentation updated -- ADR/0024 and this report are the documentation this task produces.
[x] ADR updated (if required) -- ADR/0024 created (Required ADR #3/#4/#6 resolution); ADR/0021,
    ADR/0022, ADR/0023 not touched, correctly.
[ ] AI_BOOTSTRAP updated (if required) -- not required by this task's authorized scope.
[ ] PROJECT_STATE updated (if required) -- deferred by design to post-QA governance
    synchronization, per T90's own governance lifecycle.
[ ] No unrelated refactoring -- not applicable; no code touched at all.
[x] No scope creep -- Required ADR #5 and #7 explicitly assessed, not resolved; #8-#17/#20 not
    touched; only #3/#4/#6 resolved.
[x] Ready for QA -- ADR/0024 and this report are complete and handed off below.
```

## 14. Recommended QA Handoff

This branch (`docs/t90-adr-0024-property-land-record-reference`) is handed off to the QA Reviewer
role for an independent, formal QA Decision against the actual remote PR HEAD once opened — per
T90's own row and this repository's established documentation-only-work QA requirement
(`T80`/`T81`/`T82`/`T86`/`T87`/`T88`/`T89` precedent). The QA Reviewer is specifically asked to
independently verify: (1) that Cluster A's "Land = RevenueRecord" and "Property Unit =
CitySurveyRecord" readings are correctly grounded in rule 20/21's actual text and not an
overreach; (2) that the #5/#7 dependency assessment's "no, they are not required to make #3/#4/#6
coherent" conclusion holds up against §24.4's own explicit TP/FP↔Scheme boundary assignment to #7;
(3) that no implementation occurred and no other Required ADR was touched.

## QA Decision

□ Approved
□ Approved with comments
□ Rework required

This Software Architect pass does not record, anticipate, or imply any of the three outcomes above
— per `docs/prompts/SoftwareArchitect.md` §11/§13, this role never renders a QA Decision or
substitutes for the QA Reviewer. `ADR/0024` and this report are not self-certifying.

---

**This report ends T90's authorized scope at the implementation PR handoff.** Per this task's own
governing instructions, T90 stops here, awaiting independent QA. No further action (opening/merging
a PR beyond the point specified below, creating T91, marking T90 Done, performing QA, governance
closeout) is taken by this pass.
