------------------------------------------------

# Stage 4 – Phase 6

Status: In Progress

Started: 2026-08-20

Completed:

Related Tasks: T75

Related ADRs: None explicitly named.

Git Commit: implementation commit pending (branch `feature/T75-user-display-logout`)

Pull Request: None yet

Release:

---

---

## T75 Batch: Current-User Display + Logout Action

**Authorization / Scope:** The project owner authorized T75 on 2026-08-20, recorded as its own dedicated, documentation-only commit (`caa9bc5`) before any implementation existed. Approved scope: implement the current authenticated-user display and logout action in `MainLayout`'s header using the existing `AuthProvider` state/`logout()`; wire the existing `ipcBridge.clearRefreshToken()` into the user-facing logout flow to complete the deferred secure-session cleanup `T71`/`T74` both flagged as open. `T76+` functionality, automatic refresh-token exchange/retry/rotation, and new authentication mechanisms explicitly out of scope and unauthorized.

### Objective

Surface the authenticated user's identity in the app shell and give them a way to end their session from the UI, reusing `T70`'s `AuthProvider.logout()` end-to-end rather than introducing a second logout path, and finally wiring the `T71`-built, `T74`-deferred `ipcBridge.clearRefreshToken()` call into that flow.

### Tasks Implemented

- `T75` — `MainLayout.tsx`'s header now renders `currentUser?.display_name` (via `useAuth()`) and a "Log out" `Button` (existing `presentation/components/ui/button.tsx` primitive, `variant="outline"`, `size="sm"`) when a user is present; nothing renders in that slot when `currentUser` is null (kept nullable — `MainLayout` only ever mounts under `T73`'s `ProtectedRoute` in practice, but its type isn't narrowed at this call site, so no non-null assertion was used). The button calls `logout()` and tracks a local `isLoggingOut` boolean (mirroring `LoginPage.tsx`'s existing `isSubmitting` pattern) to disable itself and show "Logging out…" while the call is in flight, preventing a double-submit. No explicit `useNavigate()` call was added for the post-logout redirect — `T73`'s `ProtectedRoute` already re-renders reactively and redirects to `/login` whenever `currentUser` goes null, the exact mechanism `T74`'s global-401 handling already relies on; reusing it here avoids a second redirect path.
- `T75` — `AuthProvider.tsx`'s `logout()` gained the `ipcBridge.clearRefreshToken()` call `T71`'s authorization note and `T74`'s Deferred Work both named as open, guarded by `ipcBridge.isAvailable()` (mirroring the exact guard `httpClient.ts`'s own global-401 handler already uses) and wrapped in the same non-throwing `try`/`catch`-and-`console.error` idiom `logout()`'s existing best-effort `POST /api/v1/auth/logout` call already uses — placed after that API call and before `setAccessToken(null)`/`setState(...)`, so a failure in either the network call or the IPC clear never blocks the in-memory session from being cleared.

### Files Modified

Per `git diff --stat` against this batch's starting point (`caa9bc5`):

- `frontend/src/app/providers/AuthProvider.tsx` (Modified) — `logout()` now calls `ipcBridge.clearRefreshToken()` when the IPC bridge is available, guarded and error-swallowed exactly as described above. New `ipcBridge` import.
- `frontend/src/presentation/layouts/MainLayout.tsx` (Modified) — header gained a conditional current-user display + "Log out" button, wired to `useAuth()`.
- `frontend/src/app/providers/AuthProvider.test.tsx` (Modified — existing `T74` file, extended, not replaced) — new `"AuthProvider — logout() IPC refresh-token clearing"` describe block; the pre-existing `"AuthProvider — global 401 handling"` describe block and its one test are untouched.
- `frontend/src/presentation/layouts/MainLayout.test.tsx` (New) — 4 tests covering the display and logout-button behavior.

### Tests Added

- `AuthProvider.test.tsx` (3 new tests, existing 1 preserved) — `"calls ipcBridge.clearRefreshToken() when the IPC bridge is available"`: logs in through the real `AuthProvider`/`httpClient` (mocked `fetch`), logs out, asserts exactly one `clearRefreshToken()` call. `"skips ipcBridge.clearRefreshToken() when the IPC bridge is unavailable"`: same flow with `isAvailable()` returning `false`, asserts zero calls. `"still clears currentUser/tokens when ipcBridge.clearRefreshToken() rejects"`: same flow with `clearRefreshToken()` rejecting, asserts the UI still transitions back to its logged-out state (`currentUser`/`tokens` cleared) — direct proof that the `try`/`catch` around the awaited IPC call shields `logout()`'s state-clearing tail from an IPC failure, per the Independent Technical Verification's required item 3.
- `MainLayout.test.tsx` (4 new tests) — the authenticated user's `display_name` renders in the header; the user/logout block renders nothing when `currentUser` is null; clicking "Log out" calls `logout()` once; the button disables and reads "Logging out…" while `logout()` is pending.

### Test Results

Run against this batch's working tree (`feature/T75-user-display-logout`):

- **Frontend tests:** 43/43 passing across 8 test files (`npm run test -- --run`) — 36 pre-existing (7 files) + 3 new in `AuthProvider.test.tsx` + 4 new in the new `MainLayout.test.tsx`.
- **Frontend lint:** clean — 0 errors, 4 warnings, all four pre-existing (`react-refresh/only-export-components` on `AuthProvider.tsx`, `NotificationProvider.tsx`, `ThemeProvider.tsx`, `button.tsx`) and unrelated to this batch's diff.
- **Frontend format:** clean (`npm run format:check`) — one file (`AuthProvider.test.tsx`) needed a single `prettier --write` pass after the new `stubFetchWithLogout()` helper was added; re-verified clean afterward, no semantic change.
- **Frontend typecheck:** clean (`npx tsc --noEmit`).
- Backend suite not run — this batch touches only `frontend/`, no backend file is part of its diff.

### Design Decisions

- **Awaited, try/catch-wrapped `ipcBridge.clearRefreshToken()` in `logout()`, vs. `T74`'s fire-and-forget `void ipcBridge.clearRefreshToken().catch(() => {})` in the global-401 path.** These are two different situations, not an inconsistency: `T74`'s call sits inside `httpClient.ts`'s `request()`, on the hot path of *every* authenticated HTTP call — a `401` there is an automatic, involuntary session-expiry signal, and the reactive `currentUser`-null → `ProtectedRoute` redirect it drives must not be delayed even momentarily by an IPC round-trip, so it's fired without waiting. `T75`'s call sits inside `AuthProvider.logout()`, invoked exactly once, deliberately, by the user clicking "Log out" — there is no hot path to protect, and since this is the one place in the app whose entire job is to end the session's secure, persisted state, letting it actually finish (success or failure) before declaring the logout complete is the more correct, intentional behavior. Both call sites use the same `isAvailable()` guard and the same "never throw past this call" discipline (fire-and-forget's trailing `.catch(() => {})` vs. logout's `try`/`catch`-and-`console.error`) — the only difference is whether the caller waits, and that difference is deliberate per the reasoning above.
- **No explicit `useNavigate()` in `MainLayout`'s logout handler.** Same reasoning `T74`'s Design Decisions already recorded for the global-401 case: `T73`'s `ProtectedRoute` already redirects to `/login` reactively whenever `currentUser` goes null, so `logout()` clearing that state is sufficient — a second, imperative redirect would be redundant and would risk racing the reactive one.
- **Existing `AuthProvider.test.tsx` extended, not replaced.** The Independent Technical Verification's item 1 required this explicitly; the pre-existing `"AuthProvider — global 401 handling"` describe block, its one test, and the shared `stubFetch()`/`TOKENS`/`ME_RESPONSE`/`AutoLogin`/`ProtectedHarness`/`renderApp()` fixtures are all untouched. The new logout tests add their own `LogoutHarness` component and a separate `stubFetchWithLogout()` fetch stub (which additionally handles `/auth/logout` with a real `204`) rather than reusing the shared `stubFetch()`, because that shared stub's catch-all `401` — deliberate for the 401-handling tests — would otherwise make the logout POST itself come back `401` and trip `httpClient.ts`'s own global-401 `ipcBridge.clearRefreshToken()` call, double-counting alongside `AuthProvider.logout()`'s own explicit call.
- **`currentUser?.display_name` kept nullable in `MainLayout.tsx`, no non-null assertion.** Per the Independent Technical Verification's item 2: although `MainLayout` only ever mounts under `ProtectedRoute` in the live route tree, its `useAuth()` return type isn't narrowed at that call site, so the header's user/logout block is rendered conditionally (`currentUser ? ... : null`) rather than asserting non-null.

### Problems Encountered

- The first test run showed the two new "IPC clearing" tests calling `mockedClearRefreshToken` twice instead of once. Root cause: the shared `stubFetch()` helper's catch-all `401` response also matched `/api/v1/auth/logout`, so the logout POST itself came back `401`, which `httpClient.ts`'s own global-401 handler (from `T74`) treated as a session-expiry signal and reacted to by calling `ipcBridge.clearRefreshToken()` a second time — on top of `AuthProvider.logout()`'s own new explicit call. Resolved by adding a logout-test-local `stubFetchWithLogout()` that returns a real `204` for `/auth/logout`, isolating the two call sites' behavior as intended. No production code changed to fix this — it was purely a test-fixture gap.

### Deferred Work

- `T76+` functionality remains explicitly out of scope and unauthorized.
- Automatic refresh-token exchange, retry-after-401, and token rotation remain explicitly unauthorized and unimplemented, per `T75`'s own scope (and `T74`'s before it).
- Full manual/live browser verification (real backend, real login, visually confirming the header) was not performed this session — no backend/dev server was running and standing one up with live credentials was judged outside `T75`'s scope. Verification instead relied on the RTL test suite above, which directly exercises the rendered DOM output (user-name text, button presence/absence, click → `logout()` call, disabled/pending state) rather than a live E2E pass. Flagged here rather than silently assumed equivalent.

### Reviewer Checklist

```
Reviewer Checklist

☑ Architecture preserved
☑ Existing design patterns followed
☑ Tests added
☑ Existing tests pass
☑ Documentation updated
□ ADR updated (if required) — no architectural decision rose to ADR-level; the await-vs-fire-and-forget and redirect-reuse choices are recorded above as Design Decisions instead
□ AI_BOOTSTRAP updated (if required) — N/A, no standing convention changed
□ PROJECT_STATE updated (if required) — out of scope for this role/session per explicit instruction; left to the Documentation Manager after QA
☑ No unrelated refactoring
☑ No scope creep
☑ Ready for QA
```

### QA Decision — T75 batch

- **Date:** 2026-08-20
- **Decision:** [ ] Approved | [x] Approved with comments | [ ] Rework required
- **Comments / Rework items:**
  - Non-blocking: Full manual/live browser verification was not performed this session; verification relied exclusively on the RTL test suite.
