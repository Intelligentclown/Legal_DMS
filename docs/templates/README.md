# Templates

Reusable document skeletons for recurring project rituals. A template in this folder is never
filled in directly — copy it, fill in the copy, and keep the template itself blank so the next use
starts clean.

## Available templates

| Template | Use it for | Copy destination |
|---|---|---|
| [PreStageChecklist.md](PreStageChecklist.md) | The gate every development stage — and every standalone post-stage framework addition — must pass before its first line of code is written. | `docs/reviews/PreStageChecklist_<target>_<YYYY-MM-DD>.md` |

This list will grow — [ADR/template.md](../../ADR/template.md) already serves the same "copy, don't
edit in place" role for architecture decisions and predates this folder; it isn't duplicated here,
just cross-referenced. Add a row above whenever a new recurring document shape (e.g. a standard QA
review skeleton, a standard session-report skeleton) gets extracted into its own template here,
rather than being reinvented by hand each time.

## How to use a template

1. **Copy it, don't edit it in place.** The file in this folder must stay a blank skeleton. Copy it
   to the destination named in the table above, with the real date and target substituted into the
   filename.
2. **Fill in every section against reality, not memory.** A template exists to force verification —
   run the tests, check `git status`, read the actual file — not to let a checklist be filled in
   from what a document *claims* is true. If a box is checked without having actually looked, the
   checklist has failed at its one job.
3. **Leave a box unchecked rather than mark it done to move faster.** An honest unchecked box with a
   reason in the Notes section is useful information for the next session. A checked box that wasn't
   actually verified is worse than no checklist at all — it actively misleads whoever reads it next.
4. **Get the sign-off fields filled in before treating the gate as passed** — Date, Reviewer,
   Developer, and Notes exist so a completed checklist is attributable and dated, not an anonymous,
   undated artifact nobody can act on with confidence later.
5. **Store the completed copy under [docs/reviews/](../reviews/)**, alongside this project's other
   point-in-time review artifacts (QA reviews, the Documentation Consistency Report) — a completed
   checklist is a review record, not a living document, and shouldn't be edited after sign-off. If
   circumstances change before the stage actually starts, do a new one rather than editing the old
   one — the same discipline [docs/releases/README.md](../releases/README.md) already applies to
   release notes ("freeze a moment in time... add a new one instead").

## Why this exists as its own folder

This project already has several "fill in the same shape every time" documents — a session report
per session, a release note per version, an ADR per decision — but until now each one's shape lived
only as an implicit convention (readable from the last one someone wrote) rather than an explicit,
reusable skeleton. `docs/templates/` makes that convention copyable instead of tribal: a fresh AI
session or a new contributor can produce a correctly-shaped document on the first try instead of
reverse-engineering the pattern from old examples, which is exactly the kind of "don't re-derive
context" discipline this project's whole documentation set is built around (see
[AI_BOOTSTRAP.md](../../AI_BOOTSTRAP.md)).

## Adding a new template

Only extract something into a template here once the same document shape has actually recurred —
don't template something speculatively before it's been written by hand at least once. When you do:

1. Write the template with every section a real instance needs, using placeholder text or a brief
   instruction in place of real content (see `PreStageChecklist.md` for the pattern: real section
   headers and checkbox items, but no filled-in answers).
2. Add a row to the table above naming what it's for and where completed copies go.
3. Point to it from wherever the ritual it supports is already documented (e.g.
   [AI_HANDOVER.md](../AI_HANDOVER.md)'s "Recommended Implementation Order" section links to
   `PreStageChecklist.md` at the point in the workflow where it applies) so it's discovered in
   context, not only by browsing this folder.
