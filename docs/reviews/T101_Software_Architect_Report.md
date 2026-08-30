# T101 Software Architect Report

**Task:** T101 — Draft and resolve Required ADR #8 ("Matter vs File"), per
`docs/Legal_DMS — Domain Model & Functional Specification.md` §21's planning-list terminology. Full
authorized-scope text: `IMPLEMENTATION_QUEUE.md`'s own T101 row (authorization commit `350bf85`, PR
#157, merge `583a6b5`).

**Role:** Software Architect, per `docs/prompts/SoftwareArchitect.md`. This report follows that
prompt's Required Output (§8) and `docs/ImplementationLog/README.md`'s Reviewer Checklist structure,
and this task's own required-report-contents list.

---

## 1. Verified Baseline and Authorization

- `git fetch origin` + `git rev-parse origin/main`: `583a6b51a757605ed37e4cdd7a8d461a4e8a12a5` —
  matches `governanceLedger.asOfCommit`'s predecessor state and the merge of PR #157
  ("docs(governance): authorize T101"), confirmed via `git log`.
- Authorization commit `350bf85` independently confirmed present and an ancestor of this branch's
  HEAD: `git merge-base --is-ancestor 350bf85 HEAD` → true.
- `governanceLedger` on `origin/main` at this baseline: `latestTaskDone: "T100"`,
  `latestTaskAuthorized: "T101"`, `resolvedRequiredADRs` not yet including `8` — consistent with T101
  being authorized but not yet implemented.
- `IMPLEMENTATION_QUEUE.md`'s T101 row, read directly from `origin/main`, names: Required ADR #8; the
  identity/lifecycle/existence boundary decision; an explicit, in-ADR reconciliation with
  `docs/BusinessRequirementsPlan.md`; downstream-consequence identification (not design); a wide,
  explicit exclusion list (Required ADR #10/#12/#20 named specifically as coupled-but-not-resolved);
  and an explicit statement that `T98`/PR #148 is separately governed and must not be touched.
- Branch `docs/t101-adr-0030-matter-file-lifecycle-boundary` created directly from `origin/main`
  (`583a6b5`).
- **ADR numbering resolved deliberately, not by default.** `ADR/0028` is the highest merged file on
  `main`; `T98`'s own in-flight `ADR/0029` exists only on its own unmerged branch
  (`origin/docs/t98-adr-0029-activity-vs-audit-boundary`, PR #148, confirmed still `OPEN`, `mergedAt:
  null`). Per this row's own disclosed ambiguity ("expected `0029` if `T98`'s own in-flight ADR draft
  ... has not yet merged by then, otherwise `0030`"), this ADR is filed as **`ADR/0030`**, not `0029`
  — deliberately reserving `0029` for `T98`'s own, independently governed number rather than racing
  it. Confirmed no other branch anywhere in the repository claims `ADR/0030` (`git branch -r` scan of
  every remote branch's `ADR/` tree). This is disclosed as a judgment call this row explicitly
  anticipated, not an assumption.

## 2. Repository/Specification Evidence Inspected

Read directly, in full where cited, not sampled:

- `docs/BusinessRequirementsPlan.md` §3 ("Core System Philosophy," quoted verbatim: "One Unique File
  Number... This file number becomes the permanent identity of the matter"), §7.1–7.3 (Number format,
  Matter Type Codes, and the matter-type-scoped "Number Generation Logic" — a fourth numbering-scope
  candidate never named anywhere in the governed specification or `ADR/0027`), the document's own
  status note (explicitly disclaiming silent authority over the repository), and its "Review notes"
  section (confirmed to flag §7's *concurrency* gap but **not** the deeper identity conflict this ADR
  resolves — proving this reconciliation was genuinely still open, not a restatement).
- `docs/Legal_DMS — Domain Model & Functional Specification.md`: §4 rules 1–7 (Matter/File groups,
  quoted verbatim); §7 Phase 4 (core invariant diagram, "File creation is independently controlled"
  exit criterion); §11.1 (`Matter → File → Document` required chain, quoted); §23 ("Final Executive
  Decision," confirming File and Matter as two separately frozen concepts); §24.8 ("File & Numbering,"
  read in full — Purpose, Repository constraint, Fields, Relationships, Lifecycle, Repository mapping,
  Open engineering decisions, for both File and File Numbering); §2 Feature Catalogue rows for File,
  File Numbering, Workflow, Task, Government Process (dependency/priority columns).
- `ADR/0027-file-numbering-algorithm-and-concurrency-strategy.md`, in full — its own Decision
  ("File Numbers are Matter-scoped... the counter's increment and the new File row's own creation must
  occur in the same database transaction," quoted verbatim) independently confirmed to already assume
  the exact layered Matter→File boundary this ADR now formally resolves, without itself performing
  this reconciliation.
- `ADR/0021`, `ADR/0022`, `ADR/0028` — relevant sections for tenant-isolation/authorization composition
  and evidentiary-discipline consistency; none modified.
- `backend/src/app/infrastructure/persistence/models/matter.py` (full file) — `matters.matter_number`
  (line 49, `String(50)`, `unique=True`) confirmed as a genuine, pre-existing, live schema fact that
  already behaviorally implements `BusinessRequirementsPlan.md`'s one-Number-per-Matter model, not the
  governed specification's model — cited in the ADR as a concrete migration-relevant disclosure, not
  merely a document-vs-document abstraction.
- `backend/src/app/infrastructure/persistence/models/document.py` — confirmed `documents.matter_id`'s
  direct-to-Matter FK, matching §24.9's own "the gap" finding.
- Full-repository grep for a File domain-entity class: zero matches (`FileStorageRecord` in
  `storage.py` confirmed as an unrelated, document-blob storage concept, not this ADR's File).

## 3. Decision Made

The governed specification's layered Matter→File model controls;
`BusinessRequirementsPlan.md`'s File-Number-as-Matter-identity language is superseded
pre-specification material, per precedence already established throughout this ADR series and stated
explicitly in `BusinessRequirementsPlan.md`'s own status note — reconciled in `ADR/0030`'s own text,
not silently assumed. The Matter–File boundary is decided as three separable questions: **existence**
(Matter is the root; File is optional, `0..N`, strictly subordinate — rules 3/5 restated as
architectural invariants), **identity** (File has its own independent identity/Number, assigned at
File creation per rule 6, scoped to but not merged with its Matter's own identity — exactly matching
`ADR/0027`'s already-accepted Matter-scoped, per-File numbering mechanism), and **lifecycle**
(existence-dependent on Matter per rule 5, but operationally independent in its own creation/status
per §7 Phase 4's "independently controlled" exit criterion — without inventing the still-`ED` status
vocabulary itself).

## 4. Alternatives Evaluated

Three alternative sets, each scored against concrete specification/repository evidence:

1. **Which document's model controls** — treating `BusinessRequirementsPlan.md` as authoritative was
   rejected (contradicts §23's frozen entity list and reopens `ADR/0027`'s already-accepted decision);
   silently assuming the specification controls without stating why was rejected (defeats this task's
   own explicit "not silently assumed" instruction and leaves `ADR/0027`'s validity implicitly
   questionable); explicit reconciliation in this ADR's own text was selected.
2. **Identity model** — File sharing Matter's identity was rejected (contradicts rule 6 and
   `ADR/0027`'s per-File numbering); a fully independent, Matter-unconnected identity was rejected as
   unsupported (ignores rule 5's existence dependency `ADR/0027` is itself built around); an
   independent-but-Matter-scoped identity was selected, matching `ADR/0027` exactly.
3. **Lifecycle coupling** — full mirroring of Matter's status was rejected (contradicts the Phase 4
   "independently controlled" criterion and rule 3's zero-File case); full decoupling including
   existence was rejected outright (direct rule 5 violation); existence-dependent-but-operationally-
   independent was selected, the only option consistent with both constraints simultaneously.

## 5. Composition Check

- **`ADR/0027`**: confirmed compatible and unaffected — this ADR is precisely the reconciliation
  `ADR/0027` itself did not perform when it made its own Matter-scoped numbering decision. Not
  modified, reopened, or reinterpreted; confirmed absent from this branch's diff.
- **`ADR/0021`/`ADR/0022`**: cited only for File's future tenant-isolation/authorization composition,
  once separately authorized — not decided here, not modified.
- **`ADR/0028`**: cited only for evidentiary-discipline consistency; no direct interaction.
- **`BusinessRequirementsPlan.md`**: not modified — its conflicting language is reconciled by citation
  and explanation in `ADR/0030`'s own text, per this task's explicit exclusion of modifying that
  document or the governed specification.
- **Required ADR #10, #12, #20**: each explicitly named as coupled-but-not-resolved, disclosed in
  "Explicitly Unresolved / Deferred Questions" and "Explicit Out-of-Scope Boundaries" — this ADR
  confirms the *boundary* those tasks build on, never their own resolution.
- **`T98`/PR #148**: not referenced as a dependency, not touched, not merged, not bypassed — confirmed
  absent from this branch's diff; this branch was created from `origin/main` directly, never from
  `T98`'s own branch.

## 6. Explicitly Unresolved Questions (named in the ADR, not silently dropped)

- Required ADR #10 (Document/File relationship mechanics).
- Required ADR #12 (Workflow/Task/GovernmentProcess attachment granularity).
- Required ADR #20 (migration strategy, including any `matters.matter_number` reconciliation against
  this ADR's per-File identity model).
- File's own lifecycle status vocabulary/terminal states.
- File's own broader field list beyond identity/lifecycle/existence's minimum implications.
- Matter-deletion cascade mechanics beyond the existence invariant itself.

## 7. Scope/Boundary Reasoning

The authorized scope names exactly three decisions (explicit reconciliation; the identity/lifecycle/
existence boundary; downstream-consequence identification without design) plus a wide, explicitly
named exclusion list. `ADR/0030` decides exactly those three and no more: it does not design File's
schema, does not resolve Required ADR #10/#12/#20 (each named as a disclosed, coupled dependency, not
decided), does not modify `docs/BusinessRequirementsPlan.md` or the governed specification, does not
modify any §4 rule or the frozen §23 entity model, and does not touch `T98`/PR #148 in any way. The one
genuine, concrete repository fact this pass surfaced beyond the document-level conflict — that
`matters.matter_number` already behaviorally implements the superseded, one-Number-per-Matter model —
is disclosed as a known, out-of-scope migration-relevant fact for Required ADR #20, not silently fixed
or silently ignored, consistent with this task's own "downstream consequences, not design" instruction
and this series' established disclosure discipline.

## 8. Governance Transition Declaration

Per this task's own authorization row (step 2) and `T99`/`T100`'s generalized transition mechanism
(`docs/GOVERNANCE_VALIDATION.md`'s "In-progress transition declarations" section), this branch adds
exactly one entry to `PROJECT_STATE.json`'s `governanceLedger.inProgressTransitions`:

```json
{"task": "T101", "requiredAdrs": [8]}
```

declaring the real, current gap this ADR introduces (`ADR/0030` resolves Required ADR #8, which
`main`'s `governanceLedger.resolvedRequiredADRs` does not yet include). No other field in
`PROJECT_STATE.json` is touched. `T101` is authorized (`IMPLEMENTATION_QUEUE.md`'s own row) and not yet
Done — satisfying `T100`'s generalized (post-frontier-constraint) requirement directly, with no
reliance on `T101` being the single numerically-highest authorized task (it is, incidentally, at this
baseline, but the mechanism no longer requires that).

## 9. Exact Files Changed

```
$ git status
On branch docs/t101-adr-0030-matter-file-lifecycle-boundary
Untracked files:
  ADR/0030-matter-file-lifecycle-and-identity-boundary.md
  docs/reviews/T101_Software_Architect_Report.md
Changes not staged:
  modified: PROJECT_STATE.json

$ git diff --stat origin/main
(the single inProgressTransitions line added to PROJECT_STATE.json; the two new files above)
```

Exactly three files: two new (the ADR, this report), one modified with a single, surgical addition
(`PROJECT_STATE.json`'s `governanceLedger.inProgressTransitions`) — no other line in that file changed.
`ADR/0001`–`0028`, `ADR/template.md`, `docs/BusinessRequirementsPlan.md`, the governed specification,
`IMPLEMENTATION_QUEUE.md`, and any `T98`/PR #148 file do not appear anywhere in this branch's diff
against `origin/main`.

## 10. Confirmation No Implementation Occurred

No database table, migration, backend model, service, repository, route, frontend, or test was created
or modified. No schema or configuration file was touched. `ADR/0030` describes the boundary; it
implements none of it — stated explicitly in the ADR's own "Implementation Boundary" section.

## 11. Confirmation Governance Boundaries Were Respected

`IMPLEMENTATION_QUEUE.md` was not modified by this pass. No `T102` was created or authorized. `T101` is
not marked Done by this report or any file it changes. `ADR/0021`–`ADR/0029` and `ADR/0007`/`ADR/0009`
are not reopened, modified, or reinterpreted — confirmed absent from this branch's diff. `T98`/PR #148
is untouched — confirmed by this branch's ancestry (created from `origin/main`, not from `T98`'s own
branch) and by its absence from the diff. No QA Decision is rendered, implied, or anticipated by this
report — see the QA Decision placeholder below.

## Validation

1. **Branch ancestry**: `git merge-base --is-ancestor 350bf85 HEAD` → `true`.
2. **ADR numbering**: `ADR/0030` independently confirmed next-available-and-uncontested (§1 above) —
   deliberately not `0029`, to avoid a foreseeable collision with `T98`'s own in-flight number.
3. **ADR references**: every `ADR/000N` cross-reference in `ADR/0030` checked against the actual
   filename it cites (`0021`, `0022`, `0027`, `0028`) — all exist, all filenames match exactly.
4. **No excluded implementation work**: confirmed via `git diff --stat origin/main` (§9 above) — two
   documentation files plus one surgical `PROJECT_STATE.json` line.
5. **Governance validator**:

```
$ python scripts/governance_validate.py
governance_validate: OK (0 warning(s), 0 errors)
```

   Clean — `ADR/0030`'s own `**Resolves:** #8` is exactly matched by the declared
   `inProgressTransitions` entry, and no other drift exists on this branch.

6. **Governance tests**: this branch does not modify `scripts/governance_validate.py` or its test
   suite — re-ran the exact command `governance.yml` invokes as a confirmation, not a claim of new
   coverage:

```
$ python scripts/tests/test_governance_validate.py -v
Ran 51 tests in 0.099s
OK
```

7. **Documentation/format validation**: no repository-prescribed markdown linter exists beyond the
   governance validator itself; none run beyond that.
8. **HEAD SHA**: recorded in the Reporting section below.
9. **Validation failures**: none found or concealed.

## Reviewer Checklist

Per `docs/prompts/SoftwareArchitect.md` §8's required output and
`docs/ImplementationLog/README.md`'s standard eleven-item self-assessment:

```
Reviewer Checklist

☑ Architecture preserved -- ADR/0021, ADR/0022, ADR/0027, ADR/0028 composed with, not modified or
  contradicted; specification rules 1-7 cited, not reinterpreted; BusinessRequirementsPlan.md and the
  governed specification both quoted verbatim, neither modified.
☑ Existing design patterns followed -- this ADR's identity/lifecycle decision is stated to be, and
  independently confirmed to be, exactly the boundary ADR/0027's own Matter-scoped numbering
  mechanism already assumed -- no new, competing pattern introduced.
☐ Tests added -- none; documentation-only architecture task, no implementation authorized.
☐ Existing tests pass -- not applicable to this pass' own scope; the governance test suite (unmodified
  by this branch) was re-run as a confirmation, per §6 above, not as new coverage this task adds.
☑ Documentation updated -- ADR/0030 and this report are the documentation this task produces.
☑ ADR updated (if required) -- ADR/0030 created (Required ADR #8 resolution); ADR/0021-0029,
  ADR/0007, ADR/0009 not touched, correctly.
☐ AI_BOOTSTRAP updated (if required) -- not required by this task's authorized scope.
☑ PROJECT_STATE updated (if required) -- the single, mechanism-required inProgressTransitions
  declaration per T99/T100's own governance-transition mechanism and this task's own authorization
  row (step 2); no other field touched; full ledger synchronization deferred to post-QA Governance
  Closeout, per this task's explicit instruction.
☑ No unrelated refactoring -- not applicable; no code touched at all.
☑ No scope creep -- Required ADR #10/#12/#20 explicitly disclosed as coupled, not resolved; File's own
  field list/status vocabulary/cascade mechanics explicitly deferred; T98/PR #148 completely untouched.
☑ Ready for QA -- ADR/0030 and this report are complete and handed off below.
```

## QA Handoff

This branch (`docs/t101-adr-0030-matter-file-lifecycle-boundary`) is handed off to the QA Reviewer
role for an independent, formal QA Decision against the actual remote PR HEAD once opened, per this
task's own governance boundary and this repository's established documentation-only-work QA
requirement (`T80`–`T101` precedent). The QA Reviewer is specifically asked to independently verify:
that the ADR-0030-vs-ADR-0029 numbering choice is genuinely collision-free against `T98`'s own,
separately governed number (re-check `origin/docs/t98-adr-0029-activity-vs-audit-boundary` and PR #148
live, not from this report's own claim); that every quoted passage from `BusinessRequirementsPlan.md`
and the governed specification is accurate against the actual files; that `ADR/0027`'s own Decision
text is quoted accurately and that this ADR's "confirmed compatible" claim actually holds under
independent re-reading, not merely asserted; that Required ADR #10/#12/#20 are genuinely disclosed as
coupled-not-resolved rather than silently decided; that the `inProgressTransitions` declaration exactly
matches the real gap `ADR/0030` introduces (and no more); and that `T98`/PR #148 is confirmed absent
from this branch's diff and untouched by its ancestry.

## QA Decision

☐ Approved
☐ Approved with comments
☐ Rework required

This Software Architect pass does not record, anticipate, or imply any of the three outcomes above —
per `docs/prompts/SoftwareArchitect.md` §11/§13, this role never renders a QA Decision or substitutes
for the QA Reviewer. `ADR/0030` and this report are not self-certifying.

---

**This report ends T101's authorized scope at the architecture-drafting handoff.** Per this task's own
governing instructions, T101 stops here, awaiting independent QA. No further action (opening/merging a
PR, performing QA, creating T102, marking T101 Done, governance closeout) is taken by this pass.
