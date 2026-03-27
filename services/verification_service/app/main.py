"""HigherMatch Verification Service entrypoint."""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class Settings:
    SERVICE_NAME: str = os.getenv("SERVICE_NAME", "verification-service")
    SERVICE_PORT: int = int(os.getenv("SERVICE_PORT", "8011"))
    KAFKA_BOOTSTRAP_SERVERS: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    CORS_ORIGINS: list[str] = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")


settings = Settings()
router_status = "healthy"
router_error: str | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s...", settings.SERVICE_NAME)
    yield
    logger.info("Shutting down %s...", settings.SERVICE_NAME)


app = FastAPI(
    title="HigherMatch Verification Service",
    description="Candidate verification service.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    from app.routers.verification import router as verification_router

    app.include_router(verification_router)
except Exception as exc:  # pragma: no cover - startup safety net
    router_status = "degraded"
    router_error = str(exc)
    logger.exception("Failed to load verification router")


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": router_status,
        "service": settings.SERVICE_NAME,
        "version": "1.0.0",
        "router_error": router_error,
        "kafka": settings.KAFKA_BOOTSTRAP_SERVERS,
        "openai_configured": bool(settings.OPENAI_API_KEY),
    }


@app.get("/", tags=["Root"])
async def root():
    return {
        "service": "HigherMatch Verification Service",
        "version": "1.0.0",
        "status": router_status,
    }
