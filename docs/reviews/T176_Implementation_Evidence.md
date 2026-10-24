# T176 Implementation Evidence

**Task:** T176 — Packaged Electron Renderer Asset-Path Remediation
**Authorization:** Issue #365; protected authorization PR #366
**Protected baseline:** `614cf79864aad2525539a3059dbe2787019ad8ed`
**Execution date:** 2026-10-24 (Asia/Kolkata)
**Candidate commit:** Pending implementation commit and PR publication; native visual verification is
an explicit evidence limitation for Independent QA.

## Original Reproduction and Root Cause

T175 recorded a blank packaged Electron renderer. Production Electron calls `BrowserWindow.loadFile()` for `frontend/dist/index.html`, using `file://`. Before remediation, Vite had no production `base`, so it emitted root-absolute asset references such as `/assets/index-….js`; under `file://`, these resolve at the filesystem root rather than beside `index.html` in `app.asar`.

After the asset remediation, a user-provided packaged-app screenshot proved that the renderer was now loading but exposed a second file-protocol boundary: `createBrowserRouter()` interpreted the absolute on-disk `index.html` pathname as an application route and rendered React Router's `404 Not Found` error page. The packaged path now uses `createHashRouter()` exclusively for the `file:` protocol, so startup resolves through `index.html#/` and the existing unauthenticated guard can navigate to `#/login`. HTTP(S) browser builds retain `createBrowserRouter()`.

## Configuration Change and Artifact Evidence

The root Electron packaging build now invokes the frontend build as `vite build --base=./`.
This emits `src="./assets/index-BKZeOrnZ.js"` and
`href="./assets/index-Bm7Yee9M.css"`, both present in `frontend/dist/assets`. The direct
frontend web build remains unchanged and emits its normal root-absolute `/assets/...` references.

`createAppRouter()` selects hash routing only for a `file:` protocol. Its focused regression test proves the generated login href is `#/login` for packaged Electron and `/login` for HTTPS browser use.

The new `scripts/verify_packaged_renderer_assets.cjs` rejects root-absolute local `src`/`href` values and missing local references. It is wired into the root `build` command and existing release-build workflow.

`npx electron-builder --win --dir --config.directories.output=release/t176-win-router`
successfully produced `release/t176-win-router/win-unpacked`. Its `app.asar` contains
`\\frontend\\dist\\index.html`, `\\frontend\\dist\\assets\\index-9UILPt29.js`, and
`\\frontend\\dist\\assets\\index-Bm7Yee9M.css`.

## Regression Results

| Check                                                                                                 | Result                                                                               |
| ----------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| `npm run build`                                                                                       | Passed, including the asset verifier (3 local references; all relative and present). |
| `npx vitest run src` (from `frontend/`)                                                               | Passed: 42 files, 372 tests.                                                         |
| `npx vitest run src/app/routes.test.ts` (from `frontend/`)                                            | Passed: 2 files, 14 tests, including file- and HTTPS-protocol router selection.      |
| `npx eslint src vite.config.ts vitest.config.ts` (from `frontend/`)                                   | 0 errors; 4 pre-existing Fast Refresh warnings.                                      |
| `npx prettier --check src package.json vite.config.ts vitest.config.ts index.html` (from `frontend/`) | Passed.                                                                              |
| `npx electron-builder --win --dir --config.directories.output=release/t176-win-router`                | Passed; unpacked Windows x64 package produced.                                       |
| Direct `npm --prefix frontend run build`                                                              | Passed and retained root-absolute web asset paths.                                   |
| `npm --prefix frontend run dev -- --host 127.0.0.1`                                                   | Passed; ready in 447 ms and returned HTTP 200 with the application title.            |

## Native Windows Package Attempt and Blocker

`release/t176-win-router/win-unpacked/Legal Document & Matter Management System.exe` was packaged.
Its Electron processes were responsive and it owned a native top-level window titled
`Legal Document & Matter Management System`. Runtime/build identifiers: Windows `10.0.26300`,
Electron `43.3.0`, Node `v24.15.0`, npm `11.12.1`, and electron-builder `26.15.3`.

However, the session's Windows computer-use bridge returned no native application surfaces while
the window was open (`apps: []`). It therefore could not observe the renderer, inspect
DevTools/network logs, or confirm the login screen. Archive inspection, process survival, and a
window title are not substitutes for those observations.

**Evidence limitation:** native login-screen and missing-asset verification remains unproven. T175
remains Authorized/not Done, and no T176 completion or closeout status is claimed.

## Scope and Remaining Work

Only Electron-packaging build configuration, Electron-specific route selection, a build artifact verifier, build wiring, focused tests, and this evidence record changed. No business logic, API, schema, migration, authentication/session
architecture, ADR, queue, calendar, acceptance status, forecast, or T175 status changed.

Independent QA must expose native windows to the computer-use bridge (or use a supported interactive
Windows operator) and visually confirm the login screen plus absence of missing-asset errors, then
record the observed result. The unscoped frontend test/lint/format commands are also contaminated
by a nested `frontend/.kilo/worktrees/buttery-eggplant` checkout: Vitest reports that checkout as a
no-suite failure; ESLint reports 179 parser errors from duplicate TypeScript roots; and Prettier
checks its unrelated files. The focused commands above exclude that pre-existing nested checkout.
