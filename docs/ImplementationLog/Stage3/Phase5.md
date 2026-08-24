------------------------------------------------

# Stage 3 – Phase 5

Status: In Progress

Started: 2026-08-24

Completed:

Related Tasks: T85

Related ADRs: ADR-0018 (D6 — Electron secure refresh-token storage; this phase changes only how
`preload.ts` is built, not the storage mechanism, IPC handlers, or exposed API surface D6
established)

Git Commit:

Pull Request:

Release:

------------------------------------------------

## Objective

Implement `T85`: investigate, then fix, the Electron preload script load failure discovered during
`T84`'s QA (`Unable to load preload script`, involving `./ipc/channels`, leaving `window.api`
undefined and `ipcBridge.isAvailable()` false) — a defect that predates `T84` and blocks `T84`'s own
required native-Electron verification, but sits outside `T84`'s authorized scope.

**Note on branch base:** this branch (`feature/T85-fix-electron-preload-load-failure`) is based on
`main` at `61a0f0f`, since `T84`'s implementation (PR #86) is not yet merged. `IMPLEMENTATION_QUEUE.md`'s
`T85` row (authorized in PR #87, also not yet merged at the time of this phase's work) was read
directly from its authorization branch/commit (`5536200`) — its content is documentation-only and
does not touch `electron/`, so this was sufficient to establish the authorized scope without waiting
on the PR merge. Flagged here per `FrontendDeveloper.md`'s Repository-First Rule ("if documentation
and implementation disagree, trust the code, then report the discrepancy") — the task instructions
that opened this phase asserted PR #87 was already merged; `git fetch` + `gh pr view 87` showed it was
still open. Reported to the project owner at the time; not silently resolved either way.

## Tasks Implemented

`T85` — both phases of its two-phase authorization:

- **Phase 1 (investigation, required before Phase 2):** confirmed live, in the real Electron
  runtime, that the failure is caused by Electron's sandboxed-preload module loader rejecting a
  local relative `require()` of another project file — not a build/path misconfiguration, not an
  Electron-version/platform-specific issue. See Design Decisions for the exact evidence.
- **Phase 2 (implementation, authorized only once Phase 1 confirmed the cause):** added an esbuild
  bundling step specifically for `electron/preload.ts`, so the compiled `dist-electron/preload.js`
  is a single self-contained file with `electron/ipc/channels.ts`'s content inlined at build time —
  no runtime local `require()` remains for the sandboxed preload loader to reject.

## Files Modified

- `package.json` — split `electron:build` into `electron:build:main` (unchanged `tsc -p
  electron/tsconfig.json`, still type-checking every file under `electron/`, including
  `preload.ts`) and a new `electron:build:preload` (`esbuild electron/preload.ts --bundle
  --platform=node --format=cjs --external:electron --outfile=dist-electron/preload.js`);
  `electron:build` now runs both in sequence, esbuild's bundled output overwriting tsc's
  multi-file `preload.js` with the single-file bundle. `electron:watch` updated to run both
  watchers concurrently (via the already-present `concurrently` devDependency) so preload changes
  keep rebuilding live in watch mode, matching the pre-existing behavior for `main.ts`/`channels.ts`.
  `electron:dev`, `electron:start`, `dev`, `build`, `dist` all unchanged (they already delegate to
  `electron:build`, which now does the right thing transparently).
- `package.json` / `package-lock.json` — added `esbuild` (`^0.28.2`) as a devDependency, the
  minimal, dependency-free bundler needed for the one file that actually requires bundling.

**Not modified:** `electron/main.ts`, `electron/preload.ts`, `electron/ipc/channels.ts`,
`frontend/src/app/providers/AuthProvider.tsx`, `frontend/src/infrastructure/ipc/ipcBridge.ts`,
backend, `electron-builder.yml` (its `files: [dist-electron/**/*, ...]` glob already picks up
whatever's on disk regardless of which tool produced it — verified, not assumed).

## Tests Added

None — this phase changes only the build pipeline that produces `dist-electron/preload.js`, not
any application source. No new unit-testable logic was introduced. Coverage instead comes from the
investigation/verification evidence in Design Decisions and Test Results below: a real Electron
process, launched twice (once failing, once succeeding), is stronger evidence for this specific
defect than a unit test could be, since the failure is inherent to Electron's own sandboxed-preload
loader, not to any of this project's own testable code.

## Test Results

**Automated (Phase 3):**
- `npm run test -- --run` (frontend, unaffected by this phase — sanity check): **43/43 passing**,
  8 test files.
- `npm run lint` (frontend): **0 errors**, 4 warnings, all four pre-existing
  (`react-refresh/only-export-components`, unrelated to this phase).
- `npx prettier --check "src/**/*.{ts,tsx}"` (frontend): clean.
- `npx tsc --noEmit` (frontend): clean.
- `npx tsc -p electron/tsconfig.json --noEmit`: clean — `preload.ts` still fully type-checked by
  `tsc`, even though esbuild (not `tsc`) produces its actual runtime output.
- `npm run build` (root — `electron:build` + `frontend` production build): succeeds cleanly;
  `dist-electron/preload.js` (1.5kb, single file) and `frontend/dist/` both produced without error.

**Native Electron (Phase 4) — see Design Decisions for the full before/after evidence.** Summary:
preload loads with no `preload-error`; `window.api` is defined with all four expected keys
(`getAppInfo`, `setRefreshToken`, `getRefreshToken`, `clearRefreshToken`); a real IPC round-trip
(`window.api.getAppInfo()`) returns genuine data from the unmodified main-process handler; a real
`window.api.getRefreshToken()` call reaches the unmodified main-process handler and resolves
(`null`, correctly, since no token is persisted in this environment) — proving `T84`'s restoration
path can now actually reach `getRefreshToken()`, the specific gap `T85`'s authorization named.

**Methodology disclosure:** this environment cannot visually display or screenshot a native
Electron `BrowserWindow`. Native-runtime evidence above was obtained by launching the real,
unmodified `electron.exe` binary against this project (`./node_modules/electron/dist/electron.exe
.`) and using `webContents.on("preload-error", ...)` / `webContents.executeJavaScript(...)` —
standard, documented Electron main-process APIs — to inspect the actual state of the actual
`BrowserWindow`'s actual renderer process from within the real running app, since no other
mechanism in this environment can observe it. This is direct observation of the real native window,
not a browser-tab simulation — but it is not the same as a person visually watching the window, and
is disclosed as such rather than implied to be more than it is.

## Design Decisions

- **Root cause, confirmed by direct reproduction, not assumed from the task's own hypothesis.**
  Launched the real, unmodified `electron.exe` against the project with a temporary
  investigation-only `preload-error` listener added to `main.ts` (reverted before any commit — see
  Problems Encountered). Result:
  ```
  [T85-DIAGNOSTIC] preload-error fired: ...dist-electron\preload.js Error: module not found: ./ipc/channels
      at preloadRequire (node:electron/js2c/sandbox_bundle:2:120320)
      at ...dist-electron\preload.js:4:20
      at runPreloadScript (node:electron/js2c/sandbox_bundle:2:120582)
      at executeSandboxedPreloadScripts (node:electron/js2c/sandbox_bundle:2:119861)
      ...
  [T85-DIAGNOSTIC] window.api probe: {"hasApi":false,"apiKeys":null}
  ```
  The stack trace's own frames (`preloadRequire`, `runPreloadScript`, `executeSandboxedPreloadScripts`,
  all inside Electron's internal `sandbox_bundle`) are Electron's own sandboxed-preload module
  loader — not Node's ordinary `require`, not this project's build output. This rules out a
  build/path misconfiguration on its own (the file demonstably exists on disk at the expected path;
  only the *inner* relative `require` from within the already-successfully-loaded `preload.js`
  fails) and rules out a narrower version/platform issue (the failure is Electron's own documented,
  general sandboxed-preload constraint, not something specific to a file or a typo).
- **Control experiment, to isolate the specific variable.** Temporarily rewrote `preload.ts` with
  `IpcChannels` inlined directly (no local relative `require`, only the pre-existing `require("electron")`
  that already worked) — same `sandbox: true` config, same file path, same everything else. Result:
  ```
  [T85-DIAGNOSTIC] window.api probe: {"hasApi":true,"apiKeys":["getAppInfo","setRefreshToken","getRefreshToken","clearRefreshToken"]}
  ```
  No `preload-error`. This is the deciding evidence: the only variable changed was removing the
  local relative `require`, and that alone fixed it — directly confirming `T85`'s authorized
  hypothesis (sandboxed-preload's restriction on local multi-file `require()`) rather than assuming
  it because the task's own assessment proposed it. Reverted immediately after (`git checkout --
  electron/preload.ts`), never committed.
- **Bundling only `preload.ts`, not `main.ts`.** `main.ts` runs in the (non-sandboxed) Electron main
  process, a full Node.js context where ordinary multi-file `require()` already works — confirmed by
  its own successful `require("./ipc/channels")` in every one of the launches above (the main
  process itself never errored; only the sandboxed preload's copy of the same import failed).
  Bundling `main.ts` too would be unnecessary scope beyond what `T85` authorized ("the minimal
  build-pipeline change needed to make `electron/preload.ts` load successfully").
- **esbuild over other bundlers.** No bundler existed in this project before this phase. esbuild was
  chosen for having zero peer dependencies, a single-binary install, and a one-line CLI invocation
  sufficient for one entry file — avoiding a heavier general-purpose bundler (webpack) or one this
  project doesn't already use anywhere else (the frontend's Vite could theoretically build the
  preload too, but wiring a second Vite config into the Electron-main build pipeline is
  meaningfully more machinery than one `esbuild --bundle` line for a problem this narrow).
- **`tsc` still type-checks `preload.ts`; esbuild only produces its runtime artifact.** `tsc -p
  electron/tsconfig.json`'s `include: ["**/*.ts"]` still covers `preload.ts`, so a real type error
  in it still fails the build — esbuild's own TS handling (fast transpile, not a full type-check)
  runs second and only replaces the *compiled output*, not the type-safety guarantee.
- **`electron/main.ts`'s existing token-storage handlers and `preload.ts`'s exposed API surface are
  both byte-for-byte unchanged** — confirmed directly (`diff <(git show main:electron/main.ts)
  electron/main.ts` → no difference; the bundled `dist-electron/preload.js`'s `contextBridge.exposeInMainWorld("api",
  api)` call exposes the identical four named functions, same names, same shapes). No defect was
  found in `main.ts`'s handlers during this investigation, so the "unless the implementation review
  demonstrates an actual defect there" exception in `T85`'s authorization was never triggered.

## Problems Encountered

- **Task instructions asserted PR #87 (T85's own authorization) was already merged into `main`;
  `git fetch` + `gh pr view 87` showed it open, not merged.** Resolved by reading the authorization
  content directly from its branch (a 2-line, documentation-only diff to `IMPLEMENTATION_QUEUE.md`,
  unrelated to `electron/`) rather than blocking on, or silently assuming, the merge state — flagged
  above per the Repository-First Rule rather than proceeding on an unverified premise.
- **This environment cannot visually observe a native `BrowserWindow`.** Addressed via
  `webContents.executeJavaScript`/`preload-error`-listener probes, run directly against the real,
  unmodified Electron binary — see Test Results' Methodology disclosure for the full honest
  accounting of what this does and doesn't prove.
- **Investigation and control-experiment code (the temporary `preload-error` diagnostic listener in
  `main.ts`, the temporary inlined-`IpcChannels` version of `preload.ts`) was never committed** —
  each was reverted via `git checkout --` immediately after capturing its evidence, confirmed clean
  via `git status --porcelain` before proceeding to the next step. The committed diff contains only
  the actual fix (`package.json`/`package-lock.json`).

## Deferred Work

- **T84's own required native-Electron verification** (login → reload → restart → invalid-token →
  logout) remains entirely outside this phase — `T85`'s authorization is explicit that this
  defect's fix only makes that verification *possible*, and that T84's real result must be recorded
  separately under T84's own row once its PR (#86) is actually run end-to-end in the native runtime.
  Not performed here, not claimed here.
- **`electron-builder`'s full packaging** (`npm run dist` — NSIS installer, code signing, etc.) was
  not run in this environment; `electron-builder.yml`'s `files` glob was verified by inspection to
  be format-agnostic (picks up whatever's in `dist-electron/` regardless of which tool produced it),
  and `npm run build` (the packaging step's own prerequisite) was verified to succeed cleanly. Full
  installer generation was judged unnecessary to prove this specific fix and outside what `T85`
  asked for.

## Future Considerations

- If a future task adds more local-file imports inside `preload.ts` (or splits it across multiple
  files again), the existing `esbuild --bundle` step already handles that transparently — no
  further build-pipeline change would be needed, since bundling inlines whatever the entry file's
  own import graph pulls in.
- If this project ever adds a second preload script (e.g. a separate one for a future secondary
  `BrowserWindow`), it would need its own `electron:build:preload`-style esbuild invocation — worth
  generalizing into a loop/glob at that point rather than duplicating the single-file command, but
  not needed yet with only one preload entry point today.

## Reviewer Checklist

```
☑ Architecture preserved
☑ Existing design patterns followed
□ Tests added — no application source changed; see Tests Added for why no new automated test
  applies to a build-pipeline-only fix, and Test Results for the investigation/verification
  evidence used in its place
☑ Existing tests pass
☑ Documentation updated
□ ADR updated (if required) — no new architectural decision; ADR-0018 D6's mechanism, IPC
  architecture, and exposed API surface are all unchanged, only how one file is compiled
□ AI_BOOTSTRAP updated (if required) — no standing convention/non-negotiable rule changed
□ PROJECT_STATE updated (if required) — not done by this role; synchronized only after a QA
  Decision exists (`docs/ImplementationLog/README.md`'s Documentation Ownership)
☑ No unrelated refactoring
☑ No scope creep
☑ Ready for QA
```

## QA Decision

```
□ Approved
☑ Approved with comments
□ Rework required
```

T85's authorized scope (bundle `electron/preload.ts` via esbuild so it loads under Electron's
sandboxed-preload constraint) is confirmed working in the actual native Electron `BrowserWindow`,
evidenced by `docs/ImplementationLog/Stage3/Phase4.md`'s native-Electron verification sections (both
the original T84 pass and the T84-rework re-verification pass): no `preload-error`, `window.api`
populated with exactly the four functions this phase's own Design Decisions name (`getAppInfo`,
`setRefreshToken`, `getRefreshToken`, `clearRefreshToken`), and `getRefreshToken()` specifically
confirmed reachable and returning real data through a live `/auth/refresh`/`/auth/me` round-trip
during T84's reload/restart checkpoints — the exact gap this phase's Objective names. Every
subsequent T84 checkpoint that depends on the IPC bridge being available (session restoration,
invalid-token handling, network-failure fallback) could only have produced its observed results if
this phase's fix genuinely holds; before this phase, the identical scenario produced
`window.api: undefined` and none of those checkpoints were reachable at all.

**Comment (non-blocking):** all native-Electron evidence for this phase comes from a combined
T84+T85 build, not an isolated T85-only build with T84's code absent — this role did not
independently launch a T85-alone Electron session, and does not claim to have. Disclosed rather than
glossed over, but this doesn't weaken the conclusion: T85's entire changed-file scope (`package.json`,
`package-lock.json`, both build-tooling only) has zero overlap with T84's files, and
`electron/preload.ts` itself — the file whose loading behavior is what's actually being verified — is
byte-identical regardless of whether T84's frontend changes are present. There is no plausible
mechanism by which T84's code presence could be responsible for `window.api` becoming populated; the
preload-loading fix is provably attributable to T85 alone. Automated build/lint/format/typecheck
results (Test Results above, independently re-run during T84's native-Electron QA sessions) also
passed cleanly for T85's specific changes.
