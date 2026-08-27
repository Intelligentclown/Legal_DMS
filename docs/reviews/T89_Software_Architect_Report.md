# T89 Software Architect Report

**Task:** T89 — Draft and resolve Required ADR #2 ("Party vs Client"), per
`docs/Legal_DMS — Domain Model & Functional Specification.md` §21's planning-list terminology. Full
authorized-scope text: `IMPLEMENTATION_QUEUE.md`'s T89 row.

**Role:** Software Architect, per the now-formally-adopted `docs/prompts/SoftwareArchitect.md`
(merged `b5b3126`, itself a role-adoption formalization of the informal precedent
`ADR/0001`–`0022` were already produced under — not a new responsibility, per that file's own
governance note). This report follows that prompt's Required Output (§8) and Reviewer Checklist
(§7 item 7) structure, and this task's own Section 12 requirements.

---

## 1. Repository Baseline Verification

Verified independently this session, not taken from the task prompt's claimed state alone:

- `git status`: clean working tree, on `main`, before any edit.
- `git fetch origin` + `git rev-parse HEAD`/`origin/main`: both `b5b3126e0bf3edda98e163dbd354489df37d73ce`
  — `main == origin/main`, no fast-forward needed this session (unlike T88's session start).
- Starting SHA recorded: `b5b3126e0bf3edda98e163dbd354489df37d73ce`.

## 2. Authorization Verification

- `git merge-base --is-ancestor 48fd8fd975e2a1a400f8ffdbab50695b69d0d7fe HEAD` → **YES**, the T89
  authorization merge commit is an ancestor of `main`.
- `git log --oneline`: confirms the exact sequence claimed —
  `3b656c6` ("docs(governance): authorize T89") merged via PR #119 (merge `48fd8fd`); T88's own
  post-merge closeout (`5112cc3`/PR #118) precedes it; the Software Architect role-adoption
  (`386caa1`/PR #120, merge `b5b3126`) follows it. No implementation commit of any kind appears
  between the T89 authorization merge and `HEAD`.
- `IMPLEMENTATION_QUEUE.md`'s T89 row, read in full directly from the file (not from the task
  prompt), confirms: Required ADR #2 scope; the explicit "must treat as already established" list
  (Organization is the tenant boundary per `ADR/0021`; authorization composes with tenant isolation
  per `ADR/0022`; neither ADR is this task's to revisit); the approved-scope sentence naming the
  three subtype-modeling candidates **and** the explicit consistency requirement with "§4 rule 8/9
  (Party is the reusable master record; Client is a Matter relationship/status, not a master entity
  or Party subtype)"; the informal-role disclosure; the required-QA-before-merge statement; and the
  three-PR governance lifecycle this report follows steps (1)–(2) of.

  **This is the one point requiring explicit note**, per this task's own Repository-First Rules
  (trust the repository, report the discrepancy): the task prompt's own Section 4/6.A framing
  ("whether Client should be a subtype of Party, a role/capability, a separate entity... Do not
  assume the answer") reads as if the Party/Client *identity* question were still open. It is not —
  `IMPLEMENTATION_QUEUE.md`'s own authorization text (quoted above) already cites §4 rule 8/9 as the
  binding constraint, and §24.2/§23 of the specification confirm that identity question was frozen
  independently of this task. This is not a conflict between the authorized scope and a frozen
  business rule (the two are consistent with each other) — it is the task prompt's narrative framing
  reading the §21 label "Party vs Client" at face value without §24.2's own disambiguation. Per this
  role's Repository-First Rules and Frozen-Business-Rule Protection, the repository (queue +
  specification) is treated as authoritative; the task prompt's framing is not followed where it
  would have required re-deciding an already-frozen rule. See §3 (Specification) and §6 (Findings)
  below for the full evidence trail, and `ADR/0023`'s own "Problem" section for where this is
  recorded permanently.
- `ADR/0021` and `ADR/0022` both exist (confirmed via `ls ADR/`).
- `ADR/0023` did **not** exist prior to this pass (confirmed via `ls ADR/0023*` failing before
  drafting).
- No `T90` reference exists anywhere in the repository — confirmed via a full-repository filename
  search (`find . -iname "*T90*"`, excluding `node_modules`/`.git`, zero matches) and a content grep
  of `IMPLEMENTATION_QUEUE.md` (the one match found is the T89 row's own "Explicitly outside scope"
  clause naming `T90` as something this authorization does *not* create — not an actual `T90` row)
  and `PROJECT_STATE.json` (zero matches).
- No unauthorized T89 implementation had already occurred: confirmed by the git log sequence above
  (nothing between the T89 authorization merge and `HEAD`) and by `git status`'s clean working tree
  at session start.

## 3. Specification Sections Examined

Read directly from `docs/Legal_DMS — Domain Model & Functional Specification.md`, in full where
cited, not sampled:

- **§1.6** "Highest risks," item 2 ("Treating `Client` as the equivalent of `Party`") and the
  business-discovery document's own parallel highest-risk list (item 1, "Current `Client` model vs
  finalized Party architecture," lines ~2480).
- **§4** rules 8–14 ("Party/Client" subsection) in full.
- **§12** "Remaining Engineering Decisions" table ("Exact Party subtype strategy — Must decide
  before implementation").
- **§21** "Required ADRs" planning list, item 2 ("Party vs Client"), and its own terminology note
  distinguishing planning-list positions from repository ADR filenames.
- **§23** "Final Executive Decision" — the frozen-concept list naming `Party` and
  `Client-as-relationship` as separate line items, and the confirmed 46-rule count.
- **§24.2 Party** in full — Purpose, Identity & tenant ownership, Business invariants, Subtype
  strategy (the three named candidates), Fields, Relationships, Lifecycle, Authorization, Audit,
  Search requirements, Repository mapping, Open engineering decisions.
- **§24.2 PartyRelationship** and **§24.2 Representative** in full — read to understand downstream
  relationship semantics; neither redesigned by this ADR.
- **§24.6 Enquiry** and **§24.6 Quotation** in full — Party relationship semantics (Enquiry⟷Party
  many-to-one at minimum; Quotation⟷Enquiry; Quotation⟷Matter on acceptance).
- **§24.7 Matter** and **§24.7 MatterParty** in full — the join entity realizing §4 rule 9, its role
  field, and its own (separately unresolved) open items.
- **§24.11 Communication** in full — Communication⟷Party/Representative participant relationships.
- **§25** cross-domain invariant table, rows 1–2 (Party-Matter multiplicity) and row 12
  (authorization bypass surface, for consistency with `ADR/0022`'s own already-recorded findings).
- **§26** "Consolidated Unresolved Engineering Decisions," item 1 ("Party subtype-modeling strategy
  (§24.2; Required ADR #2)") and item 10 (Matter's `client_id` retirement, the migration dependency
  this ADR discloses to Required ADR #20).

## 4. Existing ADRs Examined

- `ADR/template.md` — structure precedent.
- `ADR/0021-organization-tenant-boundary-enforcement.md` — read in full this session (already read
  in full during T88; re-confirmed, not re-read line-by-line, since its content is unchanged and
  already verified). Its tenant-scoping mechanism (mandatory `organization_id`, application-layer
  primary enforcement, `FORCE`d default-deny RLS backstop) is composed with, not reopened, by
  `ADR/0023`.
- `ADR/0022-authorization-architecture.md` — same basis (authored by this same role in the prior
  T88 session; content re-confirmed against the current file, not re-derived). Its resource+action
  permission model and its resource-instance-authorization extension point are composed with, not
  reopened, by `ADR/0023`.
- Neither `ADR/0021` nor `ADR/0022` was modified — confirmed via `git diff --stat main` (below):
  neither file appears in this branch's diff.

## 5. Repository Implementation Inspected

Direct inspection, `main` at `b5b3126`, read-only:

- `backend/src/app/infrastructure/persistence/models/client.py` (full file) — `Client`
  (`client_type` discriminator, `CHECK`-validated `pan_number`/`aadhaar_number`, `full_name`,
  `primary_phone`, `primary_email`, `address_id`, `notes`), `ClientContact` (partial `Representative`
  precedent), `Address` (reused unchanged).
- A full grep of `backend/src/app/infrastructure/persistence/models/*.py` (all twelve model
  modules) confirmed: no `Party`, `MatterParty`, `PartyRelationship`, `Representative`, `Enquiry`,
  `Quotation`, or `Communication` table exists anywhere; zero SQLAlchemy `relationship()` or
  joined-table/single-table polymorphic inheritance mapping exists anywhere (every model is a flat
  `Base`/`AuditMixin`/`OptimisticLockMixin` class with plain columns and `ForeignKey`s only);
  existing subtype-like distinctions elsewhere in this codebase (`Address.address_type`,
  `Role.is_system_role`, `Permission.category`) all use flat discriminator/flag columns, never a
  base-plus-extension-table pattern.
- `activity.py` and `system.py` — confirmed the codebase's existing JSONB usage
  (`activity_logs.details`, `system.py`'s `config`/`payload`/`result` columns) is exclusively for
  free-form, non-format-validated, non-searched metadata — a materially different use case from
  Party's identity-bearing, format-validated, individually-searchable subtype fields.
- `matters.client_id`/`matters.property_id` — confirmed today's single-valued foreign keys, the
  concrete manifestation of §25 invariant #1/#2's "currently impossible" status for multi-party
  Matters.
- No `backend/tests/` file testing Party/Client-subtype behavior beyond the existing
  `test_client_models.py` (inspected, not modified) — confirms no partial Party implementation
  exists to reconcile against.

## 6. Party/Client Findings

- The Party/Client **identity** question (subtype vs. role vs. separate entity) is already frozen
  by §4 rule 8/9 and §23's "Client-as-relationship" line item, independently confirmed by §1.6's
  and the business-discovery document's shared highest-risk warning against treating `Client` as
  equivalent to `Party`. This is not this ADR's decision, and is not treated as one.
- The mechanism realizing that frozen rule (`MatterParty.role`, with "Client" as one of its values)
  is itself already specified as CBR in §24.7 — cited and relied upon by `ADR/0023`, not redesigned
  by it. `MatterParty`'s own remaining open items (role vocabulary, minimum cardinality) are a
  different, unauthorized-here decision.
- The genuinely open question §21/§24.2/§26 all actually attach to "Required ADR #2" is the **Party
  subtype-modeling strategy** — three named candidates (single-table discriminator, class-table
  inheritance, JSONB profile blob).
- This repository has a real, working, tested precedent for the discriminator-column approach
  (`Client.client_type`), zero precedent for ORM-level inheritance anywhere, and existing JSONB
  usage confined to a materially different (non-identity, non-validated, non-searched) use case —
  three independent, repository-grounded signals all pointing the same direction.
- No existing `Party` implementation exists to reconcile against; `Client` is confirmed, by the
  specification's own text and by direct inspection, not to be a rename target for `Party`.

## 7. Alternatives Considered

**Tier 1 (Party/Client identity — not a live choice, evaluated only for traceability, per this
task's own instruction):** Client-as-Party-subtype/inheritance (rejected — contradicted by frozen
§4 rule 9/§23, the exact §1.6 highest-risk mistake); Client-as-role/capability-on-Party (**already
the frozen architecture** via `MatterParty.role`, not a choice this ADR makes); Party-and-Client-as-
separate-entities (rejected — contradicted by the same frozen rules). All three rejections/
confirmations are business-rule-grounded, not architectural-quality judgments — `ADR/0023`'s own
"Options Considered" section states this distinction explicitly.

**Tier 2 (Party subtype-modeling strategy — the actual decision, 3 options scored against 10
criteria including domain fidelity, field-level integrity, searchability, migration cost,
consistency with existing Legal_DMS architecture, and compatibility with `ADR/0021`/`ADR/0022`):**
single-table with a `CHECK`-constrained discriminator column (**selected** — direct working
precedent, zero-ORM-inheritance codebase convention, proven `CHECK`-constraint format validation,
direct `SearchQuery`/`FilterSpec` compatibility); class-table inheritance (rejected — zero
precedent anywhere in this codebase, would require new, unauthorized ORM/repository infrastructure,
higher per-subtype migration cost; not rejected as architecturally unsound in the abstract);
JSONB profile blob (rejected specifically for identity-bearing, format-validated, searchable
fields — this codebase's existing JSONB usage is confined to a materially different, free-form,
non-searched use case; not a rejection of JSONB as a technology generally).

## 8. Selected Architecture

Party's subtype dimension is modeled as a single `parties` table with a `CHECK`-constrained
discriminator column and nullable subtype-specific fields, directly extending — not reinventing —
this codebase's own existing `Client.client_type` pattern. No migration, table, or column is
created by this ADR; it fixes the target shape only. Full detail: `ADR/0023`'s "Decision," "Data-
Model Implications," and "API / Query Implications" sections.

## 9. Relationship to ADR-0021

`ADR/0021` is not modified, reopened, or reinterpreted. `ADR/0023` states explicitly that
`parties.organization_id` is mandatory under `ADR/0021`'s already-decided rule (mandatory
application-layer scoping as primary mechanism, `FORCE`d default-deny RLS as backstop), that this
requirement is orthogonal to the subtype-modeling decision (identical under any of the three
Tier-2 options), and that `MatterParty`/`PartyRelationship`/`Representative` — none redesigned here
— independently inherit the identical requirement once their own architecture is decided.

## 10. Relationship to ADR-0022

`ADR/0022` is not modified, reopened, or reinterpreted. `ADR/0023` states explicitly that Party
access is governed by `ADR/0022`'s existing resource+action, role-indirected permission model (a
future `parties:read`/`parties:write`-style code, checked once at the service/use-case boundary),
that the single-table approach keeps this a single permission surface (avoiding a per-subtype-table
permission-drift risk class-table inheritance could have invited), and that §24.2's own
explicitly-unresolved Party-level-confidentiality question — not decided by this ADR, per T89's own
scope exclusion — is, if and when a future ADR decides it, a consumer of `ADR/0022`'s already-
established resource-instance-authorization extension point, not a new authorization architecture.

## 11. Frozen-Business-Rule Verification

```
[x] §4 rule 8 (Party is the reusable master record) -- cited as already-settled input, not
    reinterpreted.
[x] §4 rule 9 (Client is a Matter relationship/status, not a master entity) -- cited as
    already-settled input, not reinterpreted or reopened; explicitly distinguished from this
    ADR's actual (different) decision.
[x] §4 rules 10-14 -- cited as already-settled inputs (multi-party Matters, many-Matter Party
    participation, role-varies-per-Matter, multiple Representatives, joint authorization); none
    reinterpreted.
[x] §23's frozen-concept list ("Party" / "Client-as-relationship") -- not altered; cited verbatim
    as confirming evidence.
[x] No new business rule invented merely because a modeling choice would be convenient -- the
    subtype-modeling decision is a schema-shape choice justified by repository precedent, not a
    business-rule restatement or extension.
[x] Genuinely unresolved business questions identified, not silently decided -- exact subtype
    vocabulary, exact field list per subtype, Party-merge/deduplication, and Party-level
    confidentiality are all explicitly named as unresolved in ADR/0023's own "Explicitly Unresolved
    Items" section, each with its reason for being out of T89's scope.
[x] ADR/0021 and ADR/0022 composed with, not modified -- confirmed via git diff --stat (below):
    neither file appears in this branch's diff.
```

## 12. Unresolved Questions (Named, Not Silently Dropped)

- Exact Party subtype vocabulary beyond `individual`/`organization` (trust, government body, etc.)
  and the exact field list per subtype — excluded from T89's authorized scope.
- Party-merge/deduplication — excluded.
- Party-level (or subtype-level) confidentiality (§4 rule 45's applicability to Party) — excluded;
  composition path with `ADR/0022`'s extension point named for whenever it is decided.
- `MatterParty`'s role vocabulary and minimum-cardinality question — a different entity's own open
  item (§24.7), not part of Required ADR #2.
- `PartyRelationship`'s relationship-type vocabulary and directionality — a different open item.
- `Representative`'s authorization-basis vocabulary and Document-evidence requirement — a different
  open item.
- Required ADR #3–#17 and #20 — fully open, unaffected by this ADR beyond the disclosed
  `clients`→`parties` migration dependency now recorded against #20.

## 13. Exact Files Changed

```
$ git status
On branch docs/t89-adr-0023-party-client
Untracked files:
  ADR/0023-party-vs-client-architecture.md
  docs/reviews/T89_Software_Architect_Report.md

$ git diff --stat main
(empty prior to this commit -- both files are new, untracked)
```

Exactly two new files, both documentation: `ADR/0023-party-vs-client-architecture.md` and this
report. No existing file was modified — confirmed `ADR/0021`, `ADR/0022`, `ADR/0001`–`0020`,
`ADR/template.md`, the specification, `IMPLEMENTATION_QUEUE.md`, and `PROJECT_STATE.json` do not
appear anywhere in this branch's diff against `main`.

## 14. Confirmation No Implementation Occurred

No database schema, migration, backend, frontend, or API implementation was performed. No `Party`,
`MatterParty`, `PartyRelationship`, `Representative`, `Enquiry`, `Quotation`, or `Communication`
model, repository, service, or route file was created or modified. No test was added or modified —
`test_client_models.py` and all other existing tests were read-only inspections. `ADR/0023`
describes what a future implementation task must do; it does not implement any of it.

## 15. Confirmation No Governance Synchronization Occurred

`PROJECT_STATE.json` was not modified — confirmed absent from this branch's diff; `businessFeatures`
and `currentStage` remain whatever `main`'s current values are, untouched by this pass.
`IMPLEMENTATION_QUEUE.md` was not modified — confirmed absent from this branch's diff; its existing
T89 row is left exactly as authorized. No `T90` was created or authorized. `T89` is not marked Done
by this report or by any file it changed — that remains a post-QA, post-merge governance closeout
step performed by a different role, per the established `T87`/`T88` three-PR pattern.

## 16. Reviewer Checklist

Per `docs/prompts/SoftwareArchitect.md` §8's required output and `docs/ImplementationLog/README.md`'s
standard eleven-item self-assessment format:

```
Reviewer Checklist

☑ Architecture preserved -- ADR/0021 and ADR/0022 composed with, not modified or contradicted;
  §4/§23 frozen rules cited, not reinterpreted.
☑ Existing design patterns followed -- extends Client.client_type's proven discriminator-column
  pattern; matches this codebase's confirmed zero-ORM-inheritance convention.
□ Tests added -- none; documentation-only architecture task, no implementation authorized.
□ Existing tests pass -- not applicable; no code changed for the test suite to exercise.
☑ Documentation updated -- ADR/0023 and this report are the documentation this task produces.
☑ ADR updated (if required) -- ADR/0023 created (required ADR #2 resolution); ADR/0021/0022 not
  touched, correctly.
□ AI_BOOTSTRAP updated (if required) -- not required by this task's authorized scope; not touched.
□ PROJECT_STATE updated (if required) -- deferred by design to post-QA governance synchronization,
  per T89's own governance lifecycle; correctly not done by this role/pass.
□ No unrelated refactoring -- not applicable in the sense that nothing was refactored; no code
  touched at all.
☑ No scope creep -- Tier 1 (Party/Client identity) explicitly treated as already-frozen, not
  re-decided; MatterParty/PartyRelationship/Representative/Enquiry/Quotation/Communication's own
  open items explicitly named as out of scope, not resolved; only Required ADR #2 resolved.
☑ Ready for QA -- ADR/0023 and this report are complete and handed off below.
```

## 17. Recommended QA Handoff

This branch (`docs/t89-adr-0023-party-client`) is handed off to the QA Reviewer role for an
independent, formal QA Decision (`Approved` / `Approved with comments` / `Rework required`) against
the actual remote PR HEAD once opened — per T89's own row ("the eventual ADR PR must independently
undergo QA, re-verified on its actual remote PR HEAD, before any merge") and this repository's
established documentation-only-work QA requirement (`T80`/`T81`/`T82`/`T86`/`T87`/`T88` precedent).

**QA Decision — not rendered by this pass:**

```
QA Decision

□ Approved
□ Approved with comments
□ Rework required
```

This Software Architect pass does not record, anticipate, or imply any of the three outcomes above
— per `docs/prompts/SoftwareArchitect.md` §11/§13, this role never renders a QA Decision or
substitutes for the QA Reviewer. `ADR/0023` and this report are not self-certifying. The QA Reviewer
is specifically asked to independently verify the one non-obvious judgment call this report makes
explicit in §2 above: that the task prompt's Section 4/6.A framing of "Party vs Client" as an open
identity question is superseded by the actually-authorized `IMPLEMENTATION_QUEUE.md` T89 row and the
specification's own §24.2/§23 text, and that `ADR/0023` correctly resolves the *subtype-modeling*
question rather than re-deciding the already-frozen identity question.

---

**This report ends T89's authorized scope at the implementation PR handoff.** Per this task's own
governing instructions, T89 stops here, awaiting independent QA. No further action (opening/merging
a PR beyond the point specified below, creating T90, marking T89 Done, performing QA) is taken by
this pass.
