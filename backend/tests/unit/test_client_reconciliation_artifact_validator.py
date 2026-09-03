from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from uuid import UUID, uuid4

import pytest

from app.infrastructure.cli.client_reconciliation_artifact_validator import (
    validate_client_reconciliation_artifact,
)


class _Result:
    def __init__(self, ids: set[str]) -> None:
        self._ids = ids

    def scalars(self) -> _Result:
        return self

    def __iter__(self):
        return iter(self._ids)


class _ReadOnlySession:
    def __init__(self, organization_ids: set[str]) -> None:
        self.organization_ids = {UUID(organization_id) for organization_id in organization_ids}
        self.execute_calls = 0

    async def execute(self, _statement):
        self.execute_calls += 1
        return _Result(self.organization_ids)


def _client(client_id: str, classification: str, candidates: list[str]) -> dict:
    return {
        "node_type": "client",
        "node_id": client_id,
        "classification": classification,
        "candidate_organization_ids": candidates,
        "evidence": [],
        "note": None,
    }


def _report(*clients: dict) -> dict:
    return {
        "generated_for_client_ids": [client["node_id"] for client in clients],
        "classifications": {"deterministic": 0, "ambiguous": 0, "unmappable": 0},
        "clients": list(clients),
        "addresses": [],
        "properties": [],
        "property_owners": [],
        "matters": [],
        "appointments": [],
        "invoices": [],
        "payments": [],
        "client_contacts": [],
    }


def _artifact(report_bytes: bytes, *clients: dict) -> dict:
    digest = hashlib.sha256(report_bytes).hexdigest()
    entries = []
    for client in clients:
        classification = client["classification"]
        state = "deterministic" if classification == "deterministic" else "operator_reconciled"
        selected = (
            client["candidate_organization_ids"][0]
            if classification == "deterministic"
            else str(uuid4())
        )
        decision = {
            "state": state,
            "selected_organization_id": selected,
            "resolution_basis": "T108 evidence reviewed",
            "operator_note": "Reviewed by operator",
        }
        if state == "operator_reconciled":
            decision["organization_source"] = "existing"
        entries.append(
            {
                "set_id": f"client-set:{client['node_id']}:{digest[:12]}",
                "anchor": {"node_type": "client", "node_id": client["node_id"]},
                "t108_snapshot": {
                    key: client[key]
                    for key in ("classification", "candidate_organization_ids", "evidence", "note")
                },
                "decision": decision,
                "provenance": {
                    "entered_at": "2026-09-03T12:00:00Z",
                    "entered_by": {"actor_type": "operator", "actor_id": "operator@example.com"},
                },
            }
        )
    return {
        "schema_version": "t109.party-client-reconciliation.v1",
        "task": "T109",
        "generated_at": "2026-09-03T12:00:00Z",
        "generated_by": {
            "actor_type": "operator",
            "actor_id": "operator@example.com",
            "display_name": "Operator",
        },
        "source_report": {
            "report_type": "t108.client-migration-preflight.v1",
            "report_path": "frozen.json",
            "report_sha256": digest,
        },
        "entries": entries,
    }


def _json(value: dict) -> bytes:
    return json.dumps(value, indent=2).encode()


@pytest.mark.asyncio
async def test_valid_frozen_artifact_is_executable() -> None:
    organization_id = str(uuid4())
    client = _client(str(uuid4()), "deterministic", [organization_id])
    report_bytes = _json(_report(client))
    artifact_bytes = _json(_artifact(report_bytes, client))
    session = _ReadOnlySession({organization_id})

    result = await validate_client_reconciliation_artifact(
        session, source_report_bytes=report_bytes, artifact_bytes=artifact_bytes
    )

    assert result.valid is True
    assert result.executable is True
    assert result.issues == ()
    assert session.execute_calls == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        (
            lambda artifact: artifact["source_report"].update(report_sha256="0" * 64),
            "source_report_hash_mismatch",
        ),
        (lambda artifact: artifact.update(task="T110"), "invalid_task"),
        (lambda artifact: artifact.update(schema_version="v2"), "invalid_schema_version"),
        (
            lambda artifact: artifact["source_report"].update(report_type="wrong"),
            "invalid_report_type",
        ),
        (lambda artifact: artifact["entries"].pop(), "incomplete_anchor_coverage"),
        (
            lambda artifact: artifact["entries"].append(deepcopy(artifact["entries"][0])),
            "duplicate_anchor",
        ),
        (
            lambda artifact: artifact["entries"][0]["t108_snapshot"].update(note="changed"),
            "stale_snapshot",
        ),
        (
            lambda artifact: artifact["entries"][0]["decision"].update(
                selected_organization_id="not-a-uuid"
            ),
            "invalid_organization_id",
        ),
        (
            lambda artifact: artifact["entries"][0]["decision"].update(
                selected_organization_id=str(uuid4())
            ),
            "illegal_deterministic_override",
        ),
        (
            lambda artifact: artifact["entries"][0]["decision"].update(
                state="operator_reconciled", organization_source="existing"
            ),
            "illegal_operator_override",
        ),
    ],
)
async def test_rejects_contract_violations(mutation, code: str) -> None:
    organization_id = str(uuid4())
    client = _client(str(uuid4()), "deterministic", [organization_id])
    report_bytes = _json(_report(client))
    artifact = _artifact(report_bytes, client)
    mutation(artifact)

    result = await validate_client_reconciliation_artifact(
        _ReadOnlySession({organization_id}),
        source_report_bytes=report_bytes,
        artifact_bytes=_json(artifact),
    )

    assert result.valid is False
    assert result.executable is False
    assert code in {issue.code for issue in result.issues}


@pytest.mark.asyncio
async def test_rejects_extra_anchor_and_nonexistent_organization() -> None:
    organization_id = str(uuid4())
    client = _client(str(uuid4()), "ambiguous", [organization_id, str(uuid4())])
    report_bytes = _json(_report(client))
    artifact = _artifact(report_bytes, client)
    artifact["entries"][0]["anchor"]["node_id"] = str(uuid4())
    digest_prefix = hashlib.sha256(report_bytes).hexdigest()[:12]
    extra_anchor_id = artifact["entries"][0]["anchor"]["node_id"]
    artifact["entries"][0]["set_id"] = f"client-set:{extra_anchor_id}:{digest_prefix}"

    extra_result = await validate_client_reconciliation_artifact(
        _ReadOnlySession(set()), source_report_bytes=report_bytes, artifact_bytes=_json(artifact)
    )
    assert extra_result.valid is False
    assert {"unknown_anchor", "incomplete_anchor_coverage"} <= {
        issue.code for issue in extra_result.issues
    }

    artifact = _artifact(report_bytes, client)
    missing_org_result = await validate_client_reconciliation_artifact(
        _ReadOnlySession(set()), source_report_bytes=report_bytes, artifact_bytes=_json(artifact)
    )
    assert missing_org_result.valid is False
    assert "organization_not_found" in {issue.code for issue in missing_org_result.issues}


@pytest.mark.asyncio
async def test_rejects_malformed_json_and_non_executable_state() -> None:
    result = await validate_client_reconciliation_artifact(
        _ReadOnlySession(set()), source_report_bytes=b"{}", artifact_bytes=b"not json"
    )
    assert result.valid is False
    assert result.executable is False
    assert "malformed_json" in {issue.code for issue in result.issues}

    organization_id = str(uuid4())
    client = _client(str(uuid4()), "ambiguous", [organization_id, str(uuid4())])
    report_bytes = _json(_report(client))
    artifact = _artifact(report_bytes, client)
    artifact["entries"][0]["decision"] = {
        "state": "ambiguous",
        "resolution_basis": "T108 evidence reviewed",
        "operator_note": "Awaiting operator decision",
    }
    result = await validate_client_reconciliation_artifact(
        _ReadOnlySession(set()), source_report_bytes=report_bytes, artifact_bytes=_json(artifact)
    )
    assert result.valid is True
    assert result.executable is False
