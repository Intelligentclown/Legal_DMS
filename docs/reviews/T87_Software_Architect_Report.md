# T87 Software Architect Report

**Task:** T87 — Draft and resolve Required ADR #1 ("Organization as tenant boundary") + #19
("Tenant isolation enforcement"), per `docs/Legal_DMS — Domain Model & Functional Specification.md`
§21's planning-list terminology. Full authorized-scope text: `IMPLEMENTATION_QUEUE.md`'s T87 row.

**Role:** Software Architect. Per T87's own authorization text, this role has no formally-adopted
`docs/prompts/SoftwareArchitect.md` in this repository — the same informal-role precedent
`ADR/0001`–`0020` were already produced under. This report does not create or adopt such a prompt
file; it is not authorized to.

This report follows `docs/reviews/T86_Documentation_Manager_Report.md`'s established shape for a
pure documentation/architecture task with no Stage/Phase implementation association.

---

## 1. Authorization

- **Authorization commit:** `e74f84903ed306c7706ed5757b8b3405e8d202be` ("docs(governance): authorize
  T87")
- **Authorization PR:** #113 (`docs/t87-authorization`)
- **Authorization merge commit:** `b3e8ffb162e1e38f5aba67d7b717fa288c7c9026` (on `main`)
- **Verified independently this session**, not taken from the handoff text alone:
  - `git fetch origin` showed local `main` was **behind** `origin/main` by 2 commits
    (`3b28e43..b3e8ffb`) at session start — the handoff's claimed HEAD (`b3e8ffb`) was correct for
    `origin/main`, but not yet for the local checkout. Fast-forwarded local `main` to `b3e8ffb` via
    `git merge --ff-only origin/main` (safe — no divergent local commits existed; confirmed by the
    merge being a clean fast-forward, not a three-way merge).
  - Post-fast-forward: `main == origin/main` at `b3e8ffb`, working tree clean.
  - `git show --stat b3e8ffb` / `git show --stat e74f849`: both touch exactly one file,
    `IMPLEMENTATION_QUEUE.md`, one line inserted — the T87 authorization row and nothing else.
  - `git merge-base --is-ancestor e74f849 main` → **YES** (post-fast-forward; was **NO**
    pre-fast-forward, which is expected and consistent with the "behind by 2" state, not a
    discrepancy).
  - T87's row, read in full directly from `IMPLEMENTATION_QUEUE.md` line 943, confirms: Required
    ADR #1/#19 scope, the explicit "does not decide *whether* Organization is the tenant boundary"
    boundary, the informal-role disclosure quoted above, the required-QA-before-merge statement, and
    the six-step governance lifecycle this report follows steps (1)–(2) of.
  - `PROJECT_STATE.json`: zero occurrences of `T87` — confirmed unmodified, consistent with the T87
    row's own instruction that synchronization happens only after a formal QA Decision exists.
  - No `T88` row exists anywhere in `IMPLEMENTATION_QUEUE.md` or `PROJECT_STATE.json`.
  - `ADR/0021` did not exist prior to this pass; `ADR/0001`–`0020` and `ADR/template.md` were read
    but not modified.

## 2. Sources Read Before Drafting

Per T87's own required-reading list and this report's own diligence, read directly from the
repository (not from the handoff summary) before drafting `ADR/0021`:

- `ADR/template.md` and `ADR/0009`, `ADR/0018` in full, as style/structure precedent.
- `docs/Legal_DMS — Domain Model & Functional Specification.md` §4 (all 46 rules), §21 (including
  its correction-pass terminology note distinguishing planning-list numbers from repository ADR
  filenames), §23 (the frozen entity list and the corrected "46 rules" statement), §24.1
  (Organization, User, Team, Role/Permission, and the cross-cutting "no `relationship()` anywhere"
  note), §25 (the 14-row cross-domain checklist and its own terminology note), §26 (items 2 and 8 of
  the "must resolve before implementation" list), §27.
- `IMPLEMENTATION_QUEUE.md`'s T86 and T87 rows in full.
- `docs/prompts/README.md`'s "Independent Technical Verifier" and "Frontend Developer" role-adoption
  disclosures, for governance context on how this repository treats informally-adopted roles.
- Direct source inspection (all read this session, not assumed from the specification's own prior
  citations): `backend/src/app/application/interfaces/repository.py`
  (`AbstractRepository`), `backend/src/app/infrastructure/persistence/sqlalchemy_repository.py`
  (`SqlAlchemyRepository` — confirmed `get_by_id`/`list`/`count`/`add`/`update`/`delete` are all
  tenant-blind), `backend/src/app/infrastructure/auth/rbac_authorization_service.py`
  (`RbacAuthorizationService`), `backend/src/app/application/interfaces/search.py` (`SearchIndex`),
  `backend/src/app/application/interfaces/job_queue.py` (`JobQueue`/`Job`),
  `backend/src/app/infrastructure/storage/local_file_storage.py` (`LocalFileStorage`),
  `backend/src/app/infrastructure/persistence/models/*.py` (full-repo search confirming zero
  `organization_id` columns and zero `relationship()` declarations), `docker-compose.yml` and
  `backend/.env.example`/`settings.py` (confirming a single Postgres service/database and a single
  database role that is also the Alembic migration owner — directly relevant to RLS feasibility).

## 3. ADR Drafted

- **File:** `ADR/0021-organization-tenant-boundary-enforcement.md`
- **Branch:** `docs/t87-adr-0021-tenant-enforcement` (created from `main` at `b3e8ffb`)
- **Commit:** `41baf04e504779d6f1d61a3216f4210c44a24a96` ("docs(adr): draft ADR-0021 — Organization
  tenant-boundary enforcement (T87)")
- **Files changed:** exactly one — `ADR/0021-organization-tenant-boundary-enforcement.md` (new
  file, 402 insertions). Confirmed via `git show --stat 41baf04`. No backend, frontend, test,
  migration, configuration, `PROJECT_STATE.json`, `IMPLEMENTATION_QUEUE.md`, or specification file
  touched.

**Decision summary:** shared single Postgres database/schema (unchanged from today's actual
deployment shape); a mandatory, non-nullable `organization_id` on every tenant-scoped table;
mandatory, non-optional application-layer tenant scoping as the primary enforcement mechanism on
every repository operation (read and write alike); PostgreSQL Row-Level Security
(`FORCE`d, default-deny) as a mandatory, independently-enforced defense-in-depth backstop — not a
redundant restatement of the same check. Explicitly addresses request/service origination and
propagation, the repository/data-access layer, background jobs (payload-carried Organization
identifier, validated at enqueue time), search (structural Organization field, not free-form
metadata), and file storage (Organization-namespaced storage keys, not merely
`FileStorageRecord`-metadata-only). Schema-per-tenant and database-per-tenant were evaluated and
rejected on operational-cost grounds specific to this repository's evidenced single-database
deployment shape, explicitly labeled as an assumption where the specification itself doesn't settle
scale. Application-layer-only and RLS-only were each evaluated and rejected as the sole mechanism,
grounded in a real precedent already in this repository's own history (`T79`'s discovery of
unreviewed ad hoc `insert_admin*.py` scripts) and in the concrete, currently-true fact that the
runtime database role is also the table-owning migration role (making RLS-only currently inert
without an accompanying role split).

**Explicit dependency recorded, not resolved:** Required ADR #18 (authorization architecture) must
compose with, not replace, the Organization-scope context this ADR establishes — recorded in the
ADR's own "Relationship to Required ADR #18" section, per T87's explicit instruction not to
silently decide authorization granularity.

## 4. Self-Review (Software Architect)

Adapted from `docs/ImplementationLog/README.md`'s Reviewer Checklist and T87's own §15 self-review
requirements:

```
Scope
☑ Only T87's authorized architectural scope addressed (Required ADR #1 + #19 only).
☑ No other Required ADR resolved -- #18 explicitly deferred with a recorded dependency; #2-#17,
   #20 explicitly listed as untouched in the ADR's own "Dependencies" section.

Business baseline
☑ Organization remains the tenant boundary -- not reopened; ADR's Problem section cites S4 rule 43
   and S24.1 as already-settled, not as this ADR's own decision.
☑ No S4 rule changed -- specification file not modified by this pass (confirmed: git status shows
   only ADR/0021 and this report as new files; the spec file does not appear in this branch's diff).
☑ No S23 frozen entity list changed -- not touched.
☑ Specification file byte-identical to the T86-adopted baseline -- confirmed: not included in this
   branch's diff against main at all.

ADR correctness
☑ ADR number is 0021 -- confirmed against actual repository state (ADR/0001-0020 existed;
   0021 did not, prior to this pass).
☑ Filename follows repository convention -- NNNN-kebab-case-title.md, matching all 20 existing ADRs.
☑ Follows ADR/template.md's core sections (Problem/Options Considered/Decision/Reasoning/
   Trade-offs/Future Impact), extended with Relationship-to-ADR-#18, Dependencies, Operational
   Implications, and Testing/Verification Obligations sections -- the same extension pattern
   ADR-0018 already used (a Decision table beyond the bare template), not a novel format.
☑ Decision is explicit -- one named mechanism (shared schema + mandatory app-layer scoping +
   mandatory RLS backstop), not a "use best practices" deferral.
☑ Alternatives genuinely evaluated -- 5 options, each scored against isolation strength, bypass
   risk, ergonomics, coverage (repositories/jobs/search/storage), and operational complexity,
   per S6 of the authorizing task.
☑ Rejected alternatives have concrete, repository-grounded reasons -- not generic pros/cons.
☑ Tenant isolation explicitly distinguished from authorization -- dedicated section, S18
   dependency recorded rather than silently decided.
☑ Background jobs covered -- payload-carried Organization id, validated at enqueue, no ambient
   request context assumed.
☑ Repositories covered -- all six AbstractRepository operations addressed by name, reads and
   writes both.
☑ Search covered -- structural Organization field distinguished from free-form metadata.
☑ File storage covered -- namespace-in-path, independent of FileStorageRecord metadata alone.
☑ Failure/default-deny behavior addressed -- both layers required to fail closed, stated explicitly.
☑ Context propagation addressed -- explicit-value threading required over implicit
   global/thread-local reads, with reasoning tied to the ergonomics criterion.
☑ Operational consequences addressed -- dedicated section (role split, paired-migration
   discipline, connection-pool GUC-reset correctness).
☑ Unresolved dependencies clearly identified -- dedicated "Dependencies / Other Unresolved
   Related ADRs" section naming #18 and #20 specifically, plus a blanket note on #2-#17.

Repository hygiene
☑ No unrelated files changed -- ADR/0021-organization-tenant-boundary-enforcement.md commit
   touches exactly one file (git show --stat, confirmed above).
☑ No code/schema/API/migration changes -- confirmed, no such file appears in this branch's diff.
☑ No PROJECT_STATE.json changes -- confirmed absent from this branch's diff; deferred to the
   Documentation Manager role, after a formal QA Decision exists, per governance step (5).
☑ No T88 created -- confirmed absent from IMPLEMENTATION_QUEUE.md and PROJECT_STATE.json.
```

## 5. QA Handoff

This branch (`docs/t87-adr-0021-tenant-enforcement`) and commit (`41baf04`) are handed off to the
QA Reviewer role for an independent, formal QA Decision (`Approved` / `Approved with comments` /
`Rework required`), against the actual remote PR HEAD once opened — per T87's own row ("the
eventual ADR PR must independently undergo QA, re-verified on its actual remote PR HEAD, before any
merge") and `PROJECT_WORKFLOW.md`/`docs/DefinitionOfDone.md`'s documentation-only-work QA
requirement, the same principle already established for T80/T81/T82/T86.

## 6. QA Status

**Unresolved.** No QA Decision has been rendered as of this report. This Software Architect pass
does **not** record, anticipate, or imply `Approved`, `Approved with comments`, or `Rework
required` — that decision belongs solely to the QA Reviewer role, independently, against this
commit and the eventual PR HEAD.

## 7. Explicitly Not Done By This Pass

Per T87's own authorization boundary, none of the following were performed, and none are implied by
this report or by `ADR/0021` itself:

- Required ADR #18 was not resolved — authorization granularity remains fully open; only a
  composition dependency was recorded.
- Required ADR #2–#17 and #20 were not resolved or touched.
- No `§4` business rule, `§23` frozen entity decision, or any other part of
  `docs/Legal_DMS — Domain Model & Functional Specification.md` was modified.
- No database schema, migration, backend, frontend, or API implementation was performed. No RLS
  policy, tenant middleware, tenant-aware repository class, or infrastructure configuration was
  created — `ADR/0021` describes what future implementation must do; it does not implement it.
- No test implementing the decision was added.
- No Stage 4 business feature was selected or authorized.
- `T88` or any subsequent task was not created or authorized.
- `PROJECT_STATE.json` was not modified — synchronization remains deferred until after the formal
  QA Decision exists, per the established T80/T81/T86 pattern and this role's own boundary
  (`PROJECT_WORKFLOW.md` §8).
- `IMPLEMENTATION_QUEUE.md` was not modified by this pass — its existing T87 row (recorded by the
  authorization commit `e74f849`) is left as-is; marking it "Done" is a post-QA synchronization
  step, not part of this drafting pass.
- The PR was not opened as merged, and this report does not authorize a merge — merge remains
  gated on the QA Reviewer's independent decision against the actual PR HEAD, per T87's own stop
  condition and this task's governing instructions.

---

## T87 QA Decision

**Decision: APPROVED**

**Reviewed PR:** #114 (`docs/t87-adr-0021-tenant-enforcement`)
**Reviewed HEAD:** `30a374913e7df5b124315d839ecc3b1fe19b6895`

**Blocking findings:** none.
**Non-blocking comments:** none.

The QA Reviewer independently confirmed: T87 authorization is active; `ADR/0021`'s content is
correct against the governed specification; `ADR/0001`–`0020` and `ADR/template.md` are untouched;
no source/schema/API/migration file was touched; Stage 4 remains unselected; no `T88` row exists;
the full ADR was read directly, not sampled; the relevant specification sections (§4, §21, §23,
§24.1, §25, §26) were independently checked against the ADR's claims; and this Software Architect
report was independently cross-checked rather than taken on trust. No file was modified by the QA
review itself.

**Provenance of this record:** this decision was reached and reported by the QA Reviewer role in
its own review session; at the time of that review, no GitHub-native PR review or comment was
posted to PR #114 (confirmed via `gh pr view 114 --json reviews,comments`: both empty), and no
`docs/reviews/T87_QA_Review.md` or other repository file recorded it — the decision had no
persistent repository record. This section formally records it, following the precedent set by
commit `bceff1c` ("docs(qa): record T81 approval") and commit `f6974cf` ("docs(qa): record T86
approval with comments"), both of which recorded a QA Decision under the identical circumstance.

**This is the formal QA Reviewer decision** for T87 — the sole review gate this task requires; no
earlier informal/advisory verification pass exists for T87 to be confused with.

**Independent re-verification performed by this Documentation Manager pass, not merely restated**
(mirroring `bceff1c`'s and `f6974cf`'s own "independently re-performed here" discipline):

- **PR HEAD match** — `gh pr view 114 --json headRefOid` returns `30a374913e7df5b124315d839ecc3b1fe19b6895`,
  exactly the reviewed HEAD; no commit was added to the branch after the review, and no scope
  changed after QA.
- **Diff scope** — `git diff --stat main 30a3749`: exactly two files,
  `ADR/0021-organization-tenant-boundary-enforcement.md` (new, +402) and this report (new, +206;
  now +49 more for this section). No other file touched.
- **ADR/0021 content** — re-read directly at its committed location: explicitly resolves only
  Required ADR #1 + #19; explicitly defers #18 with a recorded composition dependency, not a
  silent decision; explicitly lists #2–#17 and #20 as untouched; the "Decision" section specifies a
  mechanism, not implementation code (no repository, migration, or infrastructure file created or
  changed).
- **No other ADR touched** — confirmed `ADR/0001`–`0020` and `ADR/template.md` do not appear in
  `git diff --stat main 30a3749`.
- **No other change** — confirmed no source, schema, migration, test, configuration,
  `PROJECT_STATE.json`, `IMPLEMENTATION_QUEUE.md`, or specification file exists anywhere in this
  branch's diff against `main`.

**No rework required.** This QA Decision does not require any change to `ADR/0021`, and none was
made.
