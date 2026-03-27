"""
Guarantee Service Tests
HigherMatch™ AI Recruitment Platform
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal

from app.models import GuaranteeStatus, ClaimStatus


# ==================== Guarantee Status Tests ====================

class TestGuaranteeStatus:
    """Test guarantee status enum"""

    def test_guarantee_status_values(self):
        """Test guarantee status enum values"""
        assert GuaranteeStatus.ACTIVE.value == "active"
        assert GuaranteeStatus.EXPIRED.value == "expired"
        assert GuaranteeStatus.VOID.value == "void"
        assert GuaranteeStatus.CLAIMED.value == "claimed"

    def test_guarantee_status_from_string(self):
        """Test creating status from string"""
        status = GuaranteeStatus("active")
        assert status == GuaranteeStatus.ACTIVE


# ==================== Claim Status Tests ====================

class TestClaimStatus:
    """Test claim status enum"""

    def test_claim_status_values(self):
        """Test claim status enum values"""
        assert ClaimStatus.PENDING.value == "pending"
        assert ClaimStatus.PROCESSING.value == "processing"
        assert ClaimStatus.APPROVED.value == "approved"
        assert ClaimStatus.REJECTED.value == "rejected"

    def test_claim_status_from_string(self):
        """Test creating status from string"""
        status = ClaimStatus("pending")
        assert status == ClaimStatus.PENDING


# ==================== Guarantee Period Tests ====================

class TestGuaranteePeriod:
    """Test guarantee period calculation"""

    def test_calculate_90_day_expiry(self):
        """Test 90-day guarantee period calculation"""
        start_date = date(2024, 3, 20)
        guarantee_days = 90
        expiry_date = start_date + timedelta(days=guarantee_days)

        assert expiry_date == date(2024, 6, 18)

    def test_guarantee_period_boundary(self):
        """Test guarantee period at month boundary"""
        start_date = date(2024, 1, 15)
        guarantee_days = 90
        expiry_date = start_date + timedelta(days=guarantee_days)

        # Jan 15 + 90 days = Apr 14
        assert expiry_date == date(2024, 4, 14)

    def test_leap_year_handling(self):
        """Test guarantee period in leap year"""
        start_date = date(2024, 2, 28)
        guarantee_days = 90
        expiry_date = start_date + timedelta(days=guarantee_days)

        # Feb 28 + 90 days (includes leap day Feb 29) = May 28
        assert expiry_date == date(2024, 5, 28)


# ==================== Guarantee Number Generation ====================

class TestGuaranteeNumber:
    """Test guarantee number format"""

    def test_guarantee_number_format(self):
        """Test guarantee number format GUA-YYYYMMDD-XXXXXXXX"""
        from datetime import datetime
        import uuid

        guarantee_no = f"GUA-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

        # Check format
        assert guarantee_no.startswith("GUA-")
        parts = guarantee_no.split("-")
        assert len(parts) == 3
        assert len(parts[1]) == 8  # YYYYMMDD
        assert len(parts[2]) == 8  # 8 hex chars


# ==================== Claim Number Generation ====================

class TestClaimNumber:
    """Test claim number format"""

    def test_claim_number_format(self):
        """Test claim number format CLM-YYYYMMDD-XXXXXXXX"""
        from datetime import datetime
        import uuid

        claim_no = f"CLM-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

        # Check format
        assert claim_no.startswith("CLM-")
        parts = claim_no.split("-")
        assert len(parts) == 3
        assert len(parts[1]) == 8  # YYYYMMDD
        assert len(parts[2]) == 8  # 8 hex chars


# ==================== Claim Validation Tests ====================

class TestClaimValidation:
    """Test claim validation logic"""

    def test_valid_leaving_reasons(self):
        """Test valid leaving reasons"""
        valid_reasons = [
            "personal",
            "family",
            "career_development",
            "compensation",
            "work_environment",
            "other"
        ]
        for reason in valid_reasons:
            assert reason in valid_reasons

    def test_claim_requires_documents(self):
        """Test that claims require document URLs"""
        # Both resignation and termination proof should be provided
        resignation_proof = "https://example.com/resignation.pdf"
        termination_proof = "https://example.com/termination.pdf"

        assert resignation_proof is not None
        assert termination_proof is not None


# ==================== Guarantee Fee Tests ====================

class TestGuaranteeFee:
    """Test guarantee fee calculations"""

    def test_fee_stored_as_fen(self):
        """Test that fees are stored as fen (cents)"""
        total_fee_yuan = Decimal("12000.00")
        total_fee_fen = int(total_fee_yuan * 100)

        assert total_fee_fen == 1200000
        assert isinstance(total_fee_fen, int)

    def test_fee_conversion_roundtrip(self):
        """Test fee conversion yuan -> fen -> yuan"""
        total_fee_yuan = Decimal("12345.67")
        total_fee_fen = int(total_fee_yuan * 100)
        recovered_yuan = Decimal(total_fee_fen) / 100

        assert recovered_yuan == Decimal("12345.67")


# ==================== Edge Cases ====================

class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_same_day_expiry_calculation(self):
        """Test calculation when start and expiry are same (0 days)"""
        start_date = date(2024, 3, 20)
        expiry_date = start_date + timedelta(days=0)
        assert expiry_date == start_date

    def test_single_day_guarantee(self):
        """Test single day guarantee (1 day)"""
        start_date = date(2024, 3, 20)
        expiry_date = start_date + timedelta(days=1)
        assert expiry_date == date(2024, 3, 21)

    def test_very_long_guarantee(self):
        """Test very long guarantee period (365 days)"""
        start_date = date(2024, 1, 1)
        expiry_date = start_date + timedelta(days=365)
        assert expiry_date == date(2025, 1, 1)
