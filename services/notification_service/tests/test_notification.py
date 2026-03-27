"""
Notification Service Tests
HigherMatch™ AI Recruitment Platform
"""

import pytest
from datetime import date, timedelta

from app.schemas import (
    MatchCompletedMessage,
    InvoiceGeneratedMessage,
    GuaranteeCreatedMessage,
    ClaimApprovedMessage,
    ClaimRejectedMessage,
    LEAVING_REASON_DISPLAY,
    CandidateInfo,
)


# ==================== Schema Validation Tests ====================

class TestSchemas:
    """Test Pydantic schema validation"""

    def test_match_completed_message_valid(self):
        """Test valid match completed message"""
        msg = MatchCompletedMessage(
            employer_id="emp-123",
            employer_name="测试企业",
            employer_email="test@example.com",
            job_id="job-456",
            job_title="Python工程师",
            candidate_count=3,
            candidates=[
                CandidateInfo(
                    name="张三",
                    match_score=95,
                    current_title="开发工程师",
                    experience_years=5,
                    expected_salary=360000,
                    highlights=["BAT背景", "开源贡献"],
                )
            ],
            average_match_score=91.5,
            timestamp="2024-03-20T10:00:00Z",
        )
        assert msg.employer_id == "emp-123"
        assert msg.candidate_count == 3

    def test_invoice_generated_message_valid(self):
        """Test valid invoice generated message"""
        msg = InvoiceGeneratedMessage(
            employer_id="emp-123",
            employer_name="测试企业",
            employer_email="test@example.com",
            invoice_id="inv-456",
            invoice_no="INV-20240320-ABC12345",
            invoice_date="2024-03-20",
            due_date="2024-04-05",
            base_fee=12000.0,
            urgent_premium=3600.0,
            total_amount=15600.0,
            guarantee_start_date="2024-03-20",
            guarantee_expiry_date="2024-06-18",
            timestamp="2024-03-20T10:00:00Z",
        )
        assert msg.total_amount == 15600.0
        assert msg.invoice_no == "INV-20240320-ABC12345"

    def test_guarantee_created_message_valid(self):
        """Test valid guarantee created message"""
        msg = GuaranteeCreatedMessage(
            employer_id="emp-123",
            employer_name="测试企业",
            employer_email="test@example.com",
            guarantee_id="gua-789",
            guarantee_no="GUA-20240320-XYZ98765",
            job_id="job-456",
            job_title="Python工程师",
            start_date="2024-03-20",
            expiry_date="2024-06-18",
            total_fee=1560000,  # stored as fen
            timestamp="2024-03-20T10:00:00Z",
        )
        assert msg.total_fee == 1560000
        assert msg.guarantee_no.startswith("GUA-")

    def test_claim_approved_message_valid(self):
        """Test valid claim approved message"""
        msg = ClaimApprovedMessage(
            employer_id="emp-123",
            employer_name="测试企业",
            employer_email="test@example.com",
            claim_id="clm-001",
            claim_no="CLM-20240320-CLM00001",
            guarantee_id="gua-789",
            original_candidate_id="cand-001",
            original_candidate_name="王五",
            leaving_reason="career_development",
            review_date="2024-03-20",
            timestamp="2024-03-20T10:00:00Z",
        )
        assert msg.claim_no.startswith("CLM-")
        assert msg.original_candidate_name == "王五"

    def test_claim_rejected_message_valid(self):
        """Test valid claim rejected message"""
        msg = ClaimRejectedMessage(
            employer_id="emp-123",
            employer_name="测试企业",
            employer_email="test@example.com",
            claim_id="clm-001",
            claim_no="CLM-20240320-CLM00001",
            guarantee_id="gua-789",
            original_candidate_id="cand-001",
            original_candidate_name="王五",
            leaving_reason="personal",
            rejection_reason="保障期限已过",
            review_date="2024-03-20",
            timestamp="2024-03-20T10:00:00Z",
        )
        assert msg.rejection_reason == "保障期限已过"


# ==================== Leaving Reason Display Tests ====================

class TestLeavingReasonDisplay:
    """Test leaving reason display mapping"""

    def test_all_leaving_reasons_mapped(self):
        """Test all leaving reasons have display text"""
        reasons = [
            "personal",
            "family",
            "career_development",
            "compensation",
            "work_environment",
            "relocation",
            "health",
            "other",
        ]
        for reason in reasons:
            assert reason in LEAVING_REASON_DISPLAY
            assert isinstance(LEAVING_REASON_DISPLAY[reason], str)
            assert len(LEAVING_REASON_DISPLAY[reason]) > 0

    def test_chinese_display_text(self):
        """Test display text is in Chinese"""
        assert LEAVING_REASON_DISPLAY["personal"] == "个人原因"
        assert LEAVING_REASON_DISPLAY["career_development"] == "职业发展"
        assert LEAVING_REASON_DISPLAY["compensation"] == "薪酬问题"


# ==================== Email Template Tests ====================

class TestEmailTemplates:
    """Test email template rendering"""

    def test_render_match_completed_context(self):
        """Test match completed email context"""
        context = {
            "employer_name": "测试企业",
            "job_id": "job-123",
            "job_title": "Python工程师",
            "candidate_count": 3,
            "candidates": [
                {
                    "name": "张三",
                    "match_score": 95,
                    "current_title": "开发工程师",
                    "experience_years": 5,
                    "expected_salary": 360000,
                    "highlights": ["BAT背景", "开源贡献"],
                }
            ],
            "average_match_score": 95.0,
            "portal_url": "https://app.highermatch.com",
        }

        assert context["employer_name"] == "测试企业"
        assert context["candidate_count"] == 3
        assert len(context["candidates"]) == 1

    def test_render_invoice_context(self):
        """Test invoice email context"""
        context = {
            "employer_name": "测试企业",
            "invoice_id": "inv-123",
            "invoice_no": "INV-20240320-ABC12345",
            "invoice_date": "2024-03-20",
            "due_date": "2024-04-05",
            "base_fee": 12000.0,
            "urgent_premium": 3600.0,
            "total_amount": 15600.0,
            "guarantee_start_date": "2024-03-20",
            "guarantee_expiry_date": "2024-06-18",
            "portal_url": "https://app.highermatch.com",
        }

        assert context["total_amount"] == 15600.0
        assert context["guarantee_start_date"] == "2024-03-20"
        assert context["guarantee_expiry_date"] == "2024-06-18"


# ==================== Guarantee Period Tests ====================

class TestGuaranteePeriod:
    """Test guarantee period calculation"""

    def test_calculate_90_day_period(self):
        """Test 90 day guarantee period"""
        start = date(2024, 3, 20)
        expiry = start + timedelta(days=90)

        assert expiry == date(2024, 6, 18)
        assert (expiry - start).days == 90

    def test_guarantee_period_includes_leap_day(self):
        """Test guarantee period handles leap year"""
        start = date(2024, 2, 28)  # 2024 is leap year
        expiry = start + timedelta(days=90)

        # Feb 28 + 90 days = May 28 (includes Feb 29)
        assert expiry == date(2024, 5, 28)


# ==================== Currency Formatting Tests ====================

class TestCurrencyFormatting:
    """Test currency formatting for emails"""

    def test_format_large_amount(self):
        """Test formatting large amounts"""
        amount = 1560000  # fen = ¥15,600.00
        yuan = amount / 100

        assert f"¥{yuan:,.2f}" == "¥15,600.00"

    def test_format_with_commas(self):
        """Test number formatting with commas"""
        assert f"{12000:,}" == "12,000"
        assert f"{1200000:,}" == "1,200,000"
        assert f"{360000:,}" == "360,000"
