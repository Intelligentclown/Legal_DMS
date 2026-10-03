"""Organization-scoped persistence contract for T149 pre-engagement records."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from uuid import UUID

from app.infrastructure.persistence.models.enquiry import Enquiry, Quotation, QuotationRevision


class EnquiryRepository(ABC):
    @abstractmethod
    async def get(self, organization_id: UUID, enquiry_id: UUID) -> Enquiry | None: ...

    @abstractmethod
    async def list(
        self, organization_id: UUID, *, limit: int, offset: int
    ) -> Sequence[Enquiry]: ...

    @abstractmethod
    async def count(self, organization_id: UUID) -> int: ...

    @abstractmethod
    async def add(self, enquiry: Enquiry) -> Enquiry: ...

    @abstractmethod
    async def update(self, enquiry: Enquiry) -> Enquiry: ...

    @abstractmethod
    async def get_quotation(
        self, organization_id: UUID, enquiry_id: UUID, quotation_id: UUID
    ) -> Quotation | None: ...

    @abstractmethod
    async def list_quotations(
        self, organization_id: UUID, enquiry_id: UUID, *, limit: int, offset: int
    ) -> Sequence[Quotation]: ...

    @abstractmethod
    async def count_quotations(self, organization_id: UUID, enquiry_id: UUID) -> int: ...

    @abstractmethod
    async def add_quotation(self, quotation: Quotation) -> Quotation: ...

    @abstractmethod
    async def lock_quotation(
        self, organization_id: UUID, enquiry_id: UUID, quotation_id: UUID
    ) -> Quotation | None: ...

    @abstractmethod
    async def next_revision_ordinal(self, quotation_id: UUID) -> int: ...

    @abstractmethod
    async def add_revision(self, revision: QuotationRevision) -> QuotationRevision: ...

    @abstractmethod
    async def get_revision(
        self, organization_id: UUID, quotation_id: UUID, revision_id: UUID
    ) -> QuotationRevision | None: ...

    @abstractmethod
    async def list_revisions(
        self, organization_id: UUID, quotation_id: UUID
    ) -> Sequence[QuotationRevision]: ...

    @abstractmethod
    async def update_revision(self, revision: QuotationRevision) -> QuotationRevision: ...
