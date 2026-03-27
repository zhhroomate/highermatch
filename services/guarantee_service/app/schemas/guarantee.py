"""
Guarantee Schemas
HigherMatch™ AI Recruitment Platform

Pydantic schemas for request/response validation.
"""

from datetime import datetime, date
from typing import Optional, List

from pydantic import BaseModel, Field, ConfigDict


# ==================== Guarantee Schemas ====================

class GuaranteeBase(BaseModel):
    """Base guarantee schema"""
    job_id: str = Field(..., description="Job ID")
    employer_id: str = Field(..., description="Employer ID")
    invoice_id: str = Field(..., description="Invoice ID")
    total_fee_yuan: float = Field(..., ge=0, description="Total fee in yuan")


class GuaranteeCreate(GuaranteeBase):
    """Schema for creating a guarantee"""
    start_date: date = Field(..., description="Guarantee start date")
    expiry_date: date = Field(..., description="Guarantee expiry date")


class GuaranteeResponse(BaseModel):
    """Guarantee response schema"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    guarantee_no: str
    employer_id: str
    job_id: str
    invoice_id: str
    status: str
    start_date: date
    expiry_date: date
    total_fee_yuan: float
    created_at: Optional[datetime] = None


class GuaranteeListResponse(BaseModel):
    """Paginated guarantee list response"""
    items: List[GuaranteeResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ==================== Claim Schemas ====================

class ClaimCreate(BaseModel):
    """Schema for creating a guarantee claim"""
    guarantee_id: str = Field(..., description="Guarantee ID")
    original_candidate_id: str = Field(..., description="Original candidate ID who left")
    leaving_reason: str = Field(..., min_length=10, description="Reason for leaving (min 10 chars)")
    resignation_proof_url: Optional[str] = Field(None, description="Resignation letter URL")
    termination_proof_url: Optional[str] = Field(None, description="Termination proof URL")


class ClaimReview(BaseModel):
    """Schema for reviewing a claim"""
    claim_id: str = Field(..., description="Claim ID")
    status: str = Field(..., description="New status: approved or rejected")
    review_notes: Optional[str] = Field(None, description="Review notes")
    new_candidate_id: Optional[str] = Field(None, description="New candidate ID for replacement")


class ClaimResponse(BaseModel):
    """Claim response schema"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    claim_no: str
    guarantee_id: str
    original_candidate_id: str
    new_candidate_id: Optional[str] = None
    status: str
    leaving_reason: str
    resignation_proof_url: Optional[str] = None
    termination_proof_url: Optional[str] = None
    reviewer_id: Optional[str] = None
    review_notes: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class ClaimListResponse(BaseModel):
    """Paginated claim list response"""
    items: List[ClaimResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ==================== Kafka Message Schemas ====================

class InvoicePaidMessage(BaseModel):
    """Kafka message for invoice.paid topic"""
    invoice_id: str
    invoice_no: str
    employer_id: str
    job_id: str
    total_fee_yuan: float
    paid_at: datetime


# ==================== Health Schemas ====================

class HealthResponse(BaseModel):
    """Health check response schema"""
    status: str
    version: str
    kafka_connected: bool
    db_connected: bool
    scheduler_running: bool
