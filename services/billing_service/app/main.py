"""
Billing Service Main Application
HigherMatch™ AI Recruitment Platform

FastAPI application with Kafka consumer for billing service.
Handles invoice creation from onboarding events and payment processing.
"""

import asyncio
import json
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

import structlog
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import selectinload

from app.models import Base, Invoice, InvoiceStatus, Employer, PaymentCallback
from app.schemas import (
    OnboardingConfirmedMessage,
    InvoicePaidMessage,
    HealthResponse,
)

# ==================== Configuration ====================

logger = structlog.get_logger()


class Settings(BaseSettings):
    """Application settings"""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Application
    SERVICE_NAME: str = "billing_service"
    SERVICE_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@postgres:5432/highermatch_dev"

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "kafka:9092"
    KAFKA_CONSUMER_GROUP: str = "billing_service_group"
    KAFKA_TOPIC_ONBOARDING_CONFIRMED: str = "onboarding.confirmed"
    KAFKA_TOPIC_INVOICE_PAID: str = "invoice.paid"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # Payment (mock)
    PAYMENT_SECRET_KEY: str = "mock_payment_secret_key_12345"
    PAYMENT_EXPIRE_MINUTES: int = 30


settings = Settings()

# ==================== Database Setup ====================

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncSession:
    """Dependency to get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# ==================== Kafka Setup ====================

kafka_consumer: Optional[AIOKafkaConsumer] = None
kafka_producer: Optional[AIOKafkaProducer] = None


async def init_kafka():
    """Initialize Kafka consumer and producer"""
    global kafka_consumer, kafka_producer

    # Create producer for sending messages
    kafka_producer = AIOKafkaProducer(
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
    )
    await kafka_producer.start()
    logger.info("kafka_producer_started")

    # Create consumer for onboarding events
    kafka_consumer = AIOKafkaConsumer(
        settings.KAFKA_TOPIC_ONBOARDING_CONFIRMED,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id=settings.KAFKA_CONSUMER_GROUP,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        auto_offset_reset="earliest",
        enable_auto_commit=True,
    )
    await kafka_consumer.start()
    logger.info("kafka_consumer_started", topic=settings.KAFKA_TOPIC_ONBOARDING_CONFIRMED)


async def close_kafka():
    """Close Kafka connections"""
    global kafka_consumer, kafka_producer

    if kafka_consumer:
        await kafka_consumer.stop()
        kafka_consumer = None
        logger.info("kafka_consumer_stopped")

    if kafka_producer:
        await kafka_producer.stop()
        kafka_producer = None
        logger.info("kafka_producer_stopped")


# ==================== Kafka Consumer Loop ====================

async def kafka_consumer_loop():
    """
    Kafka consumer loop for processing onboarding.confirmed events.

    Business Logic:
    - commission_rate default = 0.10 (10%)
    - base_fee = offer_annual_salary * commission_rate
    - urgent_premium = base_fee * 0.3 if is_urgent, else 0
    - total_fee = base_fee + urgent_premium

    IMPORTANT: All amounts are converted to 'fen' (cents) as integers to avoid
    floating-point precision issues.
    """
    logger.info("kafka_consumer_loop_started")

    while True:
        try:
            async for message in kafka_consumer:
                try:
                    logger.info(
                        "kafka_message_received",
                        topic=message.topic,
                        partition=message.partition,
                        offset=message.offset
                    )

                    # Parse message
                    data = message.value
                    onboarding_msg = OnboardingConfirmedMessage(**data)

                    logger.info(
                        "processing_onboarding",
                        job_id=onboarding_msg.job_id,
                        salary=onboarding_msg.offer_annual_salary,
                        is_urgent=onboarding_msg.is_urgent
                    )

                    # Calculate billing in yuan first
                    commission_rate = Decimal("0.10")
                    annual_salary_yuan = Decimal(str(onboarding_msg.offer_annual_salary))

                    # Calculate base fee
                    base_fee_yuan = annual_salary_yuan * commission_rate

                    # Calculate urgent premium
                    if onboarding_msg.is_urgent:
                        urgent_premium_yuan = base_fee_yuan * Decimal("0.3")
                    else:
                        urgent_premium_yuan = Decimal("0")

                    # Total fee
                    total_fee_yuan = base_fee_yuan + urgent_premium_yuan

                    # Convert to fen (cents) - multiply by 100 and round
                    base_fee_fen = int(round(base_fee_yuan * 100))
                    urgent_premium_fen = int(round(urgent_premium_yuan * 100))
                    total_fee_fen = int(round(total_fee_yuan * 100))
                    annual_salary_fen = int(round(annual_salary_yuan * 100))

                    logger.info(
                        "billing_calculated",
                        base_fee=base_fee_fen,
                        urgent_premium=urgent_premium_fen,
                        total_fee=total_fee_fen
                    )

                    # Create invoice in database
                    async with AsyncSessionLocal() as session:
                        # Generate invoice number
                        invoice_no = f"INV-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

                        # Create invoice
                        invoice = Invoice(
                            id=str(uuid.uuid4()),
                            invoice_no=invoice_no,
                            employer_id=onboarding_msg.employer_id,
                            job_id=onboarding_msg.job_id,
                            status=InvoiceStatus.PENDING,
                            offer_annual_salary=annual_salary_fen,
                            commission_rate=10,
                            base_fee=base_fee_fen,
                            is_urgent=onboarding_msg.is_urgent,
                            urgent_premium=urgent_premium_fen,
                            total_fee=total_fee_fen,
                            description=f"Job placement fee for {onboarding_msg.job_id}"
                        )

                        session.add(invoice)
                        await session.commit()
                        await session.refresh(invoice)

                        logger.info(
                            "invoice_created",
                            invoice_id=invoice.id,
                            invoice_no=invoice.invoice_no,
                            total_fee=invoice.total_fee
                        )

                except Exception as e:
                    logger.error(
                        "kafka_message_processing_error",
                        error=str(e),
                        message=message.value
                    )

        except Exception as e:
            logger.error("kafka_consumer_error", error=str(e))
            await asyncio.sleep(5)  # Wait before reconnecting


async def send_invoice_paid_event(invoice: Invoice):
    """
    Send invoice.paid Kafka event after successful payment.

    Args:
        invoice: The paid invoice
    """
    if not kafka_producer:
        logger.warning("kafka_producer_not_available")
        return

    message = InvoicePaidMessage(
        invoice_id=invoice.id,
        invoice_no=invoice.invoice_no,
        employer_id=invoice.employer_id,
        job_id=invoice.job_id,
        total_fee_yuan=invoice.total_fee / 100,  # Convert fen to yuan
        paid_at=invoice.paid_at or datetime.utcnow()
    )

    try:
        await kafka_producer.send_and_wait(
            settings.KAFKA_TOPIC_INVOICE_PAID,
            value=message.model_dump()
        )
        logger.info(
            "invoice_paid_event_sent",
            invoice_id=invoice.id,
            topic=settings.KAFKA_TOPIC_INVOICE_PAID
        )
    except Exception as e:
        logger.error("failed_to_send_invoice_paid_event", error=str(e))


# ==================== Application Lifespan ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    # Startup
    logger.info("billing_service_starting", version=settings.SERVICE_VERSION)

    # Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("database_tables_created")

    # Initialize Kafka
    try:
        await init_kafka()
    except Exception as e:
        logger.warning("kafka_init_failed", error=str(e))

    # Start Kafka consumer loop
    consumer_task = asyncio.create_task(kafka_consumer_loop())

    yield

    # Shutdown
    logger.info("billing_service_shutting_down")
    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        pass
    await close_kafka()


# ==================== FastAPI Application ====================

app = FastAPI(
    title="HigherMatch Billing Service",
    description="Billing and payment service for HigherMatch recruitment platform",
    version=settings.SERVICE_VERSION,
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

# Include routers
from app.routers import billing

app.include_router(billing.router, prefix="/api/v1/billing", tags=["Billing"])


# ==================== Health Check ====================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.
    Verifies database and Kafka connectivity.
    """
    db_connected = False
    kafka_connected = kafka_consumer is not None and kafka_producer is not None

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(select(Invoice).limit(1))
            db_connected = True
    except Exception as e:
        logger.warning("health_check_db_failed", error=str(e))

    return HealthResponse(
        status="healthy" if (db_connected and kafka_connected) else "degraded",
        version=settings.SERVICE_VERSION,
        kafka_connected=kafka_connected,
        db_connected=db_connected
    )


# ==================== Dependency Exports ====================

__all__ = [
    "app",
    "settings",
    "get_db",
    "AsyncSessionLocal",
    "send_invoice_paid_event",
]
