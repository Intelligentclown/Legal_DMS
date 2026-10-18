"""T157 Matter-owned canonical MatterProperty application operations."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from app.application.errors.exceptions import NotFoundError
from app.application.interfaces.audit import AuditLogger
from app.application.interfaces.auth import CurrentUser
from app.application.interfaces.matter_property_repository import MatterPropertyRepository
from app.application.interfaces.matter_repository import MatterRepository
from app.application.interfaces.property_repository import PropertyRepository
from app.infrastructure.persistence.models.matter import Matter
from app.infrastructure.persistence.models.matter_property import MatterProperty
from app.infrastructure.persistence.models.property import Property, PropertyOwner


class MatterPropertyService:
    """Coordinates the bounded Matter-scoped association contract.

    The service deliberately resolves both endpoints under the trusted
    Organization before touching the association.  The join table remains
    the only source for canonical reads and writes.
    """

    def __init__(
        self,
        matter_repository: MatterRepository,
        property_repository: PropertyRepository,
        association_repository: MatterPropertyRepository,
        audit_logger: AuditLogger,
    ) -> None:
        self._matter_repository = matter_repository
        self._property_repository = property_repository
        self._association_repository = association_repository
        self._audit_logger = audit_logger

    async def list_properties(self, matter_id: UUID, organization_id: UUID) -> Sequence[Property]:
        await self._get_matter(matter_id, organization_id)
        return await self._association_repository.list_properties(matter_id, organization_id)

    async def associate(
        self,
        matter_id: UUID,
        property_id: UUID,
        organization_id: UUID,
        actor: CurrentUser,
    ) -> tuple[Property, bool]:
        await self._get_matter(matter_id, organization_id)
        property_ = await self._get_property(property_id, organization_id)
        created = await self._association_repository.add_if_absent(
            MatterProperty(
                organization_id=organization_id,
                matter_id=matter_id,
                property_id=property_id,
            )
        )
        if created:
            await self._audit_logger.record(
                actor=actor,
                action="matter_property_associated",
                resource_type="matter_property",
                resource_id=str(matter_id),
                metadata={"property_id": str(property_id)},
            )
        return property_, created

    async def owners(self, property_: Property) -> Sequence[PropertyOwner]:
        return await self._property_repository.list_owners(property_.id, property_.organization_id)

    async def unlink(
        self,
        matter_id: UUID,
        property_id: UUID,
        organization_id: UUID,
        actor: CurrentUser,
    ) -> bool:
        await self._get_matter(matter_id, organization_id)
        await self._get_property(property_id, organization_id)
        removed = await self._association_repository.remove_if_present(
            matter_id, property_id, organization_id
        )
        if removed:
            await self._audit_logger.record(
                actor=actor,
                action="matter_property_unlinked",
                resource_type="matter_property",
                resource_id=str(matter_id),
                metadata={"property_id": str(property_id)},
            )
        return removed

    async def _get_matter(self, matter_id: UUID, organization_id: UUID) -> Matter:
        matter = await self._matter_repository.get_by_id_in_organization(matter_id, organization_id)
        if matter is None:
            raise NotFoundError(f"Matter with id {matter_id} was not found")
        return matter

    async def _get_property(self, property_id: UUID, organization_id: UUID) -> Property:
        property_ = await self._property_repository.get_by_id_in_organization(
            property_id, organization_id
        )
        if property_ is None:
            raise NotFoundError(f"Property with id {property_id} was not found")
        return property_
