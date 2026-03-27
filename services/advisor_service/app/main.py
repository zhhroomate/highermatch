"""HigherMatch Advisor Service entrypoint."""

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
    SERVICE_NAME: str = os.getenv("SERVICE_NAME", "advisor-service")
    SERVICE_PORT: int = int(os.getenv("SERVICE_PORT", "8012"))
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
    title="HigherMatch Advisor Service",
    description="AI career advisor service.",
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
    from app.routers.advisor import router as advisor_router

    app.include_router(advisor_router)
except Exception as exc:  # pragma: no cover - startup safety net
    router_status = "degraded"
    router_error = str(exc)
    logger.exception("Failed to load advisor router")


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": router_status,
        "service": settings.SERVICE_NAME,
        "version": "1.0.0",
        "router_error": router_error,
        "openai_configured": bool(settings.OPENAI_API_KEY),
    }


@app.get("/", tags=["Root"])
async def root():
    return {
        "service": "HigherMatch Advisor Service",
        "version": "1.0.0",
        "status": router_status,
    }
