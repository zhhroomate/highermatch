"""
Guarantee Models
HigherMatch™ AI Recruitment Platform

SQLAlchemy async ORM models for guarantee service.
"""

from datetime import datetime, date
from enum import Enum
from typing import Optional, List

from sqlalchemy import String, Integer, Boolean, DateTime, Text, Date, ForeignKey, Enum as SQLEnum, BigInteger
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class GuaranteeStatus(str, Enum):
    """Guarantee status enumeration"""
    ACTIVE = "active"           # Guarantee is active
    EXPIRED = "expired"        # Guarantee has expired
    CLAIMED = "claimed"        # Guarantee has been claimed
    VOID = "void"             # Guarantee has been voided


class ClaimStatus(str, Enum):
    """Claim status enumeration"""
    PENDING = "pending"        # Claim is pending review
    APPROVED = "approved"      # Claim has been approved
    REJECTED = "rejected"     # Claim has been rejected
    PROCESSING = "processing"  # Claim is being processed


class Base(DeclarativeBase):
    """Base class for all models"""
    pass


class Guarantee(Base):
    """
    Guarantee model for job placement guarantee.

    Guarantee period: 90 days from start_date
    """
    __tablename__ = "guarantees"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    guarantee_no: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    # Foreign keys
    employer_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    job_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    invoice_id: Mapped[str] = mapped_column(String(36), nullable=False)

    # Guarantee details
    status: Mapped[GuaranteeStatus] = mapped_column(
        SQLEnum(GuaranteeStatus, native_enum=False),
        default=GuaranteeStatus.ACTIVE,
        nullable=False
    )

    # Dates - guarantee period is 90 days
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    expiry_date: Mapped[date] = mapped_column(Date, nullable=False)
    # total_fee stored as fen (cents)
    total_fee: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    # Relationships
    claims: Mapped[List["GuaranteeClaim"]] = relationship(
        "GuaranteeClaim", back_populates="guarantee", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Guarantee(id={self.id}, no={self.guarantee_no}, status={self.status})>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "guarantee_no": self.guarantee_no,
            "employer_id": self.employer_id,
            "job_id": self.job_id,
            "invoice_id": self.invoice_id,
            "status": self.status.value,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
            "total_fee_yuan": self.total_fee / 100,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class GuaranteeClaim(Base):
    """
    Guarantee claim model for replacement requests.
    """
    __tablename__ = "guarantee_claims"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    claim_no: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    # Foreign keys
    guarantee_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("guarantees.id"), nullable=False
    )
    original_candidate_id: Mapped[str] = mapped_column(String(36), nullable=False)
    new_candidate_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    # Claim details
    status: Mapped[ClaimStatus] = mapped_column(
        SQLEnum(ClaimStatus, native_enum=False),
        default=ClaimStatus.PENDING,
        nullable=False
    )

    # Reason for leaving
    leaving_reason: Mapped[str] = mapped_column(Text, nullable=False)

    # Document proof - stored as JSON array of file URLs
    resignation_proof_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    termination_proof_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Review info
    reviewer_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    # Relationships
    guarantee: Mapped["Guarantee"] = relationship("Guarantee", back_populates="claims")

    def __repr__(self) -> str:
        return f"<GuaranteeClaim(id={self.id}, no={self.claim_no}, status={self.status})>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "claim_no": self.claim_no,
            "guarantee_id": self.guarantee_id,
            "original_candidate_id": self.original_candidate_id,
            "new_candidate_id": self.new_candidate_id,
            "status": self.status.value,
            "leaving_reason": self.leaving_reason,
            "resignation_proof_url": self.resignation_proof_url,
            "termination_proof_url": self.termination_proof_url,
            "reviewer_id": self.reviewer_id,
            "review_notes": self.review_notes,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
