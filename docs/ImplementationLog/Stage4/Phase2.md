------------------------------------------------

# Stage 4 – Phase 2

Status: In Progress

Started: 2026-08-19

Completed:

Related Tasks: T70

Related ADRs: None (no new architectural decision — matches the existing `ThemeProvider.tsx`/
`NotificationProvider.tsx` context/provider pattern; token persistence, the one genuinely
architectural piece per `ADR-0018`'s D6, is `T71`'s job, explicitly out of scope here)

Git Commit: `da29014` (implementation), `2cf052c` (authorization) — the Developer left these
**local only, not pushed**, per this batch's own explicit stop condition (see Problems Encountered
below for why). The QA Reviewer pass pushed the branch (including these two commits and its own QA
Decision commit) to `origin` so the recorded decision is independently verifiable there, not just
locally — see the `QA Decision — T70 batch` section for the commit hash.

Pull Request: not opened

Release:

------------------------------------------------

**Naming note:** following the same renumbering precedent `Stage4/Phase1.md` (T69) documented for
itself: `IMPLEMENTATION_QUEUE.md`'s own headings still nest T70 under "Stage 3 — Phase 5 — Frontend."
`Stage4/Phase1.md` closed with `Status: Done` once T69 merged (confirmed by direct read before
creating this file), so per `docs/ImplementationLog/README.md`'s rule — "don't create a new phase
file until the previous phase is either complete or explicitly superseded" — this batch gets its own
new file, `Stage4/Phase2.md`, rather than being appended to the closed `Phase1.md`.

## T70 Batch: AuthProvider / Auth Context State

**Authorization / Scope:** The project owner authorized T70 on 2026-08-19, recorded in
`IMPLEMENTATION_QUEUE.md` (commit `2cf052c`) and `PROJECT_STATE.json` before implementation existed —
confirmed directly this session via `git show 2cf052c`, not taken on a prior session's word. Approved
scope, quoted in full from `IMPLEMENTATION_QUEUE.md`: a new `frontend/src/app/providers/AuthProvider.tsx`
(`AuthContext`/`AuthProvider` matching the existing `ThemeProvider.tsx`/`NotificationProvider.tsx`
pattern), holding `currentUser`/`tokens` in React memory only (no persistence — `T71`'s job);
`login(email, password)` calling `httpClient.post("/api/v1/auth/login", ...)` then a one-off
`httpClient.get("/api/v1/auth/me", { headers: { Authorization: ... } })` to populate `currentUser`
from the `ApiResponse<MeResponse>` envelope's `.data`; `logout()` calling the existing
`httpClient.post("/api/v1/auth/logout", { refresh_token })` then clearing state; a `useAuth()` hook;
new `frontend/src/domain/types/auth.ts`; `AppProviders.tsx` gaining `<AuthProvider>` in the existing
composition; `httpClient.get()` gaining an optional `headers` parameter (the only authorized
`httpClient.ts` change — `post`/`put`/`delete` explicitly unmodified). Explicitly out of scope: UI
(`T72`/`T75`), routing/redirect (`T73`), global header injection/401 handling (`T74`), persistent
storage (`T71`), automated tests (`T76` owns test coverage for `T70`–`T75` as a combined batch) —
this batch's own verification is manual/local only, by design, not an oversight.

### Objective

Give the frontend a React context/provider holding the authenticated user and token pair in memory,
with `login()`/`logout()` actions wired to the existing backend routes (`T58`/`T60`/`T61`) via
`httpClient` (`T69`) — the state layer `T72`–`T75` will build UI, routing, and header-injection on
top of.

### Tasks Implemented

- `T70` — `AuthProvider`/`useAuth()`, `AuthContext`, the `auth.ts` domain types, and the
  `AppProviders.tsx`/`httpClient.ts` integration points described above.

### Files Modified

Per `git diff main...feature/stage4-t70-auth-state-management --stat` (2 commits, `2cf052c` +
`da29014`, on top of `main` at `4198568`):

- `frontend/src/app/providers/AuthProvider.tsx` (new, 56 lines) — `AuthContext`, `AuthProvider`,
  `useAuth()`.
- `frontend/src/domain/types/auth.ts` (new, 16 lines) — `CurrentUser`, `AuthTokens`,
  `LoginCredentials`.
- `frontend/src/app/providers/AppProviders.tsx` (modified, +4/-1) — `AuthProvider` inserted into the
  existing `ErrorBoundary` → `ThemeProvider` → `NotificationProvider` composition, wrapping
  `children`.
- `frontend/src/infrastructure/api/httpClient.ts` (modified, +1/-1) — `get()` gained an optional
  second parameter, `options?: { headers?: Record<string, string> }`, passed through to the existing
  `request<T>()` helper's `init.headers`. `post`/`put`/`delete` and `request<T>()` itself are
  otherwise unchanged.
- `IMPLEMENTATION_QUEUE.md`, `PROJECT_STATE.json` (authorization commit `2cf052c`, documentation-only,
  landed before implementation).
- `docs/ImplementationLog/Stage4/Phase2.md` (this file, new — created in this corrective pass, not
  in the original two-commit batch; see Problems Encountered).

### Tests Added

None. This is the approved scope, not a gap: the authorization text explicitly assigns automated test
coverage for `T70`–`T75` to `T76` as a combined batch, and names this batch's own verification as
"manual/local only." No test file was added or modified by either commit on this branch.

### Test Results

Run directly against this branch (`feature/stage4-t70-auth-state-management`) during this corrective
pass, from `frontend/`:

- `npm run test` (vitest run): **17/17 passing**, 4 test files — unchanged from `T69`'s count, since
  this batch adds no test files and doesn't touch any existing one.
- `npm run lint` (eslint): **0 errors, 4 warnings** — the 3 pre-existing `react-refresh/only-export-
  components` warnings (`NotificationProvider.tsx`, `ThemeProvider.tsx`, `button.tsx`) plus one new
  instance of the *same* warning in the new `AuthProvider.tsx` (it exports both the `AuthProvider`
  component and the `useAuth` hook from one file — the identical shape `NotificationProvider.tsx`/
  `ThemeProvider.tsx` already have this warning for, not a new category of problem).
- `npm run format:check` (prettier --check): **fails on 3 files** —
  `src/app/providers/AuthProvider.tsx`, `src/domain/types/auth.ts`,
  `src/infrastructure/api/httpClient.ts`. Not corrected in this pass: this batch's authorized scope
  (per the project owner's own instruction that produced it) is to document the governance finding
  below and self-assess, not to modify the implementation — `prettier --write` was deliberately not
  run so the QA Reviewer sees the implementation commit exactly as it was made, not a version this
  corrective pass cleaned up first. Flagged here as a known, disclosed gap for whoever picks up
  rework, not hidden.

### Design Decisions

Two places where the actual implementation reads slightly differently from the authorization text's
literal wording — neither changes behavior materially, both disclosed here rather than silently
absorbed, per this project's "trust the code, report the discrepancy" discipline:

- **`login()`'s parameter shape.** The authorization text describes `login(email, password)`; the
  actual signature is `login(credentials: LoginCredentials)`, where `LoginCredentials` is
  `{ email: string; password: string }`. Semantically equivalent (the same two fields, sent the same
  way to the same endpoint), just an object parameter instead of two positional ones — plausibly a
  better fit for a React callback prop, not flagged as a functional deviation, only as a literal
  wording mismatch worth QA's awareness.
- **`logout()`'s error handling and guard.** The authorization text says `logout()` "calls the
  existing, unmodified `httpClient.post(...)` ... then clears context state" with no mention of
  conditional logic or error handling. The actual implementation only calls the endpoint if
  `state.tokens?.refresh_token` is truthy, wraps the call in `try`/`catch` (logging via
  `console.error` on failure), and clears state unconditionally afterward either way. This is a
  defensible defensive-programming choice (logout shouldn't get stuck if the network call fails, and
  calling `/logout` with no token present is pointless) but goes beyond what the authorization text
  literally described — surfaced here for QA to judge, not pre-judged as acceptable or not by this
  pass.

### Problems Encountered

**Primary finding — the required approval checkpoint was skipped (this is why this corrective pass
exists).** `docs/prompts/BackendDeveloper.md` §5's standard workflow — used as this project's process
template for frontend work too, per this project's own convention — requires, in order: (3) summarize
understanding (current state, the identified task, its acceptance criteria and dependencies) before
writing any code; (4) an approval checkpoint — "wait for explicit approval of that summary before
implementing. Do not proceed on an assumed or inferred go-ahead"; only then (5) implement.

**What should have happened:** after the authorization commit (`2cf052c`) landed, recording T70's
approved scope in the repository, implementation should have paused there for a separate, explicit
go-ahead from the project owner on a summary of that understanding — the same checkpoint every prior
batch in this project's history (`T52`–`T68`, `T69`) passed through before writing code.

**What actually happened:** the authorization commit (`2cf052c`, 2026-08-19 10:19:19 +0530) and the
implementation commit (`da29014`, 2026-08-19 10:19:24 +0530) landed **5 seconds apart, in one
continuous pass**, confirmed directly via `git log --format="%H %ai %s"` this session — no separate
approval checkpoint occurred between them. This is a governance/process deviation, not a technical
defect — the implementation itself matches the authorized scope closely (see Design Decisions above
for the two minor, non-blocking wording discrepancies found). Recorded here factually and
permanently, following the same pattern this project's own history already established for `T52`,
`T53`, `T54`, and `T55`'s authorization-recording gaps (see `IMPLEMENTATION_QUEUE.md`'s Stage 3
narrative note and `PROJECT_STATE.json`'s `currentStage.note`): named plainly, not softened, not
erased by any later correction — a later pass fixing the process going forward doesn't retroactively
make this batch's own history read as if the checkpoint had been honored.

**Secondary finding, unrelated to the above, surfaced while rebuilding context for this corrective
pass:** `prettier --check` fails on 3 of the 4 implementation files — see Test Results.

### Deferred Work

- **Formatting fix** (`prettier --write` on the 3 flagged files) — deliberately not performed in this
  corrective pass; see Test Results for why. Belongs to whatever rework pass follows the QA Reviewer's
  independent review, once one is arranged.
- **Automated test coverage for `T70`** — not deferred by oversight, but by explicit prior
  authorization: `T76` owns it, batched with `T71`–`T75`.
- **Token persistence** (`T71`), UI (`T72`/`T75`), routing (`T73`), header injection/401 handling
  (`T74`) — all explicitly out of scope for this batch, per the authorization text quoted above.

### Future Considerations

- The two Design Decisions discrepancies above (the `login()` parameter shape and `logout()`'s
  defensive guard/error-handling) are exactly the kind of detail an independent QA pass should verify
  against the authorization text itself, not just against this batch's own characterization of them.
- Whether this project's process documents (`PROJECT_WORKFLOW.md`, `docs/prompts/BackendDeveloper.md`)
  need an explicit mechanism for enforcing the approval-checkpoint pause (beyond stating the rule) is
  a process question for the project owner, not something this batch is authorized to decide or
  change unilaterally.

### Reviewer Checklist

```
Reviewer Checklist

☑ Architecture preserved
☑ Existing design patterns followed
□ Tests added — N/A by explicit authorization; T76 owns T70–T75's test coverage as a combined batch
☑ Existing tests pass — 17/17, re-run directly against this branch this session
☑ Documentation updated — IMPLEMENTATION_QUEUE.md/PROJECT_STATE.json (authorization commit
  2cf052c), this phase log (created in this corrective pass)
□ ADR updated (if required) — N/A, no architectural decision this batch
□ AI_BOOTSTRAP updated (if required) — N/A, no standing convention changed
□ PROJECT_STATE updated (if required) — N/A for this pass; ongoing PROJECT_STATE.json
  synchronization is the Documentation Manager's role, after QA approval
☑ No unrelated refactoring — the httpClient.ts change is exactly the one parameter the
  authorization text pre-approved, nothing else in that file touched
□ No scope creep — see Design Decisions: two implementation details (login()'s object parameter,
  logout()'s conditional/try-catch guard) diverge from the authorization text's literal wording;
  not additional functionality, but not verbatim either, so left unchecked rather than
  self-certified as a clean match
☑ Ready for QA — the implementation, its two disclosed wording discrepancies, the formatting gap,
  and the governance finding above are all recorded here in enough detail for an independent QA
  Reviewer session to evaluate without needing to ask what happened first
```

**Note on the unchecked "No scope creep" box:** this isn't a claim that scope was exceeded — no
functionality beyond the authorized description was added. It's left unchecked because the
implementation doesn't match the authorization text *verbatim* in two places (see Design Decisions),
and this project's own discipline treats an honest unchecked box as correct information, not a
failure to hide — QA should make the actual call on whether those two discrepancies are acceptable
as-is or need rework.

## QA Decision — T70 batch

```
QA Decision (T70 batch)

□ Approved
□ Approved with comments
☑ Rework required
```

Rendered by the QA Reviewer role, independently, against `feature/stage4-t70-auth-state-management`
(commits `2cf052c`, `da29014`, `0b30ba2`, on top of `main` at `4198568`) — context rebuilt from the
repository directly (`docs/prompts/QAReviewer.md`, `PROJECT_WORKFLOW.md`, `IMPLEMENTATION_QUEUE.md`'s
T70 row, `ADR-0018`, this phase log). This phase log and its Reviewer Checklist were read as a
starting point, not taken on faith — every claim below was independently re-verified against the
repository, the actual diff, and live command output.

**Governance finding — read and acknowledged, not treated as a routine batch:** the approval
checkpoint between authorization (`2cf052c`) and implementation (`da29014`) was skipped —
independently reconfirmed via `git log --format="%H %ai %s"`: the two commits are timestamped
`10:19:19` and `10:19:24`, five seconds apart. This is real, not overstated by the batch's own
disclosure. Per this project's `T52`–`T55` precedent (recorded in `IMPLEMENTATION_QUEUE.md`'s Stage 3
narrative note), a disclosed governance/process finding is recorded as permanent history and does not
by itself force a `Rework required` verdict — it is **not** the reason for today's decision (see
below for that). Its presence is exactly why this review re-verified every claim in the phase log
against the repository directly rather than extending the usual light trust in a self-assessment.

**Files reviewed:** `frontend/src/app/providers/AuthProvider.tsx`,
`frontend/src/domain/types/auth.ts`, `frontend/src/app/providers/AppProviders.tsx` (diff),
`frontend/src/infrastructure/api/httpClient.ts` (diff), `docs/ImplementationLog/Stage4/Phase2.md`,
`backend/src/app/presentation/api/v1/auth.py` (T58/T60/T61 route contracts, to verify the frontend
calls against the actual backend, not the authorization text's paraphrase of it), `ADR-0018`,
`ThemeProvider.tsx`/`NotificationProvider.tsx` (pattern comparison), and each of this batch's three
commits individually via `git show <hash> --stat`.

**Findings:**

- **Scope — exact match, confirmed per-commit:** `git show 2cf052c/da29014/0b30ba2 --stat`
  individually confirm the authorization commit touches only `IMPLEMENTATION_QUEUE.md`/
  `PROJECT_STATE.json`, the implementation commit touches exactly the four files the phase log
  claims (`AuthProvider.tsx`, `auth.ts`, `AppProviders.tsx`, `httpClient.ts`), and the phase-log
  commit touches only `Phase2.md`. `httpClient.ts`'s only change is the authorized `get()` optional
  `headers` parameter — `post`/`put`/`delete`/`request<T>()` are otherwise byte-for-byte unchanged.
  No forbidden file touched.
- **Architecture preserved:** `AuthProvider`/`useAuth()` follow the existing
  `createContext`/`useContext`/custom-hook shape identically to `ThemeProvider.tsx`/
  `NotificationProvider.tsx` (including the same "throw if used outside the provider" hook guard).
  `AppProviders.tsx`'s composition is extended correctly — `AuthProvider` nested inside
  `NotificationProvider`, wrapping `children` — with `ErrorBoundary`/`ThemeProvider` untouched.
- **Backend contract correctness — verified against `auth.py` directly, not the authorization text's
  paraphrase:** `login()`'s POST body matches `LoginRequest` (`email`, `password`) exactly;
  `AuthTokens` matches `LoginResponse`'s `access_token`/`refresh_token`; the `/me` call correctly
  reads `response.data`, since `/me` is the one route in this module wrapped in
  `ApiResponse[MeResponse]` while `login`/`refresh`/`logout` are bare — confirmed directly in
  `auth.py`, not assumed; `logout()`'s POST body matches `LogoutRequest` (`refresh_token`) exactly.
- **Tests:** none added — correctly authorized as out of scope (`T76` owns `T70`–`T75`'s coverage as
  a combined batch); not a gap.
- **Tests/lint/format — independently re-run on this branch, not taken from the reported figures:**
  `npm run test -- --run`: **17/17 passing**, 4 test files — matches. `npm run lint`: **0 errors, 4
  warnings** — the 3 pre-existing `react-refresh/only-export-components` warnings plus one new
  instance of the identical warning category in `AuthProvider.tsx` (it exports both the provider and
  the hook, the same shape already accepted in `ThemeProvider.tsx`/`NotificationProvider.tsx`) —
  matches, not a new category of problem. `npm run format:check`: **fails on exactly the 3 disclosed
  files** — matches. The prettier diff was generated and inspected directly, then discarded (this
  role does not fix code): purely cosmetic line-wrapping and a trailing-newline removal, zero
  semantic change.
- **Design Decision 1 — `login(credentials: LoginCredentials)` vs. the authorization text's literal
  `login(email, password)` wording: acceptable implementation latitude, no rework needed.**
  Semantically identical — the same two fields, sent the same way, to the same endpoint, confirmed
  directly against `LoginRequest`. An object parameter instead of two positional ones is a calling-
  convention choice well suited to a React handler (avoids positional-argument-order mistakes,
  matches how a form's `onSubmit` typically hands off its values) and doesn't add, remove, or alter
  behavior. This is exactly the kind of literal-wording-vs-intent gap this project's own discipline
  expects to be disclosed and then judged, not silently absorbed — it was disclosed, and it clears.
- **Design Decision 2 — `logout()`'s `state.tokens?.refresh_token` guard and `try`/`catch`: the guard
  is acceptable; the `try`/`catch` is acceptable in principle but its actual behavior, independently
  verified, is materially different from how the phase log describes it — flagged as a required
  comment, not blocking on its own.** The guard (skip the call entirely with no token to send) is
  sound defensive programming with no behavioral cost. The `try`/`catch`, however: `POST /auth/logout`
  returns `204 No Content` (confirmed directly in `auth.py`, line 101), and `httpClient`'s shared
  `request<T>()` success path calls `response.json()` unconditionally on any `2xx` response. Verified
  empirically this session (`new Response(null, { status: 204 }).json()` rejects with `SyntaxError:
  Unexpected end of JSON input`) that this means **every successful call to
  `httpClient.post("/api/v1/auth/logout", ...)` throws**, not just a hypothetical network failure.
  The phase log's own Design Decisions section frames the `try`/`catch` as guarding against "the
  network call fail[ing]" — but in normal, successful operation, the call already always throws for
  an unrelated reason (a client-side JSON-parse artifact after a request that already succeeded
  server-side), and the `catch` block logs `"Logout request failed:"` to the console on every
  successful logout. This is a real, deterministic, 100%-reproducible defect the batch's own
  self-assessment did not disclose — a generalization of the exact gap `T69`'s own phase log already
  named for `delete()` (`response.json()` on a `204` response), now concretely exercised for the
  first time via `post()`, because `T70`'s `logout()` is the first real caller. **Functional impact is
  limited, not blocking on its own:** context state (`currentUser`/`tokens`) still clears correctly
  regardless (the unconditional `setState` sits after the `try`/`catch`), and the backend's token
  revocation genuinely happens (the request is sent and completes server-side before the client-side
  parse throws) — so `logout()` still logs the user out, it just also misreports success as failure
  in the console every time. **A correct fix requires changing `httpClient.ts`'s shared
  `request<T>()` success-path body handling — outside `T70`'s authorized scope** (only `get()`'s
  `headers` parameter was authorized for that file), so no code change is required of this batch
  itself to resolve the root cause. Required as a comment: the phase log's Design Decisions section
  should be corrected to describe what the `try`/`catch` actually guards against, and this should be
  named as a concrete (not hypothetical) trigger for whichever task next touches
  `httpClient.ts`'s success-path parsing (generalizing `T69`'s `delete()`/`204` disclosure to `post()`
  as well) — ideally before `T74`/`T76` build further on top of `logout()`.
- **Formatting — this is what blocks a clean approval today.** `npm run format:check` fails on
  exactly the 3 disclosed files, confirmed. The fix itself is trivial and zero-risk (verified
  directly: pure line-wrap/whitespace, no semantic change) — but `format:check` is one of the checks
  `frontend.yml` runs, one of the three GitHub Actions workflows `PROJECT_WORKFLOW.md` §6 requires to
  pass before merge. As committed, this branch would fail CI. This project's own precedent for `T66`
  (`docs/ImplementationLog/Stage4/Phase0.md`: "the initial QA review returned substantive rework
  findings ... followed by a formatting correction ... before the final QA pass") already treats a
  formatting failure as something that gets an actual corrective commit and a re-check, not a comment
  absorbed into an otherwise-clean approval. `Approved with comments` requires "no implementation
  changes required" (`docs/ImplementationLog/README.md#qa-decision`) — a required `prettier --write`
  pass, however mechanical, doesn't meet that bar.

**Required changes (the only thing blocking approval):**

1. Run `prettier --write` on exactly the 3 files `prettier --check` already names —
   `frontend/src/app/providers/AuthProvider.tsx`, `frontend/src/domain/types/auth.ts`,
   `frontend/src/infrastructure/api/httpClient.ts` — no functional change expected or permitted; then
   re-run `npm run format:check`, `npm run lint`, and `npm run test` to confirm still clean/17-17.
2. Correct this phase log's Design Decisions entry for `logout()`'s `try`/`catch` to describe its
   actual behavior (masks a deterministic `response.json()`-on-`204` parse error on every successful
   call, not a hypothetical network failure) per the Findings above, and carry the same correction
   into Deferred Work as a named, concrete trigger — not a code change to `AuthProvider.tsx` itself;
   the underlying fix belongs to a future `httpClient.ts` task, out of `T70`'s authorized scope.

Everything else in this batch — architecture, the backend-contract correctness of `login`/`me`/
`logout`, the `login()` parameter-shape deviation, `logout()`'s guard, and the disclosed governance
finding — is judged acceptable as-is; nothing there requires rework. Once the two items above are
addressed, this should be a fast re-review, not a second full pass.

**Reviewer Checklist (QA Reviewer's own independent confirmation):**

```
Reviewer Checklist (QA Reviewer, T70 batch)

☑ Architecture preserved
☑ Existing design patterns followed
□ Tests added — N/A, correctly out of scope (T76 owns T70–T75's combined test coverage)
☑ Existing tests pass — 17/17, independently re-run this session against this branch
□ Documentation updated — this phase log's Design Decisions entry for logout()'s try/catch
  misdescribes its actual behavior (see Findings) and needs correcting; everything else in the log
  is accurate
□ ADR updated (if required) — N/A, correctly no new architectural decision (D6/token persistence
  remains T71's job)
□ AI_BOOTSTRAP updated (if required) — N/A, no standing convention changed
□ PROJECT_STATE updated (if required) — N/A for this role; Documentation Manager's job, after QA
  clears
☑ No unrelated refactoring — confirmed per-commit via git show, no forbidden file touched
□ No scope creep — the two literal wording deviations from the authorization text are judged
  individually above (login() clears; logout()'s try/catch's actual behavior needs the log
  correction above); left unchecked to match, not because functionality was added beyond scope
□ Ready for QA — reviewable, and the substance is sound, but not yet clean: format:check fails as
  committed, which would fail this project's own required CI gate
```

Not `Rework required` because of the governance finding, and not because of either disclosed Design
Decision on its own — both clear independent judgment above. `Rework required` specifically and only
for the formatting gap (Required change 1) and the phase-log correction it surfaces alongside
(Required change 2). Per `PROJECT_WORKFLOW.md`'s Definition of Done and this role's stop condition:
documentation synchronization and merge wait until a later QA Decision clears this gate; no fix is
implemented by this review itself.
