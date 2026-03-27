"""
HigherMatch™ Matching Service - Matching Task
============================================

核心匹配引擎模块。

功能:
1. Celery Worker 处理匹配任务
2. Kafka Consumer 监听 job.published topic
3. 执行多维评分算法
4. 结果写入 PostgreSQL match_results 表
5. 发布 match.completed 消息

匹配流程:
1. 消费 job.published 消息
2. 获取岗位需求详情
3. 向量化岗位描述
4. VDB 检索 Top-200 候选人
5. 执行多维评分
6. 过滤 verification_score < 0.6
7. 取 Top-10 写入数据库
8. 发布 match.completed 消息

版本: 1.0.0
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from typing import Optional, Any
from dataclasses import dataclass, field
from celery import Celery
from sqlalchemy.ext.asyncio import AsyncSession

# ==================== 日志配置 ====================
logger = logging.getLogger(__name__)

# ==================== 配置 ====================
class MatchingConfig:
    """匹配服务配置"""

    # Celery
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/1")
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/2")

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
    KAFKA_TOPIC_JOB_PUBLISHED = "job.published"
    KAFKA_TOPIC_MATCH_COMPLETED = "match.completed"
    KAFKA_CONSUMER_GROUP = "matching-service"

    # VDB
    QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
    VDB_COLLECTION = "candidates"
    VDB_TOP_K = 200  # VDB 检索数量

    # Matching
    MATCH_TOP_K = 10  # 最终写入数量
    VERIFICATION_THRESHOLD = 0.6  # 验证分数阈值

    # Database
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://highermatch:highermatch@postgres:5432/highermatch_dev"
    )

    # Redis
    REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")


# ==================== Celery 应用 ====================
celery_app = Celery(
    "matching_service",
    broker=MatchingConfig.CELERY_BROKER_URL,
    backend=MatchingConfig.CELERY_RESULT_BACKEND,
)

# Celery 配置
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 分钟超时
    task_soft_time_limit=240,  # 4 分钟软超时
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)


# ==================== 任务结果模型 ====================
@dataclass
class MatchTaskResult:
    """匹配任务结果"""
    job_id: str
    employer_id: str
    matched_count: int
    total_candidates_scored: int
    task_id: str
    completed_at: datetime = field(default_factory=datetime.utcnow)
    errors: list = field(default_factory=list)


# ==================== 核心匹配任务 ====================
@celery_app.task(bind=True, name="matching.match_job_candidates")
def match_job_candidates(
    self,
    job_id: str,
    job_data: dict,
    employer_id: str,
) -> dict:
    """
    匹配岗位候选人 Celery 任务

    Args:
        job_id: 岗位 ID
        job_data: 岗位数据
        employer_id: 雇主 ID

    Returns:
        匹配结果字典
    """
    task_id = self.request.id
    logger.info(f"[Task {task_id}] Starting matching for job {job_id}")

    try:
        # 创建事件循环运行异步代码
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            run_matching_pipeline(job_id, job_data, employer_id, task_id)
        )
        loop.close()

        return {
            "success": True,
            "job_id": job_id,
            "matched_count": result.matched_count,
            "total_scored": result.total_candidates_scored,
            "task_id": task_id,
        }

    except Exception as e:
        logger.error(f"[Task {task_id}] Matching failed: {e}")
        return {
            "success": False,
            "job_id": job_id,
            "error": str(e),
            "task_id": task_id,
        }


# ==================== 主匹配流程 ====================
async def run_matching_pipeline(
    job_id: str,
    job_data: dict,
    employer_id: str,
    task_id: Optional[str] = None,
) -> MatchTaskResult:
    """
    执行完整的匹配流程

    流程:
    1. 准备岗位需求
    2. 向量化岗位描述
    3. VDB 检索 Top-200 候选人
    4. 执行多维评分
    5. 过滤 verification_score < 0.6
    6. 取 Top-10
    7. 生成匹配原因
    8. 写入数据库
    9. 发布 match.completed 消息

    Args:
        job_id: 岗位 ID
        job_data: 岗位数据
        employer_id: 雇主 ID
        task_id: 任务 ID

    Returns:
        MatchTaskResult
    """
    from app.services.scoring import batch_score_candidates, ScoringResult
    from app.services.reason_generator import get_reason_generator

    if task_id is None:
        task_id = str(uuid.uuid4())

    errors = []
    logger.info(f"[Task {task_id}] Starting matching pipeline for job {job_id}")

    try:
        # 1. 准备岗位需求
        logger.info(f"[Task {task_id}] Step 1: Preparing job requirements")
        job_requirement = _prepare_job_requirement(job_data)

        # 2. 向量化岗位描述
        logger.info(f"[Task {task_id}] Step 2: Vectorizing job description")
        job_vector = await _vectorize_job(job_requirement)
        if not job_vector:
            errors.append("Failed to vectorize job description")
            logger.warning(f"[Task {task_id}] Using default vector")
            job_vector = [0.0] * 1536  # 默认向量

        # 3. VDB 检索 Top-200 候选人
        logger.info(f"[Task {task_id}] Step 3: Searching VDB for candidates")
        candidates = await _search_candidates_in_vdb(
            job_vector,
            top_k=MatchingConfig.VDB_TOP_K,
        )
        logger.info(f"[Task {task_id}] Found {len(candidates)} candidates in VDB")

        if not candidates:
            errors.append("No candidates found in VDB")
            return MatchTaskResult(
                job_id=job_id,
                employer_id=employer_id,
                matched_count=0,
                total_candidates_scored=0,
                task_id=task_id,
                errors=errors,
            )

        # 4. 执行多维评分
        logger.info(f"[Task {task_id}] Step 4: Scoring candidates")
        scoring_results = batch_score_candidates(
            job_data=job_requirement,
            candidates_data=candidates,
            job_id=job_id,
        )
        total_scored = len(scoring_results)
        logger.info(f"[Task {task_id}] Scored {total_scored} candidates")

        # 5. 过滤 verification_score < 0.6
        filtered_results = [
            r for r in scoring_results
            if r.filtered_reason is None
        ]
        logger.info(
            f"[Task {task_id}] Filtered: {total_scored - len(filtered_results)} "
            f"(verification < 0.6), remaining: {len(filtered_results)}"
        )

        # 6. 取 Top-10
        top_results = filtered_results[:MatchingConfig.MATCH_TOP_K]
        logger.info(f"[Task {task_id}] Top {len(top_results)} candidates selected")

        # 7. 生成匹配原因
        logger.info(f"[Task {task_id}] Step 5: Generating match reasons")
        await _generate_match_reasons(
            job_requirement,
            candidates,
            top_results,
            task_id,
        )

        # 8. 写入数据库
        logger.info(f"[Task {task_id}] Step 6: Writing to database")
        await _write_match_results(
            job_id=job_id,
            employer_id=employer_id,
            results=top_results,
            task_id=task_id,
        )
        logger.info(f"[Task {task_id}] Wrote {len(top_results)} match results")

        # 9. 发布 match.completed 消息
        logger.info(f"[Task {task_id}] Step 7: Publishing Kafka message")
        await _publish_match_completed(
            job_id=job_id,
            employer_id=employer_id,
            match_count=len(top_results),
            top_candidates=[r.candidate_id for r in top_results],
            task_id=task_id,
        )

        return MatchTaskResult(
            job_id=job_id,
            employer_id=employer_id,
            matched_count=len(top_results),
            total_candidates_scored=total_scored,
            task_id=task_id,
            errors=errors,
        )

    except Exception as e:
        logger.error(f"[Task {task_id}] Pipeline error: {e}", exc_info=True)
        errors.append(str(e))
        return MatchTaskResult(
            job_id=job_id,
            employer_id=employer_id,
            matched_count=0,
            total_candidates_scored=0,
            task_id=task_id,
            errors=errors,
        )


# ==================== 辅助函数 ====================

def _prepare_job_requirement(job_data: dict) -> dict:
    """准备岗位需求数据"""
    requirement = job_data.get("requirement", {})

    # 提取岗位要求
    return {
        "job_id": job_data.get("id"),
        "job_title": job_data.get("job_title", ""),
        "company_name": job_data.get("company_name", ""),
        "skills": requirement.get("skills", []),
        "core_skills": requirement.get("core_skills", requirement.get("skills", [])[:3]),
        "years_exp_min": requirement.get("years_exp_min", 0),
        "years_exp_max": requirement.get("years_exp_max", 0),
        "industries": requirement.get("industries", []),
        "salary_min": job_data.get("salary_min", 0),
        "salary_max": job_data.get("salary_max", 0),
    }


async def _vectorize_job(job_requirement: dict) -> Optional[list[float]]:
    """
    向量化岗位描述

    集成 Embedding 服务获取岗位向量。
    """
    try:
        # 尝试导入共享的 embedding 服务
        from shared.services.embedding_service import embed_text

        # 构建岗位文本
        job_text = _build_job_text(job_requirement)

        # 调用 embedding 服务
        vector = await embed_text(job_text)
        return vector

    except ImportError:
        # 如果共享服务不可用，使用本地模拟
        logger.warning("Shared embedding service not available, using mock vector")
        return await _generate_mock_vector(job_requirement)
    except Exception as e:
        logger.error(f"Vectorization failed: {e}")
        return await _generate_mock_vector(job_requirement)


async def _generate_mock_vector(job_requirement: dict) -> list[float]:
    """生成模拟向量用于测试"""
    import random

    # 基于技能生成伪随机种子
    skills_str = "".join(job_requirement.get("skills", []))
    seed = hash(skills_str) % (2**32)

    random.seed(seed)
    vector = [random.random() for _ in range(1536)]

    # 归一化
    magnitude = sum(v * v for v in vector) ** 0.5
    if magnitude > 0:
        vector = [v / magnitude for v in vector]

    return vector


def _build_job_text(job_requirement: dict) -> str:
    """构建岗位文本用于向量化"""
    parts = []

    title = job_requirement.get("job_title", "")
    if title:
        parts.append(f"职位: {title}")

    company = job_requirement.get("company_name", "")
    if company:
        parts.append(f"公司: {company}")

    skills = job_requirement.get("skills", [])
    if skills:
        parts.append(f"技能要求: {', '.join(skills)}")

    core_skills = job_requirement.get("core_skills", [])
    if core_skills:
        parts.append(f"核心技能: {', '.join(core_skills)}")

    years_min = job_requirement.get("years_exp_min", 0)
    years_max = job_requirement.get("years_exp_max", 0)
    if years_min or years_max:
        parts.append(f"经验要求: {years_min}-{years_max}年")

    industries = job_requirement.get("industries", [])
    if industries:
        parts.append(f"行业: {', '.join(industries)}")

    return " | ".join(parts)


async def _search_candidates_in_vdb(
    query_vector: list[float],
    top_k: int = 200,
) -> list[dict]:
    """
    从 VDB 检索候选人

    集成 Qdrant 检索候选人向量。
    """
    try:
        # 尝试导入共享的 VDB 服务
        from shared.services.vdb_service import search_candidates, SearchFilters

        # 执行搜索
        filters = SearchFilters()
        results = await search_candidates(
            query_vector=query_vector,
            filters=filters,
            top_k=top_k,
        )

        # 转换为候选人数据格式
        candidates = []
        for result in results:
            candidate = {
                "id": result.candidate_id,
                "name": result.payload.get("name", ""),
                "skills": result.payload.get("skills", []),
                "total_years_exp": result.payload.get("total_years_exp", 0),
                "preferred_industries": result.payload.get("preferred_industries", []),
                "expected_salary_min": result.payload.get("expected_salary_min", 0),
                "expected_salary_max": result.payload.get("expected_salary_max", 0),
                "work_history": result.payload.get("work_history", []),
                "verification_score": result.payload.get("verification_score", 1.0),
                "vdb_score": result.score,
            }
            candidates.append(candidate)

        return candidates

    except ImportError:
        # 如果共享服务不可用，返回空列表
        logger.warning("Shared VDB service not available")
        return []
    except Exception as e:
        logger.error(f"VDB search failed: {e}")
        return []


async def _generate_match_reasons(
    job_requirement: dict,
    candidates: list[dict],
    scoring_results: list,
    task_id: str,
) -> None:
    """
    为 Top-K 候选人生成匹配原因

    Args:
        job_requirement: 岗位需求
        candidates: 候选人原始数据
        scoring_results: 评分结果
        task_id: 任务 ID
    """
    try:
        from app.services.reason_generator import get_reason_generator

        # 构建候选人 ID 到数据的映射
        candidate_map = {c.get("id"): c for c in candidates}

        # 获取原因生成器
        reason_generator = get_reason_generator()

        for result in scoring_results[:5]:  # 只为前 5 个生成详细原因
            candidate = candidate_map.get(result.candidate_id, {})
            if not candidate:
                continue

            # 构建评分数据
            scores_data = {
                "skill_score": result.skill_score.score,
                "experience_score": result.experience_score.score,
                "culture_score": result.culture_score.score,
                "salary_score": result.salary_score.score,
                "trajectory_score": result.trajectory_score.score,
                "overall_score": result.overall_score,
                "skill_matched": result.skill_score.matched_items,
                "skill_unmatched": result.skill_score.unmatched_items,
            }

            # 生成原因 (简化处理，避免过多 API 调用)
            simple_reason = reason_generator.generate_simple_reason(
                job_requirement, candidate, scores_data
            )

            # 更新结果中的匹配原因
            result.match_reasons = [simple_reason] if simple_reason else result.match_reasons

        # 关闭生成器
        await reason_generator.close()

    except Exception as e:
        logger.warning(f"[Task {task_id}] Reason generation failed: {e}")
        # 不影响主流程，使用默认原因


async def _write_match_results(
    job_id: str,
    employer_id: str,
    results: list,
    task_id: str,
) -> None:
    """
    写入匹配结果到数据库

    Args:
        job_id: 岗位 ID
        employer_id: 雇主 ID
        results: 评分结果列表
        task_id: 任务 ID
    """
    try:
        from sqlalchemy import create_engine, text
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.ext.asyncio import async_sessionmaker

        # 创建异步引擎
        engine = create_async_engine(MatchingConfig.DATABASE_URL, echo=False)

        # 异步会话工厂
        async_session = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )

        async with async_session() as session:
            # 构建批量插入数据
            match_records = []
            now = datetime.utcnow()

            for i, result in enumerate(results):
                # 构建 match_reasons JSON
                match_reasons_json = {
                    "overall": result.match_reasons if isinstance(result.match_reasons, list) else [],
                    "skill_details": result.skill_score.details if result.skill_score else "",
                    "experience_details": result.experience_score.details if result.experience_score else "",
                }

                # 构建维度分数 JSON
                dimension_scores = {
                    "skill": result.skill_score.score if result.skill_score else 0,
                    "experience": result.experience_score.score if result.experience_score else 0,
                    "culture": result.culture_score.score if result.culture_score else 0,
                    "salary": result.salary_score.score if result.salary_score else 0,
                    "trajectory": result.trajectory_score.score if result.trajectory_score else 0,
                }

                record = {
                    "id": str(uuid.uuid4()),
                    "job_id": job_id,
                    "candidate_id": result.candidate_id,
                    "employer_id": employer_id,
                    "overall_score": result.overall_score,
                    "dimension_scores": dimension_scores,
                    "match_reasons": match_reasons_json,
                    "pipeline_stage": "ai_recommended",  # AI 推荐阶段
                    "match_status": "pending",
                    "task_id": task_id,
                    "rank": i + 1,
                    "created_at": now,
                    "updated_at": now,
                }
                match_records.append(record)

            # 批量插入
            if match_records:
                await _batch_insert_match_results(session, match_records)
                await session.commit()

        # 关闭引擎
        await engine.dispose()

        logger.info(
            f"[Task {task_id}] Wrote {len(match_records)} match results to database"
        )

    except Exception as e:
        logger.error(f"[Task {task_id}] Database write failed: {e}", exc_info=True)
        raise


async def _batch_insert_match_results(session: AsyncSession, records: list[dict]) -> None:
    """
    批量插入匹配结果

    Args:
        session: 数据库会话
        records: 记录列表
    """
    from sqlalchemy import text

    # 使用 executemany 批量插入
    insert_sql = text("""
        INSERT INTO match_results (
            id, job_id, candidate_id, employer_id, overall_score,
            dimension_scores, match_reasons, pipeline_stage, match_status,
            task_id, rank, created_at, updated_at
        ) VALUES (
            :id, :job_id, :candidate_id, :employer_id, :overall_score,
            :dimension_scores, :match_reasons, :pipeline_stage, :match_status,
            :task_id, :rank, :created_at, :updated_at
        )
        ON CONFLICT (job_id, candidate_id) DO UPDATE SET
            overall_score = EXCLUDED.overall_score,
            dimension_scores = EXCLUDED.dimension_scores,
            match_reasons = EXCLUDED.match_reasons,
            pipeline_stage = EXCLUDED.pipeline_stage,
            rank = EXCLUDED.rank,
            updated_at = EXCLUDED.updated_at
    """)

    for record in records:
        # 转换 JSON 字段
        record["dimension_scores"] = json.dumps(record["dimension_scores"])
        record["match_reasons"] = json.dumps(record["match_reasons"])

        await session.execute(insert_sql, record)


async def _publish_match_completed(
    job_id: str,
    employer_id: str,
    match_count: int,
    top_candidates: list[str],
    task_id: str,
) -> None:
    """
    发布 match.completed 消息到 Kafka

    Args:
        job_id: 岗位 ID
        employer_id: 雇主 ID
        match_count: 匹配数量
        top_candidates: Top 候选人 ID 列表
        task_id: 任务 ID
    """
    try:
        from aiokafka import AIOKafkaProducer

        # 创建生产者
        producer = AIOKafkaProducer(
            bootstrap_servers=MatchingConfig.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
        )

        await producer.start()

        try:
            # 构建消息
            message = {
                "event_type": "match.completed",
                "job_id": job_id,
                "employer_id": employer_id,
                "match_count": match_count,
                "top_candidates": top_candidates,
                "task_id": task_id,
                "timestamp": datetime.utcnow().isoformat(),
            }

            # 发送消息
            await producer.send_and_wait(
                MatchingConfig.KAFKA_TOPIC_MATCH_COMPLETED,
                value=message,
                key=job_id.encode("utf-8"),
            )

            logger.info(
                f"[Task {task_id}] Published match.completed: "
                f"job_id={job_id}, match_count={match_count}"
            )

        finally:
            await producer.stop()

    except ImportError:
        logger.warning("aiokafka not available, skipping Kafka publish")
    except Exception as e:
        logger.error(f"[Task {task_id}] Kafka publish failed: {e}")
        # 不抛出异常，任务已完成


# ==================== Kafka Consumer ====================
class MatchingKafkaConsumer:
    """
    Kafka 消费者

    监听 job.published topic，触发匹配任务。
    """

    def __init__(self):
        self.config = MatchingConfig()
        self._consumer = None
        self._producer = None
        self._running = False

    async def start(self) -> None:
        """启动消费者"""
        from aiokafka import AIOKafkaConsumer

        logger.info(
            f"Starting Kafka consumer: topic={self.config.KAFKA_TOPIC_JOB_PUBLISHED}, "
            f"group={self.config.KAFKA_CONSUMER_GROUP}"
        )

        # 创建消费者
        self._consumer = AIOKafkaConsumer(
            self.config.KAFKA_TOPIC_JOB_PUBLISHED,
            bootstrap_servers=self.config.KAFKA_BOOTSTRAP_SERVERS,
            group_id=self.config.KAFKA_CONSUMER_GROUP,
            auto_offset_reset="earliest",
            enable_auto_commit=True,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        )

        await self._consumer.start()
        self._running = True
        logger.info("Kafka consumer started")

    async def stop(self) -> None:
        """停止消费者"""
        self._running = False

        if self._consumer:
            await self._consumer.stop()
            self._consumer = None

        logger.info("Kafka consumer stopped")

    async def run(self) -> None:
        """运行消费者循环"""
        from aiokafka.errors import KafkaError

        logger.info("Starting Kafka consumer loop")

        while self._running:
            try:
                # 拉取消息
                async for message in self._consumer:
                    if not self._running:
                        break

                    try:
                        await self.process_message(message.value)
                    except Exception as e:
                        logger.error(f"Message processing failed: {e}")

            except KafkaError as e:
                logger.error(f"Kafka error: {e}")
                if self._running:
                    # 等待后重连
                    await asyncio.sleep(5)

            except Exception as e:
                logger.error(f"Consumer loop error: {e}")
                if self._running:
                    await asyncio.sleep(5)

        logger.info("Kafka consumer loop ended")

    async def process_message(self, message: dict) -> None:
        """
        处理 job.published 消息

        Args:
            message: Kafka 消息，包含:
                - job_id: 岗位 ID
                - job_data: 岗位完整数据
                - employer_id: 雇主 ID
                - timestamp: 发布时间戳
        """
        job_id = message.get("job_id")
        job_data = message.get("job_data", {})
        employer_id = message.get("employer_id", "")

        if not job_id:
            logger.error("Received message without job_id")
            return

        logger.info(f"Received job.published: job_id={job_id}")

        # 触发 Celery 任务
        task = match_job_candidates.apply_async(
            args=[job_id, job_data, employer_id],
            task_id=f"match-{job_id}-{int(datetime.utcnow().timestamp())}",
        )

        logger.info(f"Triggered matching task: task_id={task.id}")


# ==================== Celery Beat (定时任务) ====================
@celery_app.task(name="matching.retry_failed_tasks")
def retry_failed_tasks():
    """重试失败的匹配任务"""
    # TODO: 实现失败任务重试逻辑
    pass


@celery_app.task(name="matching.cleanup_old_results")
def cleanup_old_results(days: int = 30):
    """清理旧的匹配结果"""
    # TODO: 实现清理逻辑
    pass


# ==================== 健康检查 ====================
@celery_app.task(name="matching.health_check")
def health_check():
    """Celery 健康检查任务"""
    return {
        "status": "healthy",
        "service": "matching_service",
        "timestamp": datetime.utcnow().isoformat(),
    }


# ==================== 导出 ====================
__all__ = [
    "celery_app",
    "match_job_candidates",
    "MatchingConfig",
    "MatchingKafkaConsumer",
    "MatchTaskResult",
    "run_matching_pipeline",
]
