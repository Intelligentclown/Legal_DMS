# M1 Completion-Provenance Evidence Package

**Task:** T180 — M1 Acceptance-Date and Schema V3 Completion-Provenance Reconciliation (PR 2 of 3)
**Acceptance scope:** `internal_office_dogfooding` only
**Authoritative owner-decision timestamp:** `2026-10-24T20:40:09Z`
**Project-local acceptance date:** `2026-10-25` (`Asia/Kolkata`, 02:10:09)

## Timestamp policy

GitHub Issue #371 is the owner-authored durable publication of the formal acceptance decision. Its GitHub `createdAt` timestamp is therefore the authoritative UTC instant for this completion record. PR #372's `mergedAt` is a later repository-publication event and is not substituted for the decision timestamp.

## Immutable evidence references

The references below are sorted lexicographically and exactly match `M1.completion_provenance.evidence_references`. Repository artifacts are pinned to their protected merge commits.

1. `https://github.com/Intelligentclown/Legal_DMS/blob/422ee7ebc79eddab462f0030f128cb072540dfc4/docs/reviews/T175_Closeout_QA_Review.md`
2. `https://github.com/Intelligentclown/Legal_DMS/blob/78c2ee36363e9ddd25a5e4517afeb8df9882250f/docs/reviews/T175_Implementation_Evidence.md`
3. `https://github.com/Intelligentclown/Legal_DMS/blob/78c2ee36363e9ddd25a5e4517afeb8df9882250f/docs/reviews/T175_QA_Review.md`
4. `https://github.com/Intelligentclown/Legal_DMS/blob/b5ec4be7473556e1cd4c721f1a7b182649f56e75/docs/acceptance/M1_Full_Operational_Acceptance.md`
5. `https://github.com/Intelligentclown/Legal_DMS/issues/371`
6. `https://github.com/Intelligentclown/Legal_DMS/pull/372`

These cover the Project Owner decision, its protected publication, the canonical acceptance record, and the protected T175 operational-verification and Independent QA evidence. They do not expand acceptance beyond internal office dogfooding.

## Canonical serialization and digest

The package is a JSON object containing only `accepted_at_utc`, `acceptance_reference`, `acceptance_scope`, and `evidence_references`. Serialize with `json.dumps(package, sort_keys=True, separators=(",", ":"))`, UTF-8 encode it, append exactly one LF byte (`0x0a`), then compute SHA-256. The exact digest is:

`aed7462d9d90b9a97133e33166c536129df280568fa36f4a4b07261e0bb47131`

The focused T180 regression test independently reconstructs this serialization from the calendar record and verifies the digest.
