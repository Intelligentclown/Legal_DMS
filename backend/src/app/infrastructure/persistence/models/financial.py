"""Financial schema: PaymentMethods (lookup), Invoices, Payments, Receipts."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base
from app.infrastructure.persistence.models.mixins import AuditMixin


class PaymentMethod(Base):
    __tablename__ = "payment_methods"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class Invoice(Base, AuditMixin):
    __tablename__ = "invoices"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="amount_non_negative"),
        CheckConstraint("tax_amount >= 0", name="tax_amount_non_negative"),
        CheckConstraint("total_amount >= 0", name="total_amount_non_negative"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    invoice_number: Mapped[str] = mapped_column(String(50), unique=True)
    matter_id: Mapped[UUID] = mapped_column(ForeignKey("matters.id"), index=True)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("clients.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, server_default="0")
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    status: Mapped[str] = mapped_column(String(50), default="draft")
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Payment(Base, AuditMixin):
    __tablename__ = "payments"
    __table_args__ = (CheckConstraint("amount > 0", name="amount_positive"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    invoice_id: Mapped[UUID | None] = mapped_column(ForeignKey("invoices.id"), index=True)
    matter_id: Mapped[UUID] = mapped_column(ForeignKey("matters.id"), index=True)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("clients.id"), index=True)
    payment_method_id: Mapped[UUID] = mapped_column(ForeignKey("payment_methods.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    reference_number: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(50), default="completed")


class Receipt(Base, AuditMixin):
    __tablename__ = "receipts"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    payment_id: Mapped[UUID] = mapped_column(ForeignKey("payments.id"), index=True)
    receipt_number: Mapped[str] = mapped_column(String(50), unique=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    file_storage_record_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("file_storage_records.id")
    )
