from uuid import uuid4

import pytest

from app.application.enquiry_service import EnquiryService
from app.application.errors.exceptions import ConflictError, NotFoundError, ValidationError


class Parties:
    def __init__(self, allowed):
        self.allowed = allowed

    async def get_by_id_in_organization(self, party, organization):
        return object() if party in self.allowed else None


class Repository:
    def __init__(self):
        self.enquiries = {}
        self.quotations = {}
        self.revisions = {}
        self.locked = []

    async def get(self, organization, enquiry):
        return self.enquiries.get((organization, enquiry))

    async def list(self, organization, **_):
        return [x for (org, _), x in self.enquiries.items() if org == organization]

    async def count(self, organization):
        return len(await self.list(organization))

    async def add(self, row):
        self.enquiries[(row.organization_id, row.id)] = row
        return row

    async def update(self, row):
        return row

    async def get_quotation(self, organization, enquiry, quotation):
        return self.quotations.get((organization, enquiry, quotation))

    async def list_quotations(self, organization, enquiry, **_):
        return [
            x
            for (org, enq, _), x in self.quotations.items()
            if (org, enq) == (organization, enquiry)
        ]

    async def count_quotations(self, organization, enquiry):
        return len(await self.list_quotations(organization, enquiry))

    async def add_quotation(self, row):
        self.quotations[(row.organization_id, row.enquiry_id, row.id)] = row
        return row

    async def lock_quotation(self, organization, enquiry, quotation):
        self.locked.append(quotation)
        return await self.get_quotation(organization, enquiry, quotation)

    async def next_revision_ordinal(self, quotation):
        return 1 + max(
            (x.ordinal for x in self.revisions.values() if x.quotation_id == quotation), default=0
        )

    async def add_revision(self, row):
        self.revisions[(row.organization_id, row.quotation_id, row.id)] = row
        return row

    async def get_revision(self, organization, quotation, revision):
        return self.revisions.get((organization, quotation, revision))

    async def list_revisions(self, organization, quotation):
        return sorted(
            [
                x
                for (org, quote, _), x in self.revisions.items()
                if (org, quote) == (organization, quotation)
            ],
            key=lambda x: x.ordinal,
        )

    async def update_revision(self, row):
        return row


@pytest.mark.asyncio
async def test_prospect_party_link_and_bounded_update() -> None:
    org, party, actor = uuid4(), uuid4(), uuid4()
    repo = Repository()
    service = EnquiryService(repo, Parties({party}))
    enquiry = await service.create(
        org, {"prospect_display_name": "Prospect", "prospect_source": "web"}, actor
    )
    assert enquiry.party_id is None
    await service.link_party(org, enquiry.id, party, actor)
    updated = await service.update(
        org, enquiry.id, {"prospect_display_name": "Updated", "party_id": uuid4()}, actor
    )
    assert updated.party_id == party and updated.prospect_display_name == "Updated"
    with pytest.raises(ValidationError):
        await service.create(org, {"party_id": uuid4()}, actor)


@pytest.mark.asyncio
async def test_hierarchy_ordinal_and_one_time_issuance() -> None:
    org, actor = uuid4(), uuid4()
    repo = Repository()
    service = EnquiryService(repo, Parties(set()))
    enquiry = await service.create(org, {"prospect_display_name": "P"}, actor)
    quote = await service.create_quotation(org, enquiry.id, actor)
    first = await service.create_revision(org, enquiry.id, quote.id, {"scope": "first"}, actor)
    second = await service.create_revision(org, enquiry.id, quote.id, {"scope": "second"}, actor)
    assert [first.ordinal, second.ordinal] == [1, 2] and repo.locked == [quote.id, quote.id]
    issued = await service.issue(org, enquiry.id, quote.id, first.id, actor)
    assert issued.issued_by == actor and issued.issued_at is not None
    with pytest.raises(ConflictError):
        await service.issue(org, enquiry.id, quote.id, first.id, actor)
    with pytest.raises(NotFoundError):
        await service.revision(org, enquiry.id, uuid4(), first.id)


@pytest.mark.asyncio
async def test_requires_prospect_evidence_until_party_linked() -> None:
    org, actor = uuid4(), uuid4()
    repo = Repository()
    service = EnquiryService(repo, Parties(set()))
    with pytest.raises(ValidationError):
        await service.create(org, {}, actor)
    enquiry = await service.create(org, {"prospect_display_name": "P"}, actor)
    with pytest.raises(ValidationError):
        await service.update(org, enquiry.id, {"prospect_display_name": None}, actor)
