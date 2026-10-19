------------------------------------------------

# Stage 3 – Phase 43

Status: In Progress — implementation candidate awaiting Independent QA

Started: 2026-10-19

Completed:

Related Tasks: T160

Related ADRs: ADR-0044, ADR-0021, ADR-0022

Git Commit: 917378db4da380f8607365dc8f681513517ecb79, 806123e7849b019666deb5932cd907c067d25513

Pull Request:

Release:

------------------------------------------------

## Objective

Expose canonical Matter–Property associations on the existing Matter detail page using only the protected T157 and Property API contracts.

## Tasks Implemented

- Added typed adapters for the paginated tenant-visible Property list and Matter-scoped association list, link, and unlink operations.
- Added a Matter-detail association section that lists linked Properties, selects an existing paginated Property, links it, and unlinks only the relationship.
- Added an accessible client-side filter over each loaded Property API page; no unsupported server-side search parameter is sent.
- Preserved the backend's 201-created versus 200-idempotent link distinction in user-facing feedback.

## Files Modified

- `frontend/src/domain/types/property.ts`
- `frontend/src/infrastructure/api/propertiesApi.ts`
- `frontend/src/infrastructure/api/mattersApi.ts`
- `frontend/src/infrastructure/api/mattersApi.test.ts`
- `frontend/src/presentation/pages/MatterDetailPage.tsx`
- `frontend/src/presentation/pages/MatterDetailPage.test.tsx`
- `docs/ImplementationLog/Stage3/Phase43.md`

## Tests Added

- Matter–Property API adapter tests cover canonical list, 201 creation, 200 idempotency, and relationship-only unlink paths.
- Matter detail interaction tests cover list, empty, page-local search, selection, mutation refresh, idempotent feedback, and permission-denied mutation feedback.

## Test Results

- `npx vitest run src/infrastructure/api/mattersApi.test.ts src/presentation/pages/MatterDetailPage.test.tsx` — 23 passed.
- `npm test` — 183 passed across 21 test files.
- `npm run build` — passed (`tsc -b` and Vite production build).
- `npm run lint` — passed with 0 errors and 4 pre-existing Fast Refresh warnings in unrelated provider/button files.
- `npm run format:check` — passed.

## Design Decisions

- The link adapter uses the existing `postWithResponse` facility so the documented 200 duplicate response remains visible instead of being flattened into a generic success.
- The UI deliberately consumes only existing Matter and paginated Property routes; no Property detail navigation or Property mutation surface is introduced.
- Error presentation stays on the existing `HttpError`/`ErrorMessage` boundary, including the backend's permission-denied message.

## Problems Encountered

- Initial RTL assertions matched both the select option and the association-table cell; assertions were narrowed by semantic role/element to test the intended control.

## Deferred Work

- Independent QA, documentation synchronization, merge, and post-merge governance closeout are separately commissioned lifecycle roles.
- Server-side Property search remains excluded because the protected Property API contract exposes pagination only, not a search query; the implemented page-local filter makes that boundary explicit.

## Future Considerations

- A Property-scoped reverse association view or Property detail navigation requires separate authorization and an existing supported route.

## Reviewer Checklist

☑ Architecture preserved
☑ Existing design patterns followed
☑ Tests added
☑ Existing tests pass
☑ Documentation updated
□ ADR updated (if required) — no architectural decision changed.
□ AI_BOOTSTRAP updated (if required) — no process change.
□ PROJECT_STATE updated (if required) — Documentation Manager work after QA.
☑ No unrelated refactoring
☑ No scope creep
☑ Ready for QA

## QA Decision

None — Independent QA has not yet been commissioned or performed.
