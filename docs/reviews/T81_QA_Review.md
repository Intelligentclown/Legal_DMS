# T81 QA Review

**Task:** T81 — Writing Rules cleanup in root `README.md`

**Scope:** Investigate the stray "## Writing Rules" section appended at the end of root
`README.md`; if confirmed misplaced, move it to its correct existing location or remove it if a
pure duplicate; if not misplaced, or its disposition is genuinely ambiguous, document the finding
and stop rather than guessing. No other section of `README.md`, and no other documentation file,
authorized to be touched. Full authorized-scope text: `IMPLEMENTATION_QUEUE.md`'s T81 row.

**Authorization:** PR #90, authorization commit `dc0f5fa`, merge `0112af6` (on `main`).

**Implementation:** commit `6dfcae3`, branch `docs/t81-writing-rules-cleanup`, PR #91 (open,
unmerged at the time of this review).

**Reviewed:** `README.md` (diff `origin/main...6dfcae3`), commit `c84a339` (which originally
introduced the stray section, cited by the implementation as evidence), and
`docs/ImplementationLog/README.md` (the document the implementation claims the removed content
duplicates).

**Date:** 2026-08-24

---

## Verification performed

- **Diff scope** — confirmed via `git diff origin/main...6dfcae3` and `gh pr view 91 --json
  files`: exactly one file changed (`README.md`), +0/−9, removing exactly the "## Writing Rules"
  section and nothing else. No other README section or documentation file touched.
- **Exact-restoration claim** — confirmed via direct blob comparison: `git rev-parse
  c84a339~1:README.md` and `git rev-parse 6dfcae3:README.md` both resolve to the identical blob
  `984f891e847f48d4e240b1322a0839860a8f0eab`, verifying the implementation's own claim that this
  restores `README.md` to its exact state before the section was introduced — not merely
  approximately similar.
- **Duplication claim** — each of the 7 removed bullet points spot-checked directly against
  `docs/ImplementationLog/README.md`, not accepted from the implementation's commit message alone:
  matching content found for all 7 (the "each phase gets exactly one file" rule; the `Completed`
  metadata field's "leave blank... don't pre-fill it" instruction; the explicit ADR/CHANGELOG
  no-duplication rules; the mandatory `Related ADRs`/`Git Commit`/`Pull Request` metadata fields;
  the Task-IDs-immutable / in-place-correction-in-prose rule).
- **Disposition reasoning** (remove vs. move) assessed as sound: pasting a condensed restatement
  into `docs/ImplementationLog/README.md` would itself have violated that document's own explicit
  anti-duplication principle, and would also have touched a second documentation file — separately
  forbidden by this task's own scope restriction regardless.

## Findings

None. The implementation matches its authorized scope exactly; no unauthorized file was touched
and no unrelated change was bundled in.

## QA Decision

```
☑ Approved
□ Approved with comments
□ Rework required
```

Approved without comments — the implementation is minimal, exactly scoped, and its stated
investigation was independently re-verified against the actual repository (blob hashes, file
diffs, and the target document's content) rather than accepted on its own word.
