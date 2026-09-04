"use strict";

const BUILD_RELEVANT_EXACT_PATHS = new Set([
  "package.json",
  "package-lock.json",
  "npm-shrinkwrap.json",
  ".npmrc",
  ".node-version",
  ".tool-versions",
  ".github/workflows/release.yml",
  "scripts/release_build_relevance.cjs",
]);

const KNOWN_NON_BUILD_PATHS = new Set([
  "IMPLEMENTATION_QUEUE.md",
  "PROJECT_STATE.json",
  "AI_BOOTSTRAP.md",
  "AGENTS.md",
  "PROJECT_WORKFLOW.md",
  ".github/workflows/governance.yml",
  "scripts/governance_validate.py",
  "scripts/tests/test_governance_validate.py",
]);

function isReleaseBuildRelevantPath(filePath) {
  if (BUILD_RELEVANT_EXACT_PATHS.has(filePath)) {
    return true;
  }

  if (
    KNOWN_NON_BUILD_PATHS.has(filePath) ||
    filePath.startsWith("ADR/") ||
    filePath.startsWith("docs/") ||
    filePath.endsWith(".md")
  ) {
    return false;
  }

  if (
    filePath.startsWith("electron/") ||
    filePath.startsWith("frontend/") ||
    filePath.startsWith("scripts/") ||
    filePath.startsWith(".github/") ||
    filePath.startsWith("tsconfig") ||
    filePath.startsWith("vite.config.") ||
    filePath.startsWith("electron-builder.")
  ) {
    return true;
  }

  // Unknown paths must retain the full verification path rather than guessing.
  return true;
}

function isReleaseBuildRelevant(changedFiles) {
  return changedFiles.some(isReleaseBuildRelevantPath);
}

module.exports = { isReleaseBuildRelevant, isReleaseBuildRelevantPath };
