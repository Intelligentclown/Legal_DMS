------------------------------------------------

# Stage 4 – Phase 5

Status: In Progress

Started: 2026-08-20

Completed:

Related Tasks: T73, T74

Related ADRs: None explicitly named.

Git Commit: bf0fae3 (T73); T74 implementation commit pending

Pull Request: None (T73 has not yet been merged)

Release:

---

---

## T73 Batch: Protected Route

**Authorization / Scope:** The project owner authorized T73 on 2026-08-20, recorded as its own dedicated, documentation-only commit (`aa98a3c`) before any implementation existed. Approved scope: Implement a Protected-route wrapper that redirects unauthenticated users to `/login`, utilizing the `T70` auth state. Explicitly out of scope and unauthorized: `T74`, `T75`, and `T76+`.

### Objective

Build a `ProtectedRoute` wrapper component utilizing `T70`'s `useAuth()` hook to protect routes. Unauthenticated users (where `currentUser` is null) are redirected to `/login` via `Navigate`. Authenticated users are allowed to access protected children (`Outlet`).

### Tasks Implemented

- `T73` — Protected route: Created `ProtectedRoute` and wrapped the main application routes (`MainLayout` and its children) in it.

### Files Modified

Per uncommitted changes on `feature/T73-protected-route`:

- `frontend/src/app/routes.tsx` (Modified) — Wrapped the root route structure with `ProtectedRoute`, securing all application content under `/`.
- `frontend/src/app/ProtectedRoute.tsx` (New) — The protected route wrapper component implementing redirect logic via `Navigate`.
- `frontend/src/app/ProtectedRoute.test.tsx` (New) — 2 integration/unit tests validating unauthenticated redirection to `/login` and authenticated content rendering.

### Tests Added

- `ProtectedRoute.test.tsx` (2 tests) — Tests verify that an unauthenticated state redirects and hides protected content, while an authenticated state renders protected content correctly.

### Test Results

Run directly against the `feature/T73-protected-route` branch (with unstaged implementation files):

- **Frontend tests:** 23/23 passing across 6 test files (`npm run test -- --run`).
- **Frontend lint:** clean (0 errors, 4 warnings).
- **Frontend format:** clean (`npm run format:check`).
- **Frontend typecheck:** clean (`npx tsc --noEmit`).

### Problems Encountered

- None reported during implementation.

### Deferred Work

- `T74`, `T75`, and `T76+` remain explicitly out of scope and unauthorized.

### QA Decision — T73 batch

- **Date:** 2026-08-20
- **Decision:** [ ] Approved | [x] Approved with comments | [ ] Rework required
- **Comments / Rework items:**
  - **replace-navigation semantics:** The `replace` prop on `<Navigate to="/login" replace />` was verified by source inspection, but the automated tests do not currently assert history replacement semantics. This is a non-blocking finding.
  - **Missing phase log:** The T73 phase log was missing at QA time and is now being created. This is a non-blocking documentation gap being resolved by this document.

### Independent Technical Verification — T73 batch

- **Decision:** [ ] Approved | [x] Approved with comments | [ ] Rework required
- **Comments / Rework items:**
  - Approved with comments matching the QA decision. The two non-blocking findings (replace-navigation semantics not automated-tested; missing phase log) are recorded.
  - Verified that `T74`, `T75`, and `T76+` remain untouched.
  - Verified no changes to application/source/test logic were introduced outside the exact T73 scope.

---

## T74 Batch: Global Auth Header + 401 Handling + 204 Fix

**Authorization / Scope:** The project owner authorized T74 on 2026-08-20, recorded as its own dedicated, documentation-only commit (`d56e7c4`) before any implementation existed. Approved scope: update `httpClient` infrastructure to attach the current access token to outgoing authenticated requests and handle `401 Unauthorized` responses globally by clearing the local authentication session and redirecting to `/login`; resolve the existing `204 No Content` success-path parsing issue in `httpClient.ts`; utilize existing `T70` auth state and `T71` IPC storage as needed. Automatic refresh-token exchange, retry, rotation, or refresh-on-401 behavior explicitly prohibited. `T75`, `T76+`, and unrelated auth hardening explicitly out of scope and unauthorized.

### Objective

Make `httpClient` session-aware: attach `Authorization: Bearer <token>` to outgoing requests once a session exists, detect a `401` on an authenticated request as a session-invalidation signal (clearing both in-memory and Electron-persisted session state and redirecting to `/login`), and fix the pre-existing defect where a real `204` response (e.g. `POST /api/v1/auth/logout`) threw instead of resolving.

### Tasks Implemented

- `T74` — `httpClient.ts` gained module-level `accessToken` state (`setAccessToken`) auto-attached to every outgoing request's `Authorization` header when set, and a registrable `setUnauthorizedHandler` invoked only when a request that carried an access token comes back `401` (a `401` on a request with no token attached — e.g. a bad-credentials login attempt — is a plain auth failure, not a session expiry, and is deliberately excluded so a failed login doesn't get treated as "your session expired"). On a qualifying `401`, `httpClient` clears its own token, clears the `T71`-established IPC-persisted refresh token via a new `ipcBridge.clearRefreshToken()` (mirroring `ipcBridge.setRefreshToken()`'s existing pattern — `ipcBridge.ts` didn't expose a clear method yet, a mechanical extension needed to reach the secure storage this task's scope names), and invokes the registered handler. `AuthProvider.tsx` registers a handler on mount that clears its React `currentUser`/`tokens` state; the existing `T73` `ProtectedRoute` then reactively redirects to `/login` on its own, since it already renders `<Navigate to="/login" />` whenever `currentUser` is null — no router-singleton import or `window.location` hard-navigation was needed (the latter would in any case break under Electron's packaged `file://` load, since `/login` isn't a real file). `request()` also now returns `undefined` for a `204` response instead of unconditionally calling `response.json()`, fixing the exact defect `T70`'s QA review flagged as a non-blocking comment (`logout()`'s `POST /api/v1/auth/logout` returns `204` and was silently mis-logged as a failed logout). `AuthProvider.login()`/`logout()` now call `setAccessToken()` to keep `httpClient`'s module-level token in sync with the React auth state (set after login's tokens arrive, rolled back if `/me` then fails; cleared on logout) — a mechanical consequence of introducing token-mirroring, not new user-facing behavior. A latent header-merge-order bug was also fixed in passing: the original `{ headers: {...}, ...init }` spread order let a caller-supplied `init.headers` (e.g. `AuthProvider`'s explicit `/me` header) silently clobber the computed headers object, which happened to be harmless only because it only affected `get()`'s optional-headers path on GET requests; the merge order is now `{ ...init, headers: {...} }`, so the explicitly-computed header object (Content-Type + auto Authorization + caller overrides, in that precedence) always wins.

### Files Modified

Per `git diff --stat` against this batch's starting point:

- `frontend/src/infrastructure/api/httpClient.ts` (Modified) — `setAccessToken`/`setUnauthorizedHandler` exports, automatic `Authorization` header injection, global `401` handling (token-had-been-attached gated), `204` short-circuit, header-merge-order fix.
- `frontend/src/infrastructure/ipc/ipcBridge.ts` (Modified) — new `clearRefreshToken()` wrapper and `ElectronApi.clearRefreshToken` type, mirroring the existing `setRefreshToken()` pattern exactly.
- `frontend/src/app/providers/AuthProvider.tsx` (Modified) — registers/unregisters the unauthorized handler on mount; `login()`/`logout()` call `setAccessToken()` to keep `httpClient`'s token state in sync.
- `frontend/src/infrastructure/api/httpClient.test.ts` (Modified) — new tests for the `204` fix, Authorization-header injection/merge/precedence/clearing, and global-401 handling (including the deliberate login-401 exclusion and the `ipcBridge.clearRefreshToken()` call).
- `frontend/src/app/providers/AuthProvider.test.tsx` (New) — end-to-end test proving the full `401` → session-clear → `/login` redirect flow through the real (non-mocked) `httpClient` + `AuthProvider` + `ProtectedRoute` integration.
- `frontend/src/presentation/pages/LoginPage.test.tsx` (Modified) — its existing manual `vi.mock("@/infrastructure/api/httpClient", ...)` needed `setAccessToken`/`setUnauthorizedHandler` added as no-op `vi.fn()`s, since `AuthProvider.tsx` now imports them and the mock had previously fully replaced the module without them (mechanical fix required by the new export surface; no assertions changed).

### Tests Added

- `httpClient.test.ts` — `"204 No Content"` (1 test: resolves `undefined`, never calls `.json()`); `"Authorization header injection"` (5 tests: no header before a token is set, header attached once set, merges correctly with caller-supplied headers, an explicit caller `Authorization` header still takes precedence, header stops being sent once the token is cleared); `"global 401 handling"` (6 tests: no handler invocation on a tokenless request's `401` — e.g. login; handler invoked when a token-bearing request gets `401`; the token is cleared so the next request is unauthenticated; `ipcBridge.clearRefreshToken()` is called when the IPC bridge is available; it's skipped when unavailable — i.e. running in a plain browser/test context; the `401` still surfaces as a rejected `HttpError` to the caller).
- `AuthProvider.test.tsx` — `"clears the session and redirects to /login when an authenticated request comes back 401"`: logs in through the real `AuthProvider`/`httpClient` (mocked `fetch` only), confirms protected content renders, triggers a request that returns `401`, and asserts the app lands back on `/login` with the protected content gone — proving the full global-401 flow end-to-end, not just each piece in isolation.

### Test Results

Run against this batch's working tree (`feature/T74-global-auth-httpclient`):

- **Frontend tests:** 36/36 passing across 7 test files (`npm run test -- --run`) — 23 pre-existing (6 files) + 12 new in `httpClient.test.ts` + 1 new in the new `AuthProvider.test.tsx`.
- **Frontend lint:** clean — 0 errors, 4 warnings, all four pre-existing (`react-refresh/only-export-components` on files that export a hook alongside a component: `AuthProvider.tsx`, `NotificationProvider.tsx`, `ThemeProvider.tsx`, `button.tsx`) and unrelated to this batch's diff.
- **Frontend format:** clean (`npm run format:check`).
- **Frontend typecheck:** clean (`npx tsc --noEmit`).
- Backend suite not run — this batch touches only `frontend/`, no backend file is part of its diff.

### Design Decisions

- **401 exclusion for tokenless requests, not a hardcoded endpoint path.** Rather than special-casing the literal `/api/v1/auth/login` path, the global handler only fires when the failing request had actually carried an `Authorization` header (i.e. `accessToken` was non-null at request time). This is a more general, principled condition than a path string: it correctly excludes the login endpoint's own credential-failure `401` (there's no session to expire — the user was never authenticated) while still firing for a genuine session-expiry `401` on any endpoint, present or future, without needing to enumerate exceptions.
- **Redirect via the existing `T73` `ProtectedRoute`, not an imperative router call.** `AuthProvider` sits above `RouterProvider` in the component tree (`AppProviders` composes `... > AuthProvider > children`, and `App.tsx` renders `<RouterProvider>` as that child), so it has no `useNavigate()` context of its own. Rather than reaching for the router singleton's imperative `.navigate()` (which would require importing `@/app/routes` into either `httpClient.ts` or `AuthProvider.tsx` — both reachable from `routes.tsx` through `ProtectedRoute`/`LoginPage`, creating a real static circular import) or a hard `window.location` navigation (which breaks in the packaged Electron app, since production loads `file://.../index.html` and `/login` isn't a file), clearing `AuthProvider`'s `currentUser` state was enough: `ProtectedRoute` already re-renders reactively on every auth-context change and already redirects to `/login` whenever `currentUser` is null. This reuses `T73`'s already-QA'd mechanism instead of inventing a second redirect path.
- **`ipcBridge.clearRefreshToken()` called directly from `httpClient.ts`, not routed through the `AuthProvider` handler.** `httpClient.ts` and `ipcBridge.ts` are both `infrastructure/`-layer siblings, so `httpClient` reaching into `ipcBridge` for its own "clear the persisted session" responsibility keeps that concern in the infrastructure layer, while the handler `AuthProvider` registers is scoped purely to React/app state — matching `docs/Architecture.md`'s frontend layer split.
- **`logout()` was extended to call `setAccessToken(null)` but not `ipcBridge.clearRefreshToken()`.** The `T71` authorization note flagged wiring `clearRefreshToken()` into `logout()` as an open question for "whichever task actually needs it." `T74`'s own approved scope names the *global 401 handler* as the place secure-session-clearing happens, not `logout()` itself (which remains unauthorized/unwired to any UI — that's `T75`'s territory). `setAccessToken(null)` in `logout()` was still necessary, but only to keep `httpClient`'s own module-level token state consistent with `AuthProvider`'s state (without it, a stale token would keep being attached to requests after `state.tokens` was already cleared) — a mechanical consistency fix, not new logout behavior.

### Problems Encountered

- `frontend/src/presentation/pages/LoginPage.test.tsx`'s existing full-replacement `vi.mock("@/infrastructure/api/httpClient", ...)` didn't include the two new exports `AuthProvider.tsx` now imports (`setAccessToken`, `setUnauthorizedHandler`), which made every test in that file fail with `No "setUnauthorizedHandler" export is defined on the mock`. Resolved by adding both as no-op `vi.fn()`s to the mock's return value — no test assertion changed, confirmed by re-running the full suite (all four `LoginPage` tests pass unchanged).
- A latent header-merge-order bug (see Tasks Implemented) was found while implementing the Authorization-header injection — the original `{ headers: {...}, ...init }` spread order meant a caller-supplied `init.headers` would have silently discarded the newly-added auto-injected `Authorization` header whenever a caller passed its own `headers` object (as `AuthProvider`'s `/me` call already did). Fixed as part of this batch (see Tasks Implemented) and covered by the new `"merges an auto-attached Authorization header with caller-supplied headers"` test.

### Deferred Work

- Wiring `ipcBridge.clearRefreshToken()` into `logout()` itself remains an open question, not resolved by this batch — flagged by `T71`'s own authorization note and left for whichever task wires `logout()` to real UI (likely `T75`).
- Automatic refresh-token exchange, retry-after-401, and token rotation remain explicitly unauthorized and unimplemented, per `T74`'s own scope.
- `T75` (current-user display + logout action in `MainLayout`'s header) and `T76+` remain explicitly out of scope and untouched.

### Future Considerations

- Once a real session-restore or silent-refresh flow is authorized (if ever), it will need to decide how it interacts with this batch's `hadAccessToken`-gated `401` exclusion and with `ipcBridge`'s now-complete `setRefreshToken`/`getRefreshToken`/`clearRefreshToken` trio (only `getRefreshToken` remains unused by any caller after this batch).
- `AuthProvider.test.tsx` exercises the real `httpClient` module (only `fetch` and, implicitly, `ipcBridge`'s `window.api`-absence path are relied upon) rather than mocking `httpClient` outright, deliberately — future tests that touch `AuthProvider` should keep doing this for anything exercising the global-401 wiring, since a fully mocked `httpClient` (as `LoginPage.test.tsx`/`ProtectedRoute.test.tsx` use) never exercises this batch's new logic at all.

### Reviewer Checklist

```
Reviewer Checklist

☑ Architecture preserved
☑ Existing design patterns followed
☑ Tests added
☑ Existing tests pass
☑ Documentation updated
□ ADR updated (if required) — no architectural decision rose to ADR-level; the router/redirect and layering choices are recorded above as Design Decisions instead
□ AI_BOOTSTRAP updated (if required) — N/A, no standing convention changed
□ PROJECT_STATE updated (if required) — out of scope for this role/session per explicit instruction; left to the Documentation Manager after QA
☑ No unrelated refactoring
☑ No scope creep
☑ Ready for QA
```

### QA Decision — T74 batch

- **Date:** 2026-08-20
- **Decision:** [ ] Approved | [x] Approved with comments | [ ] Rework required
- **Comments / Rework items:**
  - Approved with comments. (Note: Both non-blocking findings from T73 remain preserved above).