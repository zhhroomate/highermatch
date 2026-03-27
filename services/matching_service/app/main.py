"""
HigherMatch™ Matching Service - Main Entry Point
================================================

Matching Service 主入口。

功能:
1. FastAPI 应用初始化
2. Kafka Consumer 生命周期管理
3. 健康检查端点
4. Celery Worker 集成

启动方式:
1. Celery Worker: celery -A app.tasks.matching_task worker --loglevel=info
2. Kafka Consumer: python -m app.main
3. API Server (可选): uvicorn app.main:app --host 0.0.0.0 --port 8001

版本: 1.0.0
"""

import asyncio
import logging
import os
import signal
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ==================== 日志配置 ====================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ==================== 导入 ====================
from app.tasks.matching_task import (
    celery_app,
    MatchingConfig,
    MatchingKafkaConsumer,
    match_job_candidates,
)


# ==================== 生命周期管理 ====================
# 全局 Kafka 消费者实例
_kafka_consumer: MatchingKafkaConsumer = None
_consumer_task: asyncio.Task = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    FastAPI 生命周期管理

    启动时:
    - 初始化 Kafka 消费者
    - 启动消费者循环

    关闭时:
    - 停止 Kafka 消费者
    - 等待任务完成
    """
    global _kafka_consumer, _consumer_task

    logger.info("Starting Matching Service...")

    # 启动 Kafka 消费者
    _kafka_consumer = MatchingKafkaConsumer()
    await _kafka_consumer.start()

    # 启动消费者循环
    _consumer_task = asyncio.create_task(_kafka_consumer.run())
    logger.info("Kafka consumer loop started")

    yield

    # 关闭
    logger.info("Shutting down Matching Service...")

    # 停止消费者
    if _kafka_consumer:
        await _kafka_consumer.stop()

    # 取消消费者任务
    if _consumer_task and not _consumer_task.done():
        _consumer_task.cancel()
        try:
            await _consumer_task
        except asyncio.CancelledError:
            pass

    logger.info("Matching Service shutdown complete")


# ==================== FastAPI 应用 ====================
app = FastAPI(
    title="HigherMatch™ Matching Service",
    description="AI 匹配引擎服务 - 核心岗位候选人匹配功能",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== Schema 定义 ====================
class HealthCheckResponse(BaseModel):
    """健康检查响应"""
    status: str = Field(description="服务状态")
    service: str = Field(description="服务名称")
    version: str = Field(description="服务版本")
    timestamp: str = Field(description="检查时间")
    kafka_connected: bool = Field(description="Kafka 连接状态")
    celery_workers: int = Field(description="Celery Worker 数量")


class TriggerMatchingRequest(BaseModel):
    """触发匹配请求"""
    job_id: str = Field(description="岗位 ID")
    job_data: dict = Field(description="岗位数据")
    employer_id: str = Field(description="雇主 ID")


class TriggerMatchingResponse(BaseModel):
    """触发匹配响应"""
    success: bool = Field(description="是否成功")
    task_id: str = Field(description="Celery 任务 ID")
    job_id: str = Field(description="岗位 ID")
    message: str = Field(description="响应消息")


class TaskStatusRequest(BaseModel):
    """查询任务状态请求"""
    task_id: str = Field(description="Celery 任务 ID")


class TaskStatusResponse(BaseModel):
    """查询任务状态响应"""
    task_id: str = Field(description="任务 ID")
    status: str = Field(description="任务状态")
    result: dict = Field(default=None, description="任务结果")
    info: str = Field(default=None, description="任务信息")


# ==================== API 路由 ====================
@app.get("/", tags=["Root"])
async def root():
    """根路径"""
    return {
        "service": "HigherMatch™ Matching Service",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health", response_model=HealthCheckResponse, tags=["Health"])
async def health_check():
    """
    健康检查端点

    检查:
    - 服务状态
    - Kafka 连接状态
    - Celery Worker 可用性
    """
    # 检查 Kafka 连接
    kafka_connected = False
    if _kafka_consumer and _kafka_consumer._consumer:
        try:
            # 尝试获取 consumer 的状态
            kafka_connected = _kafka_consumer._running
        except Exception:
            kafka_connected = False

    # 检查 Celery Workers
    celery_workers = 0
    try:
        inspect = celery_app.control.inspect()
        stats = inspect.stats()
        if stats:
            celery_workers = len(stats)
    except Exception:
        pass

    return HealthCheckResponse(
        status="healthy",
        service="matching_service",
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat(),
        kafka_connected=kafka_connected,
        celery_workers=celery_workers,
    )


@app.post(
    "/matching/trigger",
    response_model=TriggerMatchingResponse,
    tags=["Matching"],
)
async def trigger_matching(request: TriggerMatchingRequest):
    """
    手动触发匹配任务

    Args:
        request: 包含 job_id, job_data, employer_id

    Returns:
        任务 ID 和状态
    """
    try:
        # 生成任务 ID
        task_id = f"match-{request.job_id}-{int(datetime.utcnow().timestamp())}"

        # 触发 Celery 任务
        task = match_job_candidates.apply_async(
            args=[request.job_id, request.job_data, request.employer_id],
            task_id=task_id,
        )

        logger.info(f"Triggered matching task: job_id={request.job_id}, task_id={task.id}")

        return TriggerMatchingResponse(
            success=True,
            task_id=task.id,
            job_id=request.job_id,
            message="匹配任务已提交",
        )

    except Exception as e:
        logger.error(f"Failed to trigger matching: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"触发匹配失败: {str(e)}",
        )


@app.get(
    "/matching/status/{task_id}",
    response_model=TaskStatusResponse,
    tags=["Matching"],
)
async def get_task_status(task_id: str):
    """
    查询匹配任务状态

    Args:
        task_id: Celery 任务 ID

    Returns:
        任务状态和结果
    """
    from celery.result import AsyncResult

    # 获取任务结果
    task_result = AsyncResult(task_id, app=celery_app)

    response = TaskStatusResponse(
        task_id=task_id,
        status=task_result.status,
    )

    if task_result.ready():
        try:
            response.result = task_result.get(timeout=1)
            response.info = "任务已完成"
        except Exception as e:
            response.info = f"获取结果失败: {str(e)}"
    elif task_result.failed():
        response.info = "任务失败"
    elif task_result.started():
        response.info = "任务执行中"
    else:
        response.info = "任务等待中"

    return response


@app.get(
    "/matching/results/{job_id}",
    tags=["Matching"],
)
async def get_matching_results(job_id: str, limit: int = 10):
    """
    获取岗位的匹配结果

    Args:
        job_id: 岗位 ID
        limit: 返回数量限制

    Returns:
        匹配结果列表
    """
    # TODO: 从数据库查询匹配结果
    # 暂时返回模拟数据
    return {
        "job_id": job_id,
        "total_matches": 0,
        "results": [],
        "message": "请使用数据库查询获取实际结果",
    }


@app.post(
    "/matching/retry/{task_id}",
    tags=["Matching"],
)
async def retry_task(task_id: str):
    """
    重试失败的任务

    Args:
        task_id: 任务 ID

    Returns:
        新任务 ID
    """
    from celery.result import AsyncResult

    task_result = AsyncResult(task_id, app=celery_app)

    if task_result.status == "FAILURE":
        # 重新调用任务
        args = task_result.info.get("args", []) if isinstance(task_result.info, dict) else []
        kwargs = task_result.info.get("kwargs", {}) if isinstance(task_result.info, dict) else {}

        new_task = match_job_candidates.apply_async(
            args=args,
            kwargs=kwargs,
        )

        return {
            "success": True,
            "old_task_id": task_id,
            "new_task_id": new_task.id,
            "message": "任务已重新提交",
        }
    else:
        return {
            "success": False,
            "task_id": task_id,
            "status": task_result.status,
            "message": "只能重试失败的任务",
        }


# ==================== 信号处理 ====================
def signal_handler(signum, frame):
    """处理系统信号"""
    logger.info(f"Received signal {signum}, shutting down...")
    sys.exit(0)


# 注册信号处理器
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


# ==================== 主入口 ====================
def main():
    """主入口函数"""
    # 检查运行模式
    mode = os.getenv("RUN_MODE", "api")

    if mode == "celery":
        # 运行 Celery Worker
        logger.info("Starting Celery Worker...")
        celery_app.worker_main([
            "worker",
            "--loglevel=INFO",
            "--concurrency=4",
            "--prefetch-multiplier=1",
        ])
    elif mode == "consumer":
        # 仅运行 Kafka Consumer
        logger.info("Starting Kafka Consumer only...")
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8001,
            log_level="info",
            lifespan="on",
        )
    else:
        # 运行完整 API 服务
        logger.info("Starting Matching Service API...")
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8001,
            log_level="info",
            lifespan="on",
        )


if __name__ == "__main__":
    main()
