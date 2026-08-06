# Templates

Reusable document skeletons for recurring project rituals. A template in this folder is never
filled in directly — copy it, fill in the copy, and keep the template itself blank so the next use
starts clean.

## Available templates

| Template | Use it for | Copy destination |
|---|---|---|
| [PreStageChecklist.md](PreStageChecklist.md) | The gate every development stage — and every standalone post-stage framework addition — must pass before its first line of code is written. | `docs/reviews/PreStageChecklist_<target>_<YYYY-MM-DD>.md` |
| [ADR_Template.md](ADR_Template.md) | Recording an architectural decision after it's made. Mirrors [`/ADR/template.md`](../../ADR/template.md), the authoritative copy actually used to create a new ADR — see that file's own note. | `ADR/00NN-title.md` |
| [ArchitectureDecisionTemplate.md](ArchitectureDecisionTemplate.md) | Proposing an architectural decision *before* writing code, to get project-owner approval. Precedes an ADR — its "Recommended Option" becomes the ADR's "Decision" once approved. | `docs/reviews/ArchitectureProposal_<target>_<YYYY-MM-DD>.md` |
| [Feature_Template.md](Feature_Template.md) | Documenting a new real business feature. | Append a section to `docs/FeatureRegistry.md` |
| [Module_Template.md](Module_Template.md) | Documenting a new code module with more narrative than a `docs/ModuleRegistry.md` table row has room for. | Expand a `docs/ModuleRegistry.md` row, or a subsection of `docs/Architecture.md` |
| [QAReviewTemplate.md](QAReviewTemplate.md) | Running and recording a QA review. | `docs/reviews/<Scope>_QA_Review.md` |
| [SessionReportTemplate.md](SessionReportTemplate.md) | Logging a development session. | Append a section to `docs/SessionReport.md` (chronological, oldest first) |
| [ReleaseTemplate.md](ReleaseTemplate.md) | Writing a release note for a version bump. | `docs/releases/vX.Y.Z.md` — see [docs/releases/README.md](../releases/README.md) |
| [APIEndpointTemplate.md](APIEndpointTemplate.md) | Documenting a new route mounted into the real app. | Append a section + status-table row to `docs/API.md` |
| [DatabaseMigrationTemplate.md](DatabaseMigrationTemplate.md) | Documenting a new Alembic migration (the documentation only — not the migration file itself, which is source code). | `docs/Database.md` / `docs/ERD.md` |

Add a row above whenever a new recurring document shape gets extracted into its own template here,
rather than being reinvented by hand each time — see "Adding a new template" below.

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
4. **Fill in any sign-off/attribution fields before treating the document as final** — several
   templates (e.g. `PreStageChecklist.md`, `ArchitectureDecisionTemplate.md`) have explicit Date /
   Reviewer / Developer / Notes fields so the result is attributable and dated, not an anonymous
   artifact nobody can act on with confidence later. Others (a session report, a release note) carry
   that same accountability implicitly through their Date field and the fact that they're appended
   to an already-attributed, chronological document — check each template's own header for what it
   expects.
5. **Store a completed *review-type* copy** (a filled-in checklist, an architecture proposal, a QA
   review) **under [docs/reviews/](../reviews/)**, alongside this project's other point-in-time
   review artifacts — it's a review record, not a living document, and shouldn't be edited after
   sign-off. If circumstances change before the reviewed work actually starts, do a new one rather
   than editing the old one — the same discipline [docs/releases/README.md](../releases/README.md)
   already applies to release notes ("freeze a moment in time... add a new one instead"). A
   completed *registry-type* copy (a feature, a module, an API endpoint, a migration) instead
   becomes a permanent section of its living registry document (`docs/FeatureRegistry.md`,
   `docs/ModuleRegistry.md`, `docs/API.md`, `docs/Database.md`) and **is** meant to be kept current
   as that thing evolves — the "don't edit after sign-off" rule applies to reviews, not registries.

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
