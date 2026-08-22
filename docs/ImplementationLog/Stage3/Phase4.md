------------------------------------------------

# Stage 3 – Phase 4

Status: In Progress

Started: 2026-08-22

Completed:

Related Tasks: T84

Related ADRs: ADR-0018 (D6 — Electron secure refresh-token storage; this phase consumes the
existing `safeStorage`/preload/IPC mechanism D6 established, it does not change it)

Git Commit:

Pull Request:

Release:

------------------------------------------------

## Objective

Implement `T84`: the missing renderer-side session-restoration path that `T82`'s live Electron
verification confirmed does not exist — an authenticated Electron session was lost on both a
renderer reload (`Ctrl+R`) and a full application restart, even though the refresh token was
already being persisted correctly via `safeStorage` (`T71`).

## Tasks Implemented

`T84` — Restore Electron session across renderer reload and full application restart. On
`AuthProvider` mount, when running inside Electron (`ipcBridge.isAvailable() === true`), read the
persisted refresh token, exchange it via the existing `POST /api/v1/auth/refresh` endpoint, fetch
`/api/v1/auth/me`, and populate `currentUser`/`tokens` — restoring the session without a fresh
login. All eight behaviors named in `T84`'s authorized scope are covered — see Design Decisions.

## Files Modified

- `frontend/src/infrastructure/ipc/ipcBridge.ts` — added `getRefreshToken()`, following the exact
  existing named/typed function pattern (`setRefreshToken`/`clearRefreshToken`), surfacing the
  `getRefreshToken` preload API that `T71` already exposed but nothing in the renderer consumed
  (the exact gap `T82`'s static-analysis note and `T84`'s authorization both named).
- `frontend/src/app/providers/AuthProvider.tsx` — added the restoration effect (`isInitializing`
  state + a mount-time `restoreSession()`), and extracted `login()`'s existing `/auth/me` fetch
  into a shared `fetchCurrentUser()` helper reused by both `login()` and restoration rather than
  duplicated.
- `frontend/src/app/ProtectedRoute.tsx` — renders the existing `LoadingSpinner` component while
  `isInitializing` is true, instead of redirecting to `/login`.
- `frontend/src/app/providers/AuthProvider.test.tsx` — new `getRefreshToken`/`setRefreshToken`
  mocks added to the file's shared `ipcBridge` mock; new `AuthProvider — session restoration on
  mount` describe block.
- `frontend/src/app/ProtectedRoute.test.tsx` — one new test for the `isInitializing` loading state;
  existing two tests given an explicit `isInitializing: false` for clarity (behavior unchanged).

## Tests Added

All in the new `AuthProvider — session restoration on mount` describe block
(`AuthProvider.test.tsx`) unless noted:

- `restores currentUser from a persisted refresh token and persists the rotated token` — proves
  the success path (A), and that the rotated refresh token `/auth/refresh` returns is re-persisted
  via `ipcBridge.setRefreshToken()` (the backend rotates on every refresh — see Design Decisions).
- `remains unauthenticated, with no network call, when no refresh token is persisted` — proves (D):
  no persisted token, no `fetch` call attempted at all.
- `clears the persisted token and remains unauthenticated when it is invalid, expired, or revoked`
  — proves (E): a structured `401` from `/auth/refresh` triggers exactly one
  `ipcBridge.clearRefreshToken()` call.
- `leaves the persisted token untouched and remains unauthenticated on a network failure` — proves
  (F): a thrown (non-`HttpError`) network failure does **not** clear the persisted token.
- `skips restoration entirely outside Electron (ipcBridge.isAvailable() === false)` — proves (H):
  `ipcBridge.getRefreshToken()` is never called in a browser tab.
- `does not redirect ProtectedRoute to /login while restoration is still in progress` — proves (G):
  with `ipcBridge.getRefreshToken()` deliberately left pending, `ProtectedRoute` shows neither
  `/login` nor protected content until restoration resolves.
- `ProtectedRoute.test.tsx`: `does not redirect to /login while session restoration is still in
  progress` — the same (G) behavior, isolated to `ProtectedRoute` via its existing `useAuth` mock.

## Test Results

`npm run test -- --run` (frontend): **50/50 passing** (43 prior + 7 new), 8 test files.
`npm run lint` (eslint): **0 errors**, 4 warnings — all four pre-existing
(`react-refresh/only-export-components` on `AuthProvider.tsx`, `NotificationProvider.tsx`,
`ThemeProvider.tsx`, `button.tsx`; the `AuthProvider.tsx` one already existed before this phase,
from its existing `useAuth()` export alongside the `AuthProvider` component — same category `T70`'s
QA record already disclosed, not newly introduced here). `npx prettier --check "src/**/*.{ts,tsx}"`:
clean. `npx tsc --noEmit`: clean, no errors.

Not independently re-verified in this environment: the actual native Electron `BrowserWindow`
(reload/restart) — this device-bridge session cannot launch or attach to one, per `T84`'s own
Verification requirement, which explicitly calls for that separately. See Problems Encountered.

## Design Decisions

- **Distinguishing "invalid token" from "network failure."** `/auth/refresh` failures are split by
  whether the thrown error is an `HttpError` (a real, structured HTTP response — e.g. `401` for a
  revoked/expired/unknown token) versus any other thrown value (a `fetch` failure before a response
  ever came back — offline, backend unreachable, DNS, etc.). Only the former clears the persisted
  token; the latter is deliberately left in place so the same still-possibly-valid token gets
  retried on the next launch instead of being discarded on a transient network blip. This directly
  implements `T84` items (5) and (6) as two distinct behaviors, not one.
- **Re-persisting the rotated refresh token.** `AuthService.refresh()` (backend, unchanged by this
  phase) revokes the presented refresh token and issues a new one on every call — confirmed by
  reading `backend/src/app/application/auth_service.py`'s `refresh()` before implementing. A
  restoration that fetched a new token pair but didn't call `ipcBridge.setRefreshToken()` with the
  new refresh token would leave the now-revoked old one on disk, working once and then permanently
  failing on the very next reload/restart. This was not spelled out explicitly in `T84`'s
  authorization text but follows directly from the existing, unmodified backend contract — flagged
  here per `FrontendDeveloper.md`'s "use engineering judgment and document it" instruction rather
  than silently assumed.
- **`isInitializing` as a single boolean, not a three-state enum.** The existing `AuthState` shape
  is a plain object with `useState`; a third `"restoring" | "authenticated" | "unauthenticated"`
  enum was considered but rejected as unnecessary — `isInitializing` plus the existing
  `currentUser`/`tokens` pair already expresses every state `T84` requires (initializing;
  initializing done + authenticated; initializing done + unauthenticated) without a new type or
  touching `login()`/`logout()`'s existing state shape beyond adding the one new field.
- **`ProtectedRoute` renders the existing `LoadingSpinner`, not a new component.** `HealthCheckPage`
  already establishes this project's loading-indicator pattern; reusing it (rather than inventing a
  bespoke spinner or a bare `null`) matches existing design patterns per `FrontendDeveloper.md`'s
  Implementation Rules, and gives the loading state a `role="status"` for free, letting the loading
  test assert on it directly.
- **`fetchCurrentUser()` extraction.** `login()`'s existing `/auth/me` fetch-and-unwrap logic is
  used verbatim by restoration; extracting it into one shared function (rather than duplicating the
  same three lines) is the "don't duplicate three-line blocks" judgment call, not a speculative
  abstraction — both call sites already exist and need it today.
- **`setUnauthorizedHandler`'s callback changed to a functional `setState` update.** The pre-existing
  callback replaced the whole state object (`setState({ currentUser: null, tokens: null })`), which
  would have silently dropped the new `isInitializing` field (implicitly resetting it to
  `undefined`) on every global-401 event. Changed to `setState((prev) => ({ ...prev, currentUser:
  null, tokens: null }))` so `isInitializing` is preserved untouched — a necessary correctness fix
  for the new field, not an unrelated change; the existing global-401 test (`AuthProvider — global
  401 handling`) continues to pass unchanged, confirming no observable behavior difference for that
  path.

## Problems Encountered

- **No live Electron `BrowserWindow` available in this environment.** Identical constraint `T79`
  and `T82` both already disclosed for this same device-bridge session. `T84`'s own Verification
  requirement explicitly names this as a separate, later step ("T84 must ultimately be verified in
  the actual Electron runtime, not merely a Chrome/browser tab") — the automated test suite above
  covers every branch of the restoration logic in isolation (mocked `ipcBridge`, mocked `fetch`),
  but the end-to-end reload/restart behavior in a real `BrowserWindow` has not been exercised from
  this session. Disclosed here rather than claimed.
- **Existing `ipcBridge` mock in `AuthProvider.test.tsx` didn't define `getRefreshToken`/
  `setRefreshToken` at all** (only `isAvailable`/`clearRefreshToken` existed before this phase).
  Adding them to the shared mock factory as plain `vi.fn()` (rather than leaving them undefined and
  relying on a thrown-`TypeError` being incidentally caught) was the correct fix — resolved before
  writing the new tests, not a lingering issue.

## Deferred Work

- **Real Electron `BrowserWindow` verification** — explicitly required by `T84`'s own Verification
  requirement, explicitly out of this phase's reach in this environment. Trigger: the project owner
  (or whoever has access to the packaged/dev Electron app) runs the same login → reload → restart →
  invalid-token → logout walkthrough `T82` already ran once, this time expecting restoration to
  succeed. Not a new task ID — this is `T84`'s own required closing verification step, the same
  relationship `T83` had to `T82`.

## Future Considerations

- If a future task changes the backend's refresh-rotation behavior (e.g. token reuse detection,
  refresh-token TTL changes), the "re-persist the rotated token" design decision above should be
  re-examined — it currently assumes every successful `/auth/refresh` call issues a new refresh
  token, per the backend contract read during this phase.
- The distinction between `HttpError` (clear token) and any other thrown error (keep token) means a
  persistently-unreachable backend leaves a possibly-already-expired token on disk indefinitely
  without ever clearing it via this path — acceptable today (nothing in `T84`'s scope asked for a
  retry-count or staleness policy), but worth naming if a future task adds one.

## Reviewer Checklist

```
☑ Architecture preserved
☑ Existing design patterns followed
☑ Tests added
☑ Existing tests pass
☑ Documentation updated
□ ADR updated (if required) — no new architectural decision; ADR-0018 D6 is consumed, not
  changed, so correctly none written
□ AI_BOOTSTRAP updated (if required) — no standing convention/non-negotiable rule changed
□ PROJECT_STATE updated (if required) — not done by this role; `PROJECT_STATE.json` is the
  Documentation Manager's document, synchronized only after a QA Decision exists
  (`docs/ImplementationLog/README.md`'s Documentation Ownership)
☑ No unrelated refactoring
☑ No scope creep
☑ Ready for QA
```

## QA Decision

```
□ Approved
□ Approved with comments
□ Rework required
```
