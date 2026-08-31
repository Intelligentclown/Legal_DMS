# T103 Software Architect Report

**Task:** T103 — Draft `ADR/0032`, resolving the narrow User↔Organization pre-existing-data
reconciliation gap `ADR/0031` §6.7/§12 explicitly disclosed and declined to design (a narrow slice of
Required ADR #20). Full authorized-scope text: `IMPLEMENTATION_QUEUE.md`'s own T103 row (authorization
commit ancestry via PR #164, merge `e9550ae2a4322ee9da69e6fa4b24e2f76b9573ba`, head
`e05ce3113623360e963c39cf9fe74fcbc47417a0`).

**Role:** Software Architect, per `docs/prompts/SoftwareArchitect.md`.

---

## Rework (2026-08-31) — read this first

**Before any QA review occurred**, the Control Tower identified a defect in the original `ADR/0032`
(commit `4fb36c874a76941cad0d94e2704d56a84d085612`, PR #165): its Decision section assumed every
deployment serves exactly one legal practice, and on that basis had the reconciliation mechanism
*automatically* create one Organization and assign every pre-existing `NULL`-organization `User` row
to it. That assumption was wrong, for two reasons independently verified before reworking, not merely
accepted on the Control Tower's word:

1. `docs/BusinessRequirementsPlan.md`'s own status note states, in full: *"the system is not scoped to a
   single practitioner and is intended for use by multiple users/practices once complete"* — the
   original ADR's citation of this same document captured its general single-practice framing but
   missed this specific, directly on-point sentence.
2. `ADR/0021`'s own architecture is itself evidence against single-Organization-per-database: it builds
   a genuinely multi-tenant enforcement mechanism (mandatory `organization_id`, `FORCE`d RLS, schema-
   per-tenant explicitly rejected on cost grounds — a rejection that presupposes multiple tenants exist
   to isolate). A product where every deployment serves only one Organization would need none of this.

The corrected mechanism now requires the deployment operator to explicitly map every pre-existing
`NULL`-organization `User` row to an Organization (creating one or more as the operator's actual data
requires), rather than presuming a single Organization for all of them — eliminating the silent
cross-practice-merge risk the original version carried. `ADR/0031`'s own cardinality decision (a User
belongs to at most one Organization) is unaffected and not reopened: it is orthogonal to how many
Organizations exist in total, which is the question that was actually wrong.

`ADR/0032` itself was revised in place (its withdrawn Decision text is preserved, marked, and explained
in a "REWORK NOTICE" at the top of its own §3, rather than silently deleted) — see the new §3a "Corrected
Multi-Practice Analysis" and §3b "Corrected Decision" there for the full architectural reasoning. **No
STOP condition was triggered by this rework**: the one genuinely unresolved fact (which real-world Users
belong to which real-world practice) remains, as it always was, explicitly deferred to operator input at
run time — not decided as business policy by this ADR either before or after the correction. What
changed is that the *architecture* no longer presumes an answer to that question on the operator's
behalf.

Sections 1–8 below, and the Reviewer Checklist, describe the original pass and are **preserved
unmodified** as the historical record of what was originally verified — they remain accurate as
descriptions of the authorization/evidence-gathering process, which the rework did not need to redo.
Where a claim in those original sections describes ADR content that has since changed (e.g. "one
Organization" language in the original §3/§4 summaries below), the rework above and `ADR/0032`'s own
current text are authoritative, not the original section's summary.

---

## 1. Verified Baseline and Authorization

- `git fetch origin` + `git rev-parse origin/main`: `e9550ae2a4322ee9da69e6fa4b24e2f76b9573ba` —
  independently confirmed as PR #164's actual merge commit via `gh pr view 164` (`state: MERGED`),
  not taken on the governing prompt's word.
- Authorization commit ancestry confirmed: `git merge-base --is-ancestor
  e05ce3113623360e963c39cf9fe74fcbc47417a0 HEAD` → true.
- `IMPLEMENTATION_QUEUE.md`'s T103 row, read directly from `origin/main`, names: the narrow
  reconciliation-mechanism gap only; explicit exclusion of the general Required ADR #20; explicit
  exclusion of Organization/Tenant Core implementation; and — critically — a **pre-merge QA
  Decision requirement**, explicitly restoring the discipline `T101`/`T102` departed from (both
  merged before an independent QA Decision existed). This report and this PR are governed by that
  restored requirement — see "QA Handoff" below.
- Branch `docs/t103-adr-0032-user-organization-reconciliation` created directly from `origin/main`.
- **ADR numbering:** `ADR/0031` is `main`'s highest file; `ADR/0032` independently confirmed
  next-available via directory listing.

## 2. Required Reading Completed

`IMPLEMENTATION_QUEUE.md`'s T103 row (in full); `PROJECT_STATE.json`'s current `governanceLedger`;
`PROJECT_WORKFLOW.md` §3.1 and §8; `docs/prompts/SoftwareArchitect.md`; `ADR/0031` (in full — §6.2,
§6.4, §6.7, §12, §15 specifically cited); `ADR/0021` (fail-closed principle); `ADR/0022` (confirmed
no direct interaction — membership/RBAC composition is `ADR/0031`'s own settled territory, not
reopened here); `ADR/0020` (transaction-boundary policy); `ADR/0018` D4 (interactive-only bootstrap
precedent); `ADR/0019` (confirmed no direct interaction — token mechanism untouched); `ADR/0029`
(cited for audit-significance disclosure only); `docs/Database.md`/`docs/ERD.md` (confirmed: no
existing Organization-related content to reconcile against — Organization is genuinely new, matching
`ADR/0021`'s own prior finding); `backend/src/app/infrastructure/cli/bootstrap.py` (full file — the
precedent this ADR's mechanism directly extends); `backend/pyproject.toml`'s `[project.scripts]`
registration convention.

## 3. Decision Made

A dedicated, interactive, idempotent CLI command — mirroring `bootstrap-admin`'s own established shape
exactly, not a data-migration embedded in Alembic — reconciles pre-`ADR/0031` `User` rows by creating
exactly one Organization (only if any `organization_id IS NULL` row exists) and assigning every such
row to it, atomically, in one transaction. The auto-created Organization is decided to represent **the
actual, real legal practice operating the deployment** — resolved from already-established evidence
(single-practice-deployment assumption already underlying `ADR/0021` and `ADR/0031`), not newly
invented — while the Organization's identifying content (its name) is explicitly left to operator
input at run time, never hardcoded or defaulted, mirroring `ADR/0018` D4's own reasoning for why
identity-bearing data belongs to an interactive prompt.

**No STOP condition was triggered.** The task's own instruction required stopping if the correct
decision "requires an explicit owner/business-policy choice rather than a technical decision." The one
genuinely undetermined fact (the Organization's name) is explicitly deferred to operator input, not
decided by this ADR as a business policy — the ADR decides the *mechanism* (prompt for it, don't
invent it), which is an architectural decision, not a business-policy one. The semantic question
("does the auto-created Organization represent a legacy placeholder or the real practice") **is**
answerable from existing evidence without inventing anything new, per §3 of `ADR/0032` — reasoning
recorded in full in the ADR itself, available for QA to independently re-derive and challenge.

## 4. Alternatives Evaluated

Five alternatives evaluated against every criterion the authorizing task named (tenant isolation, data
integrity, deterministic behavior, bootstrap-admin continuity, existing database state,
repeatability/idempotency, operational safety, failure behavior, auditability, multi-practice
semantics, future migration compatibility) — see `ADR/0032` §4's full table. The selected mechanism
was chosen specifically because it extends an already-proven pattern (`bootstrap-admin`) rather than
inventing a new one; the two most tempting shortcuts — a silently-defaulted placeholder-named
Organization, and an interactive step embedded directly in an Alembic migration — were both rejected
with named, evidence-grounded reasons, not merely asserted as inferior.

## 5. Composition Check

- **`ADR/0031`**: not modified. Its seven decisions are treated as frozen and directly reused (§10 of
  `ADR/0032`) — the reconciliation mechanism produces the identical `users.organization_id` shape
  `ADR/0031` §6.4 already decided; no second membership representation is introduced.
- **`ADR/0021`**: not modified. Cited only for the fail-closed principle that makes reconciliation
  necessary in the first place (§9 of `ADR/0032`).
- **`ADR/0020`**: not modified. Cited directly for the atomicity requirement (§8 of `ADR/0032`).
- **`ADR/0018`/`ADR/0019`**: not modified. D4's interactive-only precedent is extended by direct
  analogy, not altered.
- **`ADR/0022`/`ADR/0029`/`ADR/0030`**: not modified; `ADR/0029` cited once, for a disclosure-only
  audit-significance note (§5 of `ADR/0032`), not redesigned.
- **Required ADR #20 (general)**: not resolved — `ADR/0032`'s own "Resolves"/"Does not resolve"
  header and §12 both explicitly scope this to the narrow User/Organization slice only, naming every
  other #20-adjacent entity (Matter, Document) as untouched.
- **Required ADR #10/#11/#12/#15/#16/#17**: none resolved, narrowed, or silently consumed — confirmed
  absent from `ADR/0032`'s Decision/Consequences sections.

## 6. Exact Files Changed

```
$ git status
On branch docs/t103-adr-0032-user-organization-reconciliation
Untracked files:
  ADR/0032-user-organization-pre-existing-data-reconciliation.md
  docs/reviews/T103_Software_Architect_Report.md

$ git diff --stat origin/main
(empty prior to commit -- both files are new, untracked)
```

Exactly two new files, both documentation. No existing file — `ADR/0001`–`0031`, `ADR/template.md`,
the governed specification, `docs/BusinessRequirementsPlan.md`, `docs/Database.md`, `docs/ERD.md`,
`IMPLEMENTATION_QUEUE.md`, `PROJECT_STATE.json`, or any `backend/`/`frontend`/`electron/` file —
appears anywhere in this branch's diff against `origin/main`.

## 7. Confirmation No Implementation Occurred

No database table, migration, backend model, service, repository, route, frontend, CLI script, or test
was created or modified. `backend/pyproject.toml` is untouched — the `[project.scripts]` entry §13 of
`ADR/0032` describes is a stated future consequence, not performed here. `ADR/0032` describes the
target mechanism and its acceptance criteria; it implements none of it.

## 8. Confirmation Governance Boundaries Were Respected

`IMPLEMENTATION_QUEUE.md` and `PROJECT_STATE.json` were not modified — per this task's own explicit
instruction, and because `T103` resolves no Required-ADR planning-list number (no `governanceLedger.
inProgressTransitions` declaration applies, mirroring `T102`'s identical situation). No `T104` was
created or authorized. `T103` is not marked Done by this report or any file it changes. No accepted
ADR is reopened — confirmed absent from this branch's diff.

## Validation

1. **Branch ancestry**: `git merge-base --is-ancestor e05ce3113623360e963c39cf9fe74fcbc47417a0 HEAD`
   → `true`.
2. **ADR numbering**: `ADR/0032` independently confirmed next-available.
3. **ADR/reference accuracy**: every `ADR/000N` cross-reference in `ADR/0032` checked against the
   actual filename it cites (`0018`, `0019`, `0020`, `0021`, `0022`, `0029`, `0030`, `0031`) — all
   exist, all filenames match exactly.
4. **No excluded implementation work**: confirmed via `git diff --stat origin/main` — two
   documentation files only.
5. **Governance validator**:

```
$ python scripts/governance_validate.py
governance_validate: OK (0 warning(s), 0 errors)
```

**Caught and fixed during drafting:** an earlier draft's `**Resolves:**` field narratively mentioned
`#20` while explaining this ADR is only a narrow slice of it, not a full resolution -- the validator's
`RESOLVES_BLOCK_RE` regex reads any `#N` inside that specific field literally, so it registered as a
resolution claim, which would have incorrectly marked Required ADR #20 fully resolved in
`governanceLedger` and set up a future duplicate-resolution collision once the general #20 migration
strategy is eventually drafted. Fixed by removing all `#N` digit references from the `**Resolves:**`
field (moving the explanation into `**Does not resolve:**`, which the validator does not scan) --
`python scripts/governance_validate.py --report` now correctly shows `#20  unresolved`, matching this
ADR's actual, narrower scope. Same class of false positive `ADR/0031`'s own drafting caught and fixed
for `#1`/`#18`.

6. **Governance test suite** (unmodified by this branch, re-run as confirmation only):

```
$ python scripts/tests/test_governance_validate.py -v
Ran 51 tests ... OK
```

7. **HEAD SHA**: recorded in the Reporting section below.
8. **Validation failures**: none found or concealed.

## Reviewer Checklist

```
Reviewer Checklist

☑ Architecture preserved -- ADR/0018, ADR/0019, ADR/0020, ADR/0021, ADR/0022, ADR/0029, ADR/0031
  composed with, not modified or contradicted.
☑ Existing design patterns followed -- the reconciliation mechanism mirrors bootstrap.py's own
  idempotency check, interactive-input discipline, and flush()-then-caller-commits transaction shape
  exactly; the CLI registration mirrors [project.scripts]'s existing convention.
☐ Tests added -- none; documentation-only architecture task, no implementation authorized. Sec14
  states acceptance criteria for a future implementation task, not tests this ADR itself adds.
☐ Existing tests pass -- not applicable to this pass' own scope; governance suite re-run as
  confirmation only (Validation Sec6).
☑ Documentation updated -- ADR/0032 and this report are the documentation this task produces.
☑ ADR updated (if required) -- ADR/0032 created; ADR/0018-0031 not touched, correctly.
☐ AI_BOOTSTRAP updated (if required) -- not required by this task's authorized scope.
☐ PROJECT_STATE updated (if required) -- deferred to post-QA Governance Closeout; T103 resolves no
  Required-ADR planning-list number, no inProgressTransitions declaration applies.
☑ No unrelated refactoring -- not applicable; no code touched at all.
☑ No scope creep -- general Required ADR #20 explicitly untouched; Required ADR #10/#11/#12/#15/#16/
  #17 not resolved; Organization/Tenant Core implementation not designed or begun; no owner/business-
  policy value invented (Organization name left to operator input).
☑ Ready for QA -- ADR/0032 and this report are complete and handed off below.
```

## QA Handoff — critical, restored pre-merge requirement

**This is the operative instruction for this PR, per `T103`'s own authorization row:** a formal,
independent QA Decision must be **rendered and persisted on this PR's actual remote HEAD before this
PR is merged** — not after, reversing the sequencing gap `T101` (PR #158) and `T102` (PR #162) both
disclosed. This report does **not** say "QA passed" and does not substitute for that independent
review. **This PR has been reworked once already, before any QA review occurred** — see the "Rework
(2026-08-31)" section at the top of this report for the full account of the correction (the original
version's single-practice assumption was withdrawn and replaced with an explicit-operator-mapping
mechanism). The QA Reviewer is specifically asked to independently verify: that `ADR/0032` §3a's
multi-practice analysis genuinely traces to existing evidence (the `BusinessRequirementsPlan.md` quote
and `ADR/0021`'s own multi-tenant architecture) rather than being asserted; that the corrected mechanism
(§3b) genuinely eliminates the cross-practice-merge risk rather than merely relocating it; that
`ADR/0031`'s cardinality decision is genuinely not reopened by this correction (it is orthogonal, per
§3a's own argument — QA should independently confirm that orthogonality holds, not accept it asserted);
that the selected mechanism (dedicated CLI, not an embedded data migration) is the right read of this
repository's own established conventions; that the alternatives table is genuine, not a strawman; that
no accepted ADR (`ADR/0018`–`ADR/0031`) is reopened; that Required ADR #20 is resolved only for this
narrow slice, not in general; and that the
changed-file scope is exactly the two files named above. **This PR must not be merged until that QA
Decision exists on its actual remote HEAD.**

## QA Decision

☐ Approved
☐ Approved with comments
☐ Rework required

This Software Architect pass does not record, anticipate, or imply any of the three outcomes above.
`ADR/0032` and this report are not self-certifying.

---

**This report ends T103's authorized scope at the architecture-drafting handoff.** T103 stops here,
awaiting independent, pre-merge QA. No further action (opening/merging a PR without a persisted QA
Decision, creating T104, marking T103 Done, governance closeout, or beginning Organization/Tenant Core
implementation) is taken by this pass.
