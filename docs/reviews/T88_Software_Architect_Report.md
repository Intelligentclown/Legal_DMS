# T88 Software Architect Report

**Task:** T88 — Draft and resolve Required ADR #18 ("Authorization architecture"), per
`docs/Legal_DMS — Domain Model & Functional Specification.md` §21's planning-list terminology. Full
authorized-scope text: `IMPLEMENTATION_QUEUE.md`'s T88 row.

**Role:** Software Architect. Per T88's own authorization text, this role has no formally-adopted
`docs/prompts/SoftwareArchitect.md` in this repository — the same informal-role precedent
`ADR/0001`–`0021` were already produced under. This report does not create or adopt such a prompt
file; it is not authorized to.

This report follows `docs/reviews/T87_Software_Architect_Report.md`'s established shape for a pure
documentation/architecture task with no Stage/Phase implementation association, through the same
governance lifecycle stage T87 reached (drafting Software Architect report, pre-QA) — not further.

---

## 1. Repository Baseline / Authorization Verification

Verified independently this session, not taken from the prompt's claimed state alone:

- `git fetch origin` showed local `main` was **behind** `origin/main` by 2 commits at session start
  (local HEAD `b3010fe`, `origin/main` at `388e723`). Fast-forwarded local `main` to `388e723` via
  `git merge --ff-only origin/main` — a clean fast-forward (no divergent local commits; working tree
  was clean before the merge).
- Post-fast-forward: `main == origin/main` at `388e723b09971a2a94849de8009d2376438f95a5`, matching
  the prompt's claimed merge-commit SHA exactly.
- `git merge-base --is-ancestor c29ef6d8845d8e27037849e86f861606c48d7e8f main` → **YES**, confirmed
  after the fast-forward (was **NO** before it, expected and consistent with "behind by 2", not a
  discrepancy).
- `git show --stat c29ef6d8845...` (the T88 authorization commit, "docs(governance): authorize T88")
  touches exactly one file, `IMPLEMENTATION_QUEUE.md`, one line inserted — read in full; matches the
  T88 authorization scope described in this task's prompt verbatim.
- `IMPLEMENTATION_QUEUE.md`'s T88 row, read in full directly from the file (not from the prompt),
  confirms: Required ADR #18 scope; the explicit "must treat as already established" list (Org is
  tenant boundary, tenant isolation governed by `ADR/0021`, authorization must never replace tenant
  scoping, `ADR/0021` remains frozen); the informal-role disclosure; the required-QA-before-merge
  statement; and the three-PR governance lifecycle (authorization → implementation+QA →
  post-merge closeout) this report follows steps (1)–(2) of.
- `ADR/0022` did not exist prior to this pass (`ls ADR/0022*` failed before drafting).
- No `T89` reference exists anywhere in the repository — checked via a full-repository filename
  search (`find . -iname "*T89*"`, excluding `node_modules`/`.git`) and a content grep of
  `IMPLEMENTATION_QUEUE.md`/`PROJECT_STATE.json`: zero matches for both.
- `PROJECT_STATE.json`: `currentStage.id` = `stage-3` ("Authentication & Authorization"),
  `currentStage.status` = `in_progress`; `businessFeatures` = `[]` — both confirmed unchanged from
  the prompt's claimed state, read directly via `node -e "JSON.parse(...)"` rather than assumed.
- No unauthorized implementation had already occurred: `git log --oneline` between the T87 closeout
  merge and the T88 authorization merge shows only the T88 authorization commit and its merge PR
  (#116) — no backend/frontend/schema/migration/test file appears anywhere on `main` between those
  two points.

## 2. Repository Investigation Performed

Read directly from the repository (not from the task prompt's summary) before drafting `ADR/0022`:

- `ADR/template.md` and `ADR/0018`, `ADR/0019`, `ADR/0020` in full, as style/structure/precedent —
  `ADR/0018` (D1–D6, the *unrelated*, already-accepted, filename-`0018` ADR — confirmed distinct
  from planning-list item #18, per §21's own terminology note); `ADR/0019` (D7,
  `AuthenticationProvider` signature — the authentication/authorization separation-of-concerns
  precedent `ADR/0022` follows); `ADR/0020` (session commit/rollback policy — the request-scoped
  transaction boundary authorization checks execute inside).
- `ADR/0021-organization-tenant-boundary-enforcement.md` in full (403 lines) — the frozen tenant-
  isolation baseline this task requires `ADR/0022` to compose with, not reopen. Its own
  "Relationship to Required ADR #18" section (lines 280–296) was read as the authoritative
  composition-dependency statement `ADR/0022` had to satisfy.
- `PROJECT_WORKFLOW.md` §8 (Documentation Ownership) — confirmed ADRs are Software Architect-owned.
- Specification sections §4 (all 46 rules, focus on 43–46), §21 (Required ADRs list and its
  planning-list-vs-filename terminology note), §24.1 (Organization, User, and — most directly —
  the Role/Permission entity block), §24.14 (Confidentiality — the three candidate mechanisms for
  §4 rule 45's finer-grained access), §25 (the 14-row cross-domain invariant table, focus on
  invariants #11 and #12), §26 (the "must resolve before implementation" list, item 8), §27
  (readiness assessment, confirming §26's items were still open at time of writing).
- **Direct source inspection**, delegated to a background investigation pass and independently
  reasoned about against the specification and `ADR/0021`'s own claims before drafting (not taken
  on faith): `backend/src/app/infrastructure/auth/rbac_authorization_service.py` (full file, 37
  lines — `RbacAuthorizationService.require_permission()`), `backend/src/app/presentation/api/deps.py`
  (`RequirePermission` factory, `get_authorization_service()`, `get_current_user()`),
  `backend/src/app/infrastructure/persistence/models/identity.py` (full file — `User`, `Role`,
  `Permission`, `UserRole`, `RolePermission`), `backend/src/app/application/interfaces/auth.py`
  (full file — `CurrentUser`, `AuthenticationProvider`, `AuthorizationService` ports),
  `backend/src/app/presentation/api/v1/users.py` (the one router currently using
  `RequirePermission`), `backend/src/app/presentation/api/v1/auth.py` (`/auth/me`'s deliberate
  non-use of `RequirePermission`), `backend/src/app/application/interfaces/repository.py` and
  `infrastructure/persistence/sqlalchemy_repository.py` (`AbstractRepository`/
  `SqlAlchemyRepository` — confirmed zero permission/tenant awareness), `backend/src/app/
  application/interfaces/job_queue.py` (`Job`/`JobQueue` — confirmed zero authorization context in
  payloads), `backend/src/app/application/interfaces/search.py` (`SearchIndex` — confirmed zero
  permission awareness), `backend/src/app/application/interfaces/file_storage.py` and
  `infrastructure/storage/local_file_storage.py` (`FileStorage`/`LocalFileStorage` — confirmed zero
  permission awareness, path-traversal guard only), and the seed migrations
  `9963e15f2752_seed_lookup_data.py` (six roles, eighteen permission codes) and
  `224b650e5235_seed_role_permissions.py` (fifty-nine role→permission grants, cross-checked against
  `test_t66_role_permissions.py`'s hardcoded `EXPECTED_MATRIX` regression assertion).
- **Existing authorization/security tests** — inspected, not modified: `test_rbac_authorization_service.py`,
  `test_auth.py` (including its `TestRequirePermission` class), `test_auth_dependency_wiring.py`,
  `test_sqlalchemy_role_permission_repository.py`, `test_t66_role_permissions.py`, `test_users.py`'s
  `TestAuthorization`/`TestRoleAssignmentAuthorization`/`TestPermissionDeniedAuditing` classes —
  read to understand the current architectural boundary (what is actually tested and passing
  today), not touched.

## 3. Architectural Findings

- A real, working, tested resource+action permission-based authorization mechanism already exists
  (`RbacAuthorizationService`/`RequirePermission`/`Role`/`Permission`/`UserRole`/`RolePermission`) —
  this is not a from-scratch design problem the way tenant isolation was for `ADR/0021`. Six seeded
  roles, eighteen permission codes, fifty-nine grants, exercised today by exactly one router
  (`users.py`).
- This mechanism has **zero** Organization/tenant awareness anywhere — confirmed identically to
  `ADR/0021`'s own finding, independently re-confirmed here by direct inspection of the same files.
- **Nothing else** in the stack (repositories, background jobs, search, file storage) has any
  permission awareness at all — confirmed by full-file reads showing no reference to `CurrentUser`,
  `AuthorizationService`, roles, or permission codes in any of those four surfaces.
- The specification (§24.1) explicitly frames the needed work as "Modify" the existing
  Role/Permission mechanism, not replace it — directly supporting formalizing the existing
  implementation as the adopted architecture rather than designing an alternative from scratch.
- Two business-model questions are explicitly left open by the specification itself and were
  **not** invented or silently decided by this pass, per the task's explicit instruction: (1) which
  of three named candidate mechanisms (§24.14) resolves §4 rule 45's resource-instance-level
  ("finer-grained") access requirement; (2) whether the Role/Permission catalog becomes
  per-Organization or stays global-with-per-Organization-assignment (§24.1). Both are recorded in
  `ADR/0022` as explicit limitations, not decided.
- One genuine architectural gap was identified and named, not silently assumed solved: direct
  service/use-case invocation bypassing the FastAPI dependency graph (a future CLI command,
  command-bus handler, or similar) has no structural guarantee against skipping the permission
  check, since no such non-HTTP entry point exists today to design a stronger guarantee against.
  `ADR/0021` accepted an analogous reliance for its own application-layer tenant scoping; `ADR/0022`
  inherits the same category of reliance for the same underlying reason, named explicitly in its
  own "Bypass Analysis" section rather than glossed over.

## 4. ADR/0022 Decision

- **File:** `ADR/0022-authorization-architecture.md`
- **Branch:** `docs/t88-adr-0022-authorization-architecture` (created from `main` at `388e723`)
- **Decision:** Resource + action permission-based authorization via role indirection (formalizing
  the existing `RbacAuthorizationService`/`RequirePermission`/`Role`/`Permission` mechanism as the
  adopted architecture, not a new design). Primary authorization decision point: the request/
  service (use-case) boundary — evaluated before the business operation executes; today implemented
  as a FastAPI route dependency, with this ADR fixing the responsibility one level more precisely
  at the service/use-case layer for future non-HTTP entry points. Repositories remain deliberately
  permission-agnostic (no second permission engine), while continuing to carry `ADR/0021`'s
  mandatory tenant-scope requirement independently. Background jobs: permission evaluated once at
  enqueue time by the already-authorized caller; execution time re-establishes only `ADR/0021`'s
  tenant scope, not a permission re-check (no principal context survives to re-check against) — a
  named, accepted staleness trade-off. Search and file storage: both treated as use-cases behind the
  same primary gate, plus `ADR/0021`'s independent tenant checks; file storage additionally requires
  indistinguishable not-found responses for "forbidden" versus "does not exist," to avoid
  information leakage. A structural extension point (not an implementation) is named for the
  still-open resource-instance-granularity question (§24.14), placed at the same data-access layer
  as `ADR/0021`'s tenant filter rather than inside the coarse-grained permission check.

## 5. Alternatives Considered

Six alternatives evaluated and scored (security, expressiveness, consistency, bypass resistance,
maintainability, operational complexity, `ADR/0021` compatibility, existing-code compatibility) in
`ADR/0022`'s own "Options Considered" section: role-only (rejected — coarser, regresses tested
model), permission-only (rejected — higher administrative burden, no expressiveness gain the
business rules need), resource+action via role indirection (**selected** — matches §4 rule 44 and
§24.1's own "Modify" guidance), service-layer-only with no route dependency (rejected as a wholesale
replacement — loses existing fail-fast behavior; its underlying concern absorbed into the Decision
and Bypass Analysis instead), duplicate-everywhere (rejected — the task's own explicit warning
against automatic duplication, and this repository's actually-evidenced bypass risk (`T79`) was ad
hoc scripts, not inter-layer permission-logic disagreement), and a policy-based/ABAC engine
(rejected for now — unjustified operational complexity at current evidenced scale, and would serve
a business rule — §4 rule 45 — not yet decided regardless).

## 6. ADR-0021 Composition

`ADR/0022` includes a dedicated "Relationship to ADR-0021 — Tenant Isolation" section stating the
composed sequence (Authentication → Organization/Tenant-Scope resolution → Authorization → Business
operation, with data access independently re-applying tenant scope regardless of the authorization
outcome) and the five Critical Architectural Constraints verbatim from this task's own instructions:
authorization does not replace tenant scoping; tenant scoping does not replace authorization; a
permission check is never an alternative tenant-isolation mechanism; an Organization-scoped
permission is never itself proof of tenant membership; both controls compose fail-closed. `ADR/0021`
is cited, not modified, reopened, or reinterpreted anywhere in `ADR/0022`.

## 7. Scope / Exclusion Verification

```
Scope
[x] Only T88's authorized architectural scope addressed (Required ADR #18 only).
[x] No other Required ADR resolved -- #1/#19 correctly attributed to ADR/0021 throughout, not
    re-resolved; #2-#17/#20 explicitly listed as untouched in ADR/0022's own "Explicitly Unresolved
    Items" section.
[x] ADR/0021 not modified, reopened, weakened, or reinterpreted -- confirmed via git diff --stat
    main (below): ADR/0021 does not appear in this branch's diff at all.
[x] ADR/0001-0020 and ADR/template.md not modified -- confirmed absent from this branch's diff.

Business baseline
[x] Organization remains the tenant boundary -- not reopened; ADR/0022 cites ADR/0021 and S4 rule
    43 as already-settled, not as its own decision.
[x] No S4 rule changed -- specification file not modified by this pass (confirmed: git status
    shows only ADR/0022 and this report as new files).
[x] No S23 frozen entity model changed -- not touched.
[x] Resource-instance-granularity mechanism (S24.14's three candidates) NOT chosen -- explicitly
    recorded as unresolved, per this task's instruction against inventing business rules.
[x] Role/Permission catalog global-vs-per-Organization shape (S24.1) NOT chosen -- explicitly
    recorded as unresolved, for the same reason.

ADR correctness
[x] ADR number is 0022 -- confirmed against actual repository state (ADR/0001-0021 existed; 0022
    did not, prior to this pass).
[x] Filename follows repository convention -- NNNN-kebab-case-title.md.
[x] Explicitly distinguishes planning-list item #18 from filename ADR/0018 -- stated in the header
    and restated in Problem, to prevent the exact numbering-collision confusion S21 itself warns
    about.
[x] Follows ADR/template.md's core sections (Problem/Options Considered/Decision/Reasoning/
    Trade-offs/Future Impact), extended with Relationship-to-ADR-0021, Bypass Analysis,
    Dependencies, Testing/Verification Obligations, and Explicitly Unresolved Items -- the same
    extension pattern ADR/0021 already used.
[x] Decision is explicit -- one named mechanism (resource+action via role indirection, formalizing
    the existing implementation), not a "use best practices" deferral.
[x] Alternatives genuinely evaluated -- 6 options, scored against 8 criteria including ADR/0021 and
    existing-code compatibility.
[x] Rejected alternatives have concrete, repository-grounded reasons -- not generic pros/cons.
[x] Tenant isolation explicitly distinguished from authorization -- dedicated "Relationship to
    ADR-0021" section with the five Critical Architectural Constraints stated verbatim.
[x] Background jobs covered -- enqueue-time-only permission evaluation, staleness trade-off named
    explicitly.
[x] Repositories covered -- explicitly kept permission-agnostic, with reasoning distinguishing
    structural (tenant) from action-level (permission) filtering.
[x] Search covered -- treated as a use-case behind the same gate; instance-level filtering deferred
    to the same extension point as file storage.
[x] File storage covered -- same-gate requirement plus an explicit not-found/forbidden
    indistinguishability rule.
[x] Fail-closed behavior addressed -- dedicated subsection, six named failure inputs, all denying.
[x] Bypass analysis performed -- dedicated section covering all nine vectors named in this task's
    instructions (API, direct service, repository, background job, search, file storage, ad hoc
    scripts/privileged DB access, stale context), each naming which layer is/isn't responsible.
[x] Unresolved dependencies clearly identified -- dedicated "Dependencies / Other Unresolved
    Related ADRs" and "Explicitly Unresolved Items" sections.

Repository hygiene
[x] No unrelated files changed -- confirmed via git status: only ADR/0022 and this report are new;
    nothing else appears as modified or untracked.
[x] No code/schema/API/migration changes -- confirmed, no such file appears anywhere in this
    branch's diff.
[x] No test file modified -- confirmed; test files were read, not edited.
[x] No PROJECT_STATE.json changes -- confirmed absent from this branch's diff; deferred to the
    Documentation Manager role, after a formal QA Decision exists, per governance step (5)/(6).
[x] No IMPLEMENTATION_QUEUE.md changes -- confirmed absent from this branch's diff; its existing
    T88 row is left as-is.
[x] No T89 created or authorized -- confirmed absent from IMPLEMENTATION_QUEUE.md and
    PROJECT_STATE.json both before and after this pass.
[x] No Stage 4 business feature selected -- businessFeatures remains [].
[x] currentStage not changed -- remains stage-3 / in_progress.
```

## 8. Exact Files Changed

```
$ git status
On branch docs/t88-adr-0022-authorization-architecture
Untracked files:
  ADR/0022-authorization-architecture.md
  docs/reviews/T88_Software_Architect_Report.md

$ git diff --stat main
(empty prior to this commit -- both files are new, untracked)
```

Exactly two new files, both documentation: `ADR/0022-authorization-architecture.md` and this
report. No existing file was modified.

## 9. Confirmation No Implementation Occurred

No database schema, migration, backend, frontend, or API implementation was performed. No
permission-check code, service-layer guard, repository parameter, job-payload field, search-index
field, or file-storage change was created or modified — `ADR/0022` describes what future
implementation must do; it does not implement it. No test was added or modified. No RBAC
infrastructure file (`rbac_authorization_service.py`, `deps.py`, `identity.py`, or any other source
file investigated above) was touched — all were read-only inspections.

## 10. Confirmation No Other Required ADR Resolved

`ADR/0022` resolves only Required ADR #18. Required ADR #1 and #19 remain attributed to `ADR/0021`
(not re-resolved or restated as this ADR's own decision anywhere). Required ADR #2–#17 and #20 are
explicitly listed as untouched in `ADR/0022`'s own "Dependencies / Other Unresolved Related ADRs"
and "Explicitly Unresolved Items" sections. `ADR/0021` itself is not modified.

## 11. T89 Absence Confirmed

No `T89` row exists in `IMPLEMENTATION_QUEUE.md`; no `T89` reference exists anywhere in
`PROJECT_STATE.json` or the wider repository (full-repository filename search, zero matches). This
pass did not create, authorize, or reference `T89`.

## 12. Unresolved Decisions (Recorded, Not Silently Decided)

- **Resource-instance-level authorization mechanism** (§4 rule 45 / §24.14) — three named
  candidates, none chosen. `ADR/0022` names the architectural slot (a structural filter at the
  data-access layer, alongside `ADR/0021`'s tenant filter) without choosing among them.
- **Role/Permission catalog shape** (§24.1) — global-with-per-Organization-assignment versus
  fully per-Organization, not chosen. `ADR/0022`'s composition architecture is stated to hold under
  either answer.
- **Required ADR #2–#17 and #20** — fully open, unaffected by this ADR.
- The genuine architectural gap named in Bypass Analysis (direct service/use-case invocation outside
  the FastAPI dependency graph) is a requirement on future implementation, not a currently-enforced
  structural guarantee — flagged, not silently treated as closed.

## 13. QA Handoff

This branch (`docs/t88-adr-0022-authorization-architecture`) is handed off to the QA Reviewer role
for an independent, formal QA Decision (`Approved` / `Approved with comments` / `Rework required`),
against the actual remote PR HEAD once opened — per T88's own row ("the eventual ADR PR must
independently undergo QA, re-verified on its actual remote PR HEAD, before any merge") and
`PROJECT_WORKFLOW.md`/`docs/DefinitionOfDone.md`'s documentation-only-work QA requirement, the same
principle already established for T80/T81/T82/T86/T87.

## 14. QA Status

**Unresolved.** No QA Decision has been rendered as of this report. This Software Architect pass
does **not** record, anticipate, or imply `Approved`, `Approved with comments`, or `Rework required`
— that decision belongs solely to the QA Reviewer role, independently, against this commit and the
eventual PR HEAD. This report and `ADR/0022` are not self-certifying.

## 15. Explicitly Not Done By This Pass

Per T88's own authorization boundary, none of the following were performed, and none are implied by
this report or by `ADR/0022` itself:

- `ADR/0021` was not modified, reopened, or reinterpreted.
- `ADR/0001`–`0020` and `ADR/template.md` were not modified.
- Required ADR #1 or #19 was not reopened; Required ADR #2–#17 or #20 was not resolved.
- No `§4` business rule, `§23` frozen entity decision, or any other part of the governed
  specification was modified.
- No database schema, migration, backend, frontend, or API implementation was performed.
- No test implementing the decision was added or modified.
- No Stage 4 business feature was selected or authorized; `businessFeatures` remains `[]`.
- `currentStage` was not changed; remains `stage-3` / `in_progress`.
- `T89` or any subsequent task was not created or authorized.
- `PROJECT_STATE.json` was not modified — synchronization remains deferred until after the formal
  QA Decision exists, per the established T80/T81/T86/T87 pattern.
- `IMPLEMENTATION_QUEUE.md` was not modified by this pass — its existing T88 row is left as-is;
  marking it "Done" is a post-QA, post-merge synchronization step.
- No PR was opened or merged by this pass, and this report does not authorize a merge — merge
  remains gated on the QA Reviewer's independent decision against the actual PR HEAD.
- This Software Architect pass did not perform QA on its own work, and does not claim to.

---

**This report ends T88's authorized scope at the implementation PR handoff.** Per this task's own
governing instructions, T88 stops here, awaiting independent QA. No further action (opening/merging
a PR beyond the point specified below, creating T89, marking T88 Done) is taken by this pass.

---

## T88 QA Decision

**Decision: APPROVED**

**Reviewed PR:** #117 (`docs/t88-adr-0022-authorization-architecture`)
**Reviewed HEAD:** `0a0a85e21fce4cabe32ce0019a69c11eb07bcfd6`

**Blocking findings:** none.
**Non-blocking comments:** none.

**Provenance of this record:** this decision was reached and reported by the QA Reviewer role in
its own independent review session against PR #117's actual head. At the time PR #117 merged, no
persistent repository record of that decision existed: no GitHub-native PR review or comment was
posted to PR #117 (confirmed via `gh pr view 117 --json reviews,comments`: both empty), and this
report's own §14 ("QA Status: Unresolved") was never updated before the merge — a deviation from
the pre-merge QA-recording norm this repository otherwise follows (`T56` onward), of the same kind
already recorded as governance history for `T62` ("merged before its QA Decision was recorded in
the repository"). This section records the QA Reviewer's decision now, as part of T88's post-merge
governance closeout, following the precedent set by commits `bceff1c` ("docs(qa): record T81
approval"), `f6974cf` ("docs(qa): record T86 approval with comments"), and `7365ae8` ("docs(qa):
record T87 approval") — each of which recorded a QA Decision under the identical circumstance of an
already-reached decision with no persistent repository record. This section does not itself render
a new QA Decision; it transcribes the one the QA Reviewer role already rendered, and does not
substitute Project Manager judgment for that independent review.

**Verification performed while persisting this record**, not merely restated from the task's own
claim:

- **PR #117 state** — `gh pr view 117 --json state,mergeCommit,mergedAt` confirms `MERGED`, merge
  commit `4e612778c08adef26672bc4cd17915a450406994`, matching the reviewed PR exactly.
- **Diff scope** — `git diff --stat 388e723b09971a2a94849de8009d2376438f95a5 0a0a85e21fce4cabe32ce0019a69c11eb07bcfd6`:
  exactly two files, `ADR/0022-authorization-architecture.md` (new, +542) and this report (new,
  +343). No other file touched.
- **ADR/0022 immutability** — `git diff 0a0a85e21fce4cabe32ce0019a69c11eb07bcfd6 main --
  ADR/0022-authorization-architecture.md` is empty: the merged content on `main` is byte-identical
  to the reviewed PR HEAD.
- **No other ADR touched** — confirmed `ADR/0001`–`0021` and `ADR/template.md` are absent from PR
  #117's diff (`git diff --name-only ... -- ADR/` returns only `ADR/0022...`).
- **Required ADR scope** — `ADR/0022`'s own content references only `Required ADR #1`, `#2`, `#18`,
  and `#19`: #1/#19 are cited as already resolved by `ADR/0021` (not re-resolved here), #18 is the
  one this ADR resolves, and #2 appears only as a listed, untouched dependency. No other Required
  ADR number appears anywhere in the file.
- **`ADR/0021` untouched** — confirmed absent from PR #117's diff entirely; not modified, reopened,
  or reinterpreted.

**No rework required.** This QA Decision does not require any change to `ADR/0022`, and none was
made.
