# AI Workflow Reviews

This folder is for periodic review reports about how the repository's AI workflow is functioning in
practice.

## Purpose

These reviews exist to:

- inspect how the current workflow is operating,
- surface friction, ambiguity, or repeated failure patterns,
- suggest candidate governance improvements for future consideration,
- and preserve that analysis in the repository instead of leaving it only in conversation.

They do **not** authorize implementation, change workflow rules automatically, reopen accepted ADRs,
or bypass the existing numbered-task governance model.

## Policy

- Run on a roughly monthly cadence, or when the Project Manager explicitly requests an out-of-band
  review because recurring workflow issues justify it.
- Treat each review as **analysis only**.
- A review may recommend changes, but it may not adopt them by itself.
- A review must not mutate `PROJECT_STATE.json`, `IMPLEMENTATION_QUEUE.md`, role prompts,
  `AI_BOOTSTRAP.md`, `PROJECT_WORKFLOW.md`, CI rules, or branch-protection settings just by being
  written.

## Suggested Report Structure

Suggested filename shape:

`YYYY-MM_Workflow_Review.md`

Suggested sections:

1. Scope and date range reviewed
2. Repository artifacts examined
3. Workflow strengths
4. Friction points or repeated failure modes
5. Evidence-backed observations
6. Health summary
7. Candidate changes worth escalation
8. Explicit non-changes / out-of-scope items

## Suggested Health Fields

Reports should include a short health summary using fields such as:

- authorization discipline
- task-selection clarity
- bootstrap/context efficiency
- executor-routing clarity
- QA independence
- remote-head publication discipline
- merge-gate reliability
- documentation synchronization discipline

These are suggested fields, not a mandatory schema.

## Escalation Path

If a review concludes that a workflow change is warranted:

1. The finding is routed to the **Project Manager** for repository-first assessment.
2. If the Project Manager agrees the change merits adoption, the change must be proposed as a
   separate, explicitly authorized, numbered governance task.
3. Only that later numbered task may modify the governing files.

This keeps reviews informative without making them self-authorizing.
