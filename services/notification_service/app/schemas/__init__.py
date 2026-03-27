"""
Pydantic Schemas
Notification Service
"""

from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime


# ==================== Kafka Message Schemas ====================

class CandidateInfo(BaseModel):
    """Candidate information"""
    name: str
    match_score: int
    current_title: str
    experience_years: int
    expected_salary: int
    highlights: List[str]


class MatchCompletedMessage(BaseModel):
    """Kafka message for match.completed topic"""
    employer_id: str
    employer_name: str
    employer_email: EmailStr
    job_id: str
    job_title: str
    candidate_count: int
    candidates: List[CandidateInfo]
    average_match_score: float
    timestamp: str


class InvoiceGeneratedMessage(BaseModel):
    """Kafka message for invoice.generated topic"""
    employer_id: str
    employer_name: str
    employer_email: EmailStr
    invoice_id: str
    invoice_no: str
    invoice_date: str
    due_date: str
    base_fee: float
    urgent_premium: float
    total_amount: float
    guarantee_start_date: str
    guarantee_expiry_date: str
    timestamp: str


class GuaranteeCreatedMessage(BaseModel):
    """Kafka message for guarantee.created topic"""
    employer_id: str
    employer_name: str
    employer_email: EmailStr
    guarantee_id: str
    guarantee_no: str
    job_id: str
    job_title: str
    start_date: str
    expiry_date: str
    total_fee: float
    timestamp: str


class ClaimApprovedMessage(BaseModel):
    """Kafka message for claim.approved topic"""
    employer_id: str
    employer_name: str
    employer_email: EmailStr
    claim_id: str
    claim_no: str
    guarantee_id: str
    original_candidate_id: str
    original_candidate_name: str
    leaving_reason: str
    review_date: str
    replacement_candidate: Optional[CandidateInfo] = None
    estimated_match_date: Optional[str] = None
    timestamp: str


class ClaimRejectedMessage(BaseModel):
    """Kafka message for claim.rejected topic"""
    employer_id: str
    employer_name: str
    employer_email: EmailStr
    claim_id: str
    claim_no: str
    guarantee_id: str
    original_candidate_id: str
    original_candidate_name: str
    leaving_reason: str
    rejection_reason: str
    review_date: str
    timestamp: str


# ==================== Leaving Reason Mapping ====================

LEAVING_REASON_DISPLAY = {
    "personal": "个人原因",
    "family": "家庭原因",
    "career_development": "职业发展",
    "compensation": "薪酬问题",
    "work_environment": "工作环境",
    "relocation": "工作地点变动",
    "health": "健康原因",
    "other": "其他原因",
}
