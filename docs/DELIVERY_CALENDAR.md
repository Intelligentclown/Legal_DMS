# T156 Delivery Calendar Governance

The machine-readable schedule is [delivery_calendar.json](delivery_calendar.json). This is the schedule authority only. `IMPLEMENTATION_QUEUE.md` alone authorizes numbered work and records Done. Calendar entries never authorize tasks.

## Activation and arithmetic
Prospective enforcement starts at **T157**, inclusive. T1–T155 and bootstrap T156 are exempt; no fictional history is reconstructed. Schema version 2 fixes the project-local clock at **Asia/Kolkata**. All dates are ISO YYYY-MM-DD project-local dates. Durations are **inclusive**: finish minus start plus one day. Finish variance is actual protected completion minus original planned finish in calendar days: negative **Early**, zero **On Time**, positive **Late**. The original planned finish is immutable for variance; forecasts may change independently. A Done task records the implementation protected-merge date, never a developer's last commit or the later closeout date.

## Forecasting
Schema version 2 distinguishes finish_to_start scheduling predecessors from defect_evidence references. Only finish-to-start edges affect forecast topology or cycle detection; evidence references preserve diagnostic provenance without making a task a completed predecessor. Independent lanes may overlap. Slack is the amount of delay absorbed without moving the milestone; the active critical path has zero slack. An early finish only accelerates a milestone when all controlling predecessor/successor and fixed-date constraints permit it. Recompute after each protected task completion, record every affected milestone including unchanged movement, and append an immutable old/new/movement/direction/trigger/reason/recalculation entry with a unique trigger key. Never replace prior entries. The forecast calculator accepts an explicitly complete task network; it must not claim a validated overall date from an incomplete future backlog.

## Initial targets and scope
The owner-proposed targets (M1 2026-11-15, M2 2026-12-31, M3 2027-02-28) are retained as **provisional, low-confidence planning baselines**, not validated achievable dates. The currently visible queue authorizes no T157+ tasks, so no defensible fully estimated critical path or exact revised dates can be computed. It would be misleading to claim schedule feasibility or fabricate a day-count revision. M1 is a controlled existing/core office vertical slice; excludes government/finance completion. M2 is meaningful regular office use with integrated Matter, follow-up, Property and applicable government processes; excludes post-V1 enhancements. M3 is full frozen V1 and operational stabilization; excludes explicitly deferred work. The unresolved Required ADRs [12,15,16,17,20] gate corresponding workflow/government, vocabulary, identifiers, lifecycle/history, and historical convergence work.

Candidate planning lanes are Matter workspace, workflow/follow-ups/government, Property completeness, commercial/finance, and frontend/stabilization. These are hypotheses until owner-authorized tasks and dependencies establish an actual graph. A late task cannot bypass owner authorization, ADR gates, role separation, Independent QA, exact-head CI, review, protected-branch rules, tenant/RLS/security, migration safety, transaction integrity or STOP conditions.

## Required update protocol
Before authorizing T157+, add a structured task entry with all required planned/forecast/dependency/critical-path fields. The implementation PR remains Authorized with null completion fields. Once its protected merge is independently verified, a separate closeout records the auditable evidence tuple (implementation PR, merge SHA and parents, GitHub UTC merged_at, Asia/Kolkata conversion, QA publication head and actual-start evidence), actuals, variance and one history event per affected milestone. Queue, calendar and PROJECT_STATE completion tuple must synchronize atomically; validator failure blocks partial, stale or premature closeout. If the protected merge is recorded while closeout is pending, the validator reports it as an operational alert but never fabricates actuals. Calendar planning never changes the task ledger.

## Cancellation and successor provenance (T168)

For T157+ the queue Status cell is authoritative and permits exactly `Authorized`, `Done`, or terminal
`Cancelled`. A cancellation is represented only by the calendar task's `cancellation_evidence` object:
`cancelled_task_id`, `owner_approval_provenance`, ISO `cancellation_date`, non-empty `reason`, and
non-empty `evidence_reference` are mandatory. Its task ID must match the calendar record. This is
distinct from `completion_evidence`; a Cancelled task must contain neither completion evidence nor
actual start/completion/variance fields, so cancellation never invents calendar actuals or counts as
Done.

An optional `successor_task_id` is provenance, not authorization. An existing successor must carry
its own Authorized or Done queue state and uses `successor_state: "authorized"`. A not-yet-created
successor is valid only with `successor_state: "proposed_unapproved"`; it remains non-executable
planning context until separately owner-authorized in the queue. Self-supersession, duplicate/top-level
successor fields, unknown successors labelled authorized, and status/evidence contradictions fail
validation. A Cancelled task cannot be a finish-to-start predecessor: scheduling edges require a
completed predecessor. Defect-evidence references remain provenance only and do not make cancellation
or successor authorization implicit.

## M1 operational acceptance decision (2026-10-20)

Separately from the schedule model, the Project Owner conditionally accepted M1 **for operational dogfooding** on 2026-10-20 under non-task §3.2 authorization [Issue #328](https://github.com/Intelligentclown/Legal_DMS/issues/328); see [the decision record](acceptance/M1_Conditional_Operational_Acceptance.md). This is not production-release approval or a certified full backend-suite pass. The schedule JSON remains unchanged: M1's original provisional 2026-11-15 baseline/forecast and null milestone actual are retained, without inventing a milestone completion date or forecast movement. Historical entries retain their contemporary status. T166 Done is distinct from the conditional milestone decision; no T167 authorization or schema/policy change is implied.
