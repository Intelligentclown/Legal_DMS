# Stage 4 (Historical / Informal Label — Not the Project's Current Stage)

**This directory name is a preserved historical artifact.** `Phase0.md` through `Phase7.md` in this
directory record `T66`–`T82`, filed under "Stage 4" between 2026-08-17 (when the `T66` implementation
branch first used the name `feature/stage4-t66-seed-role-permissions`) and 2026-08-21.

That label was never authorized by the project owner. No `PreStageChecklist_Stage4_*.md` sign-off
exists anywhere in this repository (compare
[`docs/reviews/PreStageChecklist_Stage3_2026-08-07.md`](../../reviews/PreStageChecklist_Stage3_2026-08-07.md),
which `AI_BOOTSTRAP.md` requires before any new stage begins), and neither `IMPLEMENTATION_QUEUE.md`
nor `docs/Roadmap.md` ever adopted a "Stage 4" heading — both continued to describe this exact work
(seed/bootstrap data, frontend, hardening & close-out) as Phases 4–6 of the single, continuous
**Stage 3 — Authentication & Authorization**. `docs/Roadmap.md` separately reserves the name "Stage
4" for genuinely unstarted future business-feature work (Matter/Client/Property Management, etc.),
so this directory's name also collided with that reservation.

On 2026-08-21 the project owner confirmed the project remains formally Stage 3 and authorized
correcting `PROJECT_STATE.json` accordingly — see that file's `currentStage` object and its
`stages[]` array `stage-3`/`stage-4` entries for the full governance-correction record.

Per this project's historical-preservation discipline (`AI_BOOTSTRAP.md`'s task-ID immutability rule,
applied here by the same reasoning to existing implementation-log filenames), **the files in this
directory are preserved exactly as originally written** — including any "Stage 4 Phase N" phrasing
inside them — rather than moved, renamed, or rewritten.

**Going forward:** new phase logs for continuing Stage 3 work are filed under
[`docs/ImplementationLog/Stage3/`](../Stage3/), continuing that directory's existing
`Phase0.md`–`Phase3.md` sequence (next: `Phase4.md`), not under this directory.

For the authoritative current task/phase record, consult `IMPLEMENTATION_QUEUE.md`, not this
directory's name.
