#!/usr/bin/env python3
"""Build ADR-0038 Layer-A's disposable, offline Current Context Manifest."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import governance_validate as governance

CONTEXT_SCHEMA_VERSION = "1.0"
DERIVATION_VERSION = "1.0"
SOURCE_SET_VERSION = "1.0"
REPOSITORY_ID = "Intelligentclown/Legal_DMS"


class ManifestError(Exception):
    """Authoritative input cannot produce a healthy canonical manifest."""


def _git_commit(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=False
    )
    if result.returncode or not result.stdout.strip():
        raise ManifestError("invalid: local Git source commit is unavailable")
    return result.stdout.strip()


def _adr_statuses(adr_dir: Path) -> dict[str, dict[str, str]]:
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
        if status is None:
            raise ManifestError(f"invalid: ADR/{path.name} has no recorded Status")
        statuses[f"ADR-{number}"] = {"value": status, "provenance": "repository_derived"}
    return statuses


def build(root: Path) -> dict[str, object]:
    """Derive the canonical Layer-A logical payload from the allow-listed sources."""
    root = governance.find_repo_root(root)
    queue = (root / "IMPLEMENTATION_QUEUE.md").read_text(encoding="utf-8")
    state = json.loads((root / "PROJECT_STATE.json").read_text(encoding="utf-8"))
    rows = governance.parse_task_rows(queue)
    adrs, violations = governance.parse_adr_files(root / "ADR")
    violations += governance.check_duplicate_task_ids(rows)
    violations += governance.check_done_requires_authorization(rows)
    violations += governance.check_done_requires_qa_evidence(rows)
    violations += governance.check_duplicate_required_adr_resolution(adrs)
    resolved = governance.compute_resolved_required_adrs(adrs)
    violations += governance.check_governance_ledger(state, resolved, rows)
    errors = [v for v in violations if v.severity == "ERROR"]
    if errors:
        raise ManifestError("; ".join(f"{v.check}: {v.message}" for v in errors))

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
    except (ManifestError, OSError, json.JSONDecodeError) as exc:
        print(f"current-context-manifest: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
