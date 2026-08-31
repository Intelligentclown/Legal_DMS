# T102 Software Architect Report

**Task:** T102 — Draft ADR-0031, resolving the User↔Organization membership/onboarding/tenant-context
gap a Software Architect architecture-gate assessment (2026-08-30) found blocking the Organization/
Tenant Core vertical slice. Full authorized-scope text: `IMPLEMENTATION_QUEUE.md`'s own T102 row
(authorization commit `d0b1728`, ledger-sync commit `8617cce`, PR #161, merge `508c2ea`).

**Role:** Software Architect, per `docs/prompts/SoftwareArchitect.md`. This report follows that
prompt's Required Output (§8) and `docs/ImplementationLog/README.md`'s Reviewer Checklist structure,
plus the Control Tower's own required 7-point self-review.

---

## 1. Verified Baseline and Authorization

- `git fetch origin` + `git rev-parse origin/main`: `508c2eaad79b2d70c202b5ef7139868235da741a` —
  confirmed as PR #161's actual merge commit via `gh pr view 161`, not taken on the governing prompt's
  word.
- Authorization commit `d0b1728547a153fac0d5d91c574251058fe76563` and ledger-sync commit
  `8617cce4b3fd5c2bc9fc99eb1f7f19b6b05f2120` both independently confirmed present and ancestors of
  this branch's HEAD (`git merge-base --is-ancestor`, both true).
- `governanceLedger` at this baseline: `latestTaskDone: "T101"`, `latestTaskAuthorized: "T102"`,
  `resolvedRequiredADRs`/`unresolvedRequiredADRs` unchanged from T101's closeout, `inProgressTransitions:
  []` — consistent with T102 resolving no Required-ADR planning-list number (confirmed: this gap is
  not one of the 20 enumerated items).
- Branch `docs/t102-adr-0031-org-user-membership-tenant-context` created directly from `origin/main`
  (`508c2ea`).
- **ADR numbering:** `ADR/0030` is `main`'s highest file; `ADR/0031` independently confirmed
  next-available via directory listing, not assumed from the authorization row's own "expected 0031"
  text.

## 2. Repository Evidence Inspected

Read directly, in full or in relevant sections, not sampled: `docs/Legal_DMS — Domain Model &
Functional Specification.md` §4 rules 43/46, §1.6 item 6, §24.1 (Organization/User/Role-Permission
entries, quoted verbatim); `ADR/0018` (D1–D6, Reasoning); `ADR/0019`; `ADR/0020` (full); `ADR/0021`
(full); `ADR/0022` (relevant sections — composed sequence, membership-not-added-to-CurrentUser
disclosure, catalogue-shape gap); `ADR/0029` (coverage-classification test, cited for §14);
`backend/src/app/infrastructure/persistence/models/identity.py` (full file); `backend/src/app/
application/interfaces/auth.py` (`CurrentUser`, `AuthenticationProvider`); `backend/src/app/
application/interfaces/user_repository.py` (`UserRepository` interface); `backend/src/app/
infrastructure/auth/jwt_authentication_provider.py` (full file — the live-role-rederivation mechanism
this ADR's tenant-context decision directly extends); `backend/src/app/infrastructure/cli/bootstrap.py`
(full file, T67's first-admin bootstrap); `docs/BusinessRequirementsPlan.md` (cited for the
single-practice/no-self-registration context grounding the cardinality decision). Full-repository grep
confirming zero `Organization`/`organization_id`/`organizations` references anywhere in
`backend/src/app` outside tests.

## 3. Decisions Made (all four newly `DECIDED BY ADR-0031`, per the evidence table in ADR-0031 §1)

1. **Cardinality:** one-to-one (optional) — a User belongs to at most one Organization. No repository
   evidence supports many-to-many; chosen as the smallest structure consistent with all evidence,
   eliminating tenant-context selection by construction rather than solving an unevidenced harder
   problem.
2. **First-Organization creation:** folded into the existing `bootstrap-admin` CLI (T67/`ADR-0018` D4)
   inside the same idempotency check and transaction — not a new self-service flow, consistent with
   `ADR-0018` D5's "no self-registration" decision.
3. **First-Administrator semantics:** membership carrying the existing `Administrator` Role — no new
   "ownership" concept invented on top of an already-sufficient RBAC signal.
4. **Membership↔RBAC composition:** a direct, nullable `organization_id` FK on `users` (not a join
   table, since cardinality is 1:1); structurally distinct from and orthogonal to `UserRole`; Roles/
   Permissions remain global, unchanged — the catalogue-shape question (#1/#18) is not narrowed or
   resolved.
5. **Active tenant-context resolution:** a direct, deliberate consequence of decision 1 — no selection
   needed; resolved via a live database lookup in `JwtAuthenticationProvider.get_current_user()`,
   mirroring its own existing roles-rederivation call exactly, never via a JWT claim.
6. **`CurrentUser` consequence:** exactly one new field, `organization_id: str | None = None`.
7. **Existing-data consequence:** disclosed (additive column, backfill/reconciliation needed for
   pre-Organization `User` rows) — not designed; explicitly assigned to Required ADR #20.

## 4. Alternatives Evaluated

Four alternative sets (cardinality, first-Organization creation, membership representation,
tenant-context mechanism), each scored against concrete repository evidence — see `ADR/0031`'s own
§7 for the full tables. In each case the rejected alternative was rejected either for contradicting
already-accepted evidence (`ADR/0018` D5 for a self-service onboarding flow; the live-rederivation
precedent for a JWT-claim-based tenant context) or for introducing structure (a join table, a
multi-Organization selection UI) that no evidence supports and that this task's own scope explicitly
excludes inventing.

## 5. Composition Check

- **`ADR/0021`**: not modified. This ADR supplies exactly the missing input `ADR/0021` itself named as
  its own unresolved dependency (`organization_id` resolution) — the enforcement mechanism itself
  (application-layer + RLS, fail-closed) is unchanged and directly reused in §9/§15.
- **`ADR/0022`**: not modified. The composed Authentication→Tenant-Scope→Permission sequence is
  reused verbatim; the "Organization membership is not itself proof of authorization" principle is
  restated, not altered; the global-vs-per-Organization RBAC catalogue question is explicitly left as
  open as `ADR/0022` left it.
- **`ADR/0020`**: not modified. Cited directly for the transaction-atomicity requirement the bootstrap
  extension (§6.2/§15) depends on.
- **`ADR/0029`**: not modified. Cited only to confirm Organization/membership creation falls within
  its already-decided Audit/Activity coverage — no new coverage rule invented.
- **`ADR/0018`/`ADR/0019`**: not modified. The authentication mechanism itself (token issuance,
  refresh, hashing, Electron storage) is untouched; only `CurrentUser`'s data shape and
  `JwtAuthenticationProvider`'s existing lookup are extended, at exactly the point that mechanism
  already performs an equivalent lookup for roles.
- **Required ADR #10/#11/#12/#15/#16/#17/#20**: none resolved, narrowed, or silently consumed —
  confirmed absent from `ADR/0031`'s Decision/Invariants sections; #20 explicitly named as the owner
  of the migration question this ADR only discloses.

## 6. Control Tower's 7-Point Self-Review

1. **Every approved scope item addressed:** yes — all seven items (§6.1–§6.7 in `ADR/0031`) map
   one-to-one onto `T102`'s authorized scope list.
2. **Every exclusion respected:** yes — no schema/migration/application/frontend code was written (this
   report and the ADR are the only artifacts); no Required ADR #10/#11/#12/#15/#16/#17/#20 resolved;
   no Party/Property/Matter/File/Document/Workflow/Government-Process/Finance semantics introduced; no
   unrelated Organization field invented (only name/legal-name, already `DERIVED` pre-existing spec
   text, is referenced, not newly added).
3. **`ADR-0021`/`ADR-0022` reused, not reopened:** confirmed via §5 above and via `git diff` — neither
   file appears in this branch's diff against `origin/main`.
4. **No unresolved Required ADR silently consumed:** confirmed — `ADR/0031`'s own "Resolves" header
   names only the newly-identified, non-planning-list gap; its "Does not resolve" header lists #10,
   #11, #12, #15, #16, #17, #20 explicitly.
5. **No implementation performed:** confirmed — `ADR/0031` and this report are the only files in the
   diff (§9 below); the ADR's own §15 states this explicitly in its own text.
6. **No business rule invented without being explicitly recorded as a T102 decision:** every point in
   §6 of `ADR/0031` is labeled `DECIDED BY ADR-0031` in its own heading, not silently presented as
   `GOVERNED` or `DERIVED` — the evidence table in `ADR/0031` §1 keeps the GOVERNED/DERIVED distinction
   separate from the four newly-decided items throughout.
7. **Design sufficient for a subsequent implementation slice:** `ADR/0031` §15 states binding
   implementation constraints (transaction boundary, RLS/`organization_id` discipline, no-JWT-claim
   rule) and §16 states concrete, testable acceptance criteria — sufficient for a future, separately
   authorized implementation task to build against without re-deciding any of the seven items.

## 7. Explicitly Unresolved Questions (named in the ADR, not silently dropped)

Required ADR #10, #11, #12, #15, #16, #17, #20 (the last explicitly disclosed-but-not-designed, per
§6.7/§12); the global-vs-per-Organization Role/Permission catalogue shape (#1/#18's own remaining open
item, not narrowed); Organization's full field list beyond name/legal-name; Organization lifecycle
states; sub-organization support — all named in `ADR/0021`'s own prior disclosure, none reopened or
newly resolved here.

## 8. Scope/Boundary Reasoning

The authorized scope names exactly seven decisions plus a wide, explicit exclusion list matching
`T102`'s own row. `ADR/0031` decides exactly those seven and no more — see §6 (Control Tower's 7-point
self-review) above for the itemized confirmation. The one genuine judgment call beyond the seven items
— choosing a direct FK over a join table for membership representation (§7.3 of the ADR) — is a direct,
disclosed *consequence* of decision 1 (cardinality), not an eighth independent decision; it is not
treated as new scope.

## 9. Exact Files Changed

```
$ git status
On branch docs/t102-adr-0031-org-user-membership-tenant-context
Untracked files:
  ADR/0031-user-organization-membership-onboarding-tenant-context.md
  docs/reviews/T102_Software_Architect_Report.md

$ git diff --stat origin/main
(empty prior to commit -- both files are new, untracked)
```

Exactly two new files, both documentation. No existing file — `ADR/0001`–`0030`, `ADR/template.md`,
the governed specification, `docs/BusinessRequirementsPlan.md`, `IMPLEMENTATION_QUEUE.md`,
`PROJECT_STATE.json`, or any `backend/`/`frontend/`/`electron/` file — appears anywhere in this
branch's diff against `origin/main`.

## 10. Confirmation No Implementation Occurred

No database table, migration, backend model, service, repository, route, frontend, or test was created
or modified. No schema or configuration file was touched. `ADR/0031` describes the target design and
its acceptance criteria; it implements none of it — stated explicitly in the ADR's own §15
"Implementation Constraints and Explicit Non-Goals."

## 11. Confirmation Governance Boundaries Were Respected

`IMPLEMENTATION_QUEUE.md` and `PROJECT_STATE.json` were not modified by this pass — governance-ledger
synchronization is deferred to the post-QA Governance Closeout step, per this series' established
convention; since `T102` resolves no Required-ADR planning-list number, no `governanceLedger.
inProgressTransitions` declaration applies (per `T102`'s own authorization row, explicitly). No `T103`
was created or authorized. `T102` is not marked Done by this report or any file it changes. `ADR/0007`,
`ADR/0009`, `ADR/0018`–`ADR/0030` are not reopened, modified, or reinterpreted — confirmed absent from
this branch's diff. No QA Decision is rendered, implied, or anticipated by this report — see the QA
Decision placeholder below.

## Validation

1. **Branch ancestry**: `git merge-base --is-ancestor d0b1728547a153fac0d5d91c574251058fe76563 HEAD`
   and the same for `8617cce4b3fd5c2bc9fc99eb1f7f19b6b05f2120` → both `true`.
2. **ADR numbering**: `ADR/0031` independently confirmed next-available (§1 above).
3. **ADR/reference accuracy**: every `ADR/000N` cross-reference in `ADR/0031` checked against the
   actual filename it cites (`0018`, `0019`, `0020`, `0021`, `0022`, `0029`) — all exist, all
   filenames match exactly.
4. **No excluded implementation work**: confirmed via `git diff --stat origin/main` (§9 above) — two
   documentation files only.
5. **Governance validator**:

```
$ python scripts/governance_validate.py
governance_validate: OK (0 warning(s), 0 errors)
```

6. **Governance tests**: this branch does not modify `scripts/governance_validate.py` or its suite —
   re-ran the exact command `governance.yml` invokes as confirmation, not new coverage:

```
$ python scripts/tests/test_governance_validate.py -v
Ran 51 tests ... OK
```

7. **HEAD SHA**: recorded in the Reporting section below.
8. **Validation failures**: none found or concealed.

## Reviewer Checklist

Per `docs/prompts/SoftwareArchitect.md` §8's required output and
`docs/ImplementationLog/README.md`'s standard eleven-item self-assessment:

```
Reviewer Checklist

☑ Architecture preserved -- ADR/0018, ADR/0019, ADR/0020, ADR/0021, ADR/0022, ADR/0029 composed
  with, not modified or contradicted; specification rules 43/46 cited, not reinterpreted.
☑ Existing design patterns followed -- the tenant-context mechanism reuses JwtAuthenticationProvider's
  existing live-role-rederivation call unmodified in shape; the FK representation reuses this
  repository's existing direct-FK convention (matter_number, matter_id-style).
☐ Tests added -- none; documentation-only architecture task, no implementation authorized. Sec16
  states acceptance criteria for a future implementation task, not tests this ADR itself adds.
☐ Existing tests pass -- not applicable to this pass' own scope; the governance test suite
  (unmodified by this branch) was re-run as confirmation only, per Validation Sec6 above.
☑ Documentation updated -- ADR/0031 and this report are the documentation this task produces.
☑ ADR updated (if required) -- ADR/0031 created; ADR/0018-0030 not touched, correctly.
☐ AI_BOOTSTRAP updated (if required) -- not required by this task's authorized scope.
☐ PROJECT_STATE updated (if required) -- deferred to post-QA Governance Closeout; T102 resolves no
  Required-ADR planning-list number, so no inProgressTransitions declaration applies (per T102's own
  authorization row).
☑ No unrelated refactoring -- not applicable; no code touched at all.
☑ No scope creep -- Required ADR #10/#11/#12/#15/#16/#17/#20 explicitly disclosed as untouched;
  Party/Property/Matter/File/Document/Workflow/Government-Process/Finance semantics not introduced;
  no unrelated Organization field invented; T102's authorization row's own exclusion list confirmed
  fully respected in Sec6 above.
☑ Ready for QA -- ADR/0031 and this report are complete and handed off below.
```

## QA Handoff

This branch (`docs/t102-adr-0031-org-user-membership-tenant-context`) is handed off to the QA Reviewer
role for an independent, formal QA Decision against the actual remote PR HEAD once opened, per this
task's own governance boundary and this repository's established documentation-only-work QA
requirement (`T80`–`T102` precedent). The QA Reviewer is specifically asked to independently verify:
that the cardinality decision (§6.1) is genuinely unsupported-by-evidence-either-way rather than
contradicted by some overlooked source (i.e., that "one-to-one" is a legitimate new decision, not a
misreading of an already-frozen rule); that the tenant-context mechanism (§6.5) is accurately described
against `jwt_authentication_provider.py`'s actual current code; that every one of the seven approved
scope items is genuinely addressed and no eighth, unauthorized decision was smuggled in; and that
`ADR/0021`/`ADR/0022`/`ADR/0020`/`ADR/0029`/`ADR/0018`/`ADR/0019` are confirmed absent from this
branch's diff against `origin/main`.

## QA Decision

☐ Approved
☐ Approved with comments
☐ Rework required

This Software Architect pass does not record, anticipate, or imply any of the three outcomes above —
per `docs/prompts/SoftwareArchitect.md` §11/§13, this role never renders a QA Decision or substitutes
for the QA Reviewer. `ADR/0031` and this report are not self-certifying.

---

**This report ends T102's authorized scope at the architecture-drafting handoff.** Per this task's own
governing instructions, T102 stops here, awaiting independent QA. No further action (opening/merging a
PR, performing QA, creating T103, marking T102 Done, governance closeout, or beginning Organization/
Tenant Core implementation) is taken by this pass.
