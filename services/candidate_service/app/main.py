"""
HigherMatch™ Candidate Service - Main Application
==================================================

FastAPI 应用入口，包含健康检查和候选人相关 API。

端口: 8003

版本: 1.0.0
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

# 添加 shared 模块路径
import sys
sys.path.insert(0, "/workspace/highermatch")

from shared.auth_middleware import init_auth, get_jwt_manager
from shared.core.redis import RedisClient
from app.schemas.candidate import HealthResponse

# ==================== 日志配置 ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== 配置管理 ====================
class Settings:
    SERVICE_NAME: str = os.getenv("SERVICE_NAME", "candidate-service")
    SERVICE_PORT: int = int(os.getenv("SERVICE_PORT", "8003"))
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://highermatch:highermatch@postgres:5432/highermatch_dev"
    )
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    KAFKA_BOOTSTRAP_SERVERS: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    CORS_ORIGINS: list = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

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
    """获取数据库会话"""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ==================== Redis 客户端 ====================
redis_client: Optional[RedisClient] = None

async def get_redis() -> RedisClient:
    """获取 Redis 客户端"""
    global redis_client
    if redis_client is None:
        redis_client = RedisClient(settings.REDIS_URL)
    return redis_client


# ==================== Kafka 生产者 ====================
kafka_producer: Optional["CandidateKafkaProducer"] = None

class CandidateKafkaProducer:
    """简化的 Kafka 生产者"""

    def __init__(self, bootstrap_servers: str):
        self.bootstrap_servers = bootstrap_servers
        self._producer = None

    async def send(self, topic: str, value: dict) -> None:
        """发送消息"""
        logger.info(f"Sending to Kafka topic '{topic}': {value}")
        # TODO: 实现实际的 Kafka 发送逻辑

    async def close(self) -> None:
        """关闭生产者"""
        if self._producer:
            await self._producer.stop()

async def get_kafka_producer() -> Optional[CandidateKafkaProducer]:
    """获取 Kafka 生产者"""
    global kafka_producer
    if kafka_producer is None:
        kafka_producer = CandidateKafkaProducer(settings.KAFKA_BOOTSTRAP_SERVERS)
    return kafka_producer


# ==================== 生命周期管理 ====================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info(f"Starting {settings.SERVICE_NAME}...")

    # 初始化认证模块
    init_auth(
        secret_key=settings.JWT_SECRET_KEY,
        redis_url=settings.REDIS_URL,
    )
    logger.info("Auth module initialized")

    # 初始化 Redis
    global redis_client
    try:
        redis_client = RedisClient(settings.REDIS_URL)
        await redis_client.ping()
        logger.info("Redis connected")
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}")

    yield

    # 清理资源
    logger.info(f"Shutting down {settings.SERVICE_NAME}...")
    await engine.dispose()
    if redis_client:
        await redis_client.close()
    if kafka_producer:
        await kafka_producer.close()


# ==================== FastAPI 应用 ====================
app = FastAPI(
    title="HigherMatch Candidate Service",
    description="HigherMatch™ AI 招聘平台 - 候选人服务 API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
from app.routers import candidates

app.include_router(candidates.router)


# ==================== 健康检查路由 ====================
@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    健康检查

    检查数据库和 Redis 连接状态。
    """
    db_status = "healthy"
    redis_status = "healthy"

    # 检查数据库
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "unhealthy"

    # 检查 Redis
    try:
        if redis_client:
            await redis_client.ping()
        else:
            redis_status = "not_configured"
    except Exception:
        redis_status = "unhealthy"

    overall_status = "healthy"
    if db_status == "unhealthy":
        overall_status = "unhealthy"
    elif redis_status == "unhealthy":
        overall_status = "degraded"

    return HealthResponse(
        status=overall_status,
        service=settings.SERVICE_NAME,
        version="1.0.0",
        database=db_status,
        redis=redis_status,
    )


@app.get("/", tags=["Root"])
async def root():
    """根路径"""
    return {
        "service": "HigherMatch Candidate Service",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": [
            "POST /api/v1/resume/parse",
            "GET /api/v1/candidates/profile",
            "PUT /api/v1/candidates/profile",
            "GET /api/v1/candidates/recommendations",
            "POST /api/v1/applications",
        ]
    }


# ==================== 异常处理器 ====================
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常处理器"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "内部服务器错误"
            }
        }
    )


# ==================== 启动入口 ====================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.SERVICE_PORT,
        reload=True
    )
