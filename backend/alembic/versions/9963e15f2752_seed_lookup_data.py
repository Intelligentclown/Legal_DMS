"""seed lookup data

Populates lookup/reference tables only — no schema changes. Uses
`sa.table()` "shadow" definitions (a lightweight, migration-local
column subset) rather than importing the ORM models, per Alembic's
recommended pattern: migrations must keep working even if a future
model change alters these classes.

Deliberately NOT seeded here: `role_permissions` (which permissions
each role gets is an authorization business decision with no
consuming feature yet — better made by the stage that actually
implements authorization, not guessed at during schema seeding) and
`users` (no auth exists to log in with).

Revision ID: 9963e15f2752
Revises: 5c13f11da784
Create Date: 2026-08-05 14:55:31.846619

"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "9963e15f2752"
down_revision: str | Sequence[str] | None = "5c13f11da784"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    countries = sa.table(
        "countries",
        sa.column("id", sa.Uuid()),
        sa.column("name", sa.String()),
        sa.column("iso_code", sa.String()),
    )
    india_id = uuid.uuid4()
    op.bulk_insert(countries, [{"id": india_id, "name": "India", "iso_code": "IND"}])

    states = sa.table(
        "states",
        sa.column("id", sa.Uuid()),
        sa.column("country_id", sa.Uuid()),
        sa.column("name", sa.String()),
        sa.column("code", sa.String()),
    )
    indian_states = [
        ("Andhra Pradesh", "AP"),
        ("Arunachal Pradesh", "AR"),
        ("Assam", "AS"),
        ("Bihar", "BR"),
        ("Chhattisgarh", "CG"),
        ("Goa", "GA"),
        ("Gujarat", "GJ"),
        ("Haryana", "HR"),
        ("Himachal Pradesh", "HP"),
        ("Jharkhand", "JH"),
        ("Karnataka", "KA"),
        ("Kerala", "KL"),
        ("Madhya Pradesh", "MP"),
        ("Maharashtra", "MH"),
        ("Manipur", "MN"),
        ("Meghalaya", "ML"),
        ("Mizoram", "MZ"),
        ("Nagaland", "NL"),
        ("Odisha", "OD"),
        ("Punjab", "PB"),
        ("Rajasthan", "RJ"),
        ("Sikkim", "SK"),
        ("Tamil Nadu", "TN"),
        ("Telangana", "TG"),
        ("Tripura", "TR"),
        ("Uttar Pradesh", "UP"),
        ("Uttarakhand", "UK"),
        ("West Bengal", "WB"),
        ("Andaman and Nicobar Islands", "AN"),
        ("Chandigarh", "CH"),
        ("Dadra and Nagar Haveli and Daman and Diu", "DN"),
        ("Delhi", "DL"),
        ("Jammu and Kashmir", "JK"),
        ("Ladakh", "LA"),
        ("Lakshadweep", "LD"),
        ("Puducherry", "PY"),
    ]
    state_ids: dict[str, uuid.UUID] = {name: uuid.uuid4() for name, _ in indian_states}
    op.bulk_insert(
        states,
        [
            {"id": state_ids[name], "country_id": india_id, "name": name, "code": code}
            for name, code in indian_states
        ],
    )

    # Gujarat districts only, for now -- the practice this system is built for
    # operates there (survey-number/taluka/village terminology throughout the
    # schema). Other states get their districts added when a real need arises.
    districts = sa.table(
        "districts",
        sa.column("id", sa.Uuid()),
        sa.column("state_id", sa.Uuid()),
        sa.column("name", sa.String()),
    )
    gujarat_districts = [
        "Ahmedabad",
        "Amreli",
        "Anand",
        "Aravalli",
        "Banaskantha",
        "Bharuch",
        "Bhavnagar",
        "Botad",
        "Chhota Udaipur",
        "Dahod",
        "Dang",
        "Devbhoomi Dwarka",
        "Gandhinagar",
        "Gir Somnath",
        "Jamnagar",
        "Junagadh",
        "Kheda",
        "Kutch",
        "Mahisagar",
        "Mehsana",
        "Morbi",
        "Narmada",
        "Navsari",
        "Panchmahal",
        "Patan",
        "Porbandar",
        "Rajkot",
        "Sabarkantha",
        "Surat",
        "Surendranagar",
        "Tapi",
        "Vadodara",
        "Valsad",
    ]
    op.bulk_insert(
        districts,
        [
            {"id": uuid.uuid4(), "state_id": state_ids["Gujarat"], "name": name}
            for name in gujarat_districts
        ],
    )

    roles = sa.table(
        "roles",
        sa.column("id", sa.Uuid()),
        sa.column("name", sa.String()),
        sa.column("description", sa.String()),
        sa.column("is_system_role", sa.Boolean()),
    )
    op.bulk_insert(
        roles,
        [
            {
                "id": uuid.uuid4(),
                "name": "Administrator",
                "description": "Full system access",
                "is_system_role": True,
            },
            {
                "id": uuid.uuid4(),
                "name": "Advocate",
                "description": "Handles matters and client relationships",
                "is_system_role": False,
            },
            {
                "id": uuid.uuid4(),
                "name": "Paralegal",
                "description": "Assists advocates with matters and documents",
                "is_system_role": False,
            },
            {
                "id": uuid.uuid4(),
                "name": "Clerk",
                "description": "Handles filing, scheduling, and data entry",
                "is_system_role": False,
            },
            {
                "id": uuid.uuid4(),
                "name": "Accountant",
                "description": "Handles invoices, payments, and receipts",
                "is_system_role": False,
            },
            {
                "id": uuid.uuid4(),
                "name": "Read Only",
                "description": "View-only access across the system",
                "is_system_role": False,
            },
        ],
    )

    permissions = sa.table(
        "permissions",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String()),
        sa.column("description", sa.String()),
        sa.column("category", sa.String()),
    )
    permission_rows = [
        ("matters:read", "View matters", "matters"),
        ("matters:write", "Create and edit matters", "matters"),
        ("matters:delete", "Delete matters", "matters"),
        ("clients:read", "View clients", "clients"),
        ("clients:write", "Create and edit clients", "clients"),
        ("clients:delete", "Delete clients", "clients"),
        ("properties:read", "View properties", "properties"),
        ("properties:write", "Create and edit properties", "properties"),
        ("properties:delete", "Delete properties", "properties"),
        ("documents:read", "View documents", "documents"),
        ("documents:write", "Create and edit documents", "documents"),
        ("documents:delete", "Delete documents", "documents"),
        ("financial:read", "View invoices, payments, and receipts", "financial"),
        ("financial:write", "Create and edit invoices, payments, and receipts", "financial"),
        ("users:manage", "Manage users and role assignments", "administration"),
        ("roles:manage", "Manage roles and permissions", "administration"),
        ("settings:manage", "Manage application settings and feature flags", "administration"),
        ("reports:read", "View reports", "reports"),
    ]
    op.bulk_insert(
        permissions,
        [
            {"id": uuid.uuid4(), "code": code, "description": description, "category": category}
            for code, description, category in permission_rows
        ],
    )

    matter_types = sa.table(
        "matter_types",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String()),
        sa.column("name", sa.String()),
        sa.column("description", sa.String()),
        sa.column("is_active", sa.Boolean()),
        sa.column("sort_order", sa.Integer()),
    )
    matter_type_rows = [
        ("SALE_DEED", "Sale Deed / Property Sale"),
        ("REGISTRATION", "Property Registration"),
        ("TITLE_SEARCH", "Title Search & Due Diligence"),
        ("MORTGAGE", "Mortgage & Loan Documentation"),
        ("LEASE", "Lease Agreement"),
        ("WILL_SUCCESSION", "Will & Succession"),
        ("PARTITION", "Partition Deed"),
        ("POA", "Power of Attorney"),
    ]
    op.bulk_insert(
        matter_types,
        [
            {
                "id": uuid.uuid4(),
                "code": code,
                "name": name,
                "description": None,
                "is_active": True,
                "sort_order": i,
            }
            for i, (code, name) in enumerate(matter_type_rows)
        ],
    )

    matter_statuses = sa.table(
        "matter_statuses",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String()),
        sa.column("name", sa.String()),
        sa.column("sort_order", sa.Integer()),
        sa.column("is_terminal", sa.Boolean()),
    )
    matter_status_rows = [
        ("OPEN", "Open", False),
        ("IN_PROGRESS", "In Progress", False),
        ("PENDING_REVIEW", "Pending Review", False),
        ("ON_HOLD", "On Hold", False),
        ("CLOSED", "Closed", True),
        ("CANCELLED", "Cancelled", True),
    ]
    op.bulk_insert(
        matter_statuses,
        [
            {
                "id": uuid.uuid4(),
                "code": code,
                "name": name,
                "sort_order": i,
                "is_terminal": is_terminal,
            }
            for i, (code, name, is_terminal) in enumerate(matter_status_rows)
        ],
    )

    workflow_definitions = sa.table(
        "workflow_definitions",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String()),
        sa.column("name", sa.String()),
        sa.column("description", sa.String()),
        sa.column("is_active", sa.Boolean()),
    )
    matter_lifecycle_id = uuid.uuid4()
    op.bulk_insert(
        workflow_definitions,
        [
            {
                "id": matter_lifecycle_id,
                "code": "matter_lifecycle",
                "name": "Matter Lifecycle",
                "description": "Starter workflow tracking a matter from open to close",
                "is_active": True,
            }
        ],
    )

    workflow_states = sa.table(
        "workflow_states",
        sa.column("id", sa.Uuid()),
        sa.column("workflow_definition_id", sa.Uuid()),
        sa.column("code", sa.String()),
        sa.column("name", sa.String()),
        sa.column("sort_order", sa.Integer()),
        sa.column("is_initial", sa.Boolean()),
        sa.column("is_final", sa.Boolean()),
    )
    workflow_state_rows = [
        ("OPEN", "Open", True, False),
        ("IN_PROGRESS", "In Progress", False, False),
        ("PENDING_REVIEW", "Pending Review", False, False),
        ("ON_HOLD", "On Hold", False, False),
        ("CLOSED", "Closed", False, True),
        ("CANCELLED", "Cancelled", False, True),
    ]
    op.bulk_insert(
        workflow_states,
        [
            {
                "id": uuid.uuid4(),
                "workflow_definition_id": matter_lifecycle_id,
                "code": code,
                "name": name,
                "sort_order": i,
                "is_initial": is_initial,
                "is_final": is_final,
            }
            for i, (code, name, is_initial, is_final) in enumerate(workflow_state_rows)
        ],
    )

    document_types = sa.table(
        "document_types",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String()),
        sa.column("name", sa.String()),
        sa.column("description", sa.String()),
        sa.column("is_active", sa.Boolean()),
    )
    document_type_rows = [
        ("SALE_DEED", "Sale Deed"),
        ("AGREEMENT_TO_SELL", "Agreement to Sell"),
        ("POA", "Power of Attorney"),
        ("TITLE_SEARCH_REPORT", "Title Search Report"),
        ("ENCUMBRANCE_CERTIFICATE", "Encumbrance Certificate"),
        ("MUTATION_EXTRACT", "Mutation Extract (7/12)"),
        ("PROPERTY_TAX_RECEIPT", "Property Tax Receipt"),
        ("IDENTITY_PROOF", "Identity Proof"),
        ("COURT_ORDER", "Court Order"),
        ("AFFIDAVIT", "Affidavit"),
    ]
    op.bulk_insert(
        document_types,
        [
            {"id": uuid.uuid4(), "code": code, "name": name, "description": None, "is_active": True}
            for code, name in document_type_rows
        ],
    )

    payment_methods = sa.table(
        "payment_methods",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String()),
        sa.column("name", sa.String()),
        sa.column("is_active", sa.Boolean()),
    )
    payment_method_rows = [
        ("CASH", "Cash"),
        ("CHEQUE", "Cheque"),
        ("BANK_TRANSFER", "Bank Transfer (NEFT/RTGS)"),
        ("UPI", "UPI"),
        ("CARD", "Credit/Debit Card"),
        ("DEMAND_DRAFT", "Demand Draft"),
    ]
    op.bulk_insert(
        payment_methods,
        [
            {"id": uuid.uuid4(), "code": code, "name": name, "is_active": True}
            for code, name in payment_method_rows
        ],
    )

    application_settings = sa.table(
        "application_settings",
        sa.column("id", sa.Uuid()),
        sa.column("key", sa.String()),
        sa.column("value", postgresql.JSONB()),
        sa.column("description", sa.String()),
    )
    application_setting_rows = [
        (
            "app.name",
            {"value": "Legal Document & Matter Management System"},
            "Display name shown in the UI",
        ),
        ("app.timezone", {"value": "Asia/Kolkata"}, "Default timezone for scheduling and display"),
        ("app.date_format", {"value": "DD/MM/YYYY"}, "Default date display format"),
        ("app.default_currency", {"value": "INR"}, "Default currency for financial records"),
        ("app.max_upload_size_mb", {"value": 50}, "Maximum file upload size in megabytes"),
        ("app.session_timeout_minutes", {"value": 30}, "Idle session timeout in minutes"),
    ]
    op.bulk_insert(
        application_settings,
        [
            {"id": uuid.uuid4(), "key": key, "value": value, "description": description}
            for key, value, description in application_setting_rows
        ],
    )

    feature_flags = sa.table(
        "feature_flags",
        sa.column("id", sa.Uuid()),
        sa.column("name", sa.String()),
        sa.column("is_enabled", sa.Boolean()),
        sa.column("description", sa.String()),
    )
    feature_flag_rows = [
        ("ocr_pipeline", "Automatic OCR processing of uploaded documents"),
        ("ai_drafting", "AI-assisted document drafting"),
        ("e_signature", "Electronic signature capture on documents"),
        ("client_portal", "Self-service client portal"),
        ("cloud_sync", "Cloud synchronization of local data"),
    ]
    op.bulk_insert(
        feature_flags,
        [
            {"id": uuid.uuid4(), "name": name, "is_enabled": False, "description": description}
            for name, description in feature_flag_rows
        ],
    )


def downgrade() -> None:
    """Downgrade schema."""
    for table in (
        "feature_flags",
        "application_settings",
        "payment_methods",
        "document_types",
        "workflow_states",
        "workflow_definitions",
        "matter_statuses",
        "matter_types",
        "permissions",
        "roles",
        "districts",
        "states",
        "countries",
    ):
        op.execute(f"DELETE FROM {table}")
