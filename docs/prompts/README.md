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
