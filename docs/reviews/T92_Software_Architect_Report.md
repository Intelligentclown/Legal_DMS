# T92 Software Architect Report

**Task:** T92 — Draft and resolve Required ADR #7 ("Flexible Scheme hierarchy," including the
TP/FP-Record ↔ Scheme conceptual boundary), per
`docs/Legal_DMS — Domain Model & Functional Specification.md` §21's planning-list terminology. Full
authorized-scope text: `IMPLEMENTATION_QUEUE.md`'s T92 row.

**Role:** Software Architect, per `docs/prompts/SoftwareArchitect.md` (formally adopted, PR #120).

This report follows `docs/reviews/T88_Software_Architect_Report.md`/`T89_.../T91_...`'s established
shape for a pure documentation/architecture task with no Stage/Phase implementation association.

---

## 1. Repository Baseline / Authorization Verification

Verified independently this session, not taken from the task prompt's claimed state alone:

- `git fetch origin` + `git checkout main` + `git merge --ff-only origin/main`: clean fast-forward,
  no divergent local commits, working tree clean before and after.
- `main == origin/main` at `ed1466dd38f0f28ce103135fa0647e0f62f844d6`, the T92 authorization merge
  commit — confirmed directly, not assumed.
- `IMPLEMENTATION_QUEUE.md`'s T92 row, read in full directly from the file (not from the task
  prompt), confirms: Required ADR #7 scope; the explicit "must treat as already established" list
  (`ADR/0021`–`0025`, including that `TPRecord.tp_scheme_number` exists today as a plain, unlinked
  string); the required-QA-before-merge statement; and the governance lifecycle this report follows
  steps (1)–(2) of.
- `ADR/0026` did not exist prior to this pass (`ls ADR/0026*` failed before drafting).
- No `T93` reference exists anywhere in `IMPLEMENTATION_QUEUE.md`/`PROJECT_STATE.json` — confirmed
  via direct grep, zero matches.
- `T91` confirmed `Done -- merged` in `IMPLEMENTATION_QUEUE.md`.
- `ADR/0021`, `ADR/0022`, `ADR/0023`, `ADR/0024`, `ADR/0025` all confirmed byte-identical to their
  own respective merge commits — no drift, no unauthorized edit.

## 2. Repository Investigation Performed

Read directly from the repository (not from the task prompt's summary) before drafting `ADR/0026`:

- `docs/Legal_DMS — Domain Model & Functional Specification.md` §4 rules 25–28 (Scheme CBR content),
  §24.3 (Property's own Scheme-relationship open item), §24.4 (TP/FP Record's own overlap note and
  its explicit assignment of the boundary question to #7, not #6), §24.5 (Scheme's full entity
  treatment: purpose, structure requirement, fields, relationships, open engineering decisions),
  §26 item 4 (Scheme hierarchy storage mechanism, must-resolve list), §27 (dependency-ordering
  coherence self-check), and §12's one-line Scheme-hierarchy-storage table entry (no additional
  detail beyond §24.5).
- `ADR/0021`, `ADR/0022`, `ADR/0024`, `ADR/0025` — read in full as the frozen decisions this ADR
  must compose with. `ADR/0025`'s own "Explicit #7 Deferral" section was read as the authoritative
  statement of exactly what #5 left for #7 to decide.
- **Full-repository, case-insensitive grep for `scheme`** across `backend/src/app/`: exactly two
  matches, both `deps.py`'s `_bearer_scheme`/`HTTPAuthorizationCredentials`-related — an HTTP
  authentication concept, structurally unrelated to the business `Scheme` entity. Zero matches for
  `Scheme`, `SchemeNode`, `scheme_id`, `scheme_node`, `TPRecord`, `FPRecord`, or `tp_scheme_number`
  in `backend/src/app/` or `backend/alembic/`.
- **Full grep for `parent_id`, self-referencing `ForeignKey` patterns, and nested-set column names**
  (`lft`/`rgt`) across `backend/src/app/infrastructure/persistence/models/`: zero matches — confirmed
  no self-referencing hierarchy pattern of any kind exists anywhere in this codebase today.
- **`geography.py` read in full** — the only hierarchy-shaped precedent in this codebase:
  `Country → State → District → Taluka → Village`, five separate fixed-level tables, each with a
  single non-nullable `ForeignKey` to its parent's table, no `AuditMixin` (reference/lookup data).
  Directly informed this ADR's rejection of the "fixed/optional levels" alternative — this pattern
  works for `geography.py` because that hierarchy's depth and level names are genuinely fixed in
  reality, the opposite of what §4 rule 27/28 requires for Scheme.
- **`docs/ERD.md` searched directly** for any existing Scheme/`scheme_nodes` documentation: zero
  matches.

## 3. Architectural Findings

- A variable-depth, business-editable hierarchy has **no existing precedent** in this codebase — a
  genuinely different situation from `ADR/0024`'s polymorphic-reference decision, which had five
  direct precedents to draw on. This ADR's mechanism choice rests on the specification's own
  requirement (variable depth) and general SQL/Postgres best practice, disclosed explicitly as a
  first-of-its-kind idiom for this repository, not minimized.
- `geography.py`'s existing fixed-level-per-table pattern is directly relevant as **negative
  precedent** — proof the codebase already uses that shape successfully, and exactly why it does not
  transfer to Scheme's business-variable structure.
- The TP/FP↔Scheme boundary question, read carefully against §4 rule 26's "Organization
  own[ing]/control[ling]" framing, has a reasoned, textually-grounded answer (the two concepts are
  distinct) — but that answer is disclosed explicitly as an architectural *interpretation*, not an
  explicit specification statement, per the task's own instruction against converting an inference
  into a specification requirement.
- Property↔Scheme cardinality was deliberately left assessed, not resolved — the hierarchy mechanism
  decided here does not constrain that future decision in either direction, so resolving it now would
  have been scope creep beyond what T92 actually required.

## 4. ADR/0026 Decision

- **File:** `ADR/0026-scheme-hierarchy-and-tpfp-scheme-boundary.md`
- **Branch:** `docs/t92-adr-0026-scheme-hierarchy-tpfp-boundary` (created from `main` at `ed1466d`)
- **Decision:** Adjacency list — two new tables, `schemes` (stable top-level Scheme identity,
  Organization-owned) and `scheme_nodes` (self-referencing `parent_id`, variable-depth internal
  structure, `node_type` as an unconstrained, organization-configurable label). TP/FP↔Scheme
  boundary: distinct concepts, no database relationship — `TPRecord.tp_scheme_number` remains exactly
  as `ADR/0025` froze it, unchanged by this ADR.

## 5. Alternatives Considered

Four options evaluated against variable-depth support, parent/child representation, insertion/update
complexity, subtree/ancestor queries, integrity constraints, concurrency implications, future
hierarchy-change cost, tenant isolation, ORM/repository complexity, migration implications, and
suitability for Legal_DMS's expected (staff-editable, not static) usage pattern — all in `ADR/0026`'s
own "Alternatives Considered" section: adjacency list (**selected**), materialized path (rejected —
expensive, error-prone re-parenting cost), nested set (rejected — worst-case write amplification and
a genuine concurrency risk this specification's own concurrency-critical discipline elsewhere argues
against), fixed/optional levels (rejected — directly contradicted by §4 rule 27/28's variable-depth
requirement, despite being `geography.py`'s own proven pattern for a categorically different,
genuinely-fixed-depth use case).

## 6. Composition Check

- **`ADR/0021` (tenant isolation):** not modified, reopened, or reinterpreted. `schemes` and
  `scheme_nodes` both carry mandatory `organization_id`, with `scheme_nodes` specifically requiring
  its own column (not merely inherited via `scheme_id`) for the same reason `ADR/0024` required it on
  `property_record_references` — the RLS backstop must not depend on a join always being present,
  especially not inside a recursive query.
- **`ADR/0022` (authorization):** not modified, reopened, or reinterpreted. `schemes`/`scheme_nodes`
  governed by the existing resource+action permission model, `scheme_nodes` accessed only through its
  owning `Scheme`'s `schemes:*` permission codes — mirroring `ADR/0023`'s and `ADR/0024`'s identical
  anti-fragmentation reasoning for their own sub-entities.
- **`ADR/0024` (Property/Land/Record-Reference):** not modified, reopened, or reinterpreted.
  Property↔Scheme cardinality — `ADR/0024`'s own disclosed open item — is assessed, not resolved,
  exactly as T92's authorization requires.
- **`ADR/0025` (Gujarat record fields):** not modified, reopened, or reinterpreted.
  `TPRecord.tp_scheme_number` is confirmed unchanged — no `scheme_id` or other structural column
  added to `TPRecord` by this ADR.

## 7. #5 ↔ #7 Traceability (explicit, per T91's QA watch item)

`ADR/0026` contains a dedicated "#5 ↔ #7 Traceability" section, placed immediately after its
Context, stating explicitly and separately: (1) what `ADR/0025` already decided about
`tp_scheme_number`; (2) what `ADR/0025` deliberately deferred to this ADR; (3) what this ADR now
resolves; (4) what remains unresolved after this ADR. This is a visibly auditable section, not a
passing mention that `ADR/0025` was "consulted."

## 8. Scope / Exclusion Verification

```
Scope
[x] Only T92's authorized architectural scope addressed (Required ADR #7 only).
[x] No other Required ADR resolved -- #1-#6/#18/#19 correctly attributed to their own ADRs
    throughout, not re-resolved; #8-#17/#20 explicitly listed as untouched.
[x] ADR/0021-0025 not modified, reopened, weakened, or reinterpreted -- confirmed via git diff
    --stat main (below): none of the five appears in this branch's diff at all.
[x] ADR/0001-0020 and ADR/template.md not modified -- confirmed absent from this branch's diff.

Business baseline
[x] Scheme's Matter-independence and Organization-ownership (S4 rules 25/26) not reopened -- cited
    as already-frozen, not as this ADR's own decision.
[x] S4 rule 27/28's flexibility requirement respected -- adjacency list selected specifically
    because it satisfies this requirement; fixed/optional levels rejected specifically because it
    does not.
[x] tp_scheme_number's existence/format/type (ADR/0025) NOT reopened -- confirmed unchanged.
[x] Property<->Scheme cardinality NOT silently resolved -- explicitly assessed only, per this
    task's own instruction.

ADR correctness
[x] ADR number is 0026 -- confirmed against actual repository state (ADR/0001-0025 existed; 0026
    did not, prior to this pass).
[x] Filename follows repository convention -- NNNN-kebab-case-title.md.
[x] Explicitly distinguishes planning-list item #7 from any repository ADR filename number --
    stated in the header, consistent with S21's own terminology note.
[x] Follows ADR/template.md's core sections, extended with the #5<->#7 Traceability, Tenant-
    Isolation Composition, Authorization Composition, and Property<->Scheme Relationship sections --
    the same extension pattern ADR/0021-0025 already used.
[x] Decision is explicit -- one named mechanism (adjacency list, two tables) plus one named boundary
    conclusion (TP/FP and Scheme are distinct), not a "use best practices" deferral.
[x] Alternatives genuinely evaluated -- 4 options, scored against 11 criteria including
    specification fidelity, concurrency, and repository precedent.
[x] Rejected alternatives have concrete, repository-grounded and specification-grounded reasons --
    not generic pros/cons.
[x] TP/FP<->Scheme boundary decided, labeled explicitly as an architectural interpretation, not
    misattributed as an explicit specification statement.
[x] Tenant isolation and authorization composition addressed in dedicated sections.
[x] Property<->Scheme relationship addressed -- assessed, not resolved, with explicit reasoning for
    why resolving it is not required by this ADR's own scope.
[x] Consequences, Risks, and Explicitly Unresolved Items all present as separate, honest sections --
    including the disclosed cycle-prevention gap and the "first self-referencing pattern in this
    codebase" disclosure.
[x] Implementation Boundary section present -- no schema/code created by this ADR.

Repository hygiene
[x] No unrelated files changed -- confirmed via git status: only ADR/0026 and this report are new;
    nothing else appears as modified or untracked.
[x] No code/schema/API/migration changes -- confirmed, no such file appears anywhere in this
    branch's diff.
[x] No test file modified -- confirmed; no test file touched.
[x] No PROJECT_STATE.json changes -- confirmed absent from this branch's diff; deferred to the
    Documentation Manager role, after a formal QA Decision exists, per governance step (5)/(6).
[x] No IMPLEMENTATION_QUEUE.md changes -- confirmed absent from this branch's diff; its existing
    T92 row is left as-is.
[x] No T93 created or authorized -- confirmed absent from IMPLEMENTATION_QUEUE.md and
    PROJECT_STATE.json both before and after this pass.
[x] No Stage 4 business feature selected -- businessFeatures remains [].
[x] currentStage not changed -- remains stage-3 / in_progress.
```

## 9. Exact Files Changed

```
$ git status
On branch docs/t92-adr-0026-scheme-hierarchy-tpfp-boundary
Untracked files:
  ADR/0026-scheme-hierarchy-and-tpfp-scheme-boundary.md
  docs/reviews/T92_Software_Architect_Report.md

$ git diff --stat main
(empty prior to this commit -- both files are new, untracked)
```

Exactly two new files, both documentation: `ADR/0026-scheme-hierarchy-and-tpfp-scheme-boundary.md`
and this report. No existing file was modified.

## 10. Confirmation No Implementation Occurred

No database schema, migration, backend, frontend, or API implementation was performed. No
`schemes`/`scheme_nodes` table, model, service, repository, or route was created or modified —
`ADR/0026` describes what future implementation must build; it does not build it. No test was added
or modified. No source file investigated above (`geography.py`, `deps.py`) was touched — all were
read-only inspections.

## 11. Confirmation No Other Required ADR Resolved

`ADR/0026` resolves only Required ADR #7. Required ADR #1–#6, #18, #19 remain attributed to their
own respective ADRs (not re-resolved or restated as this ADR's own decision anywhere). Required ADR
#8–#17 and #20 are explicitly listed as untouched in `ADR/0026`'s own "Explicitly Unresolved Items"
section. `ADR/0021`, `ADR/0022`, `ADR/0024`, and `ADR/0025` are not modified.

## 12. T93 Absence Confirmed

No `T93` row exists in `IMPLEMENTATION_QUEUE.md`; no `T93` reference exists anywhere in
`PROJECT_STATE.json` or the wider repository. This pass did not create, authorize, or reference
`T93`.

## 13. Unresolved Decisions (Recorded, Not Silently Decided)

- **Property↔Scheme cardinality and mechanism** (§24.3) — assessed, not chosen. `ADR/0026` names the
  stable identity (`schemes.id`/`scheme_nodes.id`) a future decision would reference, without
  choosing among the possible mechanisms.
- **Cycle-prevention mechanism for `scheme_nodes`** — application-layer validation vs. a database
  trigger, not chosen; named as a disclosed gap, not hidden.
- **Building/Block/Section/Unit vocabulary** — business/config content per §6.2's general pattern,
  not a schema decision.
- **Required ADR #8–#17, #20** — fully open, unaffected by this ADR.

## 14. QA Handoff

This branch (`docs/t92-adr-0026-scheme-hierarchy-tpfp-boundary`) is handed off to the QA Reviewer
role for an independent, formal QA Decision (`Approved` / `Approved with comments` / `Rework
required`), against the actual remote PR HEAD once opened — per T92's own row ("the eventual ADR PR
must independently undergo QA, re-verified on its actual remote PR HEAD, before any merge, and must
explicitly re-verify the #5<->#7 traceability section") and this repository's established
documentation-only-work QA requirement (`T80`/`T81`/`T82`/`T86`–`T91` precedent).

The QA Reviewer is specifically asked to independently verify: (1) the #5↔#7 traceability section is
genuinely auditable, not a passing mention; (2) `tp_scheme_number` was not silently converted into an
FK or otherwise redesigned; (3) Property↔Scheme cardinality was not silently resolved; (4) the
hierarchy-mechanism alternatives analysis is grounded in the specification and this repository's
actual code, not asserted without evidence.

## 15. QA Status

**Unresolved.** No QA Decision has been rendered as of this report. This Software Architect pass
does **not** record, anticipate, or imply `Approved`, `Approved with comments`, or `Rework required`
— that decision belongs solely to the QA Reviewer role, independently, against this commit and the
eventual PR HEAD. This report and `ADR/0026` are not self-certifying.

## 16. Explicitly Not Done By This Pass

Per T92's own authorization boundary, none of the following were performed, and none are implied by
this report or by `ADR/0026` itself:

- `ADR/0021`, `ADR/0022`, `ADR/0023`, `ADR/0024`, or `ADR/0025` were not modified, reopened, or
  reinterpreted.
- `ADR/0001`–`0020` and `ADR/template.md` were not modified.
- Required ADR #1–#6, #18, or #19 was not reopened; Required ADR #8–#17 or #20 was not resolved.
- No `§4` business rule, `§23` frozen entity decision, or any other part of the governed
  specification was modified.
- No database schema, migration, backend, frontend, or API implementation was performed.
- No test implementing the decision was added or modified.
- No Stage 4 business feature was selected or authorized; `businessFeatures` remains `[]`.
- `currentStage` was not changed; remains `stage-3` / `in_progress`.
- `T93` or any subsequent task was not created or authorized.
- `PROJECT_STATE.json` was not modified — synchronization remains deferred until after the formal
  QA Decision exists, per the established `T80`/`T81`/`T86`–`T91` pattern.
- `IMPLEMENTATION_QUEUE.md` was not modified by this pass — its existing T92 row is left as-is;
  marking it "Done" is a post-QA, post-merge synchronization step.
- No PR was merged by this pass, and this report does not authorize a merge — merge remains gated on
  the QA Reviewer's independent decision against the actual PR HEAD.
- This Software Architect pass did not perform QA on its own work, and does not claim to.

---

**This report ends T92's authorized scope at the implementation PR handoff.** Per this task's own
governing instructions, T92 stops here, awaiting independent QA. No further action (opening/merging
a PR beyond the point specified below, creating T93, marking T92 Done, performing QA, governance
closeout) is taken by this pass.
