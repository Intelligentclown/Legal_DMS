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

**Rework batch (2026-08-24, QA finding: invalid-token restoration defect, see the Rework section
below for full detail):**

- `frontend/src/app/providers/AuthProvider.tsx` — `restoreSession()`'s invocation is now guarded by
  two new refs (`restorationStartedRef`, `isMountedRef`) so it runs its side-effecting work at most
  once per app startup, structurally, instead of relying solely on a per-invocation `cancelled`
  local variable. `ipcBridge.ts`, `ProtectedRoute.tsx`, `electron/*`, and the backend are untouched
  by this batch.
- `frontend/src/app/providers/AuthProvider.test.tsx` — new `AuthProvider — StrictMode-safe session
  restoration (T84 rework)` describe block.

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

**Rework batch — new `AuthProvider — StrictMode-safe session restoration (T84 rework)` describe
block:**

- `invalid refresh token: refresh is attempted at most once under StrictMode, and the app remains
  fully unauthenticated` — the regression test for the QA finding itself: renders under real
  `<StrictMode>` with a persisted invalid token and a `/auth/refresh` mock that always 401s, then
  asserts `refreshCallCount === 1` (not 2, matching QA's literal "two POST /auth/refresh responses
  returned HTTP 401" observation), `currentUser=null tokens=null`, and exactly one
  `clearRefreshToken()` call. **Confirmed to genuinely fail against the pre-rework code**
  (`refreshCallCount` was `2`) by temporarily reverting `AuthProvider.tsx` via `git stash` and
  re-running this test in isolation before restoring the fix — not merely asserted to be a
  regression test without checking.
- `successful restoration still works under StrictMode, with /auth/refresh called exactly once` —
  proves the fix doesn't regress the already-QA-passed success path: under `<StrictMode>`, a valid
  persisted token still restores `currentUser` and persists the rotated token, with `/auth/refresh`
  called exactly once (not twice, eliminating a redundant network call that was always latent even
  in the success case, just not the one QA's finding named).
- `does not throw or warn when the component unmounts while restoration is still in flight` — a
  genuine-unmount safety test (distinct from StrictMode's simulated cleanup): unmounts the component
  while `getRefreshToken()` is still pending, then resolves it, and asserts no
  "update on an unmounted component" React warning was logged. Passed even against the pre-rework
  code (the old `cancelled` flag already handled real unmounts correctly) — included as a permanent
  safety-net test for the new `isMountedRef` mechanism, not itself a regression test.

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

**Rework batch:** `npm run test -- --run`: **53/53 passing** (50 prior + 3 new), 8 test files.
`npm run lint`: **0 errors**, same 4 pre-existing warnings, none new. `npx prettier --check
"src/**/*.{ts,tsx}"`: clean. `npx tsc --noEmit`: clean. Native-Electron regression verification of
this specific fix has **not** been performed from this environment — see the Rework section's own
Native-Electron status below; this remains outstanding, to be performed by the operator per T84's
Phase 4 verification scenario.

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

## Rework — QA Finding: Invalid/Expired/Revoked Refresh-Token Restoration Defect (2026-08-24)

**QA finding.** Genuine native-Electron testing of `T84`+`T85` combined (disposable local branch
`qa/t84-t85-native-verification` = `1c29703` + `dd0a505`) passed six of seven scenarios. Scenario 7
(invalid/expired/revoked refresh token) **FAILED**: the operator persisted the literal string
`invalid-test-token-12345` as the refresh token, restarted the app, observed **two** `POST
/api/v1/auth/refresh` responses each returning `401`, yet the application displayed authenticated
protected content instead of `/login`. QA Decision: **Rework required**; final disposition:
**FAIL**. QA explicitly did not diagnose the mechanism, and named React 18 development StrictMode
(duplicate effect execution) only as an unconfirmed possible contributor, not an assumed cause.

**Investigation.** Traced the full `restoreSession()` lifecycle (mount → `isInitializing` →
`getRefreshToken()` → `/auth/refresh` → `HttpError` handling → `clearRefreshToken()` →
`fetchCurrentUser()` → `currentUser`/`tokens` state → `ProtectedRoute`) directly against the exact
code QA tested (`1c29703`, unchanged at investigation start). Confirmed `frontend/src/main.tsx`
wraps `<App />` in `<StrictMode>`, and `electron/main.ts`'s `isDev = !app.isPackaged` means the
operator's dev-mode test genuinely runs under React 18's development build, where StrictMode
double-invokes every effect (mount → cleanup → mount) specifically to surface effects unsafe to run
twice — exactly the shape of `restoreSession()`'s effect (a real, side-effecting network call).

Wrote a real `<StrictMode>`-wrapped Vitest reproduction (mocked `ipcBridge`/`fetch`, an always-401
`/auth/refresh`) to test this hypothesis directly rather than assume it. Result: **StrictMode does
reproduce a second, concurrent `/auth/refresh` call** (`getRefreshToken` and `/auth/refresh` each
invoked twice) — matching QA's own "two POST /auth/refresh responses returned HTTP 401" observation
precisely. However, under this exact, idealized reproduction, the pre-rework code's existing
per-invocation `cancelled` local variable **already correctly prevented false authentication**: the
StrictMode-cleaned-up (first) invocation's `cancelled` flag is set `true` before its own async chain
resolves, and its `if (!cancelled)` guard (both on the success-branch `setState` and the outer
`.finally()`) correctly discarded its result; the surviving (second) invocation reached the same
`401` and returned via the same `catch` branch. Final state in this reproduction was correctly
unauthenticated — the exact false-authentication interleaving QA observed live could not be
reproduced bit-for-bit under this test's idealized, synchronously-resolving mock timing.

**Root cause, as established, and why a fix was made despite not pinning the exact interleaving.**
Two things are true simultaneously, and this rework treats both as load-bearing: (1) StrictMode
double-invocation of `restoreSession()`'s effect is **real and confirmed** — it produces the exact
duplicate-network-call symptom QA observed, not merely a theoretical possibility; (2) the *exact*
mechanism by which that duplication produced visible false authentication in the real native
Electron runtime (with real, variable network/IPC latency, unlike this test's instant-resolving
mocks) could not be conclusively reproduced in isolation. Rather than leave a confirmed race class
in place on the theory that the pre-rework guard "should" be sufficient, the minimal, defensible fix
is to **eliminate the race class structurally** — guarantee `restoreSession()`'s side-effecting work
executes at most once per app startup, so there is no second, competing attempt for *any* timing to
race against, regardless of real-world latency this environment's tests cannot fully model. This
directly satisfies every invariant Phase 2 named ("HTTP 401 ... cannot be followed by authentication
from a stale or competing restoration attempt"; "currentUser/tokens cannot be populated by an
obsolete restoration attempt after a newer restoration attempt has failed") by construction, not by
continuing to reason about interleavings.

**Exact minimal fix.** `AuthProvider.tsx`'s restoration `useEffect` gained two `useRef`s:
`restorationStartedRef` (a one-shot gate: only the first effect invocation ever calls
`restoreSession()`) and `isMountedRef` (reset to `true` synchronously at the top of *every* effect
invocation's body, set `false` only by that invocation's cleanup). Because StrictMode's
mount→cleanup→mount sequence for a given effect happens entirely synchronously within React's commit
phase — before any awaited promise can resolve — `isMountedRef.current` is already back to `true`
(reset by the second invocation's synchronous body) by the time the *one* real `restoreSession()`
call reaches any of its `await` points, so its eventual `setState` calls remain safe. The previous
per-invocation `cancelled` local variable is removed; its two `if (!cancelled)` checks became `if
(isMountedRef.current)`. No other logic changed: the `HttpError`-vs-network-failure distinction,
token-clearing, token-rotation-persistence, and the success/failure branches are all byte-identical
to the pre-rework code. `ipcBridge.ts`, `ProtectedRoute.tsx`, `electron/main.ts`, `electron/preload.ts`,
T85's preload bundling, and the backend are all untouched.

**Regression tests** — see Tests Added's Rework batch above for the three new tests, including
confirmation (via a temporary `git stash` of the fix) that the two duplicate-call assertions
genuinely fail against the pre-rework code and pass only with the fix applied.

**Remaining limitation.** The exact interleaving that produced visible false authentication in the
live native-Electron run was not reproduced bit-for-bit in isolation, so this rework cannot claim
certainty that duplicate StrictMode invocation *alone*, unassisted by real-world network/IPC timing
this environment's mocks cannot fully replicate, was the complete mechanism. What *is* established
with certainty: the duplicate-call symptom QA directly observed is real, confirmed, and now
eliminated structurally rather than patched around. Native-Electron regression verification of this
specific fix (the Phase 4 scenario the rework instructions specify: invalid token → restart → 401 →
remains unauthenticated → `/login` shown → token cleared → fresh login → reload/restart still
restore) has not been performed from this environment and remains outstanding.

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
- **Rework batch:** the same native-Electron verification, now including the invalid-token scenario
  specifically (Phase 4 of the rework instructions) — not performed from this environment, remains
  the operator's next step once this rework is re-reviewed.

## Future Considerations

- If a future task changes the backend's refresh-rotation behavior (e.g. token reuse detection,
  refresh-token TTL changes), the "re-persist the rotated token" design decision above should be
  re-examined — it currently assumes every successful `/auth/refresh` call issues a new refresh
  token, per the backend contract read during this phase.
- The distinction between `HttpError` (clear token) and any other thrown error (keep token) means a
  persistently-unreachable backend leaves a possibly-already-expired token on disk indefinitely
  without ever clearing it via this path — acceptable today (nothing in `T84`'s scope asked for a
  retry-count or staleness policy), but worth naming if a future task adds one.

## Reviewer Checklist (original batch)

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

## QA Decision (original batch)

```
□ Approved
□ Approved with comments
☑ Rework required
```

QA finding: invalid/expired/revoked refresh-token restoration produced false authentication in the
live native-Electron runtime (two `POST /auth/refresh` `401` responses, yet authenticated protected
content shown). Full detail in the Rework section above. This decision is recorded here as the
historical fact it is (communicated to this role as the starting point of the rework batch below) —
not rendered by this role.

## Reviewer Checklist (rework batch)

```
☑ Architecture preserved
☑ Existing design patterns followed
☑ Tests added — 3 new tests, 2 of which are confirmed genuine regressions (fail against the
  pre-rework code, verified via a temporary git stash; see Tests Added's Rework batch)
☑ Existing tests pass — 53/53 (50 prior + 3 new), no existing test's assertions changed
□ Documentation updated — this phase log only; no other document required updating for this batch
□ ADR updated (if required) — no new architectural decision; the fix is an internal
  implementation-robustness change to an existing effect, not a new design decision requiring an ADR
□ AI_BOOTSTRAP updated (if required) — no standing convention/non-negotiable rule changed
□ PROJECT_STATE updated (if required) — not done by this role; see original batch's identical note
☑ No unrelated refactoring — `ipcBridge.ts`, `ProtectedRoute.tsx`, `electron/*`, T85's preload
  bundling, and the backend are all confirmed untouched (`git diff 1c29703 --stat` shows exactly
  `AuthProvider.tsx` and `AuthProvider.test.tsx`)
☑ No scope creep — no T86 created, T84's authorized scope not broadened, T85 not modified
☑ Ready for QA
```

**Limitation, disclosed rather than omitted:** the exact interleaving that produced QA's observed
false authentication was not reproduced bit-for-bit in isolated testing (see the Rework section's
own "Remaining limitation" for the full account) — the fix eliminates the confirmed race class
structurally, but this role cannot claim 100% certainty it was *the entire* mechanism. Native-Electron
regression verification of this specific fix remains outstanding (see Deferred Work).

## QA Re-Verification — Native-Electron Regression Testing (2026-08-24)

Performed by the QA Reviewer role, in the same session as this rework was submitted for review,
directly against commit `152ca81` (this rework, on `feature/T84-restore-electron-session`) combined
with `T85`'s preload fix (`dd0a505`, `feature/T85-fix-electron-preload-load-failure`) via a
disposable, unpushed local branch (`qa/t84-t85-rework-verification`), built and launched as the
actual native Electron `BrowserWindow`. This role has no tool capable of driving that window
directly; every runtime observation below was made by the project owner operating it live and
reported to this role in real time — none are inferred from source code or from the automated test
suite alone, consistent with `T84`'s own Verification requirement.

**Scenario-by-scenario results:**

1. Preload/IPC bridge — **PASS**. No preload-load error; `window.api` populated with `getAppInfo`,
   `setRefreshToken`, `getRefreshToken`, `clearRefreshToken`.
2. Login — **PASS**. Authenticated, protected content rendered.
3–10. Invalid/expired/revoked token regression (the critical scenario) — **PASS**. After persisting
   a deliberately invalid token (`await window.api.setRefreshToken("invalid-test-token-12345")`, via
   the DevTools console — not a code change) and a full application restart: exactly **one**
   `POST /api/v1/auth/refresh` request, returning `401` (one corresponding console resource-load
   error, not two as in the original QA finding); no `/auth/me` request followed; the application
   ended on `/login`, not protected content — directly contradicting the original defect. A
   subsequent restart showed no further `refresh` attempt at all, consistent with the invalid token
   having been cleared.
11. Successful persisted-token restoration — **PASS**. A full restart with a valid token restored
    `currentUser` without manual login; exactly one `/auth/me` request (not duplicated), its
    Network-panel Initiator stack confirmed as `fetchCurrentUser @ AuthProvider.tsx:27` ←
    `AuthProvider.tsx:99` (the restoration path, not `login()`), with a valid `Authorization: Bearer`
    header present on the request.
12. Renderer reload while authenticated — **PASS**. Session survived `Ctrl+R`, protected content
    remained visible, no errors.
13. Network/backend failure — **PASS**. With the backend stopped, a restart correctly fell back to
    `/login` (`net::ERR_CONNECTION_REFUSED`, a genuine network-level failure, distinguished from an
    HTTP error); after restarting the backend, a subsequent reload successfully restored the session
    — confirming the persisted token had been left intact during the failure, not wrongly cleared.
14. No-token startup — **PASS**. After logout, a full restart landed cleanly on `/login` with no
    `refresh` attempt and no console error.
15. Logout / subsequent reload/restart — **PASS**. Logout returned to `/login`, no error; a reload
    while at `/login` stayed at `/login`; no stale-token re-authentication.

**StrictMode duplicate-restoration invariant:** confirmed by direct request-count evidence above —
exactly one `401` in the invalid-token scenario and exactly one `/auth/me` in the successful-
restoration scenario, both of which were **two** under the pre-rework build in this same role's prior
verification pass — not asserted from source code alone.

**Governance note:** this rework commit is now confirmed genuinely pushed to
`origin/feature/T84-restore-electron-session` / PR #86 (`git fetch` + `gh pr view 86`, now 2
commits) — closing the "unpushed at time of testing" gap this role flagged in its own immediately
prior verification pass the same session. This also closes the Deferred Work item above ("Rework
batch: ... remains the operator's next step") — superseded by this section, not rewritten.

**Automated validation, independently re-run, not accepted from the Developer's report alone:**
`npm run test -- --run`: 53/53 passing, matching the report exactly. `npm run lint`: 0 errors, 4
pre-existing warnings (same category, no new ones). `npx prettier --check`: clean. `npx tsc
--noEmit`: clean. `npm run electron:build` (including `T85`'s esbuild preload-bundling step):
succeeds cleanly.

**Remaining observation (non-blocking):** on full-restart scenarios specifically (both this pass and
this role's prior one), the `refresh` request row itself was not visible in the DevTools Network
panel at capture time, despite strong corroborating evidence (console error counts, Initiator call
stacks, valid Bearer tokens, and the observed end states) that it genuinely occurred. Most likely a
DevTools-attach timing artifact, not a functional defect — noted for completeness, not treated as an
open finding.

## QA Decision (rework batch)

```
□ Approved
☑ Approved with comments
□ Rework required
```

The one comment above (DevTools Network-capture timing gap on full restarts) is informational only —
no implementation change is required. All native-Electron scenarios required by `T84`'s Verification
requirement and by this rework's own Deferred Work item passed, including the specific invalid-token
regression that produced the original `Rework required` finding. That defect is confirmed resolved
by direct live observation, not by source-code reasoning or automated tests alone.
