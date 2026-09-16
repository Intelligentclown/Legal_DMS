# T125 Software Architect Report

**Task:** T125 — Fresh-Install Operational-State Continuation Architecture

**Role:** Software Architect

**Artifact:** `ADR/0037-operational-fresh-installation-provenance.md`

**Lifecycle:** PR 2 of 3, architecture plus later independent QA. This report contains the
architect's self-assessment only; it performs no independent QA, merge, closeout, implementation,
database operation, or future-task authorization.

## Verified baseline and authorization

- A fresh origin fetch verified remote `main` at
  `b8796b1e72da203dedb0dc39bb69e572e852a8e0`.
- That commit is the PR #218 merge and has exact parents
  `121f9d8d358460b1f558dc757e8b09bdd90fbf05` and
  `6ca60e55001e2ec4a6386724fe39448335098e4c`; the latter is the T125
  authorization head.
- `IMPLEMENTATION_QUEUE.md` directly records T125 as project-owner Authorized under
  `PROJECT_WORKFLOW.md` section 3.1 and does not mark it Done.
- Starting governance: `latestTaskDone = T124`, `latestTaskAuthorized = T125`,
  `inProgressTransitions = []`; ADR-0036 is Proposed; Required ADR #20 is unresolved; T126+ is
  unauthorized.
- Alembic has exactly one head, `1b8f4a9c2e6d`.
- Fresh remote inspection found no `docs/t125-operational-fresh-continuation` branch. ADR-0036 was
  the highest numbered ADR, so ADR-0037 was available and not overwritten.

The requested Windows checkout was not mounted in this executor. The accessible old checkout was
left untouched, including its unrelated `docs/ArchitectureScorecard.md` modification. Recovery was
performed in a new clean clone at
`/workspace/scratch/893c09a5b14b/Legal_DMS_T125_recovery`, based directly on verified
`origin/main`. No unrelated Codex/Muse worktree was reused.

## Architectural question

How can a mechanically proven genuinely fresh installation enter durable operation and accumulate
legitimate Party, Address, Matter, Property, File, and later new-domain records without allowing a
legacy, migrated, reset, emptied, copied, or operator-asserted database to manufacture a fresh
lineage?

## Repository evidence read

The architecture was re-authored after reading the canonical bootstrap, routing, workflow, Software
Architect prompt, ADR template, T125 queue/state records, ADR-0021/0022/0023/0033/0034/0035/0036,
Required ADR #20 context, T121 architecture/QA evidence, T122-T124 implementation/QA evidence, the
live `InstallationClassifier`, `SqlAlchemyInstallationClassifier`, `PartyWriteGate`, Party service
and routes, Address/Party persistence models, and the current Alembic inventory. The earlier
non-durable report was treated only as a hypothesis.

## Alternatives reconsidered

1. expanding zero-row exclusions;
2. mutable installation-state flag;
3. schema revision plus row counts;
4. immutable singleton provenance only;
5. append-only ledger without birth identity;
6. installer-created immutable birth identity plus append-only transition evidence;
7. cryptographically signed evidence; and
8. external registry.

The selected minimum is option 6. A singleton alone does not record the protected transition; a
ledger created only from current emptiness cannot distinguish deletion from birth; cryptography and
an external registry add useful defenses but are not the provenance root required here.

## Decision and durable provenance

The dedicated new-install path creates one immutable installation identity before any Legal_DMS
business surface exists. A later serialized bootstrap mechanically proves ADR-0036's full empty and
security prerequisites and appends exactly one immutable operational-fresh transition. Database
privileges and constraints—not application convention—make evidence append-only and inaccessible to
normal runtime mutation.

## State model and transition matrix

The minimum model is:

- `UNPROVEN` — no valid operational lineage; writes denied;
- transient `VERIFIED_FRESH_EMPTY` — birth plus full predicate verified inside bootstrap; bootstrap
  only;
- `OPERATIONAL_FRESH` — valid birth and operational transition; fresh-path writes eligible;
- `LEGACY_WITH_BUSINESS_DATA` — legacy evidence without operational lineage; denied;
- `MIGRATED` — complete T118 evidence; denied pending ADR #20;
- invalid/ambiguous behavior — corruption, contradiction, unsupported version, or observation
  failure; denied.

Allowed transitions are no-installation -> birth-established unproven -> transient verified-empty
-> operational-fresh, plus idempotent observation of an existing operational transition.
Classification may identify legacy or migrated. `LEGACY -> OPERATIONAL_FRESH` and
`MIGRATED -> OPERATIONAL_FRESH` are prohibited. Destruction/recreation is a new installation, not a
transition. ADR-0036's reset-to-fresh allowance is superseded.

The ADR contains the explicit transition matrix and evidence conditions.

## Bootstrap and trust contract

A dedicated deployment/install command, using a narrowly privileged bootstrap role, acquires an
installation lock and runs one serializable transaction. It validates birth evidence, contract and
schema revision, absence of migration contradictions, the complete zero-row bootstrap predicate,
and ADR-0036 security prerequisites before appending one operational event and committing.

Concurrent attempts serialize; duplicate attempts are idempotent; concurrent business appearance
fails/retries rather than using a stale proof; pre-commit interruption leaves no state; uncertain
post-commit results are safely retryable. `legal_dms_app` cannot invoke bootstrap or mutate evidence.
Migration/admin execution remains separate and audited.

## Classifier precedence

1. corruption, contradiction, unsupported evidence, or incompatible revision => invalid/ambiguous;
2. fresh evidence contradicting migration evidence => invalid/ambiguous;
3. valid complete T118 evidence => migrated;
4. valid operational-fresh provenance => operational fresh;
5. valid birth plus full zero-row proof => transient bootstrap eligibility;
6. legacy/business evidence => legacy;
7. otherwise => unproven.

Zero-row inspection becomes bootstrap-only rather than continuing runtime provenance.

## PartyWriteGate and composition

Only `OPERATIONAL_FRESH` is eligible for normal Party create/update/delete. Verified-empty,
unproven, legacy, migrated, invalid, ambiguous, and errors deny. The gate remains independent from
authentication, Organization scope, permissions, same-Organization integrity, RLS, and runtime role.

Legitimate Address rows therefore do not revoke Party maintenance after bootstrap. T122 Address
ownership, same-Organization constraints, forced RLS, and non-owning runtime execution remain
mandatory. Future Matter/Property/File rows likewise require no classifier exclusion, but their own
domain/security architecture remains separate. MatterParty semantics are untouched.

## Attack/failure conclusions

- Legacy with Clients, deleted Clients, or every row deleted: denied because birth is missing.
- Partial or complete migration: denied; complete T118 evidence remains `MIGRATED`.
- Backup without provenance: unproven/denied; valid same-lineage restore must pass compatibility and
  contradiction checks.
- Legacy clone: denied. Operational-fresh clone duplicates the same identity and is not a distinct
  installation; separate active use requires later governed activation/registry architecture.
- Fabricated runtime evidence: denied by privileges and constraints. Privileged owner tampering is a
  security incident inside the explicit administrative trust boundary.
- Concurrent/interrupted bootstrap: serialized and atomic.
- Missing, malformed, contradictory, or incompatible evidence: fail closed.
- Existing T124-era development/test databases: no grandfathering; recreate or require separately
  authorized reconstruction architecture.

## Required ADR #20 boundary

Existing/upgraded databases cannot receive fresh birth through normal upgrade/bootstrap, and T118
migration evidence outranks any claimed fresh eligibility. T125 therefore cannot enable migrated
Party writes, perform Client-master cutover, retire `matters.client_id`/`clients`, remove bridges,
declare migration complete, or clean legacy state. Required ADR #20 remains unresolved.

## Schema and deployment implications

Future schema requires installation-wide immutable identity plus an append-only transition record,
unique sequence/transition constraints, database timestamps, contract/predicate versions, schema
revision binding, and optional digest chaining. Exact physical names remain implementation choices.

New installs use the guarded installer/bootstrap. Existing upgrades may receive structures but no
birth/operational evidence. T124-era databases are not inferred fresh. Shared-development-DB process
debt is not provenance and was not inspected or changed.

## Relationship to ADR-0036

ADR-0037 preserves ADR-0036 history and qualifies it:

- Decision 1's full zero-row condition becomes bootstrap proof;
- Decision 2 is limited to that protected transition;
- Decision 3 no longer sends legitimate operational rows to legacy classification;
- Decision 7 uses durable operational provenance for continuing eligibility; and
- full reset no longer establishes freshness.

ADR-0036 remains Proposed. Its tenant, permission, RLS, Address, Party, migration, and ADR #20
boundaries remain intact.

## Future implementation decomposition — not authorized

1. provenance schema/privileges, installer birth, guarded bootstrap, and integrity/concurrency tests;
2. classifier and PartyWriteGate integration without migrated-write enablement;
3. separately authorized Address application composition under T122; and
4. later Matter/MatterParty/domain composition with separate decisions and ADR #20 boundaries.

Clone activation/registry, privileged reconstruction/recovery, and cryptographic attestation are
separate future architecture. No task number, priority, or authorization is assigned.

## Files changed

- `ADR/0037-operational-fresh-installation-provenance.md`
- `docs/reviews/T125_Software_Architect_Report.md`

No production source, migration, schema, database, test, queue, state-ledger, QA, or closeout file is
changed.

## Reviewer Checklist

- [x] Architecture preserved
- [x] Existing design patterns followed
- [ ] Tests added
- [x] Existing tests pass
- [x] Documentation updated
- [x] ADR updated (if required)
- [ ] AI_BOOTSTRAP updated (if required)
- [ ] PROJECT_STATE updated (if required)
- [x] No unrelated refactoring
- [x] No scope creep
- [x] Ready for QA

Unchecked notes: T125 is architecture-only, so no production tests were added. `AI_BOOTSTRAP.md`
does not change because no standing process rule changed. `PROJECT_STATE.json` remains untouched
because QA/closeout synchronization has not occurred. “Existing tests pass” refers only to the
repository-required governance suite recorded below, not the production suite.

## Validation

- `python scripts/governance_validate.py` — OK, 0 warnings and 0 errors.
- `python -m unittest discover -s scripts/tests -p 'test_governance_validate.py' -v` — 51 tests
  passed.
- `git diff --check` — clean.
- The governance validator supplied the repository's ADR validation: ADR number/header integrity,
  references, Required-ADR resolution uniqueness, task authorization/Done/QA invariants, and
  governance-ledger consistency passed.
- No production suite was required or run because this architecture-only diff changes no executable
  application, migration, schema, or test surface.
- Exact-head remote CI is reported only after publication; it is not claimed locally.

## QA Decision

- [ ] Approved
- [ ] Approved with comments
- [ ] Rework required

All boxes intentionally remain unchecked for independent Antigravity QA.
