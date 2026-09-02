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

## 4. Bootstrap Modes

`AI_BOOTSTRAP.md` defines two bootstrap modes:

- **Control Tower Bootstrap** for broad-context planning, status reconstruction, task selection,
  and merge-gate work.
- **Authorized Task Bootstrap** for a fresh executor receiving one already-authorized task with
  bounded scope.

The mode changes how much context is loaded up front. It does **not** change the repository's
authorization, QA, or merge rules.

## 5. Context-Loading Principles

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

## 6. Recommended Context Order

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

## 7. Monthly Workflow Reviews

Periodic workflow reviews belong under `docs/AI_WORKFLOW_REVIEWS/README.md`.

Those reviews are:

- analysis-only,
- non-authorizing,
- unable to mutate governance automatically,
- and escalated through the Project Manager plus a separately numbered governance task when they
  identify a change worth adopting.

## 8. Thin Entry Points

- `AGENTS.md` exists as a thin entry point only.
- It must stay a router to `AI_BOOTSTRAP.md` and this document.
- It must not become a second copy of project state, task history, acceptance criteria, or process
  detail already governed elsewhere.
