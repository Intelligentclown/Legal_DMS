"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");
const { isReleaseBuildRelevant } = require("../release_build_relevance.cjs");

test("documentation and governance-only changes use the Release fast path", () => {
  assert.equal(
    isReleaseBuildRelevant([
      "docs/ProjectStatus.md",
      "ADR/0033-party-client-migration-organization-boundary.md",
      "IMPLEMENTATION_QUEUE.md",
      ".github/workflows/governance.yml",
    ]),
    false,
  );
});

test("root dependencies and build configuration require the full build", () => {
  for (const filePath of [
    "package.json",
    "package-lock.json",
    "electron-builder.yml",
    "tsconfig.release.json",
    "vite.config.ts",
    ".github/workflows/release.yml",
  ]) {
    assert.equal(isReleaseBuildRelevant([filePath]), true, filePath);
  }
});

test("Electron, frontend, and build-script changes require the full build", () => {
  for (const filePath of [
    "electron/main.ts",
    "frontend/src/main.tsx",
    "frontend/package-lock.json",
    "scripts/release_build_relevance.cjs",
  ]) {
    assert.equal(isReleaseBuildRelevant([filePath]), true, filePath);
  }
});

test("an unrecognized path fails safe to the full build", () => {
  assert.equal(
    isReleaseBuildRelevant(["infrastructure/build-settings.toml"]),
    true,
  );
});
