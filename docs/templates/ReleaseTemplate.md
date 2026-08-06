# Release Notes Template

**Purpose:** The skeleton for a new release note under [docs/releases/](../releases/). This is the
**authoritative copy** of the template — [docs/releases/README.md](../releases/README.md) explains
the release notes system and points here rather than embedding a second copy, so there's exactly
one place this shape is defined.

**When to use:** Every time [PROJECT_STATE.json](../../PROJECT_STATE.json)'s `currentVersion` is
bumped — see [docs/releases/README.md](../releases/README.md) for the full workflow (why this
exists, how it differs from `CHANGELOG.md`/`SessionReport.md`, and how to fill it in accurately
rather than from memory).

**Copy destination:** `docs/releases/vX.Y.Z.md`, using the exact semantic version from
[PROJECT_STATE.json](../../PROJECT_STATE.json)'s `currentVersion` and the root
[CHANGELOG.md](../../CHANGELOG.md)'s matching `## [X.Y.Z]` heading.

---

# Release vX.Y.Z

## Release Version
X.Y.Z

## Release Date
YYYY-MM-DD

## Project Stage
<copy from PROJECT_STATE.json / docs/ProjectStatus.md at release time>

## Summary
<3-6 plain-language sentences. State plainly if this is not a feature release.>

## Major Features
<or "None — <why>">

## Architectural Improvements
<or "None">

## Bug Fixes
<or "None">

## Documentation Improvements
<or "None">

## Breaking Changes
None — <or describe the break and who it affects>

## Migration Notes
None — no schema change <or describe the required steps>

## Known Issues
<carried-forward + new, or "None new; see docs/KnownIssues.md">

## Technical Debt
<summarize, point to IMPLEMENTATION_QUEUE.md / docs/ArchitectureScorecard.md — don't duplicate
verbatim, so the two don't drift out of sync with each other>

## Next Planned Release
<version + scope, or "Not yet planned — pending project-owner direction">

## Files Modified
<list, grouped source/tests/docs — generate from `git diff --stat` against the previous release's
commit, don't reconstruct from memory>

## Related ADRs
<links>

## Future Work
<deferred items, each with a named trigger condition — not vague "someday" notes>
