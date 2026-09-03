"""T110: read-only validation of a T109 reconciliation artifact.

The validator consumes frozen JSON documents and only SELECTs Organization ids.
It deliberately does not attempt the future live-graph stale-detection work.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.session import get_session_factory
from app.infrastructure.persistence.models.organization import Organization

_ARTIFACT_KEYS = {
    "schema_version",
    "task",
    "generated_at",
    "generated_by",
    "source_report",
    "entries",
}
_REPORT_KEYS = {
    "generated_for_client_ids",
    "classifications",
    "clients",
    "addresses",
    "properties",
    "property_owners",
    "matters",
    "appointments",
    "invoices",
    "payments",
    "client_contacts",
}
_ENTRY_KEYS = {"set_id", "anchor", "t108_snapshot", "decision", "provenance"}
_SNAPSHOT_KEYS = {"classification", "candidate_organization_ids", "evidence", "note"}
_DECISION_BASE_KEYS = {"state", "resolution_basis", "operator_note"}
_EXECUTABLE_STATES = {"deterministic", "operator_reconciled"}
_ALL_STATES = _EXECUTABLE_STATES | {"ambiguous", "unmappable", "stale", "rejected"}


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    code: str
    message: str
    anchor_id: str | None = None


@dataclass(frozen=True, slots=True)
class ValidationResult:
    valid: bool
    executable: bool
    source_report_sha256: str
    issues: tuple[ValidationIssue, ...]


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _parse_json(raw: bytes, label: str, issues: list[ValidationIssue]) -> dict[str, Any] | None:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        issues.append(
            ValidationIssue("malformed_json", f"{label} is not valid UTF-8 JSON: {error}")
        )
        return None
    if not isinstance(value, dict):
        issues.append(ValidationIssue("invalid_document", f"{label} must be a JSON object"))
        return None
    return value


def _require_exact_keys(
    value: Any, keys: set[str], label: str, issues: list[ValidationIssue]
) -> bool:
    if not isinstance(value, dict) or set(value) != keys:
        issues.append(
            ValidationIssue("invalid_schema", f"{label} has missing or unexpected fields")
        )
        return False
    return True


def _uuid(value: Any) -> UUID | None:
    if not isinstance(value, str):
        return None
    try:
        return UUID(value)
    except ValueError:
        return None


def _timestamp(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def _valid_evidence(evidence: list[Any]) -> bool:
    required = {"source_type", "source_id", "path", "organization_id"}
    known_types = {
        "user",
        "ledger",
        "client",
        "address",
        "property",
        "property_owner",
        "matter",
        "appointment",
        "invoice",
        "payment",
        "client_contact",
    }
    return all(
        isinstance(item, dict)
        and set(item) == required
        and item["source_type"] in known_types
        and isinstance(item["path"], str)
        and _uuid(item["source_id"]) is not None
        and _uuid(item["organization_id"]) is not None
        for item in evidence
    )


def _validate_report(
    report: dict[str, Any], issues: list[ValidationIssue]
) -> dict[str, dict[str, Any]]:
    if not _require_exact_keys(report, _REPORT_KEYS, "T108 report", issues):
        return {}
    client_ids = report["generated_for_client_ids"]
    clients = report["clients"]
    if not isinstance(client_ids, list) or not isinstance(clients, list):
        issues.append(
            ValidationIssue("invalid_source_report", "T108 client collections must be arrays")
        )
        return {}
    if any(_uuid(client_id) is None for client_id in client_ids) or len(set(client_ids)) != len(
        client_ids
    ):
        issues.append(
            ValidationIssue(
                "invalid_source_report", "T108 generated client ids must be unique UUIDs"
            )
        )
        return {}

    by_id: dict[str, dict[str, Any]] = {}
    for client in clients:
        if not isinstance(client, dict):
            issues.append(
                ValidationIssue("invalid_source_report", "T108 clients entries must be objects")
            )
            continue
        required = {
            "node_type",
            "node_id",
            "classification",
            "candidate_organization_ids",
            "evidence",
            "note",
        }
        if set(client) != required or client.get("node_type") != "client":
            issues.append(
                ValidationIssue("invalid_source_report", "T108 client node has an invalid shape")
            )
            continue
        client_id = client.get("node_id")
        if _uuid(client_id) is None or client_id in by_id:
            issues.append(
                ValidationIssue(
                    "invalid_source_report", "T108 client node ids must be unique UUIDs"
                )
            )
            continue
        if client.get("classification") not in {"deterministic", "ambiguous", "unmappable"}:
            issues.append(
                ValidationIssue(
                    "invalid_source_report", "T108 classification is invalid", client_id
                )
            )
            continue
        candidates = client.get("candidate_organization_ids")
        evidence = client.get("evidence")
        if not isinstance(candidates, list) or not isinstance(evidence, list):
            issues.append(
                ValidationIssue(
                    "invalid_source_report", "T108 snapshot arrays are invalid", client_id
                )
            )
            continue
        if any(_uuid(candidate) is None for candidate in candidates) or len(set(candidates)) != len(
            candidates
        ):
            issues.append(
                ValidationIssue(
                    "invalid_source_report", "T108 candidate ids must be unique UUIDs", client_id
                )
            )
            continue
        if not _valid_evidence(evidence):
            issues.append(
                ValidationIssue("invalid_source_report", "T108 evidence is invalid", client_id)
            )
            continue
        by_id[client_id] = client
    if set(client_ids) != set(by_id) or len(client_ids) != len(by_id):
        issues.append(
            ValidationIssue("invalid_source_report", "T108 client anchors do not match clients[]")
        )
    return by_id


async def validate_client_reconciliation_artifact(
    session: AsyncSession, *, source_report_bytes: bytes, artifact_bytes: bytes
) -> ValidationResult:
    """Validate frozen T108/T109 inputs without mutating the database or filesystem."""
    issues: list[ValidationIssue] = []
    digest = hashlib.sha256(source_report_bytes).hexdigest()
    report = _parse_json(source_report_bytes, "T108 report", issues)
    artifact = _parse_json(artifact_bytes, "T109 artifact", issues)
    if report is None or artifact is None:
        return ValidationResult(False, False, digest, tuple(issues))

    clients = _validate_report(report, issues)
    if not _require_exact_keys(artifact, _ARTIFACT_KEYS, "T109 artifact", issues):
        return ValidationResult(False, False, digest, tuple(issues))
    if artifact["schema_version"] != "t109.party-client-reconciliation.v1":
        issues.append(ValidationIssue("invalid_schema_version", "T109 schema_version is invalid"))
    if artifact["task"] != "T109":
        issues.append(ValidationIssue("invalid_task", "artifact task must be T109"))
    if not _timestamp(artifact["generated_at"]):
        issues.append(
            ValidationIssue("invalid_timestamp", "generated_at must be an ISO-8601 timestamp")
        )
    if not _require_exact_keys(
        artifact["generated_by"], {"actor_type", "actor_id", "display_name"}, "generated_by", issues
    ):
        pass
    elif not all(isinstance(value, str) and value for value in artifact["generated_by"].values()):
        issues.append(
            ValidationIssue("invalid_provenance", "generated_by fields must be non-empty strings")
        )
    source = artifact["source_report"]
    if not _require_exact_keys(
        source, {"report_type", "report_path", "report_sha256"}, "source_report", issues
    ):
        source = {}
    elif not isinstance(source["report_path"], str) or not source["report_path"]:
        issues.append(
            ValidationIssue("invalid_source_report", "source_report.report_path is invalid")
        )
    elif source["report_type"] != "t108.client-migration-preflight.v1":
        issues.append(
            ValidationIssue("invalid_report_type", "source_report.report_type is invalid")
        )
    elif source["report_sha256"] != digest:
        issues.append(
            ValidationIssue(
                "source_report_hash_mismatch",
                "source_report.report_sha256 does not match the supplied T108 report",
            )
        )

    entries = artifact["entries"]
    if not isinstance(entries, list):
        issues.append(ValidationIssue("invalid_schema", "entries must be an array"))
        entries = []
    seen_sets: set[str] = set()
    seen_anchors: set[str] = set()
    selected_ids: set[UUID] = set()
    executable = True
    for entry in entries:
        anchor_id = entry.get("anchor", {}).get("node_id") if isinstance(entry, dict) else None
        if not _require_exact_keys(entry, _ENTRY_KEYS, "entry", issues):
            executable = False
            continue
        if not isinstance(entry["set_id"], str) or entry["set_id"] in seen_sets:
            issues.append(
                ValidationIssue("duplicate_or_invalid_set_id", "set_id must be unique", anchor_id)
            )
        else:
            seen_sets.add(entry["set_id"])
        anchor = entry["anchor"]
        if (
            not _require_exact_keys(anchor, {"node_type", "node_id"}, "anchor", issues)
            or anchor.get("node_type") != "client"
            or _uuid(anchor.get("node_id")) is None
        ):
            issues.append(
                ValidationIssue("invalid_anchor", "anchor must identify a Client UUID", anchor_id)
            )
            executable = False
            continue
        anchor_id = anchor["node_id"]
        if anchor_id in seen_anchors:
            issues.append(
                ValidationIssue("duplicate_anchor", "anchor appears more than once", anchor_id)
            )
        seen_anchors.add(anchor_id)
        expected_set_id = f"client-set:{anchor_id}:{digest[:12]}"
        if entry["set_id"] != expected_set_id:
            issues.append(
                ValidationIssue(
                    "invalid_set_id", "set_id does not match the frozen report", anchor_id
                )
            )
        client = clients.get(anchor_id)
        if client is None:
            issues.append(
                ValidationIssue(
                    "unknown_anchor", "anchor is not present in the T108 report", anchor_id
                )
            )
            executable = False
            continue
        snapshot = entry["t108_snapshot"]
        if not _require_exact_keys(snapshot, _SNAPSHOT_KEYS, "t108_snapshot", issues):
            executable = False
            continue
        expected_snapshot = {key: client[key] for key in _SNAPSHOT_KEYS}
        if _canonical(snapshot) != _canonical(expected_snapshot):
            issues.append(
                ValidationIssue(
                    "stale_snapshot",
                    "embedded T108 snapshot differs from the frozen report",
                    anchor_id,
                )
            )
        decision = entry["decision"]
        if not isinstance(decision, dict) or not set(decision) >= _DECISION_BASE_KEYS:
            issues.append(
                ValidationIssue("invalid_schema", "decision has missing fields", anchor_id)
            )
            executable = False
            continue
        state = decision.get("state")
        if state not in _ALL_STATES:
            issues.append(
                ValidationIssue("invalid_decision_state", "decision state is invalid", anchor_id)
            )
            executable = False
            continue
        allowed_keys = set(_DECISION_BASE_KEYS)
        if state in _EXECUTABLE_STATES:
            allowed_keys.add("selected_organization_id")
        if state == "operator_reconciled":
            allowed_keys.add("organization_source")
        if set(decision) != allowed_keys:
            issues.append(
                ValidationIssue("invalid_schema", "decision has unexpected fields", anchor_id)
            )
        selected = decision.get("selected_organization_id")
        if state in _EXECUTABLE_STATES:
            selected_uuid = _uuid(selected)
            if selected_uuid is None:
                issues.append(
                    ValidationIssue(
                        "invalid_organization_id",
                        "executable decisions require an Organization UUID",
                        anchor_id,
                    )
                )
            else:
                selected_ids.add(selected_uuid)
        elif "selected_organization_id" in decision:
            issues.append(
                ValidationIssue(
                    "illegal_selected_organization",
                    "non-executable decisions must not select an Organization",
                    anchor_id,
                )
            )
        if state == "deterministic":
            candidates = snapshot["candidate_organization_ids"]
            if (
                snapshot["classification"] != "deterministic"
                or len(candidates) != 1
                or selected != candidates[0]
            ):
                issues.append(
                    ValidationIssue(
                        "illegal_deterministic_override",
                        "deterministic decisions must select T108's sole candidate",
                        anchor_id,
                    )
                )
        elif state == "operator_reconciled":
            if snapshot["classification"] not in {"ambiguous", "unmappable"}:
                issues.append(
                    ValidationIssue(
                        "illegal_operator_override",
                        "operator_reconciled is only allowed for ambiguous or unmappable anchors",
                        anchor_id,
                    )
                )
            if decision.get("organization_source") not in {"existing", "operator_created"}:
                issues.append(
                    ValidationIssue(
                        "invalid_organization_source",
                        "operator_reconciled requires a valid organization_source",
                        anchor_id,
                    )
                )
        else:
            executable = False
            if "organization_source" in decision:
                issues.append(
                    ValidationIssue(
                        "illegal_organization_source",
                        "non-operator decisions must not declare organization_source",
                        anchor_id,
                    )
                )
        if not isinstance(decision.get("resolution_basis"), str) or not isinstance(
            decision.get("operator_note"), str
        ):
            issues.append(
                ValidationIssue(
                    "invalid_decision",
                    "decision basis and operator note must be strings",
                    anchor_id,
                )
            )
        provenance = entry["provenance"]
        if (
            not isinstance(provenance, dict)
            or set(provenance) != {"entered_at", "entered_by"}
            or not _timestamp(provenance.get("entered_at"))
        ):
            issues.append(
                ValidationIssue("invalid_provenance", "entry provenance is invalid", anchor_id)
            )
        elif not _require_exact_keys(
            provenance["entered_by"], {"actor_type", "actor_id"}, "entered_by", issues
        ):
            pass
        elif not all(
            isinstance(value, str) and value for value in provenance["entered_by"].values()
        ):
            issues.append(
                ValidationIssue(
                    "invalid_provenance", "entered_by fields must be non-empty strings", anchor_id
                )
            )
    if set(clients) != seen_anchors or len(entries) != len(clients):
        issues.append(
            ValidationIssue(
                "incomplete_anchor_coverage",
                "entries must cover every T108 Client anchor exactly once",
            )
        )
        executable = False
    if selected_ids:
        existing = set(
            (
                await session.execute(
                    select(Organization.id).where(Organization.id.in_(selected_ids))
                )
            ).scalars()
        )
        for organization_id in selected_ids - existing:
            issues.append(
                ValidationIssue(
                    "organization_not_found",
                    "selected Organization does not exist",
                    str(organization_id),
                )
            )
    valid = not issues
    return ValidationResult(valid, valid and executable, digest, tuple(issues))


async def _async_main(report_path: Path, artifact_path: Path) -> int:
    async with get_session_factory()() as session:
        result = await validate_client_reconciliation_artifact(
            session,
            source_report_bytes=report_path.read_bytes(),
            artifact_bytes=artifact_path.read_bytes(),
        )
    print(json.dumps(asdict(result), indent=2))
    return 0 if result.valid and result.executable else 1


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate a frozen T108/T109 reconciliation artifact"
    )
    parser.add_argument("source_report", type=Path)
    parser.add_argument("artifact", type=Path)
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_async_main(args.source_report, args.artifact)))
