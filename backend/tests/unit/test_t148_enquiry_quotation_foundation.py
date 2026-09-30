"""T148 ORM contract tests; conversion remains intentionally unimplemented."""

from app.infrastructure.persistence.models.enquiry import (
    Acceptance,
    Enquiry,
    Quotation,
    QuotationRevision,
)


def _constraint_names(model: type[object]) -> set[str]:
    return {constraint.name for constraint in model.__table__.constraints if constraint.name}


def test_enquiry_supports_party_link_or_bounded_prospect_evidence() -> None:
    assert {
        "organization_id",
        "party_id",
        "prospect_display_name",
        "prospect_phone",
        "prospect_email",
        "prospect_description",
        "prospect_source",
    } <= set(Enquiry.__table__.columns.keys())
    assert "ck_enquiries_party_or_prospect_evidence" in _constraint_names(Enquiry)
    assert "fk_enquiries_organization_id_parties" in _constraint_names(Enquiry)


def test_quotation_hierarchy_and_revision_ordinal_are_tenant_safe() -> None:
    assert "fk_quotations_organization_id_enquiries" in _constraint_names(Quotation)
    assert {
        "fk_quotation_revisions_organization_id_quotations",
        "ck_quotation_revisions_ordinal_positive",
        "uq_quotation_revisions_quotation_id_ordinal",
    } <= _constraint_names(QuotationRevision)
    assert "proposal_snapshot" in QuotationRevision.__table__.columns


def test_acceptance_preserves_exact_hierarchy_and_replay_keys() -> None:
    names = _constraint_names(Acceptance)
    assert {
        "fk_acceptances_organization_id_enquiries",
        "fk_acceptances_organization_id_enquiry_id_quotations",
        "fk_acceptances_organization_id_quotation_id_revisions",
        "fk_acceptances_organization_id_matters",
        "uq_acceptances_organization_id_enquiry_id",
        "uq_acceptances_organization_id_matter_id",
        "uq_acceptances_organization_id_quotation_revision_id",
        "uq_acceptances_organization_id_enquiry_id_idempotency_key",
    } <= names
    assert {"accepted_by", "accepted_at", "idempotency_key", "request_fingerprint"} <= set(
        Acceptance.__table__.columns.keys()
    )
