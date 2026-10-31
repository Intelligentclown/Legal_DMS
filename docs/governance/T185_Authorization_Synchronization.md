# T185 Authorization Synchronization — 2026-10-31

**Task:** T185 — Required ADR #12: Workflow vs Government Status  
**Project Owner authorization:** [Issue #405](https://github.com/Intelligentclown/Legal_DMS/issues/405)  
**Lifecycle:** `PROJECT_WORKFLOW.md §3.1`, PR 1 of 3  
**Expected protected baseline:** `b2ea94e817c5afd9088ba47dd3b5d5650f60383a`  
**Candidate branch:** `docs/t185-authorization-adr12`

## 1. Authorization and governance registration

The Project Owner approved T185 on 2026-10-31 for authorization publication only. The approved future PR 2 is an architecture-only resolution of specification Required ADR #12. It must preserve the distinction between internal firm Workflow status and external Government Process status.

Candidate governance frontier:
- `latestTaskDone=T184`
- `latestTaskAuthorized=T185`
- `inProgressTransitions=[]`
- Required ADRs [12, 15, 16, 17, 20] remain unresolved.

T185 is registered as `Authorized`, not `Done`, in `IMPLEMENTATION_QUEUE.md`; the structured state frontier is synchronized in `PROJECT_STATE.json`. Schema V3 `docs/delivery_calendar.json` registers T185 under M2 `workflow`, with T181 as the completed finish-to-start predecessor, provisional 2026-11-02 through 2026-11-05 inclusive, no actuals or completion evidence, and no milestone forecast movement. `docs/DELIVERY_CALENDAR.md` carries the corresponding narrative entry.

## 2. Approved future PR 2 scope

Only after PR 1 protected merge and separate Software Architect commissioning:
1. Inspect the existing workflow state-machine engine, `workflow_definitions`, `workflow_states`, `workflow_history`, and their current wiring or absence.
2. Inspect frozen specification §4 rules 32–34 and §24.10–§24.11.
3. Evaluate genuine alternatives for distinct internal Workflow and external Government Process status.
4. Decide only the technical boundary/mechanism separating internal workflow state/history from external government status and append-only Government Events.
5. Define ownership/attachment only as necessary for Required ADR #12; leave vocabulary, identifiers, history/soft-deletion and migration decisions to Required ADRs #15/#16/#17/#20.
6. Compose with accepted ADRs without modifying them or promoting Proposed ADRs.
7. Draft one formal ADR (expected ADR-0048, verify against protected main) using `ADR/template.md`, with Architect Reviewer Checklist and QA Decision boxes unchecked.

## 3. Acceptance criteria

- AC-01 preserve the frozen distinction between internal Workflow and external Government Process status.
- AC-02 evidence-backed repository analysis of the workflow engine, persistence models and wiring.
- AC-03 at least two genuine alternatives and trade-offs.
- AC-04 separate internal workflow state/history from external government status/events.
- AC-05 resolve Required ADR #12 only; #15/#16/#17/#20 remain unresolved.
- AC-06 compose with accepted ADRs; no modification or promotion of other ADRs.
- AC-07 explicitly defer unresolved vocabulary, identifiers, history and migration details.
- AC-08 no product, schema, API/UI, migration or runtime implementation.
- AC-09 Comprehensive / Risk Tier 1 Independent QA published and re-read from exact remote PR head.
- AC-10 authorization commit is a genuine PR 2 ancestor; PR 3 remains a separate closeout.

## 4. Exclusions and invariants

No workflow/Government Process feature implementation, application code, database models/schema, Alembic migration, API/UI routes, RLS/RBAC changes, seed data or runtime changes. No accepted ADR changes. ADR-0043, ADR-0044 and ADR-0047 remain Proposed. Preserve Alembic frontier `b155caa6d4e1`, M1 internal-office-dogfooding-only acceptance, and milestone baselines/forecasts (M1 2026-11-15 actual 2026-10-25; M2 2026-12-31 actual null; M3/finalization 2027-02-28 actual null). Resources, effort and capacity remain Unknown; calendar dates are provisional only. No M2 acceptance, production-release claim or successor authorization.

## 5. Owner-approved sequencing exception

The Documentation Manager prompt ordinarily requires an existing Approved/Approved-with-comments QA Decision before synchronization. The Project Owner explicitly approved following the T184 authorization-PR precedent, in which Documentation Manager synchronization precedes PR 1 Independent QA. This is a task-specific sequencing exception for T185 PR 1 only. It does not waive Independent QA, exact-head CI, collaborator review, protected merge, or subsequent role boundaries.

The independent QA Decision is **not yet recorded** and must be published independently against the exact PR head before merge. This record does not claim QA approval.

## 6. STOP boundary

T185 is Authorized/not Done. No ADR drafting or implementation begins until PR 1 is independently QA-approved, exact-head CI passes, collaborator review is complete, and PR 1 is protected-merged. PR 2 requires a separate role commissioning. PR 3 remains a separate governance closeout after PR 2 protected merge.
