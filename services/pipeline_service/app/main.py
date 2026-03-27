"""
HigherMatch™ AI 招聘平台 - Pipeline Service
FastAPI 应用入口 - 使用 SQLAlchemy 2.0 Async ORM

版本: 1.0.0
"""

import os
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.routers import pipeline, ws
from app.services.websocket import get_websocket_manager

# ==================== 日志配置 ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== 配置管理 ====================
class Settings:
    SERVICE_NAME: str = os.getenv("SERVICE_NAME", "pipeline-service")
    SERVICE_PORT: int = int(os.getenv("SERVICE_PORT", "8003"))
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://highermatch:highermatch@postgres:5432/highermatch_dev"
    )
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    CORS_ORIGINS: list = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")

settings = Settings()

# ==================== 数据库配置 ====================
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=os.getenv("SQL_ECHO", "false").lower() == "true",
    pool_pre_ping=True,
    poolclass=NullPool
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ==================== Pydantic Schemas ====================
class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    service: str
    version: str
    database: str


# ==================== 生命周期管理 ====================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info(f"Starting {settings.SERVICE_NAME}...")

    # 启动 WebSocket 心跳检测
    ws_manager = get_websocket_manager()
    await ws_manager.start_heartbeat()

    yield

    logger.info(f"Shutting down {settings.SERVICE_NAME}...")

    # 停止 WebSocket 心跳检测
    await ws_manager.stop_heartbeat()

    await engine.dispose()


# ==================== FastAPI 应用 ====================
app = FastAPI(
    title="HigherMatch Pipeline Service",
    description="HigherMatch™ AI 招聘平台 - 招聘管道服务 API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(pipeline.router)
app.include_router(ws.router)


# ==================== 健康检查路由 ====================
@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check(db: AsyncSession = Depends(get_db)):
    """健康检查"""
    db_status = "healthy"
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "unhealthy"

    return HealthResponse(
        status="healthy" if db_status == "healthy" else "degraded",
        service=settings.SERVICE_NAME,
        version="1.0.0",
        database=db_status,
    )


@app.get("/", tags=["Root"])
async def root():
    """根路由"""
    return {
        "service": "HigherMatch Pipeline Service",
        "version": "1.0.0",
        "status": "operational"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.SERVICE_PORT,
        reload=True
    )
