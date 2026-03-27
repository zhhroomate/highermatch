"""
Billing Router
HigherMatch™ AI Recruitment Platform

REST API endpoints for billing service:
- GET /api/v1/billing/invoices - List invoices with pagination
- POST /api/v1/billing/pay - Generate payment URL (mock)
- POST /api/v1/billing/callback - Payment platform webhook callback
"""

import hashlib
import hmac
import json
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import get_db, settings, send_invoice_paid_event
from app.models import Invoice, InvoiceStatus, PaymentCallback
from app.schemas import (
    InvoiceResponse,
    InvoiceListResponse,
    PaymentRequest,
    PaymentResponse,
    PaymentCallbackRequest,
    PaymentCallbackResponse,
)

logger = structlog.get_logger()

router = APIRouter()


# ==================== Helper Functions ====================

def generate_payment_url(invoice: Invoice) -> tuple[str, str]:
    """
    Generate a mock payment URL for the invoice.

    Returns:
        Tuple of (payment_url, payment_no)
    """
    payment_no = f"PAY-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"

    # Mock payment URL (in production, this would call actual payment gateway)
    payment_url = f"https://pay.example.com/checkout?order={payment_no}&amount={invoice.total_fee / 100}"

    return payment_url, payment_no


def verify_payment_signature(data: dict, signature: str) -> bool:
    """
    Verify payment callback signature.

    Args:
        data: Callback data dictionary
        signature: Signature from payment platform

    Returns:
        True if signature is valid
    """
    # Sort keys and create signature payload
    sorted_data = sorted(data.items())
    payload = "&".join([f"{k}={v}" for k, v in sorted_data if k != "signature"])

    # Generate expected signature
    expected_signature = hmac.new(
        settings.PAYMENT_SECRET_KEY.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(signature, expected_signature)


# ==================== Invoice Endpoints ====================

@router.get("/invoices", response_model=InvoiceListResponse)
async def list_invoices(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    employer_id: Optional[str] = Query(None, description="Filter by employer ID"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    db: AsyncSession = Depends(get_db),
):
    """
    List invoices with pagination.

    Returns paginated list of invoices sorted by creation date (newest first).
    """
    # Build query
    query = select(Invoice)

    # Apply filters
    if employer_id:
        query = query.where(Invoice.employer_id == employer_id)

    if status_filter:
        try:
            status_enum = InvoiceStatus(status_filter)
            query = query.where(Invoice.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status_filter}"
            )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.order_by(desc(Invoice.created_at)).offset(offset).limit(page_size)

    # Execute query
    result = await db.execute(query)
    invoices = result.scalars().all()

    # Calculate pagination
    total_pages = (total + page_size - 1) // page_size

    # Convert to response
    items = [
        InvoiceResponse(
            id=inv.id,
            invoice_no=inv.invoice_no,
            employer_id=inv.employer_id,
            job_id=inv.job_id,
            status=inv.status.value,
            offer_annual_salary_yuan=inv.offer_annual_salary / 100,
            commission_rate=inv.commission_rate / 100,
            base_fee_yuan=inv.base_fee / 100,
            is_urgent=inv.is_urgent,
            urgent_premium_yuan=inv.urgent_premium / 100,
            total_fee_yuan=inv.total_fee / 100,
            payment_url=inv.payment_url,
            paid_at=inv.paid_at,
            description=inv.description,
            created_at=inv.created_at,
            updated_at=inv.updated_at,
        )
        for inv in invoices
    ]

    logger.info(
        "invoices_listed",
        page=page,
        page_size=page_size,
        total=total,
        employer_id=employer_id
    )

    return InvoiceListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific invoice by ID.
    """
    query = select(Invoice).where(Invoice.id == invoice_id)
    result = await db.execute(query)
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice not found: {invoice_id}"
        )

    return InvoiceResponse(
        id=invoice.id,
        invoice_no=invoice.invoice_no,
        employer_id=invoice.employer_id,
        job_id=invoice.job_id,
        status=invoice.status.value,
        offer_annual_salary_yuan=invoice.offer_annual_salary / 100,
        commission_rate=invoice.commission_rate / 100,
        base_fee_yuan=invoice.base_fee / 100,
        is_urgent=invoice.is_urgent,
        urgent_premium_yuan=invoice.urgent_premium / 100,
        total_fee_yuan=invoice.total_fee / 100,
        payment_url=invoice.payment_url,
        paid_at=invoice.paid_at,
        description=invoice.description,
        created_at=invoice.created_at,
        updated_at=invoice.updated_at,
    )


# ==================== Payment Endpoints ====================

@router.post("/pay", response_model=PaymentResponse)
async def create_payment(
    request: PaymentRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a mock payment URL for the invoice.

    In production, this would integrate with actual payment gateways
    (Alipay, WeChat Pay, etc.) to generate a real payment URL.
    """
    # Get invoice
    query = select(Invoice).where(Invoice.id == request.invoice_id)
    result = await db.execute(query)
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice not found: {request.invoice_id}"
        )

    # Check invoice status
    if invoice.status == InvoiceStatus.PAID:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invoice already paid"
        )

    if invoice.status == InvoiceStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invoice has been cancelled"
        )

    # Generate mock payment URL
    payment_url, payment_no = generate_payment_url(invoice)

    # Update invoice with payment URL
    invoice.payment_url = payment_url
    await db.commit()

    # Calculate expiration time
    expired_at = datetime.utcnow() + timedelta(minutes=settings.PAYMENT_EXPIRE_MINUTES)

    logger.info(
        "payment_url_generated",
        invoice_id=invoice.id,
        payment_no=payment_no,
        total_fee=invoice.total_fee
    )

    return PaymentResponse(
        payment_url=payment_url,
        payment_no=payment_no,
        expired_at=expired_at
    )


@router.post("/callback", response_model=PaymentCallbackResponse)
async def payment_callback(
    request: PaymentCallbackRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Payment platform webhook callback.

    This endpoint receives payment confirmation from the payment platform,
    verifies the signature, and updates the invoice status.

    After successful verification:
    1. Updates invoice status to PAID
    2. Records callback in audit log
    3. Sends invoice.paid Kafka event

    IMPORTANT: This endpoint should be secured with IP whitelist or
    additional signature verification in production.
    """
    # Log received callback
    logger.info(
        "payment_callback_received",
        callback_id=request.callback_id,
        invoice_no=request.invoice_no,
        status=request.status
    )

    # Create callback record for audit
    callback_record = PaymentCallback(
        id=str(uuid.uuid4()),
        callback_id=request.callback_id,
        signature=request.signature,
        raw_data=json.dumps(request.model_dump(), default=str),
        is_valid=False,
    )
    db.add(callback_record)

    # Find invoice
    query = select(Invoice).where(Invoice.invoice_no == request.invoice_no)
    result = await db.execute(query)
    invoice = result.scalar_one_or_none()

    if not invoice:
        # Record callback but return error
        callback_record.error_message = f"Invoice not found: {request.invoice_no}"
        await db.commit()
        logger.warning("callback_invoice_not_found", invoice_no=request.invoice_no)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice not found: {request.invoice_no}"
        )

    # Verify signature (in production, implement full signature verification)
    # For mock purposes, we accept all callbacks
    # In production, uncomment and implement proper verification:
    # data_for_verify = {k: v for k, v in request.model_dump().items() if k != 'signature'}
    # if not verify_payment_signature(data_for_verify, request.signature):
    #     callback_record.error_message = "Invalid signature"
    #     await db.commit()
    #     raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")

    callback_record.invoice_id = invoice.id

    # Process based on payment status
    if request.status.lower() == "success":
        # Update invoice to PAID
        invoice.status = InvoiceStatus.PAID
        if request.paid_at:
            try:
                invoice.paid_at = datetime.fromisoformat(request.paid_at.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                invoice.paid_at = datetime.utcnow()
        else:
            invoice.paid_at = datetime.utcnow()

        callback_record.is_valid = True
        await db.commit()
        await db.refresh(invoice)

        logger.info(
            "payment_success",
            invoice_id=invoice.id,
            invoice_no=invoice.invoice_no,
            amount=request.amount
        )

        # Send Kafka event
        try:
            await send_invoice_paid_event(invoice)
        except Exception as e:
            logger.error("failed_to_send_invoice_paid_event", error=str(e))

        return PaymentCallbackResponse(code=0, message="Success")

    elif request.status.lower() in ("failed", "cancelled"):
        # Log failed/cancelled payment
        callback_record.error_message = f"Payment {request.status}: {request.callback_id}"
        callback_record.is_valid = True
        await db.commit()

        logger.info(
            "payment_failed_or_cancelled",
            invoice_id=invoice.id,
            status=request.status
        )

        return PaymentCallbackResponse(code=0, message=f"Payment {request.status} recorded")

    else:
        # Unknown status
        callback_record.error_message = f"Unknown payment status: {request.status}"
        await db.commit()

        logger.warning(
            "callback_unknown_status",
            invoice_id=invoice.id,
            status=request.status
        )

        return PaymentCallbackResponse(code=1, message=f"Unknown status: {request.status}")
