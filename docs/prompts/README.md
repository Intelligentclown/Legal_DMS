# AI Role Prompts

Reusable, copy-ready prompt templates for the four roles [`PROJECT_WORKFLOW.md`](../../PROJECT_WORKFLOW.md)
defines. Each file in this folder is the standing instruction set for one role — copy it into a new
session as-is to start that role's work, rather than re-deriving its responsibilities from scratch
each time.

## Why these exist

`PROJECT_WORKFLOW.md`'s own [Standard Prompts](../../PROJECT_WORKFLOW.md#standard-prompts) section
names this folder's purpose directly: "these prompts are maintained outside this document to allow
evolution without changing the workflow itself." A prompt can be sharpened — a clearer instruction,
a missing edge case named — without touching the stable operating manual it implements, and without
every future session needing to re-read the full manual to reconstruct what a given role is supposed
to do.

## How this relates to `AI_BOOTSTRAP.md`

`AI_BOOTSTRAP.md` is session-level: the New Session Protocol and non-negotiable rules every session
follows regardless of role. These prompts don't replace or restate it — every prompt in this folder
assumes `AI_BOOTSTRAP.md` has already been read and its rules are already in effect, then adds only
what's specific to one role on top.

## How this relates to `PROJECT_WORKFLOW.md`

`PROJECT_WORKFLOW.md` explains *why* the lifecycle has the shape it does — the roles, the gates, the
branch/PR/release mechanics — as stable narrative. These prompts are the *operational* form of that
same lifecycle: instructions written to be acted on directly, for one role at a time. If a prompt and
`PROJECT_WORKFLOW.md` ever disagree, `PROJECT_WORKFLOW.md` is authoritative — a prompt is how the
workflow gets executed, not a second definition of what it is.

## When each prompt is used

| Prompt | Used when |
|---|---|
| [`ProjectManager.md`](ProjectManager.md) | At the start of a work session — rebuilds repository state and recommends the next implementation batch. |
| [`BackendDeveloper.md`](BackendDeveloper.md) | Once a task is approved — implements it. |
| [`QAReviewer.md`](QAReviewer.md) | Once an implementation batch is ready for review — renders the QA Decision. |
| [`DocumentationManager.md`](DocumentationManager.md) | Once QA approves — synchronizes project-wide documentation. |

## Workflow

```
Project Manager
        ↓
Backend Developer
        ↓
QA Reviewer
        ↓
Documentation Manager
        ↓
Git / CI / PR / Merge
        ↓
Repeat
```

Full detail on every step: [`PROJECT_WORKFLOW.md`](../../PROJECT_WORKFLOW.md), especially
§3 (Standard Development Lifecycle) and §7 (AI Roles).

## A fifth prompt: `GitCI_PR_Manager.md`

[`GitCI_PR_Manager.md`](GitCI_PR_Manager.md) operationalizes the "Git / CI / PR / Merge" box in the
diagram above — the same box §3's lifecycle table already describes (Git Commit → Push → GitHub
Actions → Pull Request → Merge → Delete Branch → Update Local `main`), just not previously packaged
as a copy-ready prompt the way the other four steps are.

**This is not yet a fifth entry in `PROJECT_WORKFLOW.md` §7's "AI Roles" table**, and
`PROJECT_WORKFLOW.md`'s own "Standard Prompts" list still names only the four above — both are
authoritative and neither has been updated to list it. Formally adopting a fifth standing role is a
process change under `AI_BOOTSTRAP.md`'s "Process changes are versioned" rule and requires its own
proposal, review, and sign-off before those documents are edited to match. Until then, treat
`GitCI_PR_Manager.md` as an available, usable prompt for the already-described lifecycle steps — not
as evidence that a fifth role has been formally established.

## Two more roles operating in practice, neither formally adopted (added 2026-08-21)

A repository-first documentation/governance reconciliation pass (2026-08-21, Documentation Manager)
found two more roles in the same position as `GitCI_PR_Manager.md` above — operating in this
project's actual history, but without a standing prompt file or an entry in `PROJECT_WORKFLOW.md`
§7's AI Roles table. Recorded here as disclosure, following the same pattern as the section above —
**neither is adopted by writing this section**, and neither prompt file is created here.

**Frontend Developer.** Distinct from Backend Developer, first used for `T69`
(`docs/ImplementationLog/Stage4/Phase1.md`: "the first task to use the Frontend Developer role instead
of Backend Developer") and used again for `T70`, `T72`, `T73`, `T74`, `T75` — five further merged
tasks. `PROJECT_STATE.json`'s own `T70` governance note discloses that this role has been following
`docs/prompts/BackendDeveloper.md` §5's approval-checkpoint discipline "as this project's process
template for frontend work too," in the absence of any Frontend-Developer-specific prompt. No
`docs/prompts/FrontendDeveloper.md` exists, and `PROJECT_WORKFLOW.md` §7 lists only "Backend
Developer." This is a real, repeatedly-used operational role without a standing definition — not a
hypothetical gap.

**Independent Technical Verifier.** `T72`'s and `T73`'s own batch records name an "Independent
Technical Verification" step, rendering its own disposition ("Approved with comments") alongside
each batch's ordinary QA Decision — a second review gate, not a synonym for the first.
`PROJECT_STATE.json`'s `git` block additionally describes a session in this role performing a
Documentation Manager closeout directly, citing a role-fallback procedure ("per Legal_DMS_
Process_Supervision.md §§2/3, Claude Code is the documented fallback for the Documentation Manager
role when the primary isn't available"). **`Legal_DMS_Process_Supervision.md` does not exist anywhere
in this repository or its git history** — confirmed by direct search (`git log --all --diff-filter=A`
and a full-tree grep, 2026-08-21) — so that citation currently points at nothing. No `docs/prompts/`
file defines this role, and `PROJECT_WORKFLOW.md` §7 does not list it.

**Neither gap is resolved by this section.** Per `AI_BOOTSTRAP.md`'s "process changes are versioned"
rule, formally adopting either role (a standing prompt file, an entry in `PROJECT_WORKFLOW.md` §7,
and — for the Independent Technical Verifier — either writing the governing document its own
citation assumes exists or correcting that citation) requires its own proposal, review, and sign-off
from the project owner. Until then, both continue as informal, undocumented practice — accurately
disclosed here, not silently formalized and not silently removed from the record either.
