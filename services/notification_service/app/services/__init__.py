"""
Email Service
Notification Service
"""

import asyncio
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Optional, Dict, Any

import aiosmtplib
import jinja2
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.config import get_settings

logger = logging.getLogger(__name__)


def format_currency(value: float) -> str:
    """Format currency with comma separators"""
    if value is None:
        return "0"
    return f"{value:,.2f}"


def comma_filter(value: Any) -> str:
    """Jinja2 filter for formatting numbers with commas"""
    if isinstance(value, (int, float)):
        return f"{value:,}"
    return str(value)


class EmailService:
    """Email sending service with Jinja2 templates"""

    def __init__(self):
        self.settings = get_settings()
        self.enabled = self.settings.EMAIL_ENABLED and not self.settings.EMAIL_DEV_MODE

        # Setup Jinja2 environment
        template_dir = Path(__file__).parent.parent / "templates"
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )
        self.jinja_env.filters["comma"] = comma_filter

        # Base template variables
        self.base_context = {
            "portal_url": "https://app.highermatch.com",
        }

    def _get_recipient(self, email: str) -> str:
        """Get actual recipient (dev mode override)"""
        if self.settings.EMAIL_DEV_MODE:
            return self.settings.EMAIL_DEV_RECIPIENT
        return email

    async def _send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        retry_count: int = 0,
    ) -> bool:
        """Send email via SMTP"""
        if not self.enabled:
            logger.info(f"[DEV MODE] Email to {to_email}: {subject}")
            return True

        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = f"{self.settings.SMTP_FROM_NAME} <{self.settings.SMTP_FROM_EMAIL}>"
        message["To"] = to_email

        html_part = MIMEText(html_content, "html", "utf-8")
        message.attach(html_part)

        try:
            await aiosmtplib.send(
                message,
                hostname=self.settings.SMTP_HOST,
                port=self.settings.SMTP_PORT,
                username=self.settings.SMTP_USER,
                password=self.settings.SMTP_PASSWORD,
                start_tls=self.settings.SMTP_USE_TLS,
            )
            logger.info(f"Email sent to {to_email}: {subject}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")

            # Retry logic
            if retry_count < self.settings.EMAIL_MAX_RETRIES:
                await asyncio.sleep(self.settings.EMAIL_RETRY_DELAY)
                return await self._send_email(
                    to_email, subject, html_content, retry_count + 1
                )

            return False

    def _render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render email template with context"""
        template = self.jinja_env.get_template(template_name)
        full_context = {**self.base_context, **context}
        return template.render(**full_context)

    async def send_match_completed(
        self,
        employer_email: str,
        employer_name: str,
        job_id: str,
        job_title: str,
        candidate_count: int,
        candidates: list,
        average_match_score: float,
    ) -> bool:
        """Send match completed notification email"""
        subject = f"【HigherMatch】您发布的「{job_title}」已匹配到 {candidate_count} 位优质候选人"

        context = {
            "employer_name": employer_name,
            "job_id": job_id,
            "job_title": job_title,
            "candidate_count": candidate_count,
            "candidates": candidates,
            "average_match_score": round(average_match_score, 1),
        }

        html = self._render_template("match_completed.html", context)
        return await self._send_email(
            self._get_recipient(employer_email), subject, html
        )

    async def send_invoice_generated(
        self,
        employer_email: str,
        employer_name: str,
        invoice_id: str,
        invoice_no: str,
        invoice_date: str,
        due_date: str,
        base_fee: float,
        urgent_premium: float,
        total_amount: float,
        guarantee_start_date: str,
        guarantee_expiry_date: str,
    ) -> bool:
        """Send invoice generated notification email"""
        subject = f"【HigherMatch】发票已生成 - ¥{total_amount:,.2f}"

        context = {
            "employer_name": employer_name,
            "invoice_id": invoice_id,
            "invoice_no": invoice_no,
            "invoice_date": invoice_date,
            "due_date": due_date,
            "base_fee": base_fee,
            "urgent_premium": urgent_premium,
            "total_amount": total_amount,
            "guarantee_start_date": guarantee_start_date,
            "guarantee_expiry_date": guarantee_expiry_date,
        }

        html = self._render_template("invoice_generated.html", context)
        return await self._send_email(
            self._get_recipient(employer_email), subject, html
        )

    async def send_guarantee_created(
        self,
        employer_email: str,
        employer_name: str,
        guarantee_id: str,
        guarantee_no: str,
        start_date: str,
        expiry_date: str,
    ) -> bool:
        """Send guarantee created notification email"""
        subject = "【HigherMatch】您的90天求职保障已生效"

        context = {
            "employer_name": employer_name,
            "guarantee_id": guarantee_id,
            "guarantee_no": guarantee_no,
            "start_date": start_date,
            "expiry_date": expiry_date,
        }

        html = self._render_template("guarantee_created.html", context)
        return await self._send_email(
            self._get_recipient(employer_email), subject, html
        )

    async def send_claim_approved(
        self,
        employer_email: str,
        employer_name: str,
        claim_id: str,
        claim_no: str,
        original_candidate_name: str,
        leaving_reason: str,
        review_date: str,
        replacement_candidate: Optional[dict] = None,
        estimated_match_date: Optional[str] = None,
    ) -> bool:
        """Send claim approved notification email"""
        from app.schemas import LEAVING_REASON_DISPLAY

        subject = "【HigherMatch】您的保障理赔申请已通过"

        context = {
            "employer_name": employer_name,
            "claim_id": claim_id,
            "claim_no": claim_no,
            "original_candidate_name": original_candidate_name,
            "leaving_reason_display": LEAVING_REASON_DISPLAY.get(
                leaving_reason, leaving_reason
            ),
            "review_date": review_date,
            "replacement_candidate": replacement_candidate,
            "estimated_match_date": estimated_match_date,
        }

        html = self._render_template("claim_approved.html", context)
        return await self._send_email(
            self._get_recipient(employer_email), subject, html
        )

    async def send_claim_rejected(
        self,
        employer_email: str,
        employer_name: str,
        claim_id: str,
        claim_no: str,
        guarantee_id: str,
        original_candidate_name: str,
        leaving_reason: str,
        rejection_reason: str,
        review_date: str,
    ) -> bool:
        """Send claim rejected notification email"""
        from app.schemas import LEAVING_REASON_DISPLAY

        subject = "【HigherMatch】保障理赔申请审核结果通知"

        context = {
            "employer_name": employer_name,
            "claim_id": claim_id,
            "claim_no": claim_no,
            "guarantee_id": guarantee_id,
            "original_candidate_name": original_candidate_name,
            "leaving_reason_display": LEAVING_REASON_DISPLAY.get(
                leaving_reason, leaving_reason
            ),
            "rejection_reason": rejection_reason,
            "review_date": review_date,
        }

        html = self._render_template("claim_rejected.html", context)
        return await self._send_email(
            self._get_recipient(employer_email), subject, html
        )


# Singleton instance
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Get email service singleton"""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
