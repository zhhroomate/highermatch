"""HigherMatch Embedding Service entrypoint."""

import logging
import os
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class Settings:
    SERVICE_NAME: str = os.getenv("SERVICE_NAME", "embedding-service")
    SERVICE_PORT: int = int(os.getenv("SERVICE_PORT", "8010"))
    QDRANT_URL: str = os.getenv("QDRANT_URL", "http://qdrant:6333")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    CORS_ORIGINS: list[str] = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")


settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s...", settings.SERVICE_NAME)
    yield
    logger.info("Shutting down %s...", settings.SERVICE_NAME)


app = FastAPI(
    title="HigherMatch Embedding Service",
    description="Embedding and Qdrant helper service.",
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


async def _check_qdrant() -> str:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.QDRANT_URL}/readyz")
            if response.is_success:
                return "healthy"
    except Exception as exc:
        logger.warning("Qdrant health check failed: %s", exc)
    return "unhealthy"


@app.get("/health", tags=["Health"])
async def health_check():
    qdrant_status = await _check_qdrant()
    overall_status = "healthy" if qdrant_status == "healthy" else "degraded"
    return {
        "status": overall_status,
        "service": settings.SERVICE_NAME,
        "version": "1.0.0",
        "qdrant": qdrant_status,
        "openai_configured": bool(settings.OPENAI_API_KEY),
    }


@app.get("/", tags=["Root"])
async def root():
    return {
        "service": "HigherMatch Embedding Service",
        "version": "1.0.0",
        "status": "operational",
    }
