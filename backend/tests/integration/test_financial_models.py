"""Schema-level tests for the financial models: check constraints and
required FKs.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.models.client import Client
from app.infrastructure.persistence.models.financial import Invoice, Payment, PaymentMethod, Receipt
from app.infrastructure.persistence.models.matter import Matter, MatterStatus, MatterType


async def _make_matter_and_client(session: AsyncSession) -> tuple[Matter, Client]:
    matter_type = MatterType(code=f"TYPE-{uuid4()}", name="Sale")
    status = MatterStatus(code=f"STATUS-{uuid4()}", name="Open")
    client = Client(full_name="Client", primary_phone="9876543210")
    session.add_all([matter_type, status, client])
    await session.flush()

    matter = Matter(
        matter_number=f"M-{uuid4()}",
        matter_type_id=matter_type.id,
        matter_status_id=status.id,
        client_id=client.id,
        title="Test",
        opened_at=datetime.now(UTC),
    )
    session.add(matter)
    await session.flush()
    return matter, client


class TestInvoice:
    async def test_valid_invoice_succeeds(self, db_session: AsyncSession) -> None:
        matter, client = await _make_matter_and_client(db_session)

        db_session.add(
            Invoice(
                invoice_number=f"INV-{uuid4()}",
                matter_id=matter.id,
                client_id=client.id,
                amount=1000,
                tax_amount=180,
                total_amount=1180,
                issued_at=datetime.now(UTC),
            )
        )
        await db_session.flush()

    async def test_negative_amount_is_rejected(self, db_session: AsyncSession) -> None:
        matter, client = await _make_matter_and_client(db_session)

        db_session.add(
            Invoice(
                invoice_number=f"INV-{uuid4()}",
                matter_id=matter.id,
                client_id=client.id,
                amount=-100,
                total_amount=0,
                issued_at=datetime.now(UTC),
            )
        )

        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_invoice_number_must_be_unique(self, db_session: AsyncSession) -> None:
        matter, client = await _make_matter_and_client(db_session)
        number = f"INV-{uuid4()}"
        db_session.add(
            Invoice(
                invoice_number=number,
                matter_id=matter.id,
                client_id=client.id,
                amount=100,
                total_amount=100,
                issued_at=datetime.now(UTC),
            )
        )
        await db_session.flush()

        db_session.add(
            Invoice(
                invoice_number=number,
                matter_id=matter.id,
                client_id=client.id,
                amount=200,
                total_amount=200,
                issued_at=datetime.now(UTC),
            )
        )
        with pytest.raises(IntegrityError):
            await db_session.flush()


class TestPayment:
    async def test_amount_must_be_positive(self, db_session: AsyncSession) -> None:
        matter, client = await _make_matter_and_client(db_session)
        method = PaymentMethod(code=f"PM-{uuid4()}", name="Cash")
        db_session.add(method)
        await db_session.flush()

        db_session.add(
            Payment(
                matter_id=matter.id,
                client_id=client.id,
                payment_method_id=method.id,
                amount=0,
                paid_at=datetime.now(UTC),
            )
        )

        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_requires_a_valid_payment_method(self, db_session: AsyncSession) -> None:
        matter, client = await _make_matter_and_client(db_session)

        db_session.add(
            Payment(
                matter_id=matter.id,
                client_id=client.id,
                payment_method_id=uuid4(),
                amount=500,
                paid_at=datetime.now(UTC),
            )
        )

        with pytest.raises(IntegrityError):
            await db_session.flush()


class TestReceipt:
    async def test_requires_an_existing_payment(self, db_session: AsyncSession) -> None:
        db_session.add(
            Receipt(
                payment_id=uuid4(), receipt_number=f"RCPT-{uuid4()}", issued_at=datetime.now(UTC)
            )
        )

        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_receipt_number_must_be_unique(self, db_session: AsyncSession) -> None:
        matter, client = await _make_matter_and_client(db_session)
        method = PaymentMethod(code=f"PM-{uuid4()}", name="Cash")
        db_session.add(method)
        await db_session.flush()

        payment = Payment(
            matter_id=matter.id,
            client_id=client.id,
            payment_method_id=method.id,
            amount=500,
            paid_at=datetime.now(UTC),
        )
        db_session.add(payment)
        await db_session.flush()

        number = f"RCPT-{uuid4()}"
        db_session.add(
            Receipt(payment_id=payment.id, receipt_number=number, issued_at=datetime.now(UTC))
        )
        await db_session.flush()

        db_session.add(
            Receipt(payment_id=payment.id, receipt_number=number, issued_at=datetime.now(UTC))
        )
        with pytest.raises(IntegrityError):
            await db_session.flush()
