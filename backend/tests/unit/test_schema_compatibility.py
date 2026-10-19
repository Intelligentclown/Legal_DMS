"""Unit coverage for ADR-0047's release-bound compatibility authority."""

from __future__ import annotations

import pytest

from app.application.interfaces.install_classifier import InstallationClassificationError
from app.infrastructure.persistence.schema_compatibility import SchemaCompatibilityAuthority


def test_every_approved_bootstrap_revision_is_an_ancestor_of_the_runtime_head() -> None:
    authority = SchemaCompatibilityAuthority()

    for bootstrap_revision in authority.approved_lineage:
        authority.validate_current_revision(authority.approved_runtime_head)
        authority.validate_bootstrap_ancestry(bootstrap_revision, authority.approved_runtime_head)


@pytest.mark.parametrize(
    "current_revision",
    ("cdcfd7df5fde", "unknown-revision"),
)
def test_non_head_or_unknown_current_revision_is_fail_closed(current_revision: str) -> None:
    with pytest.raises(InstallationClassificationError):
        SchemaCompatibilityAuthority().validate_current_revision(current_revision)


def test_bootstrap_revision_after_current_revision_is_fail_closed() -> None:
    authority = SchemaCompatibilityAuthority()

    with pytest.raises(InstallationClassificationError, match="downgrade"):
        authority.validate_bootstrap_ancestry("b155caa6d4e1", "cdcfd7df5fde")
