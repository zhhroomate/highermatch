"""
Billing Service Tests
HigherMatch™ AI Recruitment Platform
"""

import pytest
from decimal import Decimal
from datetime import datetime

from app.schemas import (
    OnboardingConfirmedMessage,
    InvoiceResponse,
    PaymentCallbackRequest,
)
from app.models import InvoiceStatus


# ==================== Billing Calculation Tests ====================

class TestBillingCalculation:
    """Test billing calculation logic"""

    def test_calculate_billing_with_commission(self):
        """Test billing calculation with 10% commission rate"""
        annual_salary_yuan = Decimal("120000.00")  # ¥120,000
        commission_rate = Decimal("0.10")

        base_fee_yuan = annual_salary_yuan * commission_rate
        assert base_fee_yuan == Decimal("12000.00")

    def test_calculate_billing_with_urgent_premium(self):
        """Test billing calculation with 30% urgent premium"""
        annual_salary_yuan = Decimal("120000.00")
        commission_rate = Decimal("0.10")
        urgent_premium_rate = Decimal("0.30")

        base_fee_yuan = annual_salary_yuan * commission_rate
        urgent_premium_yuan = base_fee_yuan * urgent_premium_rate
        total_fee_yuan = base_fee_yuan + urgent_premium_yuan

        assert base_fee_yuan == Decimal("12000.00")
        assert urgent_premium_yuan == Decimal("3600.00")
        assert total_fee_yuan == Decimal("15600.00")

    def test_calculate_billing_without_urgent(self):
        """Test billing calculation without urgent premium"""
        annual_salary_yuan = Decimal("120000.00")
        commission_rate = Decimal("0.10")

        base_fee_yuan = annual_salary_yuan * commission_rate
        urgent_premium_yuan = Decimal("0")  # is_urgent = False
        total_fee_yuan = base_fee_yuan + urgent_premium_yuan

        assert base_fee_yuan == Decimal("12000.00")
        assert urgent_premium_yuan == Decimal("0")
        assert total_fee_yuan == Decimal("12000.00")

    def test_fen_conversion_precision(self):
        """Test that fen conversion maintains precision"""
        annual_salary_yuan = Decimal("123456.78")
        commission_rate = Decimal("0.10")

        base_fee_yuan = annual_salary_yuan * commission_rate
        base_fee_fen = int(round(base_fee_yuan * 100))

        # 123456.78 * 0.10 = 12345.678 -> round = 1234568 fen
        assert base_fee_fen == 1234568

    def test_large_salary_calculation(self):
        """Test calculation with large salary"""
        annual_salary_yuan = Decimal("1000000.00")  # ¥1,000,000
        commission_rate = Decimal("0.10")
        urgent_premium_rate = Decimal("0.30")

        base_fee_yuan = annual_salary_yuan * commission_rate
        urgent_premium_yuan = base_fee_yuan * urgent_premium_rate
        total_fee_yuan = base_fee_yuan + urgent_premium_yuan

        assert base_fee_yuan == Decimal("100000.00")
        assert urgent_premium_yuan == Decimal("30000.00")
        assert total_fee_yuan == Decimal("130000.00")


# ==================== Schema Validation Tests ====================

class TestSchemas:
    """Test Pydantic schema validation"""

    def test_onboarding_confirmed_message_valid(self):
        """Test valid onboarding confirmed message"""
        msg = OnboardingConfirmedMessage(
            job_id="job-123",
            offer_annual_salary=120000.0,
            is_urgent=True,
            employer_id="emp-456",
            candidate_id="cand-789",
            offer_id="offer-001"
        )
        assert msg.job_id == "job-123"
        assert msg.offer_annual_salary == 120000.0
        assert msg.is_urgent is True

    def test_payment_callback_request_valid(self):
        """Test valid payment callback request"""
        req = PaymentCallbackRequest(
            callback_id="cb-123",
            invoice_no="INV-20240320-ABC12345",
            amount=12000.0,
            status="success",
            paid_at="2024-03-20T10:00:00Z",
            signature="abc123signature"
        )
        assert req.callback_id == "cb-123"
        assert req.status == "success"
        assert req.amount == 12000.0


# ==================== Invoice Status Tests ====================

class TestInvoiceStatus:
    """Test invoice status enum"""

    def test_invoice_status_values(self):
        """Test invoice status enum values"""
        assert InvoiceStatus.PENDING.value == "pending"
        assert InvoiceStatus.PAID.value == "paid"
        assert InvoiceStatus.CANCELLED.value == "cancelled"
        assert InvoiceStatus.REFUNDED.value == "refunded"

    def test_invoice_status_from_string(self):
        """Test creating status from string"""
        status = InvoiceStatus("paid")
        assert status == InvoiceStatus.PAID


# ==================== Edge Cases ====================

class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_zero_salary(self):
        """Test calculation with zero salary"""
        annual_salary_yuan = Decimal("0")
        commission_rate = Decimal("0.10")

        base_fee_yuan = annual_salary_yuan * commission_rate
        assert base_fee_yuan == Decimal("0")

    def test_small_salary(self):
        """Test calculation with very small salary"""
        annual_salary_yuan = Decimal("0.01")
        commission_rate = Decimal("0.10")

        base_fee_yuan = annual_salary_yuan * commission_rate
        # 0.01 * 0.10 = 0.001 yuan = 0.1 fen, rounds to 0
        base_fee_fen = int(round(base_fee_yuan * 100))
        assert base_fee_fen == 0

    def test_maximum_commission_rate(self):
        """Test with maximum commission rate"""
        annual_salary_yuan = Decimal("100000.00")
        commission_rate = Decimal("1.00")  # 100%

        base_fee_yuan = annual_salary_yuan * commission_rate
        assert base_fee_yuan == Decimal("100000.00")
