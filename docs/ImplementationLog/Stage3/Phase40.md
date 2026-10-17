------------------------------------------------

# Stage 3 – Phase 40

Status: In Progress — implementation complete, awaiting independent QA

Started: 2026-10-17

Completed:

Related Tasks: T153

Related ADRs: [ADR-0043](../../../ADR/0043-enquiry-quotation-acceptance-matter-conversion.md)

Git Commit:

Pull Request:

Release:

------------------------------------------------

## Objective

Implement the authorized frontend workflow from Enquiry through exact-revision Acceptance and Party-canonical Matter navigation, consuming the existing authenticated API contract.

## Tasks Implemented

- Added the authenticated Enquiry list, prospect-only create form, detail/edit form, and explicit existing-Party link action.
- Added quotation creation/navigation, revision JSON evidence creation/history detail, and one-time issuance action.
- Added exact issued-revision Acceptance with the required Matter inputs, stable same-payload retry key, duplicate-submit protection, HTTP 201/200 distinction, conflict/error display, and resulting Matter navigation.

## Files Modified

- `frontend/src/app/routes.tsx`, `frontend/src/app/routes.test.ts`, and `frontend/src/presentation/layouts/MainLayout.tsx`
- `frontend/src/domain/types/enquiry.ts`, `frontend/src/infrastructure/api/enquiriesApi.ts`, `frontend/src/infrastructure/api/enquiriesApi.test.ts`, and `frontend/src/infrastructure/api/httpClient.ts`
- `frontend/src/presentation/pages/EnquiriesPage.tsx`, `EnquiryCreatePage.tsx`, `EnquiryDetailPage.tsx`, and `QuotationDetailPage.tsx`
- This phase log.

## Tests Added

- `enquiriesApi.test.ts` verifies exact acceptance hierarchy, `Idempotency-Key`, 201 creation, 200 replay, and unchanged proposal-snapshot submission.
- Router coverage now includes the Enquiry/Quotation hierarchy identifiers.

## Test Results

- `npm run test` — 20 files, 172 tests passed.
- `npm run lint` — 0 errors; 4 pre-existing `react-refresh/only-export-components` warnings in unrelated provider/button files.
- `npm run format:check` — passed.
- `npm run build` — passed (`tsc -b && vite build`).

## Design Decisions

The frontend consumes ADR-0043 and the T149–T152 API contracts without redefining their eligibility, tenant, or transaction semantics.

## Problems Encountered

- The fresh dedicated worktree did not include installed frontend dependencies. `npm ci` restored the declared dependency set before validation.

## Deferred Work

- Party selection is limited by the existing paginated Party-list contract (the UI loads its maximum currently supported page). Server-side Party search/filtering is not part of T153 and would require a separately authorized backend contract change.

## Future Considerations

Independent QA and post-QA documentation synchronization require separately commissioned roles.

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
