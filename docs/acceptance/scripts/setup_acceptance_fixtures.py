"""Setup controlled, reproducible operational acceptance test fixtures for T163.
Creates Organization A (Apex Legal Chambers) and Organization B (Beacon Law Associates)
with permitted (Advocate) and restricted (Read Only) test identities, baseline parties,
and properties.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.session import get_session_factory
from app.infrastructure.persistence.models.identity import Role, User, UserRole
from app.infrastructure.persistence.models.matter import Matter, MatterStatus, MatterType
from app.infrastructure.persistence.models.matter_property import MatterProperty
from app.infrastructure.persistence.models.organization import Organization
from app.infrastructure.persistence.models.party import MatterParty, Party
from app.infrastructure.persistence.models.property import Property
from app.infrastructure.persistence.models.file import File
from app.infrastructure.persistence.models.document import Document, DocumentVersion, DocumentType
from app.infrastructure.security.password_hasher import hash_password

ORG_A_ID = UUID("11111111-1111-4111-8111-111111111111")
ORG_B_ID = UUID("22222222-2222-4222-8222-222222222222")

USER_A1_ID = UUID("11111111-1111-4111-8111-000000000001") # Advocate Anita Roy (Org A)
USER_A2_ID = UUID("11111111-1111-4111-8111-000000000002") # Read Only Aaron Patel (Org A)
USER_B1_ID = UUID("22222222-2222-4222-8222-000000000001") # Advocate Brian Sen (Org B)

PARTY_A1_ID = UUID("11111111-1111-4111-8111-000000000010") # Sunita Sharma (Org A)
PARTY_B1_ID = UUID("22222222-2222-4222-8222-000000000010") # Vikram Patel (Org B)

PROPERTY_A1_ID = UUID("11111111-1111-4111-8111-000000000020") # Shanti Commercial Complex (Org A)
PROPERTY_B1_ID = UUID("22222222-2222-4222-8222-000000000020") # Beacon Logistics Park (Org B)

PASSWORD_PLAIN = "Password@Apex2026!"


async def setup_fixtures() -> None:
    factory = get_session_factory()
    async with factory() as session:
        print("Cleaning up previous acceptance test fixtures if present...")
        # Clean up child entities first
        await session.execute(delete(MatterProperty).where(MatterProperty.organization_id.in_([ORG_A_ID, ORG_B_ID])))
        await session.execute(delete(DocumentVersion).where(DocumentVersion.organization_id.in_([ORG_A_ID, ORG_B_ID])))
        await session.execute(delete(Document).where(Document.organization_id.in_([ORG_A_ID, ORG_B_ID])))
        await session.execute(delete(File).where(File.organization_id.in_([ORG_A_ID, ORG_B_ID])))
        await session.execute(delete(MatterParty).where(MatterParty.organization_id.in_([ORG_A_ID, ORG_B_ID])))
        await session.execute(delete(Matter).where(Matter.organization_id.in_([ORG_A_ID, ORG_B_ID])))
        await session.execute(delete(Property).where(Property.organization_id.in_([ORG_A_ID, ORG_B_ID])))
        await session.execute(delete(Party).where(Party.organization_id.in_([ORG_A_ID, ORG_B_ID])))
        await session.execute(delete(UserRole).where(UserRole.user_id.in_([USER_A1_ID, USER_A2_ID, USER_B1_ID])))
        await session.execute(delete(User).where(User.organization_id.in_([ORG_A_ID, ORG_B_ID])))
        await session.execute(delete(Organization).where(Organization.id.in_([ORG_A_ID, ORG_B_ID])))
        await session.flush()

        print("Creating Organizations...")
        org_a = Organization(
            id=ORG_A_ID,
            name="Apex Legal Chambers",
            legal_name="Apex Legal Chambers LLP",
        )
        org_b = Organization(
            id=ORG_B_ID,
            name="Beacon Law Associates",
            legal_name="Beacon Law Associates LLP",
        )
        session.add_all([org_a, org_b])
        await session.flush()

        # Find roles
        roles = (await session.execute(select(Role))).scalars().all()
        roles_by_name = {r.name: r for r in roles}
        advocate_role = roles_by_name["Advocate"]
        read_only_role = roles_by_name["Read Only"]

        print("Creating Test Users...")
        pwd_hash = hash_password(PASSWORD_PLAIN)

        user_a1 = User(
            id=USER_A1_ID,
            email="advocate.apex@example.com",
            full_name="Anita Roy",
            phone="+919820011111",
            password_hash=pwd_hash,
            is_active=True,
            organization_id=ORG_A_ID,
        )
        user_a2 = User(
            id=USER_A2_ID,
            email="readonly.apex@example.com",
            full_name="Aaron Patel",
            phone="+919820022222",
            password_hash=pwd_hash,
            is_active=True,
            organization_id=ORG_A_ID,
        )
        user_b1 = User(
            id=USER_B1_ID,
            email="advocate.beacon@example.com",
            full_name="Brian Sen",
            phone="+919820033333",
            password_hash=pwd_hash,
            is_active=True,
            organization_id=ORG_B_ID,
        )
        session.add_all([user_a1, user_a2, user_b1])
        await session.flush()

        print("Assigning Roles...")
        ur_a1 = UserRole(id=UUID("11111111-1111-4111-8111-000000000031"), user_id=USER_A1_ID, role_id=advocate_role.id, assigned_by=USER_A1_ID)
        ur_a2 = UserRole(id=UUID("11111111-1111-4111-8111-000000000032"), user_id=USER_A2_ID, role_id=read_only_role.id, assigned_by=USER_A1_ID)
        ur_b1 = UserRole(id=UUID("22222222-2222-4222-8222-000000000031"), user_id=USER_B1_ID, role_id=advocate_role.id, assigned_by=USER_B1_ID)
        session.add_all([ur_a1, ur_a2, ur_b1])
        await session.flush()

        print("Creating Base Parties...")
        party_a1 = Party(
            id=PARTY_A1_ID,
            organization_id=ORG_A_ID,
            party_type="individual",
            display_name="Sunita Sharma",
            primary_phone="+919876543210",
            primary_email="sunita.sharma@example.com",
            notes="Client for residential and commercial property matters.",
        )
        party_b1 = Party(
            id=PARTY_B1_ID,
            organization_id=ORG_B_ID,
            party_type="individual",
            display_name="Vikram Patel",
            primary_phone="+919876543299",
            primary_email="vikram.patel@example.com",
            notes="Client for commercial warehouse logistics.",
        )
        session.add_all([party_a1, party_b1])
        await session.flush()

        print("Creating Base Properties...")
        prop_a1 = Property(
            id=PROPERTY_A1_ID,
            organization_id=ORG_A_ID,
            property_type="commercial",
            survey_number="SRV-AHM-2026-302",
            sub_division_number="Plot-4",
            area_value=1250.00,
            area_unit="sq_ft",
        )
        prop_b1 = Property(
            id=PROPERTY_B1_ID,
            organization_id=ORG_B_ID,
            property_type="commercial",
            survey_number="SRV-BRD-2026-005",
            sub_division_number="Block-B",
            area_value=4500.00,
            area_unit="sq_ft",
        )
        session.add_all([prop_a1, prop_b1])
        await session.flush()

        await session.commit()
        print("Test fixtures successfully created and committed!")


if __name__ == "__main__":
    asyncio.run(setup_fixtures())
