------------------------------------------------

# Stage 3 - Phase 13

Status: In Progress

Started: 2026-09-04

Completed:

Related Tasks: T113

Related ADRs: [ADR-0017](../../../ADR/0017-github-actions-ci.md)

Git Commit: `066e5565b82d8ec9831f31907875bd378ad53781`

Pull Request:

Release:

---

---

## Objective

Reduce unnecessary Release verification work for clearly documentation/governance-only pull requests while preserving a visible, successful required check and fail-safe full builds.

## Tasks Implemented

T113 authorization was recorded before this phase. The Release workflow now classifies pull-request changes before dependency installation and conditionally runs the existing reproducible build path.

## Files Modified

- `.github/workflows/release.yml`
- `scripts/release_build_relevance.cjs`
- `scripts/tests/release_build_relevance.test.cjs`
- `docs/ImplementationLog/Stage3/Phase13.md`

## Tests Added

- `scripts/tests/release_build_relevance.test.cjs` verifies documentation/governance fast-path classification, build-relevant inputs, and the unknown-path fail-safe.

## Test Results

- `node --test scripts/tests/release_build_relevance.test.cjs`: 4/4 passing.
- `npm run build`: Electron TypeScript/preload build and Vite production build passed.
- `npm --prefix frontend run lint` and `npm --prefix frontend run format:check`: passed.
- `frontend/node_modules/.bin/vitest.cmd run --reporter=verbose`: 8 files and 53 tests passed. Existing test stderr for React `act(...)` and the deliberately handled secure-storage rejection was observed, with no test failures.
- `python scripts/governance_validate.py`: 0 warnings and 0 errors.
- `python scripts/tests/test_governance_validate.py -v`: 51/51 passing.
- `js-yaml` parsing verified the preserved `Release build verification` job and dual-lockfile npm cache configuration; Prettier reports all changed files formatted. Hosted GitHub Actions verification remains pending on the implementation PR.

## Design Decisions

The existing `Release build verification` job remains present for every event. Only expensive steps are conditional, so branch protection continues to receive a successful, visible check on the fast path. `actions/setup-node` caches npm's package cache using both lockfiles; `node_modules` is not cached and `npm ci` remains mandatory before every actual build.

## Problems Encountered

The first focused test caught an ordering defect: the broad `.github/` build-relevant rule incorrectly overrode the explicit governance-workflow fast path. The classifier now checks known safe documentation/governance paths before broad build-relevant directories; unknown paths still run the full build.

## Deferred Work

No Electron packaging, publishing, deployment, or broader CI refactoring is included. Any future change to the build-relevance policy requires separate authorization.

## Future Considerations

Observe the first documentation/governance-only pull request after this workflow merges to confirm the GitHub Actions fast path and its measured duration in the hosted environment.

## Reviewer Checklist

☑ Architecture preserved
☑ Existing design patterns followed
☑ Tests added
☑ Existing tests pass
☑ Documentation updated
□ ADR updated (if required)
□ AI_BOOTSTRAP updated (if required)
□ PROJECT_STATE updated (if required)
☑ No unrelated refactoring
☑ No scope creep
☑ Ready for QA

## QA Decision

□ Approved
□ Approved with comments
□ Rework required
