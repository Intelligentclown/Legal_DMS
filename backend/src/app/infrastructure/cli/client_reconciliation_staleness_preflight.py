"""T111: read-only live staleness preflight for a T108/T109 reconciliation basis."""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.cli.client_migration_preflight import run_client_migration_preflight
from app.infrastructure.cli.client_reconciliation_artifact_validator import (
    ValidationIssue,
    canonical_json,
    validate_client_reconciliation_artifact,
)
from app.infrastructure.database.session import get_session_factory

_SNAPSHOT_FIELDS = {"classification", "candidate_organization_ids", "evidence", "note"}


@dataclass(frozen=True, slots=True)
class AnchorStalenessResult:
    anchor_id: str
    stale: bool
    executable: bool
    issues: tuple[ValidationIssue, ...]


@dataclass(frozen=True, slots=True)
class LiveReconciliationStalenessResult:
    valid: bool
    stale: bool
    executable: bool
    anchors: tuple[AnchorStalenessResult, ...]
    issues: tuple[ValidationIssue, ...]


def _artifact_snapshots(artifact_bytes: bytes) -> dict[str, dict[str, Any]]:
    artifact = json.loads(artifact_bytes.decode("utf-8"))
    return {entry["anchor"]["node_id"]: entry["t108_snapshot"] for entry in artifact["entries"]}


def _current_snapshots(
    report: object,
) -> tuple[dict[str, dict[str, Any]], tuple[ValidationIssue, ...]]:
    payload = asdict(report)
    client_ids = payload["generated_for_client_ids"]
    clients = payload["clients"]
    issues: list[ValidationIssue] = []
    current: dict[str, dict[str, Any]] = {}
    for client in clients:
        client_id = client["node_id"]
        if client_id in current:
            issues.append(
                ValidationIssue(
                    "duplicate_current_anchor",
                    "current T108 anchor is duplicated",
                    client_id,
                )
            )
            continue
        current[client_id] = {field: client[field] for field in _SNAPSHOT_FIELDS}
    if len(client_ids) != len(set(client_ids)) or set(client_ids) != set(current):
        issues.append(
            ValidationIssue(
                "invalid_current_anchor_set",
                "current T108 client anchors do not match the generated anchor set",
            )
        )
    return current, tuple(issues)


async def run_live_reconciliation_staleness_preflight(
    session: AsyncSession, *, source_report_bytes: bytes, artifact_bytes: bytes
) -> LiveReconciliationStalenessResult:
    """Recompute T108 evidence and fail closed when it differs from the frozen basis."""
    validated = await validate_client_reconciliation_artifact(
        session, source_report_bytes=source_report_bytes, artifact_bytes=artifact_bytes
    )
    if not validated.valid or not validated.executable:
        return LiveReconciliationStalenessResult(
            valid=False,
            stale=True,
            executable=False,
            anchors=(),
            issues=validated.issues,
        )

    try:
        frozen = _artifact_snapshots(artifact_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError):
        return LiveReconciliationStalenessResult(
            valid=False,
            stale=True,
            executable=False,
            anchors=(),
            issues=(
                ValidationIssue(
                    "invalid_artifact",
                    "T109 artifact cannot be read after validation",
                ),
            ),
        )

    current_report = await run_client_migration_preflight(session)
    current, current_issues = _current_snapshots(current_report)
    all_anchor_ids = sorted(set(frozen) | set(current))
    anchor_results: list[AnchorStalenessResult] = []
    for anchor_id in all_anchor_ids:
        issues: list[ValidationIssue] = []
        frozen_snapshot = frozen.get(anchor_id)
        current_snapshot = current.get(anchor_id)
        if frozen_snapshot is None:
            issues.append(
                ValidationIssue(
                    "unexpected_current_anchor",
                    "current T108 has an extra anchor",
                    anchor_id,
                )
            )
        elif current_snapshot is None:
            issues.append(
                ValidationIssue(
                    "missing_current_anchor",
                    "current T108 anchor is missing",
                    anchor_id,
                )
            )
        elif canonical_json(frozen_snapshot) != canonical_json(current_snapshot):
            issues.append(
                ValidationIssue(
                    "stale_current_snapshot",
                    "current T108 snapshot differs from the frozen reconciliation basis",
                    anchor_id,
                )
            )
        anchor_results.append(
            AnchorStalenessResult(
                anchor_id=anchor_id,
                stale=bool(issues),
                executable=not issues,
                issues=tuple(issues),
            )
        )
    stale = bool(current_issues) or any(result.stale for result in anchor_results)
    return LiveReconciliationStalenessResult(
        valid=not stale,
        stale=stale,
        executable=not stale,
        anchors=tuple(anchor_results),
        issues=current_issues,
    )


async def _async_main(source_report_path: Path, artifact_path: Path) -> int:
    async with get_session_factory()() as session:
        result = await run_live_reconciliation_staleness_preflight(
            session,
            source_report_bytes=source_report_path.read_bytes(),
            artifact_bytes=artifact_path.read_bytes(),
        )
    print(json.dumps(asdict(result), indent=2))
    return 0 if result.valid and result.executable else 1


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Recompute T108 evidence and validate live reconciliation staleness"
    )
    parser.add_argument("source_report", type=Path)
    parser.add_argument("artifact", type=Path)
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_async_main(args.source_report, args.artifact)))
