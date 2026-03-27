"""
Guarantee Service Main Application
HigherMatch™ AI Recruitment Platform

FastAPI application with Kafka consumer for guarantee management.
Handles guarantee creation from invoice.paid events and claim processing.
"""

import asyncio
import json
import uuid
from contextlib import asynccontextmanager
from datetime import date, timedelta
from typing import Optional

import structlog
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.models import Base, Guarantee, GuaranteeStatus, GuaranteeClaim, ClaimStatus
from app.schemas import InvoicePaidMessage, HealthResponse

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
    SERVICE_NAME: str = "guarantee_service"
    SERVICE_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@postgres:5432/highermatch_dev"

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "kafka:9092"
    KAFKA_CONSUMER_GROUP: str = "guarantee_service_group"
    KAFKA_TOPIC_INVOICE_PAID: str = "invoice.paid"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # Guarantee settings
    GUARANTEE_DURATION_DAYS: int = 90


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

    kafka_producer = AIOKafkaProducer(
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
    )
    await kafka_producer.start()
    logger.info("kafka_producer_started")

    kafka_consumer = AIOKafkaConsumer(
        settings.KAFKA_TOPIC_INVOICE_PAID,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id=settings.KAFKA_CONSUMER_GROUP,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        auto_offset_reset="earliest",
        enable_auto_commit=True,
    )
    await kafka_consumer.start()
    logger.info("kafka_consumer_started", topic=settings.KAFKA_TOPIC_INVOICE_PAID)


async def close_kafka():
    """Close Kafka connections"""
    global kafka_consumer, kafka_producer

    if kafka_consumer:
        await kafka_consumer.stop()
        kafka_consumer = None

    if kafka_producer:
        await kafka_producer.stop()
        kafka_producer = None


# ==================== Kafka Consumer Loop ====================

async def kafka_consumer_loop():
    """
    Kafka consumer loop for processing invoice.paid events.

    When an invoice is paid:
    1. Create a new guarantee record
    2. Set start_date = TODAY
    3. Set expiry_date = TODAY + 90 days
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

                    data = message.value
                    invoice_msg = InvoicePaidMessage(**data)

                    logger.info(
                        "processing_invoice_paid",
                        invoice_id=invoice_msg.invoice_id,
                        job_id=invoice_msg.job_id,
                        amount=invoice_msg.total_fee_yuan
                    )

                    # Create guarantee
                    async with AsyncSessionLocal() as session:
                        today = date.today()
                        expiry = today + timedelta(days=settings.GUARANTEE_DURATION_DAYS)

                        # Generate guarantee number
                        guarantee_no = f"GRT-{today.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

                        # Convert total fee to fen
                        total_fee_fen = int(round(invoice_msg.total_fee_yuan * 100))

                        guarantee = Guarantee(
                            id=str(uuid.uuid4()),
                            guarantee_no=guarantee_no,
                            employer_id=invoice_msg.employer_id,
                            job_id=invoice_msg.job_id,
                            invoice_id=invoice_msg.invoice_id,
                            status=GuaranteeStatus.ACTIVE,
                            start_date=today,
                            expiry_date=expiry,
                            total_fee=total_fee_fen,
                        )

                        session.add(guarantee)
                        await session.commit()
                        await session.refresh(guarantee)

                        logger.info(
                            "guarantee_created",
                            guarantee_id=guarantee.id,
                            guarantee_no=guarantee.guarantee_no,
                            start_date=today,
                            expiry_date=expiry
                        )

                except Exception as e:
                    logger.error(
                        "kafka_message_processing_error",
                        error=str(e),
                        message=message.value
                    )

        except Exception as e:
            logger.error("kafka_consumer_error", error=str(e))
            await asyncio.sleep(5)


# ==================== Scheduler Setup ====================

scheduler = AsyncIOScheduler()


async def expire_guarantees():
    """
    Daily scheduled task to expire guarantees.

    Scans for guarantees where:
    - status = ACTIVE
    - expiry_date < TODAY

    Updates status to EXPIRED.
    """
    logger.info("expire_guarantees_task_started")

    try:
        today = date.today()

        async with AsyncSessionLocal() as session:
            # Find expired guarantees
            query = select(Guarantee).where(
                Guarantee.status == GuaranteeStatus.ACTIVE,
                Guarantee.expiry_date < today
            )
            result = await session.execute(query)
            expired_guarantees = result.scalars().all()

            if expired_guarantees:
                for guarantee in expired_guarantees:
                    guarantee.status = GuaranteeStatus.EXPIRED
                    logger.info(
                        "guarantee_expired",
                        guarantee_id=guarantee.id,
                        guarantee_no=guarantee.guarantee_no,
                        expiry_date=guarantee.expiry_date
                    )

                await session.commit()
                logger.info(
                    "expire_guarantees_task_completed",
                    expired_count=len(expired_guarantees)
                )
            else:
                logger.info("expire_guarantees_task_completed", expired_count=0)

    except Exception as e:
        logger.error("expire_guarantees_task_error", error=str(e))


# ==================== Application Lifespan ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    # Startup
    logger.info("guarantee_service_starting", version=settings.SERVICE_VERSION)

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

    # Start scheduler for daily tasks
    scheduler.add_job(
        expire_guarantees,
        CronTrigger(hour=0, minute=5),  # Run at 00:05 every day
        id="expire_guarantees",
        name="Expire Guarantees",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("scheduler_started")

    yield

    # Shutdown
    logger.info("guarantee_service_shutting_down")
    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        pass

    scheduler.shutdown(wait=False)
    await close_kafka()


# ==================== FastAPI Application ====================

app = FastAPI(
    title="HigherMatch Guarantee Service",
    description="Guarantee management service for HigherMatch recruitment platform",
    version=settings.SERVICE_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.routers import guarantee

app.include_router(guarantee.router, prefix="/api/v1/guarantee", tags=["Guarantee"])


# ==================== Health Check ====================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    db_connected = False
    kafka_connected = kafka_consumer is not None and kafka_producer is not None
    scheduler_running = scheduler.running

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(select(Guarantee).limit(1))
            db_connected = True
    except Exception as e:
        logger.warning("health_check_db_failed", error=str(e))

    return HealthResponse(
        status="healthy" if (db_connected and kafka_connected and scheduler_running) else "degraded",
        version=settings.SERVICE_VERSION,
        kafka_connected=kafka_connected,
        db_connected=db_connected,
        scheduler_running=scheduler_running
    )


__all__ = [
    "app",
    "settings",
    "get_db",
    "AsyncSessionLocal",
]
