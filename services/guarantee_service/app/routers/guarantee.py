"""
Guarantee Router
HigherMatch™ AI Recruitment Platform

REST API endpoints for guarantee service:
- GET /api/v1/guarantee/guarantees - List guarantees with pagination
- GET /api/v1/guarantee/guarantees/{guarantee_id} - Get guarantee details
- POST /api/v1/guarantee/claim - Submit a guarantee claim
- GET /api/v1/guarantee/claims - List claims with pagination
- PATCH /api/v1/guarantee/claims/{claim_id}/review - Review a claim
"""

import json
import uuid
from datetime import datetime
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import get_db
from app.models import Guarantee, GuaranteeStatus, GuaranteeClaim, ClaimStatus
from app.schemas import (
    GuaranteeResponse,
    GuaranteeListResponse,
    ClaimCreate,
    ClaimReview,
    ClaimResponse,
    ClaimListResponse,
)

logger = structlog.get_logger()

router = APIRouter()


# ==================== Guarantee Endpoints ====================

@router.get("/guarantees", response_model=GuaranteeListResponse)
async def list_guarantees(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    employer_id: Optional[str] = Query(None),
    job_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
):
    """
    List guarantees with pagination.
    """
    query = select(Guarantee)

    if employer_id:
        query = query.where(Guarantee.employer_id == employer_id)
    if job_id:
        query = query.where(Guarantee.job_id == job_id)
    if status_filter:
        try:
            status_enum = GuaranteeStatus(status_filter)
            query = query.where(Guarantee.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status_filter}"
            )

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginate
    offset = (page - 1) * page_size
    query = query.order_by(desc(Guarantee.created_at)).offset(offset).limit(page_size)

    result = await db.execute(query)
    guarantees = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size

    items = [
        GuaranteeResponse(
            id=g.id,
            guarantee_no=g.guarantee_no,
            employer_id=g.employer_id,
            job_id=g.job_id,
            invoice_id=g.invoice_id,
            status=g.status.value,
            start_date=g.start_date,
            expiry_date=g.expiry_date,
            total_fee_yuan=g.total_fee / 100,
            created_at=g.created_at,
        )
        for g in guarantees
    ]

    return GuaranteeListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/guarantees/{guarantee_id}", response_model=GuaranteeResponse)
async def get_guarantee(
    guarantee_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific guarantee by ID."""
    query = select(Guarantee).where(Guarantee.id == guarantee_id)
    result = await db.execute(query)
    guarantee = result.scalar_one_or_none()

    if not guarantee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Guarantee not found: {guarantee_id}"
        )

    return GuaranteeResponse(
        id=guarantee.id,
        guarantee_no=guarantee.guarantee_no,
        employer_id=guarantee.employer_id,
        job_id=guarantee.job_id,
        invoice_id=guarantee.invoice_id,
        status=guarantee.status.value,
        start_date=guarantee.start_date,
        expiry_date=guarantee.expiry_date,
        total_fee_yuan=guarantee.total_fee / 100,
        created_at=guarantee.created_at,
    )


# ==================== Claim Endpoints ====================

@router.post("/claim", response_model=ClaimResponse, status_code=status.HTTP_201_CREATED)
async def create_claim(
    request: ClaimCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Submit a guarantee claim (replacement request).

    Required documents:
    - Resignation proof (resignation letter from candidate)
    - Termination proof (proof of leaving the job)

    The claim will be reviewed by the platform team.
    """
    # Get guarantee
    query = select(Guarantee).where(Guarantee.id == request.guarantee_id)
    result = await db.execute(query)
    guarantee = result.scalar_one_or_none()

    if not guarantee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Guarantee not found: {request.guarantee_id}"
        )

    # Check guarantee status
    if guarantee.status == GuaranteeStatus.EXPIRED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Guarantee has expired, cannot submit claim"
        )

    if guarantee.status == GuaranteeStatus.VOID:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Guarantee has been voided"
        )

    if guarantee.status == GuaranteeStatus.CLAIMED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Guarantee has already been claimed"
        )

    # Check if there's already a pending claim
    pending_claim_query = select(GuaranteeClaim).where(
        GuaranteeClaim.guarantee_id == request.guarantee_id,
        GuaranteeClaim.status.in_([ClaimStatus.PENDING, ClaimStatus.PROCESSING])
    )
    pending_result = await db.execute(pending_claim_query)
    if pending_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="There is already a pending claim for this guarantee"
        )

    # Generate claim number
    claim_no = f"CLM-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

    # Create claim
    claim = GuaranteeClaim(
        id=str(uuid.uuid4()),
        claim_no=claim_no,
        guarantee_id=request.guarantee_id,
        original_candidate_id=request.original_candidate_id,
        leaving_reason=request.leaving_reason,
        resignation_proof_url=request.resignation_proof_url,
        termination_proof_url=request.termination_proof_url,
        status=ClaimStatus.PENDING,
    )

    db.add(claim)
    await db.commit()
    await db.refresh(claim)

    logger.info(
        "claim_created",
        claim_id=claim.id,
        claim_no=claim.claim_no,
        guarantee_id=guarantee.id
    )

    return ClaimResponse(
        id=claim.id,
        claim_no=claim.claim_no,
        guarantee_id=claim.guarantee_id,
        original_candidate_id=claim.original_candidate_id,
        new_candidate_id=claim.new_candidate_id,
        status=claim.status.value,
        leaving_reason=claim.leaving_reason,
        resignation_proof_url=claim.resignation_proof_url,
        termination_proof_url=claim.termination_proof_url,
        reviewer_id=claim.reviewer_id,
        review_notes=claim.review_notes,
        reviewed_at=claim.reviewed_at,
        created_at=claim.created_at,
    )


@router.get("/claims", response_model=ClaimListResponse)
async def list_claims(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    guarantee_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
):
    """List guarantee claims with pagination."""
    query = select(GuaranteeClaim)

    if guarantee_id:
        query = query.where(GuaranteeClaim.guarantee_id == guarantee_id)
    if status_filter:
        try:
            status_enum = ClaimStatus(status_filter)
            query = query.where(GuaranteeClaim.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status_filter}"
            )

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginate
    offset = (page - 1) * page_size
    query = query.order_by(desc(GuaranteeClaim.created_at)).offset(offset).limit(page_size)

    result = await db.execute(query)
    claims = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size

    items = [
        ClaimResponse(
            id=c.id,
            claim_no=c.claim_no,
            guarantee_id=c.guarantee_id,
            original_candidate_id=c.original_candidate_id,
            new_candidate_id=c.new_candidate_id,
            status=c.status.value,
            leaving_reason=c.leaving_reason,
            resignation_proof_url=c.resignation_proof_url,
            termination_proof_url=c.termination_proof_url,
            reviewer_id=c.reviewer_id,
            review_notes=c.review_notes,
            reviewed_at=c.reviewed_at,
            created_at=c.created_at,
        )
        for c in claims
    ]

    return ClaimListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.patch("/claims/{claim_id}/review", response_model=ClaimResponse)
async def review_claim(
    claim_id: str,
    request: ClaimReview,
    db: AsyncSession = Depends(get_db),
):
    """
    Review a guarantee claim.

    Can approve or reject the claim.
    If approved, the guarantee status will be updated to CLAIMED.
    """
    # Get claim
    query = select(GuaranteeClaim).where(GuaranteeClaim.id == claim_id)
    result = await db.execute(query)
    claim = result.scalar_one_or_none()

    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Claim not found: {claim_id}"
        )

    # Check claim status
    if claim.status not in [ClaimStatus.PENDING, ClaimStatus.PROCESSING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Claim is already {claim.status.value}, cannot review"
        )

    # Validate new status
    if request.status not in ["approved", "rejected"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Status must be 'approved' or 'rejected'"
        )

    # Update claim
    claim.status = ClaimStatus.APPROVED if request.status == "approved" else ClaimStatus.REJECTED
    claim.review_notes = request.review_notes
    claim.reviewer_id = "system"  # In production, use actual reviewer ID
    claim.reviewed_at = datetime.utcnow()

    if request.new_candidate_id:
        claim.new_candidate_id = request.new_candidate_id

    # If approved, update guarantee status
    if request.status == "approved":
        guarantee_query = select(Guarantee).where(Guarantee.id == claim.guarantee_id)
        guarantee_result = await db.execute(guarantee_query)
        guarantee = guarantee_result.scalar_one_or_none()

        if guarantee:
            guarantee.status = GuaranteeStatus.CLAIMED

    await db.commit()
    await db.refresh(claim)

    logger.info(
        "claim_reviewed",
        claim_id=claim.id,
        status=claim.status.value,
        reviewer=claim.reviewer_id
    )

    return ClaimResponse(
        id=claim.id,
        claim_no=claim.claim_no,
        guarantee_id=claim.guarantee_id,
        original_candidate_id=claim.original_candidate_id,
        new_candidate_id=claim.new_candidate_id,
        status=claim.status.value,
        leaving_reason=claim.leaving_reason,
        resignation_proof_url=claim.resignation_proof_url,
        termination_proof_url=claim.termination_proof_url,
        reviewer_id=claim.reviewer_id,
        review_notes=claim.review_notes,
        reviewed_at=claim.reviewed_at,
        created_at=claim.created_at,
    )
