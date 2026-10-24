"use strict";

const fs = require("node:fs");
const path = require("node:path");

const indexPath = process.argv[2] ?? "frontend/dist/index.html";
const html = fs.readFileSync(indexPath, "utf8");
const referencePattern = /\b(?:src|href)=["']([^"']+)["']/gi;
const references = [...html.matchAll(referencePattern)].map(
  (match) => match[1],
);
const localReferences = references.filter(
  (reference) =>
    !reference.startsWith("#") &&
    !/^(?:[a-z][a-z\d+.-]*:|\/\/)/i.test(reference),
);

const rootAbsoluteReferences = localReferences.filter((reference) =>
  reference.startsWith("/"),
);
if (rootAbsoluteReferences.length > 0) {
  throw new Error(
    `Packaged renderer contains root-absolute asset references: ${rootAbsoluteReferences.join(", ")}`,
  );
}

const missingReferences = localReferences.filter((reference) => {
  const relativePath = decodeURIComponent(reference.split(/[?#]/, 1)[0]);
  return !fs.existsSync(path.resolve(path.dirname(indexPath), relativePath));
});
if (missingReferences.length > 0) {
  throw new Error(
    `Packaged renderer references missing local files: ${missingReferences.join(", ")}`,
  );
}

console.log(
  `packaged-renderer-assets: OK (${localReferences.length} local references; all relative and present)`,
);
