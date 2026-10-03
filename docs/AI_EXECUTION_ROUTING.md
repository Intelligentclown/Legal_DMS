# AI Execution Routing

This document defines how this repository maps **roles** to **executors** when AI tools are used.
It is governance/process documentation only. It does not authorize implementation, merge a PR, or
change any accepted ADR, application behavior, schema, CI rule, or branch-protection setting.

## 1. Role vs. Executor

- A **role** is a repository-defined responsibility such as Project Manager, Backend Developer,
  Frontend Developer, QA Reviewer, Software Architect, or Documentation Manager.
- An **executor** is the product/session actually performing that role in a given run.
- Role and executor are **not the same concept**. The repository governs roles; executors may vary
  over time without redefining the repository's role model.

Examples:

- "Project Manager" is a role.
- "ChatGPT" or "Codex" may be the executor acting in that role for a specific task.
- A later tool change does not, by itself, create a new repository role.

## 2. Default Routing

Default routing is a starting point, not an automatic authorization:

- **ChatGPT** is the default Control Tower / Project Manager executor.
- **Codex** is the default bounded executor for backend, database, migration, security, debugging,
  and Git/PR verification work.
- **Antigravity** is the default executor for frontend, browser, and more autonomous end-to-end
  work.
- Any repository role may be executed by a different tool/session when explicitly chosen, but the
  role's repository-defined boundaries remain unchanged.

These defaults guide task assignment. They do not weaken owner authorization, QA, CI, or merge
gates.

## 3. QA Independence

- Independent QA remains mandatory wherever the repository already requires it.
- **Different-executor QA is the default expectation.** When practical, the executor performing QA
  should be different from the executor that performed implementation.
- For T107's intended operating model, Antigravity is the default QA executor when Codex performed
  the implementation, but this is a routing default, not a new standing repository role.
- Different-executor QA does not replace the existing requirement that the QA Reviewer verify the
  actual repository state, publish the QA decision to the PR branch, and re-read it from the remote
  PR head before reporting approval.

If a different executor is unavailable, the repository's existing role boundaries and publication
requirements still control; this document does not create an automatic waiver.

## 3. Assignment Role Boundary

A commissioned AI assignment executes **exactly one repository role**. Completion of that role
ends the assignment. Approval, a passing check, or a handoff-ready result does not implicitly
commission the same assignment to become QA Reviewer, Documentation Manager, Git / CI / PR
Manager, Project Manager / Control Tower, Software Architect, or another role. The next role needs
a separate explicit commissioning.

This is a governance boundary around the commissioned assignment and its authority, not a technical
claim about chat or product-session internals. A human may start a separately commissioned
assignment in the same interface where repository policy permits it. Role definitions and lifecycle
gates remain useful and unchanged; this rule prevents their routine automatic chaining.

## 4. Minimal Control Tower Handoff

A normal Control Tower commissioning message should normally contain only:

- assigned role;
- task ID;
- expected protected-`main` baseline;
- an exceptional task-specific constraint not already durable in repository authority;
- instruction to bootstrap from protected repository truth; and
- the explicit STOP boundary.

Repository facts already encoded durably should normally be rediscovered from protected repository
state, not copied into every handoff. A larger prompt remains appropriate for genuinely exceptional
or high-risk work; brevity never overrides safety or scope clarity.

## 5. Bootstrap Modes

`AI_BOOTSTRAP.md` defines two bootstrap modes:

- **Control Tower Bootstrap** for broad-context planning, status reconstruction, task selection,
  and merge-gate work.
- **Authorized Task Bootstrap** for a fresh executor receiving one already-authorized task with
  bounded scope.

The mode changes how much context is loaded up front. It does **not** change the repository's
authorization, QA, or merge rules.

## 6. Context-Loading Principles

- **Repository first, always.** Prior chat may provide a lead, but repository evidence decides.
- **Load the minimum context that is sufficient for the current role and task.**
- **Expand on demand.** Read broader history only when the current task, evidence, or a discovered
  discrepancy requires it.
- **Task-scoped execution is valid.** A fresh executor working on an already-authorized task does
  not need to reconstruct the entire project if the repository already contains the task's
  authorization, dependencies, and governing context.
- **Escalate outward, not inward.** If task-scoped context is insufficient, expand to the next most
  relevant repository artifact rather than reading everything by default.
- **Never substitute scoped reading for verification.** A narrow bootstrap is allowed only so long
  as the executor can still prove the task's authorization, dependencies, and relevant governance
  constraints from repository artifacts.

### Reverify the invariant; do not repeatedly reconstruct its entire history

Reverify each critical invariant directly from repository or platform truth; do not treat a prior
role's report as authority and do not reload unrelated history merely because it exists. As
applicable, independently verify protected `main`, durable authorization, required ancestry, the
exact candidate/head, QA publication and ancestry, candidate mutation after QA, mandatory CI,
review/protection state, and the protected merge result. This principle narrows unnecessary context,
not independent verification or lifecycle gates.

## 7. Recommended Context Order

### Control Tower Bootstrap

Use when selecting work, validating repository state broadly, or performing pre-merge governance
verification.

1. `AI_BOOTSTRAP.md`
2. `docs/AI_EXECUTION_ROUTING.md`
3. `PROJECT_WORKFLOW.md`
4. `PROJECT_STATE.json`
5. `IMPLEMENTATION_QUEUE.md`
6. Any active `docs/ImplementationLog/` or `docs/reviews/` record relevant to the task under
   consideration
7. Additional ADRs, handoff docs, or code only as required by the current decision

### Authorized Task Bootstrap

Use when the Project Manager/Control Tower has already selected an authorized task and passed that
task ID/scope to an executor.

1. `AI_BOOTSTRAP.md`
2. `docs/AI_EXECUTION_ROUTING.md`
3. `PROJECT_WORKFLOW.md`
4. The authorized task's own `IMPLEMENTATION_QUEUE.md` row
5. The specific prompt for the assigned repository role
6. Direct dependencies named by that task's row, prompt, ADRs, or currently touched files
7. Broader project history only if a discrepancy, missing dependency, or scope question makes it
   necessary

### Downstream context profiles

These are minimum initial contexts beneath the bootstrap modes above, not competing workflows or
exhaustive checklists. Expand on demand when evidence, scope, or a discrepancy requires it.

| Role | Minimum initial context |
|---|---|
| **Independent QA** | Authorized task/scope; exact frozen candidate identity; relevant diff; directly relevant ADRs/invariants; relevant tests; known baseline failures/evidence where applicable. QA independently verifies all policy-critical facts. |
| **Documentation synchronization** | Task authority; published QA decision; exact candidate identity where relevant; and the governance/documentation surfaces that require synchronization. |
| **Git / CI final verification** | PR identity; expected protected baseline; exact final head; required authorization and QA ancestry; mandatory checks; review/protection state; and merge result. |

### Risk-scaled QA depth

QA selects depth from the authorized change's risk, without changing whether independent QA is
required. Governance/documentation-only work normally emphasizes scope, authority, cross-reference,
and parser/validator checks; ordinary CRUD/application work adds behavior and regression coverage;
frontend/UI work adds rendered and interaction coverage; architecture/ADR work deeply validates
authority, alternatives, and downstream invariants. Migration/schema, RLS/security/tenant, and
transaction/concurrency/storage/integrity work require deep verification of the relevant persistence,
isolation, failure, and boundary behavior.

Lower risk means a narrower appropriate verification depth, never self-review, no QA, weaker
exact-candidate checks, or waived fresh CI. Different-executor QA remains the default where
practical, and candidate mutation still requires the repository's applicable fresh-QA process.

## 8. Monthly Workflow Reviews

Periodic workflow reviews belong under `docs/AI_WORKFLOW_REVIEWS/README.md`.

Those reviews are:

- analysis-only,
- non-authorizing,
- unable to mutate governance automatically,
- and escalated through the Project Manager plus a separately numbered governance task when they
  identify a change worth adopting.

## 9. Thin Entry Points

- `AGENTS.md` exists as a thin entry point only.
- It must stay a router to `AI_BOOTSTRAP.md` and this document.
- It must not become a second copy of project state, task history, acceptance criteria, or process
  detail already governed elsewhere.
