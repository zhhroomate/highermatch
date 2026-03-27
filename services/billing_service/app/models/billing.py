"""
Billing Models
HigherMatch™ AI Recruitment Platform

SQLAlchemy async ORM models for billing service.
All monetary amounts are stored as integers in 'fen' (cents) to avoid floating-point precision issues.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    String, Integer, Boolean, DateTime, Text, Index,
    ForeignKey, Enum as SQLEnum, BigInteger
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


class InvoiceStatus(str, Enum):
    """Invoice status enumeration"""
    PENDING = "pending"       # Invoice created, awaiting payment
    PAID = "paid"           # Payment confirmed
    CANCELLED = "cancelled"  # Invoice cancelled
    REFUNDED = "refunded"    # Payment refunded


class Base(DeclarativeBase):
    """Base class for all models"""
    pass


class Employer(Base):
    """Employer model for billing"""
    __tablename__ = "employers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<Employer(id={self.id}, company={self.company_name})>"


class Invoice(Base):
    """
    Invoice model for billing.

    IMPORTANT: All monetary amounts (base_fee, urgent_premium, total_fee) are stored
    as integers in 'fen' (cents) to avoid floating-point precision issues.
    Example: ¥10,000.00 -> 1000000 (fen)
    """
    __tablename__ = "invoices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    invoice_no: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    # Foreign keys
    employer_id: Mapped[str] = mapped_column(String(36), nullable=False)
    job_id: Mapped[str] = mapped_column(String(36), nullable=False)

    # Status
    status: Mapped[InvoiceStatus] = mapped_column(
        SQLEnum(InvoiceStatus, native_enum=False),
        default=InvoiceStatus.PENDING,
        nullable=False
    )

    # Billing details - all stored as integers in fen (cents)
    # offer_annual_salary: Annual salary in fen (e.g., 12000000 = ¥120,000)
    offer_annual_salary: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # Commission: 10% default rate
    commission_rate: Mapped[int] = mapped_column(Integer, default=10, nullable=False)

    # base_fee = offer_annual_salary * commission_rate / 100, stored as fen
    base_fee: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # Urgent premium: 30% of base_fee if is_urgent=True, stored as fen
    is_urgent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    urgent_premium: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)

    # Total fee = base_fee + urgent_premium, stored as fen
    total_fee: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # Payment info
    payment_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Metadata
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    # Indexes for performance
    __table_args__ = (
        Index("ix_invoices_employer_id", "employer_id"),
        Index("ix_invoices_job_id", "job_id"),
        Index("ix_invoices_status", "status"),
        Index("ix_invoices_created_at", "created_at"),
        Index("ix_invoices_invoice_no", "invoice_no"),
    )

    def __repr__(self) -> str:
        return f"<Invoice(id={self.id}, no={self.invoice_no}, status={self.status}, total={self.total_fee})>"

    def to_dict(self) -> dict:
        """Convert to dictionary with monetary values converted to yuan"""
        return {
            "id": self.id,
            "invoice_no": self.invoice_no,
            "employer_id": self.employer_id,
            "job_id": self.job_id,
            "status": self.status.value,
            "offer_annual_salary_yuan": self.offer_annual_salary / 100,
            "commission_rate": self.commission_rate,
            "base_fee_yuan": self.base_fee / 100,
            "is_urgent": self.is_urgent,
            "urgent_premium_yuan": self.urgent_premium / 100,
            "total_fee_yuan": self.total_fee / 100,
            "payment_url": self.payment_url,
            "paid_at": self.paid_at.isoformat() if self.paid_at else None,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class PaymentCallback(Base):
    """Payment callback log for audit trail"""
    __tablename__ = "payment_callbacks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    invoice_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("invoices.id"), nullable=False
    )

    # Callback data
    callback_id: Mapped[str] = mapped_column(String(100), nullable=False)
    signature: Mapped[str] = mapped_column(Text, nullable=False)
    raw_data: Mapped[str] = mapped_column(Text, nullable=False)

    # Processing result
    is_valid: Mapped[bool] = mapped_column(Boolean, default=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Indexes
    __table_args__ = (
        Index("ix_payment_callbacks_invoice_id", "invoice_id"),
        Index("ix_payment_callbacks_callback_id", "callback_id"),
    )

    def __repr__(self) -> str:
        return f"<PaymentCallback(id={self.id}, invoice={self.invoice_id}, valid={self.is_valid})>"
