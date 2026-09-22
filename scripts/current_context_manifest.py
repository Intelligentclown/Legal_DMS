#!/usr/bin/env python3
"""Build ADR-0038 Layer-A's disposable, offline Current Context Manifest."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import governance_validate as governance

CONTEXT_SCHEMA_VERSION = "1.0"
DERIVATION_VERSION = "1.0"
SOURCE_SET_VERSION = "1.0"
REPOSITORY_ID = "Intelligentclown/Legal_DMS"
SOURCE_SET = ("IMPLEMENTATION_QUEUE.md", "PROJECT_STATE.json", "numbered ADR/*.md", "local Git HEAD")
NUMBERED_ADR_PATH_RE = re.compile(r"^ADR/\d{4}-.+\.md$")


class ManifestError(Exception):
    """Authoritative input cannot produce a healthy canonical manifest."""

    def __init__(self, diagnostics: list[dict[str, str]]):
        self.diagnostics = diagnostics
        super().__init__("Current Context Manifest derivation failed")


def _diagnostic(classification: str, code: str, message: str) -> dict[str, str]:
    return {"class": classification, "code": code, "message": message}


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=False
    )
    if result.returncode:
        raise ManifestError([_diagnostic("invalid", "local-git", result.stderr.strip() or "git failed")])
    return result.stdout.strip()


def _git_commit(root: Path) -> str:
    commit = _git(root, "rev-parse", "HEAD")
    if not commit:
        raise ManifestError([_diagnostic("invalid", "local-git", "local Git source commit is unavailable")])
    return commit


def _authoritative_worktree_changes(root: Path) -> list[str]:
    """Only changes able to alter the declared source set invalidate ``HEAD`` identity."""
    if not (root / ".git").exists():
        return []  # Fixture callers provide an explicit source commit.
    changed = _git(root, "diff", "--name-only", "HEAD", "--", "IMPLEMENTATION_QUEUE.md", "PROJECT_STATE.json", "ADR").splitlines()
    untracked = _git(root, "ls-files", "--others", "--exclude-standard", "--", "ADR").splitlines()
    relevant = {path for path in changed + untracked if path in {"IMPLEMENTATION_QUEUE.md", "PROJECT_STATE.json"} or NUMBERED_ADR_PATH_RE.fullmatch(path)}
    return sorted(relevant)


def _adr_statuses(adr_dir: Path) -> dict[str, dict[str, str | None]]:
    statuses: dict[str, dict[str, str]] = {}
    for path in sorted(adr_dir.glob("[0-9][0-9][0-9][0-9]-*.md")):
        number = path.name[:4]
        status = next(
            (
                line.split(":", 1)[1].strip().strip("*").strip()
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.startswith("**Status:**")
            ),
            None,
        )
        statuses[f"ADR-{number}"] = {
            "value": status,
            "provenance": "repository_derived" if status is not None else "unverified",
        }
    return statuses


def build(root: Path) -> dict[str, object]:
    """Derive the canonical Layer-A logical payload from the allow-listed sources."""
    root = governance.find_repo_root(root)
    dirty_sources = _authoritative_worktree_changes(root)
    if dirty_sources:
        raise ManifestError([_diagnostic(
            "invalid",
            "dirty-authoritative-source",
            "Refusing to label modified authoritative evidence as local Git HEAD: " + ", ".join(dirty_sources),
        )])
    queue = (root / "IMPLEMENTATION_QUEUE.md").read_text(encoding="utf-8")
    state = json.loads((root / "PROJECT_STATE.json").read_text(encoding="utf-8"))
    rows = governance.parse_task_rows(queue)
    adrs, violations = governance.parse_adr_files(root / "ADR")
    violations += governance.check_duplicate_task_ids(rows)
    violations += governance.check_done_requires_authorization(rows)
    violations += governance.check_done_requires_qa_evidence(rows)
    violations += governance.check_duplicate_required_adr_resolution(adrs)
    violations += governance.check_adr_references(queue, {adr.number for adr in adrs})
    resolved = governance.compute_resolved_required_adrs(adrs)
    violations += governance.check_governance_ledger(state, resolved, rows)
    errors = [v for v in violations if v.severity == "ERROR"]
    if errors:
        raise ManifestError([
            _diagnostic("conflicting" if v.check == "governance-ledger-drift" else "invalid", v.check, v.message)
            for v in errors
        ])

    required = set(governance.REQUIRED_ADR_RANGE)
    return {
        "context_schema_version": CONTEXT_SCHEMA_VERSION,
        "derivation_version": DERIVATION_VERSION,
        "source_set_version": SOURCE_SET_VERSION,
        "identity": {
            "repository": REPOSITORY_ID,
            "source_commit": _git_commit(root),
            "provenance": "git_verified",
        },
        "governance_frontier": {
            "latest_done": governance.latest_task_number(
                rows, lambda row: f"{row.task_id} is now Done" in row.text
            ),
            "latest_authorized": governance.latest_task_number(
                rows, lambda row: governance.AUTHORIZATION_PHRASE in row.text
            ),
            "in_progress_transitions": state.get("governanceLedger", {}).get(
                "inProgressTransitions", []
            ),
            "provenance": "mechanically_verified",
        },
        "required_adrs": {
            "resolved": sorted(resolved),
            "unresolved": sorted(required - resolved),
            "provenance": "mechanically_verified",
        },
        "adr_statuses": _adr_statuses(root / "ADR"),
        "discrepancies": [],
        "projection": {"authority": "non_authoritative", "layer": "A"},
    }


def canonical_json(root: Path) -> str:
    return json.dumps(build(root), sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a non-authoritative Current Context Manifest")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    try:
        sys.stdout.write(canonical_json(args.root))
    except ManifestError as exc:
        print(json.dumps({"diagnostics": exc.diagnostics}, sort_keys=True, separators=(",", ":")), file=sys.stderr)
        return 1
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"diagnostics": [_diagnostic("invalid", "authoritative-input", str(exc))]}, sort_keys=True, separators=(",", ":")), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
