"""
HigherMatch™ - FastAPI Application Factory Template
====================================================

标准 FastAPI 微服务应用工厂模板。
所有微服务 (User Service, Job Service, AI Service) 应基于此模板创建。

功能特性:
- Lifespan 事件管理 (数据库、Redis 连接生命周期)
- 全局 CORS 中间件
- 全局异常处理器
- 健康检查路由
- 统一响应格式

版本: 1.0.0

使用说明:
    1. 复制此文件到服务的 app/ 目录
    2. 修改 SERVICE_NAME 为实际服务名称
    3. 添加业务路由和逻辑

依赖:
    - fastapi >= 0.109.0
    - uvicorn[standard] >= 0.27.0
    - shared (HigherMatch Shared Core Library)
"""

import logging
import sys
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# ==================== 导入共享模块 ====================
try:
    from shared.core.config import Settings, get_settings
    from shared.core.db import (
        Base,
        engine,
        init_db,
        dispose_engine,
        check_db_health,
    )
    from shared.core.redis import (
        get_redis,
        close_redis,
        redis_health_check,
    )
    from shared.core.exceptions import (
        HigherMatchException,
        ErrorCode,
        ErrorResponse,
        ErrorDetail,
        register_exception_handlers,
    )
    SHARED_AVAILABLE = True
except ImportError:
    SHARED_AVAILABLE = False
    logging.warning("Shared module not available, using standalone configuration")

# ==================== 日志配置 ====================
def setup_logging() -> logging.Logger:
    """
    配置应用日志

    Returns:
        配置好的 Logger 实例
    """
    logger = logging.getLogger("highermatch")

    # 避免重复配置
    if logger.handlers:
        return logger

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    return logger


logger = setup_logging()


# ==================== 配置管理 ====================
class ServiceConfig:
    """
    服务独立配置 (当 shared 模块不可用时使用)

    当 shared 模块可用时，优先使用 shared.core.config.Settings
    """

    SERVICE_NAME: str = "highermatch-service"
    SERVICE_PORT: int = 8000
    DEBUG: bool = True

    # CORS 配置
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    CORS_CREDENTIALS: bool = True
    CORS_METHODS: list[str] = ["*"]
    CORS_HEADERS: list[str] = ["*"]

    # 数据库配置
    DATABASE_URL: str = "postgresql+asyncpg://highermatch:highermatch@postgres:5432/highermatch_dev"

    # Redis 配置
    REDIS_URL: str = "redis://redis:6379/0"

    def __init__(self) -> None:
        if SHARED_AVAILABLE:
            settings = get_settings()
            self.SERVICE_NAME = settings.service_name
            self.SERVICE_PORT = settings.api_port
            self.DEBUG = settings.debug
            self.CORS_ORIGINS = settings.cors.allow_origins
            self.DATABASE_URL = settings.database.async_url
            self.REDIS_URL = settings.redis.url


config = ServiceConfig()


# ==================== Pydantic 模型 ====================
class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    service: str
    version: str
    database: str
    redis: str
    timestamp: str


class ErrorResponseModel(BaseModel):
    """统一错误响应格式"""
    success: bool = False
    error: dict[str, Any]


# ==================== Lifespan 管理器 ====================
@asynccontextmanager
async def lifespan_manager(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    应用生命周期管理器

    管理以下资源的启动和关闭:
    - 数据库连接池
    - Redis 连接
    - 应用初始化

    使用方式:
        app = FastAPI(lifespan=lifespan_manager)
    """
    logger.info(f"{'=' * 50}")
    logger.info(f"Starting {config.SERVICE_NAME}...")
    logger.info(f"{'=' * 50}")

    # ==================== 启动阶段 ====================
    startup_success = True

    # 1. 初始化数据库
    if SHARED_AVAILABLE:
        try:
            logger.info("Initializing database connection...")
            await init_db()
            db_healthy = await check_db_health()
            if db_healthy:
                logger.info("✓ Database connection established")
            else:
                logger.warning("⚠ Database connection failed, service may have limited functionality")
                startup_success = False
        except Exception as e:
            logger.error(f"✗ Database initialization failed: {e}")
            startup_success = False
    else:
        logger.info("✓ Database (standalone mode)")

    # 2. 初始化 Redis
    if SHARED_AVAILABLE:
        try:
            logger.info("Initializing Redis connection...")
            await get_redis()
            redis_healthy = await redis_health_check()
            if redis_healthy:
                logger.info("✓ Redis connection established")
            else:
                logger.warning("⚠ Redis connection failed, caching disabled")
        except Exception as e:
            logger.error(f"✗ Redis initialization failed: {e}")
    else:
        logger.info("✓ Redis (standalone mode)")

    # 3. 应用启动完成
    logger.info(f"{'=' * 50}")
    logger.info(f"{config.SERVICE_NAME} started successfully")
    logger.info(f"Documentation: http://0.0.0.0:{config.SERVICE_PORT}/docs")
    logger.info(f"{'=' * 50}")

    yield  # 应用运行中

    # ==================== 关闭阶段 ====================
    logger.info(f"{'=' * 50}")
    logger.info(f"Shutting down {config.SERVICE_NAME}...")

    # 1. 关闭 Redis 连接
    if SHARED_AVAILABLE:
        try:
            await close_redis()
            logger.info("✓ Redis connection closed")
        except Exception as e:
            logger.error(f"✗ Redis shutdown error: {e}")

    # 2. 关闭数据库连接
    if SHARED_AVAILABLE:
        try:
            await dispose_engine()
            logger.info("✓ Database connection closed")
        except Exception as e:
            logger.error(f"✗ Database shutdown error: {e}")

    logger.info(f"{config.SERVICE_NAME} shutdown complete")
    logger.info(f"{'=' * 50}")


# ==================== FastAPI 应用工厂 ====================
def create_app() -> FastAPI:
    """
    创建 FastAPI 应用实例

    这是应用工厂函数，所有微服务应使用此函数创建应用。

    Returns:
        配置好的 FastAPI 应用实例

    使用示例:
        from app.main import create_app

        app = create_app()

        # 开发环境运行
        # uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
    """
    # 创建 FastAPI 实例
    app = FastAPI(
        title=f"HigherMatch™ {config.SERVICE_NAME.title()}",
        description="HigherMatch™ AI 招聘平台微服务 API",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan_manager,
    )

    # ==================== 注册中间件 ====================

    # CORS 中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.CORS_ORIGINS,
        allow_credentials=config.CORS_CREDENTIALS,
        allow_methods=config.CORS_METHODS,
        allow_headers=config.CORS_HEADERS,
    )

    logger.info(f"CORS middleware configured: {config.CORS_ORIGINS}")

    # ==================== 注册异常处理器 ====================

    if SHARED_AVAILABLE:
        # 使用共享模块的异常处理器
        register_exception_handlers(app)
        logger.info("Global exception handlers registered (shared)")
    else:
        # 独立异常处理器
        @app.exception_handler(HigherMatchException)
        async def highermatch_exception_handler(
            request: Request,
            exc: HigherMatchException
        ) -> JSONResponse:
            """处理 HigherMatch 自定义异常"""
            logger.warning(
                f"[{exc.code}] {exc.message}",
                extra={"path": request.url.path}
            )
            return JSONResponse(
                status_code=exc.status_code,
                content=ErrorResponse(
                    success=False,
                    error=ErrorDetail(
                        code=exc.code,
                        message=exc.message,
                        details=exc.details,
                    )
                ).model_dump(),
            )

        @app.exception_handler(ValueError)
        async def value_error_handler(
            request: Request,
            exc: ValueError
        ) -> JSONResponse:
            """处理值错误异常"""
            logger.warning(
                f"Validation error: {exc}",
                extra={"path": request.url.path}
            )
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=ErrorResponse(
                    success=False,
                    error=ErrorDetail(
                        code=ErrorCode.VALIDATION_ERROR,
                        message=str(exc),
                    )
                ).model_dump(),
            )

        @app.exception_handler(Exception)
        async def generic_exception_handler(
            request: Request,
            exc: Exception
        ) -> JSONResponse:
            """处理未捕获的异常"""
            logger.error(
                f"Unhandled exception: {exc}",
                exc_info=True,
                extra={"path": request.url.path}
            )
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content=ErrorResponse(
                    success=False,
                    error=ErrorDetail(
                        code=ErrorCode.INTERNAL_ERROR,
                        message="服务器内部错误，请稍后重试",
                    )
                ).model_dump(),
            )

        logger.info("Global exception handlers registered (standalone)")

    # ==================== 健康检查路由 ====================

    @app.get(
        "/health",
        response_model=HealthResponse,
        tags=["Health"],
        summary="健康检查",
        description="检查服务、数据库和 Redis 的健康状态"
    )
    async def health_check() -> HealthResponse:
        """
        健康检查端点

        返回服务整体健康状态，包含:
        - 服务状态
        - 数据库连接状态
        - Redis 连接状态
        """
        db_status = "unknown"
        redis_status = "unknown"

        # 检查数据库
        if SHARED_AVAILABLE:
            try:
                db_healthy = await check_db_health()
                db_status = "healthy" if db_healthy else "unhealthy"
            except Exception:
                db_status = "unhealthy"
        else:
            db_status = "standalone"

        # 检查 Redis
        if SHARED_AVAILABLE:
            try:
                redis_healthy = await redis_health_check()
                redis_status = "healthy" if redis_healthy else "unhealthy"
            except Exception:
                redis_status = "unhealthy"
        else:
            redis_status = "standalone"

        # 确定整体状态
        overall_status = "healthy"
        if db_status == "unhealthy":
            overall_status = "degraded"
        if db_status == "unhealthy" and redis_status == "unhealthy":
            overall_status = "unhealthy"

        from datetime import datetime, timezone

        return HealthResponse(
            status=overall_status,
            service=config.SERVICE_NAME,
            version="1.0.0",
            database=db_status,
            redis=redis_status,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    # ==================== 根路由 ====================

    @app.get("/", tags=["Root"])
    async def root() -> dict[str, str]:
        """服务根路径"""
        return {
            "service": f"HigherMatch™ {config.SERVICE_NAME.title()}",
            "version": "1.0.0",
            "status": "operational",
            "docs": "/docs",
            "health": "/health",
        }

    # ==================== 就绪检查路由 ====================

    @app.get("/ready", tags=["Health"])
    async def readiness_check() -> dict[str, str]:
        """
        就绪检查端点 (Kubernetes readiness probe)

        仅在所有依赖服务就绪时返回 200
        """
        if SHARED_AVAILABLE:
            db_ready = await check_db_health()
            redis_ready = await redis_health_check()

            if not db_ready:
                return JSONResponse(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    content={"status": "not ready", "reason": "database unavailable"}
                )

            if not redis_ready:
                return JSONResponse(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    content={"status": "not ready", "reason": "redis unavailable"}
                )

        return {"status": "ready"}

    # ==================== 存活检查路由 ====================

    @app.get("/live", tags=["Health"])
    async def liveness_check() -> dict[str, str]:
        """
        存活检查端点 (Kubernetes liveness probe)

        简单检查服务是否运行
        """
        return {"status": "alive"}

    logger.info(f"{config.SERVICE_NAME} application created successfully")

    return app


# ==================== 全局应用实例 ====================
# 注意: 仅用于本地开发，生产环境应使用 create_app() 函数
app = create_app()


# ==================== 主程序入口 ====================
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=config.SERVICE_PORT,
        reload=config.DEBUG,
        log_level="info",
    )
