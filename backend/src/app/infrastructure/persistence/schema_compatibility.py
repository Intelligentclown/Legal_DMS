"""Release-bound schema compatibility authority for ADR-0047 (T165).

This module deliberately contains no Alembic discovery or database access.  It
is the reviewed application-release contract that says which historical
operational-fresh bootstrap revisions may lead to this runtime's current schema.
"""

from __future__ import annotations

from app.application.interfaces.install_classifier import InstallationClassificationError


class SchemaCompatibilityAuthority:
    """Validate the approved, linear operational-fresh schema lineage."""

    provenance_contract_version = "adr-0037.v1"
    approved_lineage: tuple[str, ...] = (
        "c4e7a9b2d6f1",
        "5d8a3f2e9c6b",
        "7f1b9c3d4a2e",
        "9e6a4b2c8d1f",
        "b8c4d2e1f7a9",
        "be439c0d6fdb",
        "cdcfd7df5fde",
        "e148c0f5a8b2",
        "8d77007b9d7f",
        "b155caa6d4e1",
    )
    approved_runtime_head = approved_lineage[-1]

    def validate_current_revision(self, revision: str) -> None:
        """Require this database to be at this release's exact approved head."""
        if revision not in self.approved_lineage:
            raise InstallationClassificationError("unsupported or divergent schema revision")
        if revision != self.approved_runtime_head:
            raise InstallationClassificationError("schema downgrade detected")

    def validate_bootstrap_ancestry(self, bootstrap_revision: str, current_revision: str) -> None:
        """Require approved directional bootstrap-to-current ancestry."""
        try:
            bootstrap_position = self.approved_lineage.index(bootstrap_revision)
            current_position = self.approved_lineage.index(current_revision)
        except ValueError as exc:
            raise InstallationClassificationError(
                "unsupported or divergent schema revision"
            ) from exc
        if bootstrap_position > current_position:
            raise InstallationClassificationError("schema downgrade detected")
