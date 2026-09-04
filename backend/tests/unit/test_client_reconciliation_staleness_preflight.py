from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from uuid import UUID, uuid4

import pytest

from app.infrastructure.cli import client_reconciliation_staleness_preflight as staleness
from app.infrastructure.cli.client_migration_preflight import (
    ClientPreflightReport,
    EvidencePath,
    NodeReport,
)


class _Result:
    def __init__(self, ids: set[str]) -> None:
        self._ids = {UUID(value) for value in ids}

    def scalars(self) -> _Result:
        return self

    def __iter__(self):
        return iter(self._ids)


class _ReadOnlySession:
    def __init__(self, organization_ids: set[str]) -> None:
        self.organization_ids = organization_ids

    async def execute(self, _statement):
        return _Result(self.organization_ids)


def _client(client_id: str, organization_id: str) -> dict:
    return {
        "node_type": "client",
        "node_id": client_id,
        "classification": "deterministic",
        "candidate_organization_ids": [organization_id],
        "evidence": [],
        "note": None,
    }


def _source_report(*clients: dict) -> dict:
    return {
        "generated_for_client_ids": [client["node_id"] for client in clients],
        "classifications": {"deterministic": len(clients), "ambiguous": 0, "unmappable": 0},
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


def _artifact(report_bytes: bytes, *clients: dict) -> bytes:
    digest = hashlib.sha256(report_bytes).hexdigest()
    return json.dumps(
        {
            "schema_version": "t109.party-client-reconciliation.v1",
            "task": "T109",
            "generated_at": "2026-09-04T12:00:00Z",
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
            "entries": [
                {
                    "set_id": f"client-set:{client['node_id']}:{digest[:12]}",
                    "anchor": {"node_type": "client", "node_id": client["node_id"]},
                    "t108_snapshot": {
                        key: client[key]
                        for key in (
                            "classification",
                            "candidate_organization_ids",
                            "evidence",
                            "note",
                        )
                    },
                    "decision": {
                        "state": "deterministic",
                        "selected_organization_id": client["candidate_organization_ids"][0],
                        "resolution_basis": "T108 evidence reviewed",
                        "operator_note": "Confirmed",
                    },
                    "provenance": {
                        "entered_at": "2026-09-04T12:00:00Z",
                        "entered_by": {
                            "actor_type": "operator",
                            "actor_id": "operator@example.com",
                        },
                    },
                }
                for client in clients
            ],
        },
        indent=2,
    ).encode()


def _current_report(*clients: dict) -> ClientPreflightReport:
    reports = tuple(
        NodeReport(
            node_type="client",
            node_id=client["node_id"],
            classification=client["classification"],
            candidate_organization_ids=tuple(client["candidate_organization_ids"]),
            evidence=tuple(EvidencePath(**item) for item in client["evidence"]),
            note=client["note"],
        )
        for client in clients
    )
    return ClientPreflightReport(
        generated_for_client_ids=tuple(client["node_id"] for client in clients),
        classifications={"deterministic": len(clients), "ambiguous": 0, "unmappable": 0},
        clients=reports,
        addresses=(),
        properties=(),
        property_owners=(),
        matters=(),
        appointments=(),
        invoices=(),
        payments=(),
        client_contacts=(),
    )


def _install_current(monkeypatch, report: ClientPreflightReport) -> None:
    async def fake_preflight(_session):
        return report

    monkeypatch.setattr(staleness, "run_client_migration_preflight", fake_preflight)


@pytest.mark.asyncio
async def test_unchanged_authoritative_evidence_is_live_and_executable(monkeypatch) -> None:
    organization_id = str(uuid4())
    client = _client(str(uuid4()), organization_id)
    source_bytes = json.dumps(_source_report(client), indent=2).encode()
    _install_current(monkeypatch, _current_report(client))

    result = await staleness.run_live_reconciliation_staleness_preflight(
        _ReadOnlySession({organization_id}),
        source_report_bytes=source_bytes,
        artifact_bytes=_artifact(source_bytes, client),
    )

    assert result.valid is True
    assert result.stale is False
    assert result.executable is True
    assert result.anchors[0].issues == ()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("classification", "ambiguous"),
        ("candidate_organization_ids", [str(uuid4())]),
        (
            "evidence",
            [
                {
                    "source_type": "user",
                    "source_id": str(uuid4()),
                    "path": "Client.created_by -> users.organization_id",
                    "organization_id": str(uuid4()),
                }
            ],
        ),
        ("note", "Current evidence changed"),
    ],
)
async def test_snapshot_drift_is_stale(monkeypatch, field: str, value: object) -> None:
    organization_id = str(uuid4())
    frozen_client = _client(str(uuid4()), organization_id)
    source_bytes = json.dumps(_source_report(frozen_client), indent=2).encode()
    current_client = deepcopy(frozen_client)
    current_client[field] = value
    _install_current(monkeypatch, _current_report(current_client))

    result = await staleness.run_live_reconciliation_staleness_preflight(
        _ReadOnlySession({organization_id}),
        source_report_bytes=source_bytes,
        artifact_bytes=_artifact(source_bytes, frozen_client),
    )

    assert result.valid is False
    assert result.stale is True
    assert result.executable is False
    assert result.anchors[0].issues[0].code == "stale_current_snapshot"


@pytest.mark.asyncio
async def test_missing_and_extra_current_anchors_fail_closed(monkeypatch) -> None:
    organization_id = str(uuid4())
    frozen_client = _client(str(uuid4()), organization_id)
    extra_client = _client(str(uuid4()), organization_id)
    source_bytes = json.dumps(_source_report(frozen_client), indent=2).encode()
    _install_current(monkeypatch, _current_report(extra_client))

    result = await staleness.run_live_reconciliation_staleness_preflight(
        _ReadOnlySession({organization_id}),
        source_report_bytes=source_bytes,
        artifact_bytes=_artifact(source_bytes, frozen_client),
    )

    assert result.stale is True
    assert {issue.code for anchor in result.anchors for issue in anchor.issues} == {
        "missing_current_anchor",
        "unexpected_current_anchor",
    }


@pytest.mark.asyncio
async def test_duplicate_current_anchor_fails_closed(monkeypatch) -> None:
    organization_id = str(uuid4())
    client = _client(str(uuid4()), organization_id)
    source_bytes = json.dumps(_source_report(client), indent=2).encode()
    duplicate_report = _current_report(client, client)
    _install_current(monkeypatch, duplicate_report)

    result = await staleness.run_live_reconciliation_staleness_preflight(
        _ReadOnlySession({organization_id}),
        source_report_bytes=source_bytes,
        artifact_bytes=_artifact(source_bytes, client),
    )

    assert result.valid is False
    assert result.stale is True
    assert result.executable is False
    assert {issue.code for issue in result.issues} == {
        "duplicate_current_anchor",
        "invalid_current_anchor_set",
    }


@pytest.mark.asyncio
async def test_invalid_governed_input_and_missing_selected_organization_fail_closed(
    monkeypatch,
) -> None:
    organization_id = str(uuid4())
    client = _client(str(uuid4()), organization_id)
    source_bytes = json.dumps(_source_report(client), indent=2).encode()
    _install_current(monkeypatch, _current_report(client))

    invalid = await staleness.run_live_reconciliation_staleness_preflight(
        _ReadOnlySession({organization_id}),
        source_report_bytes=source_bytes,
        artifact_bytes=b"not json",
    )
    missing_organization = await staleness.run_live_reconciliation_staleness_preflight(
        _ReadOnlySession(set()),
        source_report_bytes=source_bytes,
        artifact_bytes=_artifact(source_bytes, client),
    )

    assert invalid.valid is False
    assert invalid.stale is True
    assert "malformed_json" in {issue.code for issue in invalid.issues}
    assert missing_organization.valid is False
    assert missing_organization.stale is True
    assert "organization_not_found" in {issue.code for issue in missing_organization.issues}
