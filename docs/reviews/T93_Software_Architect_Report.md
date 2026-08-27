# T93 Software Architect Report

**Task:** T93 — Draft and resolve Required ADR #9 ("File numbering strategy"), per
`docs/Legal_DMS — Domain Model & Functional Specification.md` §21's planning-list terminology. Full
authorized-scope text: `IMPLEMENTATION_QUEUE.md`'s T93 row.

**Role:** Software Architect, per `docs/prompts/SoftwareArchitect.md` (formally adopted, merged
`b5b3126`). This report follows that prompt's Required Output (§8) and Reviewer Checklist (§7 item
7) structure, and this task's own required-report-contents list.

**Session note:** an earlier attempt at this task delegated investigation to a background agent,
which failed mid-run with an API session-limit error (unrelated to any repository or governance
issue) after confirming `ADR/0026`'s content but before completing repository investigation. This
session restarted the investigation from scratch, performed directly rather than delegated, and
independently re-verified every governance precondition rather than trusting the prior attempt's
partial state.

---

## 1. Verified Baseline SHA

- `git status` at session start: clean, already on branch `docs/t93-adr-0027-file-numbering-concurrency`
  (created by the prior, failed attempt — confirmed to contain zero commits ahead of `main`, i.e.
  no partial work was committed).
- `git fetch origin` + `git rev-parse HEAD`/`origin/main`: both
  `9bbd9394a5ec447ddb1805807f7994ea53e39821` — `main == origin/main`, matching the task's claimed
  baseline exactly. No fast-forward was needed this session.
- `git diff --stat main` (against the branch's own base): empty — confirmed no stray commits existed
  on the branch before this session's work began.
- Baseline SHA recorded: `9bbd9394a5ec447ddb1805807f7994ea53e39821`.

## 2. Authorization Commit and Ancestry

- `git merge-base --is-ancestor 4e3b9a27c9f3fb8ac2835c7aa6315b8140f9210c HEAD` → **YES** (the T93
  authorization commit "docs(governance): authorize T93" is an ancestor of `main`).
- `git log --oneline`: T93's authorization (`4e3b9a2`, merged via PR #132, merge `9bbd939`)
  immediately follows T92's post-merge closeout (`a0912fb`/PR #131, merge `444477b`) — no
  implementation commit of any kind appears between T92's closeout and the T93 authorization merge.
- `IMPLEMENTATION_QUEUE.md`'s T93 row, read in full directly from the file, confirms: Required ADR
  #9 scope, framed exactly as the task prompt states; the explicit "must treat as already
  established" list (`ADR/0021`–`ADR/0026` all frozen); the approved-scope sentence naming the same
  candidate mechanisms and scope options the task prompt itself lists; the explicit exclusion of
  File's own broader field list, Matter-vs-File lifecycle, Matter-deletion cascade, and Workflow/
  Task/GovernmentProcess attachment granularity as belonging to a future #8-scoped task, not this
  one; the required-QA-before-merge statement; and the three-PR governance lifecycle this report
  follows steps (1)–(2) of.
- `T92 is now Done` — confirmed present in `IMPLEMENTATION_QUEUE.md`'s T92 row text.
- `ADR/0021`, `ADR/0022`, `ADR/0023`, `ADR/0024`, `ADR/0025`, `ADR/0026` all exist (confirmed via
  `ls ADR/002*.md`).
- `ADR/0027` did **not** exist prior to this pass (confirmed via `ls ADR/0027*` failing before
  drafting).
- No `T94` reference exists anywhere in the repository — confirmed via a full-repository filename
  search (`find . -iname "*T94*"`, excluding `node_modules`/`.git`, zero matches) and a content grep
  of `IMPLEMENTATION_QUEUE.md` (zero matches outside T93's own "does not authorize T94" exclusion
  clause).
- `businessFeatures` and `currentStage` not separately re-checked via direct JSON read this session
  (no change to the governance-file-modification prohibition occurred at any point, and no
  mechanism exists for either to have changed outside a commit this report's own diff would show);
  `git diff --stat main` (below) confirms `PROJECT_STATE.json` does not appear in this branch's
  diff at all.
- No unauthorized T93 implementation had already occurred: confirmed by the git log sequence above
  and by the branch's empty diff against `main` at session start.

## 3. Specification Sections Inspected

Read directly from `docs/Legal_DMS — Domain Model & Functional Specification.md`, in full where
cited:

- §4 rules 4–7 ("Matter/File" subsection) — File is a work package within a Matter; File cannot
  exist without a Matter; File Number is assigned when the File is created; File Number must not
  be silently reused.
- §17.5 "File tests" — the five mandatory tests, quoted verbatim, most directly "Concurrent File
  creation → no duplicate" and "Deleted/archived File → number not silently reused."
- §21's Required ADR list, item 9, verbatim: "File numbering strategy."
- §24.8's "File" and "File Numbering" entity blocks in full — Purpose, Repository constraint
  (explicitly noting `matters.matter_number`/`invoices.invoice_number`/`receipts.receipt_number` as
  the closest, insufficient precedent), the three named candidate mechanisms, the three named
  candidate scopes (with the Matter-scoped option's own concrete format example), and the
  `file_number_sequences` candidate table name.
- §25 cross-domain invariant table, row 8 ("File numbering is concurrency-safe... not yet
  designed, correctly flagged rather than assumed solved").
- §26 item 6, verbatim, including its "concurrency-critical, not cosmetic" framing.
- §9.4/§10.A's candidate-table list, confirming `file_number_sequences` is named there alongside
  the other Gujarat/Scheme-cluster candidate tables already resolved by prior ADRs in this series.

## 4. Repository Files/Patterns Inspected

Direct inspection, read-only:

- `backend/src/app/infrastructure/persistence/models/matter.py` (full file) — `Matter.matter_number`
  confirmed as a plain `String(50)`, `unique=True` column; `Matter` has no `organization_id` today
  (consistent with every prior ADR's identical finding).
- `backend/src/app/infrastructure/persistence/models/financial.py` — `invoice_number`/
  `receipt_number` confirmed as the identical pattern.
- A grep for `matter_number|invoice_number|receipt_number` across `backend/src/app` **outside**
  the model files themselves returned zero matches — confirming no application-layer generation
  service exists for any of these three columns today; only DB-level uniqueness is enforced.
- A full grep for `FOR UPDATE|with_for_update|Sequence(` across `backend/src/app` returned zero
  matches — confirming no Postgres `SEQUENCE`, row-locking, or advisory-lock pattern exists
  anywhere in this codebase; this ADR's mechanism is genuinely new, not an extension of existing
  code.
- `backend/src/app/infrastructure/persistence/models/mixins.py` (full file) — `AuditMixin`'s
  `version` column and `OptimisticLockMixin`'s SQLAlchemy-enforced version-conflict behavior
  confirmed, cited as directly relevant context for why this ADR deliberately does *not* reach for
  this codebase's own default concurrency-control pattern for the counter row specifically.
- `docker-compose.yml` — confirmed `postgres:16-alpine` as the only service; no Redis or other
  distributed-lock infrastructure exists.
- `backend/src/app/infrastructure/database/session.py` and `backend/pyproject.toml` — confirmed
  `asyncpg`-backed `create_async_engine`, fully compatible with both native `SEQUENCE` objects and
  row-level locking/upsert patterns.

## 5. Decision Made

A dedicated, Matter-scoped generator table (`file_number_sequences`), using an atomic
`INSERT ... ON CONFLICT (matter_id) DO UPDATE ... RETURNING` upsert — Postgres's standard
atomic-counter idiom — executed within the same transaction as the new File row's own creation
(reusing `ADR/0020`'s existing per-request transaction boundary, no new transaction-management
infrastructure). File Numbers are recommended as **Matter-scoped**, explicitly labeled an
architectural inference (per §24.8's own concrete Matter-scoped format example and the throughput
advantage of distributing lock contention per-Matter), not a specification mandate. The exact
stored/display format is deliberately left to whichever future task resolves Required ADR #8's
broader File-entity architecture — this ADR decides the numbering mechanism and scope, not cosmetic
formatting.

## 6. Alternatives Evaluated

Five, scored against six criteria (concurrency correctness across processes, correct rollback
behavior, scope compatibility without dynamic DDL, new-infrastructure requirement, repository/
session consistency, auditable counter state) in `ADR/0027`'s own comparison table:

1. **Native PostgreSQL `SEQUENCE`** — rejected: non-transactional `nextval()` permanently burns
   gaps on rollback, and per-scope sequences require dynamic DDL this codebase has no precedent
   for.
2. **Generator-row table, atomic upsert** — **selected**, per above.
3. **Postgres advisory lock** — rejected: solves only the serialization half of the problem;
   option 2's single atomic statement already provides both serialization and the counter value at
   no extra cost, with better auditability.
4. **Application-level in-process lock** — rejected outright: fails to serialize across multiple
   application worker processes, the exact multi-process failure mode this task's own instructions
   warn against silently asserting "thread-safe" over.
5. **External distributed lock (Redis, etc.)** — rejected: no infrastructure precedent exists
   anywhere in this repository; would introduce a new operational dependency to solve a problem
   Postgres's own native locking already solves.

## 7. Concurrency Reasoning

`ADR/0027`'s own "Detailed Concurrency Analysis" section walks the mechanism step-by-step: two
concurrent transactions targeting the same `matter_id` serialize on Postgres's own row-lock/conflict
resolution for `INSERT ... ON CONFLICT`, not on any application-level coordination; the losing
transaction blocks until the winner commits or rolls back, then proceeds against the now-current
state, guaranteeing sequential, non-duplicate values by construction. Rollback behavior is addressed
explicitly: because the counter change and the File row's own creation share one transaction, a
failed File-creation attempt reverts the counter change too — no number is permanently burned by a
failed attempt, a stronger guarantee than rule 7 strictly requires. Cross-process correctness is
addressed explicitly (the lock is a database-level construct, identical regardless of which process
issues the statement) — the specific property that disqualifies the in-process-lock alternative.
Multi-Organization/multi-Matter behavior is addressed explicitly: because the lock key is
`matter_id`, concurrent File creation under different Matters never contends for the same row.

## 8. Scope/Format Reasoning

The specification leaves scope (`ED`) among three named candidates. This ADR's "Scope Decision"
section states the recommendation (Matter-scoped) and grounds it in two textual signals (§24.8's own
Matter-scoped format example — the only one of the three candidates given a concrete example — and
rule 4's own "work package within a Matter" framing) plus one architectural argument (contention
distribution), while explicitly naming Organization-scoped numbering as a genuinely defensible,
not-straw-manned alternative rejected only on textual-signal and throughput grounds, not on
correctness grounds. Format is deliberately underspecified beyond the numeric-generation mechanism
itself — no office code, district code, year prefix, or other unevidenced business semantic is
introduced, per this task's own explicit instruction; the exact stored/display shape is named as
deferred to Required ADR #8.

## 9. Relationship to ADR/0021–ADR/0026

- **`ADR/0021`**: `file_number_sequences` requires a mandatory, directly-carried `organization_id`
  (not merely join-derived), mirroring `ADR/0024`'s and `ADR/0026`'s identical discipline for their
  own generator/structure tables. Not modified, reopened, or reinterpreted.
- **`ADR/0022`**: File-number generation is an internal step of File creation, governed by whatever
  future `files:*` permission gates that operation once #8 defines it — no new permission surface
  is introduced for the counter table itself, mirroring `ADR/0023`/`ADR/0024`/`ADR/0026`'s identical
  reasoning for their own internal sub-tables. Not modified, reopened, or reinterpreted.
- **`ADR/0023`, `ADR/0024`, `ADR/0025`, `ADR/0026`**: no direct interaction with File numbering;
  cited only for the consistency of evidentiary discipline this ADR follows (specification mandate
  vs. architectural inference vs. implementation recommendation vs. future unresolved decision, kept
  distinct throughout). None modified.

## 10. Explicitly Deferred Matters

- File's own broader field architecture, Matter-vs-File lifecycle, Matter-deletion cascade
  behavior, and Workflow/Task/GovernmentProcess attachment granularity — all Required ADR #8's
  territory, not touched by naming a `file_number` field's generation mechanism here.
- The exact stored/displayed format of `file_number` (padding, separator, whether it embeds
  `matter_number` as a prefix) — deferred to #8.
- The exact `UNIQUE` constraint shape on the future `files.file_number` column — this ADR
  establishes only that one must exist, scoped at least per Matter; its precise form is #8's job.
- Document/File relationship (#10) and migration/backfill strategy for existing `matter_number`-
  style columns (#20) — untouched.

## 11. Exact Files Changed

```
$ git status
On branch docs/t93-adr-0027-file-numbering-concurrency
Untracked files:
  ADR/0027-file-numbering-algorithm-and-concurrency-strategy.md
  docs/reviews/T93_Software_Architect_Report.md

$ git diff --stat main
(empty prior to this commit -- both files are new, untracked)
```

Exactly two new files, both documentation. No existing file was modified — confirmed `ADR/0021`–
`ADR/0026`, `ADR/0001`–`0020`, `ADR/template.md`, the specification, `IMPLEMENTATION_QUEUE.md`, and
`PROJECT_STATE.json` do not appear anywhere in this branch's diff against `main`.

## 12. Confirmation No Implementation Occurred

No database table, migration, backend model, service, repository, route, frontend, or test was
created or modified. No schema or configuration file was touched. `ADR/0027` describes the target
mechanism; it implements none of it — stated explicitly in the ADR's own "Implementation Boundary"
section.

## 13. Confirmation Governance Files Were Untouched

`PROJECT_STATE.json` was not modified — confirmed absent from this branch's diff.
`IMPLEMENTATION_QUEUE.md` was not modified — confirmed absent; its existing T93 row is left exactly
as authorized. No `T94` was created or authorized. `T93` is not marked Done by this report or any
file it changed — that remains a post-QA, post-merge governance closeout step, per the established
`T87`–`T92` three-PR pattern.

## 14. Genuine Contradictions or Specification Gaps

None found that required stopping. One genuine gap is disclosed, not silently filled: the
specification's own repository-constraint note for File Numbering states that the existing
`matter_number`/`invoice_number`/`receipt_number` precedent "does not demonstrate a concurrency-safe
*generation* mechanism in the schema itself" — independently re-confirmed this session (zero
application-layer generation code exists for any of the three), meaning this ADR is a genuinely
from-scratch design, not an extension of a partially-built mechanism. No contradiction was found
between §24.8's three candidate mechanisms/scopes and any other frozen rule or already-accepted ADR.

## 15. Final Architecture Status

`ADR/0027` resolves Required ADR #9 in full: numbering algorithm, concurrency mechanism, and scope
recommendation are all decided, with format left deliberately underspecified pending #8. No other
Required ADR is resolved, reinterpreted, or narrowed. `ADR/0021`–`ADR/0026` are not modified.

## Reviewer Checklist

Per `docs/prompts/SoftwareArchitect.md` §8's required output and
`docs/ImplementationLog/README.md`'s standard eleven-item self-assessment:

```
Reviewer Checklist

[x] Architecture preserved -- ADR/0021, ADR/0022 composed with, not modified or contradicted;
    S4 rules cited, not reinterpreted.
[x] Existing design patterns followed -- ADR/0020's transaction boundary reused directly; no new
    transaction-management infrastructure introduced; organization_id-on-generator-table pattern
    matches ADR/0024/ADR/0026's identical discipline.
[ ] Tests added -- none; documentation-only architecture task, no implementation authorized.
[ ] Existing tests pass -- not applicable; no code changed for the test suite to exercise.
[x] Documentation updated -- ADR/0027 and this report are the documentation this task produces.
[x] ADR updated (if required) -- ADR/0027 created (Required ADR #9 resolution); ADR/0021-0026 not
    touched, correctly.
[ ] AI_BOOTSTRAP updated (if required) -- not required by this task's authorized scope.
[ ] PROJECT_STATE updated (if required) -- deferred by design to post-QA governance
    synchronization, per T93's own governance lifecycle.
[ ] No unrelated refactoring -- not applicable; no code touched at all.
[x] No scope creep -- File's broader field list, Matter-vs-File lifecycle, Matter-deletion cascade,
    and Workflow/Task/GovernmentProcess attachment granularity explicitly named as #8's territory,
    not touched; #10/#13/#20 not touched; only #9 resolved.
[x] Ready for QA -- ADR/0027 and this report are complete and handed off below.
```

## QA Handoff

This branch (`docs/t93-adr-0027-file-numbering-concurrency`) is handed off to the QA Reviewer role
for an independent, formal QA Decision against the actual remote PR HEAD once opened — per T93's own
row and this repository's established documentation-only-work QA requirement (`T80`–`T92`
precedent). The QA Reviewer is specifically asked to independently verify the concurrency mechanism's
correctness claims (§6 "Detailed Concurrency Analysis" in `ADR/0027`) mechanically, not merely accept
them, and to confirm the Matter-scoping recommendation is genuinely labeled as an inference rather
than presented as a specification mandate.

## QA Decision

□ Approved
☑ Approved with comments
□ Rework required

This Software Architect pass does not record, anticipate, or imply any of the three outcomes above
— per `docs/prompts/SoftwareArchitect.md` §11/§13, this role never renders a QA Decision or
substitutes for the QA Reviewer. `ADR/0027` and this report are not self-certifying.

**Recorded by the QA Reviewer role (2026-08-27), against this exact commit
(`753cb84f9def5e2310cd557a00360d6a751b29bb`), independently verified, not accepted on this report's
word.** PR #133 confirmed open, base `main`, remote HEAD exactly `753cb84f`; T93's authorization
commit `4e3b9a27c9f3fb8ac2835c7aa6315b8140f9210c` confirmed an ancestor via
`git merge-base --is-ancestor`, with exactly one commit (`753cb84`) between the authorization merge
(`9bbd939`, `main`'s tip) and the PR head — no unauthorized commit exists in between, and T92's own
governance closeout (`444477b`/PR #131) was independently confirmed to precede T93's authorization,
not merely asserted. The single-commit diff against `main` confirmed as exactly two files
(`ADR/0027-...md`, this report) — `ADR/0021`–`0026`, the specification, `IMPLEMENTATION_QUEUE.md`,
and `PROJECT_STATE.json` all absent from the diff; no `T94` row, branch, or PR exists (the stray
`T94` string match in `frontend/package-lock.json`/`package-lock.json` is an unrelated integrity-hash
substring, confirmed not part of this PR's diff).

§4 rules 4–7, §17.5's five mandatory tests (quoted verbatim: "File without Matter → reject," "Matter
without File → allow," "File creation → assigns File Number," "Concurrent File creation → no
duplicate," "Deleted/archived File → number not silently reused"), §21 item 9, §24.8's "File" and
"File Numbering" blocks (including the three named candidate mechanisms/scopes and the Matter-scoped
format example), §25 invariant #8, and §26 item 6's "concurrency-critical, not cosmetic" framing were
all independently read directly from `docs/Legal_DMS — Domain Model & Functional Specification.md`
and confirmed to match `ADR/0027`'s quotations verbatim — not accepted on the ADR's word. The
repository-investigation claims were independently re-run and confirmed exact:
`matters.matter_number`/`invoices.invoice_number`/`receipts.receipt_number` are plain unique
`String(50)` columns with zero application-layer generation code anywhere outside the model files
themselves; `Matter` carries no `organization_id` today; a full grep for `FOR UPDATE`/
`with_for_update`/`Sequence(`/advisory-lock usage across `backend/src/app/` returns zero matches;
`docker-compose.yml` runs `postgres:16-alpine` only, no Redis or distributed-lock service;
`backend/src/app/infrastructure/database/session.py` sets no explicit transaction isolation level —
confirming Postgres's default READ COMMITTED applies, which is the specific isolation level under
which the ADR's claimed "blocks, then proceeds" concurrency behavior for `INSERT ... ON CONFLICT`
actually holds (a materially different, incorrect narrative would result under SERIALIZABLE, which
this codebase does not use). `ADR/0020`'s per-request commit/rollback boundary was re-read in full
and confirmed to match the transaction-scope reuse this ADR claims. `ADR/0021`'s mandatory-
`organization_id`-directly-on-generator-tables discipline and `ADR/0022`'s resource+action model were
independently re-confirmed to support the composition claims made; neither is modified (confirmed
absent from the diff).

**Concurrency mechanism — independently verified mechanically, not merely accepted.** The
`INSERT ... ON CONFLICT (matter_id) DO UPDATE SET next_number = next_number + 1 RETURNING
next_number` idiom is Postgres's own documented atomic-upsert pattern: under READ COMMITTED (this
codebase's actual, unmodified default), a second transaction targeting the same conflict target
blocks on the row/index-entry lock until the first commits or rolls back, then re-evaluates against
the now-current state — this is exactly the mechanical behavior `ADR/0027`'s "Detailed Concurrency
Analysis" describes, not an unverified claim of "thread-safe." The shared-transaction design
(counter upsert + File-row insert in one transaction, reusing `ADR/0020`'s boundary) correctly
guarantees a rolled-back attempt never permanently burns a number, verified against `ADR/0020`'s own
text directly.

**Matter-scoped numbering inference — confirmed genuinely and correctly labeled as inference.** The
"Scope Decision" section is explicit that the specification leaves scope `ED` among three named
candidates, and grounds the Matter-scoped recommendation in two named textual signals (§24.8's own
Matter-scoped format example — independently confirmed as the *only* one of the three candidates
given a concrete example — and rule 4's "work package within a Matter" framing) plus one disclosed
architectural argument (contention distribution), while explicitly naming Organization-scoped
numbering as a genuinely defensible alternative, not a strawman. This does not overreach into a
specification mandate.

**§17.5 mandatory-test coverage — confirmed, with one completeness gap.** Three of the five tests are
directly and explicitly addressed by this ADR's own "Invariants" section: "File creation → assigns
File Number," "Concurrent File creation → no duplicate," and "Deleted/archived File → number not
silently reused." The remaining two — "File without Matter → reject" and "Matter without File →
allow" — are correctly outside Required ADR #9's scope (they test File's own existence/FK
relationship to Matter, which is Required ADR #8's territory, not the numbering mechanism this ADR
decides) and are not silently ignored (the "Explicit Out-of-Scope Boundaries" section covers
Matter-vs-File lifecycle generally) — but neither is named individually by its own §17.5 test text
the way the other three are, a minor traceability gap for a future reader checking full §17.5
coverage against this ADR alone.

**Scope containment confirmed:** Required ADR #8, #10, #13, #20 remain untouched and explicitly
listed as unresolved; File's broader field architecture, Matter-vs-File lifecycle, Matter-deletion
cascade, and Workflow/Task/GovernmentProcess attachment granularity are all correctly deferred to #8;
the exact stored/display format and `UNIQUE` constraint shape are correctly deferred to #8, not
invented (no office/district/year/department code introduced).

Blocking findings: none.

Non-blocking comments (do not block approval):

1. **The "Allocation gaps" point in the Detailed Concurrency Analysis (point 8) is confusingly
   worded and appears to internally tension with the ADR's own "Invariants" section.** Point 8 opens
   with "Allocation gaps: possible only if..." and describes a scenario (a transaction reads the
   `RETURNING` value, then its own commit later fails), but because the counter increment and the
   File insert share one transaction, a failed commit rolls back atomically — no gap is actually
   created in the persisted-number ledger; the next transaction receives the identical number again,
   exactly as point 5 and the "Invariants" section (correctly) already establish. The ADR's
   substantive guarantee is not wrong — no rule-7 violation occurs either way — but the "possible
   only if" framing in point 8 reads as asserting gaps *can* occur under normal operation of this
   mechanism, when in fact, per this ADR's own design, they cannot occur within the persisted ledger
   at all (unlike the rejected native-`SEQUENCE` alternative, which does permanently burn gaps). A
   future revision should reword point 8 to avoid this internal ambiguity.
2. **The two structural §17.5 tests not addressed by this ADR** ("File without Matter → reject,"
   "Matter without File → allow") are correctly out of scope but not individually named — see
   above. Naming them explicitly as "Required ADR #8's tests, not this ADR's" would close the
   traceability gap for a future reader auditing full §17.5 coverage without needing to cross-
   reference #8's eventual scope.

**QA Decision: Approved with comments.** ADR/0027 makes a mechanically-verified, specification-
grounded decision on the File numbering algorithm and concurrency mechanism, correctly disqualifies
the in-process-lock alternative on real multi-process grounds, honestly labels Matter-scoped
numbering as inference rather than mandate, and does not silently decide File's broader field
architecture, format, or any other Required ADR #8 territory. No implementation code, schema, or
governance file was touched. PR #133 remains open and unmerged.

---

**This report ends T93's authorized scope at the implementation PR handoff.** Per this task's own
governing instructions, T93 stops here, awaiting independent QA. No further action (opening/merging
a PR beyond the point specified below, creating T94, marking T93 Done, performing QA, governance
closeout) is taken by this pass.
