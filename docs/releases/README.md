# Release Notes

This folder holds one comprehensive document per released version — a durable, point-in-time
snapshot of "what shipped, what's known about it, and what's next," distinct from the two
changelog files and the session log this project already keeps. See "How this differs from
existing docs" below before assuming this duplicates something else.

## When to create a new release note

**Every time [`PROJECT_STATE.json`](../../PROJECT_STATE.json)'s `currentVersion` is bumped**, create
a matching `docs/releases/vX.Y.Z.md`. One document per version, no exceptions — including
documentation-only or QA-fix releases that don't ship a new business feature (see
[`v0.3.8.md`](v0.3.8.md) for an example of exactly that). If a version bump ever ships without a
matching release note, treat that the same way this project already treats any other
documentation gap: the release isn't done until it does.

This project versions per meaningful unit of work (each standalone framework addition, each QA-fix
pass, each stage) rather than only at stage boundaries — see the root
[`CHANGELOG.md`](../../CHANGELOG.md) for the version history this folder mirrors one-to-one.

## Naming convention

`docs/releases/vX.Y.Z.md` — lowercase `v` prefix, the exact semantic version from
`PROJECT_STATE.json`'s `currentVersion` and the root `CHANGELOG.md`'s `## [X.Y.Z]` heading for that
release. No suffixes, no dates in the filename (the date is a field inside the document, not part
of its name, since a release document's identity is its version, not when it happened to be
written).

## Required sections, in this order

Every release document uses exactly these headings, in this order, even when a section is short or
says "None." An omitted section reads as an oversight, not a deliberate "nothing to report" — write
"None" explicitly rather than leaving a heading out.

| Section | What goes here |
|---|---|
| **Release Version** | The exact semantic version, matching `PROJECT_STATE.json` and the root `CHANGELOG.md` for this release. |
| **Release Date** | The date this version became current (`PROJECT_STATE.json`'s `lastUpdated` at release time), `YYYY-MM-DD`. |
| **Project Stage** | Which numbered stage (or post-stage addition) this release belongs to — copy the phrasing from `PROJECT_STATE.json`'s `currentStage` / `docs/ProjectStatus.md`'s header at the time. |
| **Summary** | 3–6 sentences: what this release is, in plain language, for a reader who hasn't read anything else. State plainly if it's not a feature release (a QA-fix pass, a documentation sync, a hardening pass) — don't imply feature work happened if it didn't. |
| **Major Features** | New business or framework capabilities shipped in this release. Write "None" if this release didn't add one — don't stretch a bug fix or a doc update to sound like a feature. |
| **Architectural Improvements** | Structural/design changes: new ports, new ADRs, refactors, new abstractions. Link the relevant ADR(s). |
| **Bug Fixes** | Concrete defects fixed, each with enough detail (file, symptom, root cause in one line) that a reader doesn't have to open the diff to understand what changed and why it mattered. |
| **Documentation Improvements** | Docs added, corrected, or resynced — including pure documentation-only releases like this one's own precedent. |
| **Breaking Changes** | Anything that changes an existing port signature, route, table, or contract in a way that breaks an existing caller. Write "None" if genuinely none — this project's convention across every release so far has been additive-only; say so explicitly rather than leaving the reader to infer it. |
| **Migration Notes** | Database migrations, config changes, or manual steps a deployer/developer must take when moving to this version. Write "None — no schema change" (or equivalent) when nothing applies. |
| **Known Issues** | Carry forward from [`docs/KnownIssues.md`](../KnownIssues.md) anything still open and relevant at this release, plus anything newly discovered. Don't silently drop a known issue just because it's not new. |
| **Technical Debt** | Point to [`IMPLEMENTATION_QUEUE.md`](../../IMPLEMENTATION_QUEUE.md) and/or [`docs/ArchitectureScorecard.md`](../ArchitectureScorecard.md)'s Technical Debt-relevant rows rather than re-deriving the list — summarize, don't duplicate verbatim, so the two don't drift out of sync with each other. |
| **Next Planned Release** | The next version, if scoped, or an explicit "not yet planned, pending project-owner direction" if not — this project's charter is not to guess at unscoped future work. |
| **Files Modified** | The actual file list for this release (source, tests, docs) — `git diff --stat` against the previous release's commit is the fastest way to generate this accurately; don't reconstruct it from memory. |
| **Related ADRs** | Every ADR this release's work is governed by or introduces, linked. |
| **Future Work** | Deferred items with a named trigger condition (not vague "someday" notes) — mirror the phrasing style `IMPLEMENTATION_QUEUE.md` already uses for its deferred QA findings (a gap is fine to leave open as long as *why* and *until when* are both stated). |

## How this differs from existing docs

This project already tracks change history three other ways — a release note is not a fourth copy
of the same information, it's a different *shape* of the same underlying facts:

- **[`/CHANGELOG.md`](../../CHANGELOG.md)** (root) — a short, version-indexed pointer list. One
  paragraph per version, links out to the detail. Read this to find *which* version did *roughly*
  what.
- **[`docs/CHANGELOG.md`](../CHANGELOG.md)** — the detailed, per-addition changelog: added/modified
  files, new tests, lint fixes, verification notes. Read this for the *diff-level* detail of what
  changed.
- **[`docs/SessionReport.md`](../SessionReport.md)** — a chronological log of *development
  sessions*, including problems hit and how they were solved, objectives, and next-session goals.
  Read this for the *narrative* of how the work happened. A session and a release don't always
  line up 1:1 (one session can span multiple version bumps, or a version bump can span multiple
  sessions).
- **`docs/releases/vX.Y.Z.md`** (this folder) — a *self-contained*, point-in-time snapshot of one
  released version specifically: not just what changed, but what's known, open, deferred, and next
  as of that version. It's the document a reader should be able to read **alone**, without opening
  any of the three docs above, and come away with a complete picture of that release. Every other
  doc in this project is written to be current; a release note is written to freeze a moment in time
  and stay accurate to *that moment* forever, even after later releases change the state it
  describes — don't edit a past release note to reflect later reality, add a new one instead.

## Writing a new release note

1. Copy [`docs/templates/ReleaseTemplate.md`](../templates/ReleaseTemplate.md) — the authoritative
   copy of this release note's shape, kept in one place so it can't drift out of sync with a second
   copy — into `docs/releases/vX.Y.Z.md`.
2. Fill every section — pull facts from `PROJECT_STATE.json`, `docs/ProjectStatus.md`, both
   `CHANGELOG.md` files, `docs/SessionReport.md`'s latest session entry(ies), and
   `IMPLEMENTATION_QUEUE.md`, rather than inventing detail. If something is genuinely unknown or
   unverified (e.g. a test suite that couldn't be run in the current environment), say so explicitly
   — the same "trust the code, report the discrepancy" discipline [`AI_BOOTSTRAP.md`](../../AI_BOOTSTRAP.md)
   already asks for elsewhere applies here too.
3. Cross-check the previous release note's "Next Planned Release" section — if this release matches
   what it predicted, say so; if it doesn't (a different version shipped than expected), say that
   too, briefly, rather than silently ignoring the mismatch.
4. Link this new file from the root [`CHANGELOG.md`](../../CHANGELOG.md) entry for the same
   version, and confirm [`PROJECT_STATE.json`](../../PROJECT_STATE.json)'s `documentation` block
   points at this folder (it should already, once set up once).

See [`docs/templates/README.md`](../templates/README.md) for how this template relates to the
project's other reusable templates.
