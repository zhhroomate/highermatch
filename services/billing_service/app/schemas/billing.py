"""
Billing Schemas
HigherMatch™ AI Recruitment Platform

Pydantic schemas for request/response validation.
All monetary amounts are in 'yuan' for API, converted to 'fen' for storage.
"""

from datetime import datetime
from typing import Optional, List
from decimal import Decimal

from pydantic import BaseModel, Field, ConfigDict


# ==================== Invoice Schemas ====================

class InvoiceBase(BaseModel):
    """Base invoice schema"""
    job_id: str = Field(..., description="Job ID for the invoice")
    offer_annual_salary: float = Field(..., ge=0, description="Annual salary in yuan")
    is_urgent: bool = Field(default=False, description="Whether this is an urgent placement")
    commission_rate: float = Field(default=0.10, ge=0, le=1, description="Commission rate (0.10 = 10%)")


class InvoiceCreate(InvoiceBase):
    """Schema for creating an invoice"""
    employer_id: str = Field(..., description="Employer ID")
    description: Optional[str] = Field(None, description="Invoice description")


class InvoiceResponse(BaseModel):
    """Invoice response schema"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    invoice_no: str
    employer_id: str
    job_id: str
    status: str
    offer_annual_salary_yuan: float = Field(..., description="Annual salary in yuan")
    commission_rate: float
    base_fee_yuan: float = Field(..., description="Base fee in yuan")
    is_urgent: bool
    urgent_premium_yuan: float = Field(..., description="Urgent premium in yuan")
    total_fee_yuan: float = Field(..., description="Total fee in yuan")
    payment_url: Optional[str] = None
    paid_at: Optional[datetime] = None
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class InvoiceListResponse(BaseModel):
    """Paginated invoice list response"""
    items: List[InvoiceResponse]
    total: int = Field(..., description="Total count")
    page: int = Field(..., description="Current page")
    page_size: int = Field(..., description="Page size")
    total_pages: int = Field(..., description="Total pages")


# ==================== Payment Schemas ====================

class PaymentRequest(BaseModel):
    """Payment request schema"""
    invoice_id: str = Field(..., description="Invoice ID to pay")
    payment_method: str = Field(default="alipay", description="Payment method")


class PaymentResponse(BaseModel):
    """Payment response schema"""
    payment_url: str = Field(..., description="Payment URL to redirect to")
    payment_no: str = Field(..., description="Payment order number")
    expired_at: datetime = Field(..., description="Payment expiration time")


class PaymentCallbackRequest(BaseModel):
    """Payment callback webhook schema"""
    callback_id: str = Field(..., description="Payment platform callback ID")
    invoice_no: str = Field(..., description="Invoice number")
    amount: float = Field(..., ge=0, description="Payment amount in yuan")
    status: str = Field(..., description="Payment status: success, failed, cancelled")
    paid_at: Optional[str] = Field(None, description="Payment timestamp")
    signature: str = Field(..., description="Callback signature for verification")
    extra_data: Optional[str] = Field(None, description="Extra callback data")


class PaymentCallbackResponse(BaseModel):
    """Payment callback response schema"""
    code: int = Field(..., description="Response code: 0 = success")
    message: str = Field(..., description="Response message")


# ==================== Kafka Message Schemas ====================

class OnboardingConfirmedMessage(BaseModel):
    """Kafka message for onboarding.confirmed topic"""
    job_id: str = Field(..., description="Job ID")
    offer_annual_salary: float = Field(..., description="Offered annual salary in yuan")
    is_urgent: bool = Field(..., description="Whether it's an urgent placement")
    employer_id: str = Field(..., description="Employer ID")
    candidate_id: str = Field(..., description="Candidate ID")
    offer_id: str = Field(..., description="Offer ID")


class InvoicePaidMessage(BaseModel):
    """Kafka message for invoice.paid topic"""
    invoice_id: str = Field(..., description="Invoice ID")
    invoice_no: str = Field(..., description="Invoice number")
    employer_id: str = Field(..., description="Employer ID")
    job_id: str = Field(..., description="Job ID")
    total_fee_yuan: float = Field(..., description="Total fee in yuan")
    paid_at: datetime = Field(..., description="Payment timestamp")


# ==================== Health Schemas ====================

class HealthResponse(BaseModel):
    """Health check response schema"""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="Service version")
    kafka_connected: bool = Field(..., description="Kafka connection status")
    db_connected: bool = Field(..., description="Database connection status")
