"""
Notification Service Main Application
HigherMatch™ AI Recruitment Platform

FastAPI application for notification service with Kafka consumer.
"""

import asyncio
import logging
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.services.kafka_consumer import NotificationKafkaConsumer

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
)

logger = structlog.get_logger()

# Settings
settings = get_settings()

# Kafka consumer instance
kafka_consumer: NotificationKafkaConsumer = None
consumer_task: asyncio.Task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global kafka_consumer, consumer_task

    # Startup
    logger.info(
        "notification_service_starting",
        service=settings.SERVICE_NAME,
        log_level=settings.LOG_LEVEL,
    )

    # Start Kafka consumer in background
    kafka_consumer = NotificationKafkaConsumer()
    consumer_task = asyncio.create_task(kafka_consumer.run())

    logger.info("notification_service_started")

    yield

    # Shutdown
    logger.info("notification_service_stopping")

    # Stop Kafka consumer
    if kafka_consumer:
        await kafka_consumer.stop()

    # Cancel consumer task
    if consumer_task:
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass

    logger.info("notification_service_stopped")


# Create FastAPI app
app = FastAPI(
    title="HigherMatch Notification Service",
    description="Email notification service for HigherMatch AI Recruitment Platform",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== Health Check Endpoints ====================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": settings.SERVICE_NAME,
        "version": "1.0.0",
    }


@app.get("/health/ready")
async def readiness_check():
    """Readiness check endpoint"""
    # Check if Kafka consumer is running
    if kafka_consumer and kafka_consumer.running:
        return {
            "status": "ready",
            "kafka": "connected",
        }
    else:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "not_ready",
                "kafka": "disconnected",
            },
        )


# ==================== Test Endpoints ====================

@app.post("/test/send-email")
async def test_send_email(
    to_email: str,
    template: str = "match_completed",
):
    """
    Test endpoint to send a sample email.
    For development/testing only.
    """
    from app.services import get_email_service

    email_service = get_email_service()

    if template == "match_completed":
        success = await email_service.send_match_completed(
            employer_email=to_email,
            employer_name="测试企业",
            job_id="test-job-123",
            job_title="高级Python工程师",
            candidate_count=3,
            candidates=[
                {
                    "name": "张三",
                    "match_score": 95,
                    "current_title": "Python开发工程师",
                    "experience_years": 5,
                    "expected_salary": 360000,
                    "highlights": ["BAT背景", "熟悉AI", "开源贡献者"],
                },
                {
                    "name": "李四",
                    "match_score": 88,
                    "current_title": "全栈工程师",
                    "experience_years": 4,
                    "expected_salary": 320000,
                    "highlights": ["创业公司经验", "架构设计能力"],
                },
            ],
            average_match_score=91.5,
        )
    elif template == "invoice_generated":
        success = await email_service.send_invoice_generated(
            employer_email=to_email,
            employer_name="测试企业",
            invoice_id="test-inv-123",
            invoice_no="INV-20240320-TEST001",
            invoice_date="2024-03-20",
            due_date="2024-04-05",
            base_fee=12000.00,
            urgent_premium=3600.00,
            total_amount=15600.00,
            guarantee_start_date="2024-03-20",
            guarantee_expiry_date="2024-06-18",
        )
    elif template == "guarantee_created":
        success = await email_service.send_guarantee_created(
            employer_email=to_email,
            employer_name="测试企业",
            guarantee_id="test-gua-123",
            guarantee_no="GUA-20240320-TEST001",
            start_date="2024-03-20",
            expiry_date="2024-06-18",
        )
    elif template == "claim_approved":
        success = await email_service.send_claim_approved(
            employer_email=to_email,
            employer_name="测试企业",
            claim_id="test-clm-123",
            claim_no="CLM-20240320-TEST001",
            original_candidate_name="王五",
            leaving_reason="career_development",
            review_date="2024-03-20",
            estimated_match_date="2024-03-27",
        )
    elif template == "claim_rejected":
        success = await email_service.send_claim_rejected(
            employer_email=to_email,
            employer_name="测试企业",
            claim_id="test-clm-123",
            claim_no="CLM-20240320-TEST001",
            guarantee_id="test-gua-123",
            original_candidate_name="王五",
            leaving_reason="personal",
            rejection_reason="候选人离职时间已超过保障期限",
            review_date="2024-03-20",
        )
    else:
        raise HTTPException(status_code=400, detail="Unknown template")

    return {
        "success": success,
        "message": f"Test email sent to {to_email}" if success else "Failed to send email",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        log_level=settings.LOG_LEVEL.lower(),
    )
