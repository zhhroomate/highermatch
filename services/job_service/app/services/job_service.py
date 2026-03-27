"""
HigherMatch™ Job Service - Job Service
======================================

岗位管理业务逻辑层。

提供:
- 岗位 CRUD 操作
- Cursor 分页查询
- Kafka 消息发送
- 权限验证

版本: 1.0.0
"""

import base64
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import select, and_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.models import Job, Employer, JobStatus
from app.schemas.job import (
    JobCreateRequest,
    JobUpdateRequest,
    JobRequirement,
    JobRequirementResponse,
    JobResponse,
    JobCreateResponse,
    JobPublishResponse,
    JobListResponse,
    JobStatus as JobStatusEnum,
)

# ==================== 日志配置 ====================
logger = logging.getLogger(__name__)


# ==================== Kafka 客户端 ====================


class KafkaProducer:
    """
    Kafka 生产者 (异步)

    用于发送岗位相关的 Kafka 消息。
    """

    def __init__(self, bootstrap_servers: str) -> None:
        """
        初始化 Kafka 生产者

        Args:
            bootstrap_servers: Kafka 服务器地址
        """
        self.bootstrap_servers = bootstrap_servers
        self._producer = None

    async def start(self) -> None:
        """启动生产者"""
        try:
            from aiokafka import AIOKafkaProducer
            self._producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
            )
            await self._producer.start()
            logger.info(f"Kafka producer started: {self.bootstrap_servers}")
        except ImportError:
            logger.warning("aiokafka not installed, using mock producer")
            self._producer = None

    async def stop(self) -> None:
        """停止生产者"""
        if self._producer:
            await self._producer.stop()
            logger.info("Kafka producer stopped")

    async def send(self, topic: str, message: dict) -> bool:
        """
        发送消息

        Args:
            topic: Kafka Topic
            message: 消息内容

        Returns:
            True: 发送成功
            False: 发送失败
        """
        if self._producer is None:
            logger.warning(f"Kafka not configured, message to {topic} not sent: {message}")
            return False

        try:
            await self._producer.send_and_wait(topic, message)
            logger.info(f"Message sent to {topic}: {message.get('job_id')}")
            return True
        except Exception as e:
            logger.error(f"Failed to send message to {topic}: {e}")
            return False


# 全局 Kafka 生产者
_kafka_producer: Optional[KafkaProducer] = None


async def init_kafka(bootstrap_servers: str) -> KafkaProducer:
    """初始化 Kafka 生产者"""
    global _kafka_producer
    _kafka_producer = KafkaProducer(bootstrap_servers)
    await _kafka_producer.start()
    return _kafka_producer


async def get_kafka() -> Optional[KafkaProducer]:
    """获取 Kafka 生产者"""
    return _kafka_producer


async def close_kafka() -> None:
    """关闭 Kafka 生产者"""
    global _kafka_producer
    if _kafka_producer:
        await _kafka_producer.stop()
        _kafka_producer = None


# ==================== 岗位仓储 ====================


class JobRepository:
    """
    岗位仓储

    处理岗位的数据库查询和操作。
    """

    def __init__(self, db: AsyncSession) -> None:
        """
        初始化仓储

        Args:
            db: 数据库会话
        """
        self.db = db

    async def get_by_id(self, job_id: uuid.UUID) -> Optional[Job]:
        """
        根据 ID 获取岗位

        Args:
            job_id: 岗位 ID

        Returns:
            Job 对象或 None
        """
        stmt = (
            select(Job)
            .options(selectinload(Job.employer))
            .where(
                and_(
                    Job.id == job_id,
                    Job.is_deleted == False
                )
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_with_employer(self, job_id: uuid.UUID) -> Optional[Job]:
        """
        根据 ID 获取岗位 (包含雇主信息)

        Args:
            job_id: 岗位 ID

        Returns:
            Job 对象或 None
        """
        stmt = (
            select(Job)
            .options(selectinload(Job.employer))
            .where(
                and_(
                    Job.id == job_id,
                    Job.is_deleted == False
                )
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, employer_id: uuid.UUID, data: JobCreateRequest) -> Job:
        """
        创建岗位

        Args:
            employer_id: 雇主 ID
            data: 创建请求数据

        Returns:
            创建的 Job 对象
        """
        job = Job(
            employer_id=employer_id,
            job_title=data.job_title,
            requirement=data.requirement.model_dump(),
            jd_html=data.jd_html,
            status=JobStatus.DRAFT,
            is_urgent=data.is_urgent,
            employment_type=data.employment_type.value if data.employment_type else None,
            work_location_type=data.work_location_type.value if data.work_location_type else None,
            work_province=data.work_province,
            work_city=data.work_city,
            work_district=data.work_district,
            work_address_detail=data.work_address_detail,
            salary_min=data.requirement.salary_min,
            salary_max=data.requirement.salary_max,
            salary_negotiable=data.salary_negotiable,
            commission_rate=data.commission_rate or 0.10,
            max_applications=data.max_applications,
            view_count=0,
            apply_count=0,
            current_applications=0,
        )

        if data.is_urgent:
            job.urgent_expires_at = datetime.now(timezone.utc) + timedelta(days=7)

        self.db.add(job)
        await self.db.flush()
        await self.db.refresh(job)

        logger.info(f"Job created: {job.id} by employer {employer_id}")
        return job

    async def update(self, job: Job, data: JobUpdateRequest) -> Job:
        """
        更新岗位

        Args:
            job: Job 对象
            data: 更新请求数据

        Returns:
            更新后的 Job 对象
        """
        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            if field == "requirement":
                setattr(job, field, value.model_dump() if isinstance(value, JobRequirement) else value)
            elif field in ("employment_type", "work_location_type") and value is not None:
                setattr(job, field, value.value if hasattr(value, "value") else value)
            else:
                setattr(job, field, value)

        job.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(job)

        logger.info(f"Job updated: {job.id}")
        return job

    async def publish(self, job: Job, expires_at: Optional[datetime] = None) -> Job:
        """
        发布岗位

        Args:
            job: Job 对象
            expires_at: 过期时间 (可选)

        Returns:
            发布后的 Job 对象
        """
        job.status = JobStatus.PUBLISHED
        job.published_at = datetime.now(timezone.utc)
        job.updated_at = datetime.now(timezone.utc)

        if expires_at:
            job.expires_at = expires_at
        else:
            # 默认 30 天过期
            job.expires_at = datetime.now(timezone.utc) + timedelta(days=30)

        await self.db.flush()
        await self.db.refresh(job)

        logger.info(f"Job published: {job.id}")
        return job

    async def list_by_employer(
        self,
        employer_id: uuid.UUID,
        status: Optional[str] = None,
        cursor: Optional[str] = None,
        limit: int = 20,
    ) -> tuple[list[Job], Optional[str]]:
        """
        获取雇主的岗位列表 (Cursor 分页)

        Args:
            employer_id: 雇主 ID
            status: 按状态筛选 (可选)
            cursor: 分页游标 (可选)
            limit: 每页数量

        Returns:
            (岗位列表, 下一页游标)
        """
        conditions = [
            Job.employer_id == employer_id,
            Job.is_deleted == False,
        ]

        if status:
            conditions.append(Job.status == status)

        if cursor:
            try:
                decoded_cursor = base64.b64decode(cursor).decode("utf-8")
                cursor_id = uuid.UUID(decoded_cursor)
                conditions.append(Job.created_at < (
                    select(Job.created_at).where(Job.id == cursor_id).scalar_subquery()
                ))
            except Exception as e:
                logger.warning(f"Invalid cursor: {cursor}, error: {e}")

        stmt = (
            select(Job)
            .options(selectinload(Job.employer))
            .where(and_(*conditions))
            .order_by(desc(Job.created_at), desc(Job.id))
            .limit(limit + 1)  # 多查一条用于判断是否有下一页
        )

        result = await self.db.execute(stmt)
        jobs = list(result.scalars().all())

        next_cursor = None
        if len(jobs) > limit:
            jobs = jobs[:limit]
            last_job = jobs[-1]
            next_cursor = base64.b64encode(str(last_job.id).encode("utf-8")).decode("utf-8")

        return jobs, next_cursor

    async def list_active(
        self,
        cursor: Optional[str] = None,
        limit: int = 20,
    ) -> tuple[list[Job], Optional[str]]:
        """
        获取已发布的岗位列表 (公开列表)

        Args:
            cursor: 分页游标 (可选)
            limit: 每页数量

        Returns:
            (岗位列表, 下一页游标)
        """
        conditions = [
            Job.status == JobStatus.PUBLISHED,
            Job.is_deleted == False,
        ]

        if cursor:
            try:
                decoded_cursor = base64.b64decode(cursor).decode("utf-8")
                cursor_id = uuid.UUID(decoded_cursor)
                conditions.append(Job.published_at < (
                    select(Job.published_at).where(Job.id == cursor_id).scalar_subquery()
                ))
            except Exception as e:
                logger.warning(f"Invalid cursor: {cursor}, error: {e}")

        stmt = (
            select(Job)
            .options(selectinload(Job.employer))
            .where(and_(*conditions))
            .order_by(desc(Job.published_at), desc(Job.id))
            .limit(limit + 1)
        )

        result = await self.db.execute(stmt)
        jobs = list(result.scalars().all())

        next_cursor = None
        if len(jobs) > limit:
            jobs = jobs[:limit]
            last_job = jobs[-1]
            next_cursor = base64.b64encode(str(last_job.id).encode("utf-8")).decode("utf-8")

        return jobs, next_cursor

    async def count_by_employer(self, employer_id: uuid.UUID) -> int:
        """统计雇主的岗位数量"""
        stmt = select(Job).where(
            and_(
                Job.employer_id == employer_id,
                Job.is_deleted == False
            )
        )
        result = await self.db.execute(stmt)
        return len(result.scalars().all())


# ==================== 岗位服务 ====================


class JobService:
    """
    岗位服务

    处理岗位的业务逻辑，包括 CRUD、Kafka 消息发送等。
    """

    def __init__(self, db: AsyncSession) -> None:
        """
        初始化服务

        Args:
            db: 数据库会话
        """
        self.db = db
        self.repository = JobRepository(db)

    def _job_to_response(self, job: Job) -> JobResponse:
        """将 Job 模型转换为响应模型"""
        requirement_data = job.requirement or {}
        requirement = JobRequirementResponse(
            skills=requirement_data.get("skills", []),
            years_exp_min=requirement_data.get("years_exp_min"),
            years_exp_max=requirement_data.get("years_exp_max"),
            location=requirement_data.get("location", []),
            salary_min=requirement_data.get("salary_min"),
            salary_max=requirement_data.get("salary_max"),
            industry=requirement_data.get("industry"),
            education=requirement_data.get("education"),
            language=requirement_data.get("language"),
        )

        return JobResponse(
            job_id=str(job.id),
            employer_id=str(job.employer_id),
            job_title=job.job_title,
            job_category=job.job_category,
            job_tags=job.job_tags or [],
            requirement=requirement,
            jd_html=job.jd_html,
            status=JobStatus(job.status),
            employment_type=job.employment_type,
            work_location_type=job.work_location_type,
            work_province=job.work_province,
            work_city=job.work_city,
            work_district=job.work_district,
            work_address_detail=job.work_address_detail,
            salary_min=job.salary_min,
            salary_max=job.salary_max,
            salary_negotiable=job.salary_negotiable,
            is_urgent=job.is_urgent,
            urgent_expires_at=job.urgent_expires_at,
            commission_rate=job.commission_rate,
            max_applications=job.max_applications,
            current_applications=job.current_applications,
            view_count=job.view_count,
            apply_count=job.apply_count,
            published_at=job.published_at,
            expires_at=job.expires_at,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )

    async def create_job(
        self,
        employer_id: str,
        data: JobCreateRequest,
    ) -> JobCreateResponse:
        """
        创建岗位

        Args:
            employer_id: 雇主 ID
            data: 创建请求

        Returns:
            创建响应

        Raises:
            ValueError: 雇主不存在或无权限
        """
        employer_uuid = uuid.UUID(employer_id)

        # 验证雇主存在
        stmt = select(Employer).where(Employer.id == employer_uuid)
        result = await self.db.execute(stmt)
        employer = result.scalar_one_or_none()

        if not employer:
            raise ValueError("雇主不存在")

        if not employer.is_active:
            raise ValueError("雇主账号已被禁用")

        # 创建岗位
        job = await self.repository.create(employer_uuid, data)

        # 发送 Kafka 消息
        kafka = await get_kafka()
        if kafka:
            await kafka.send("job.created", {
                "event_type": "job.created",
                "job_id": str(job.id),
                "employer_id": employer_id,
                "job_title": job.job_title,
                "status": job.status,
                "created_at": job.created_at.isoformat(),
            })

        return JobCreateResponse(
            job_id=str(job.id),
            status=JobStatusEnum.DRAFT,
            created_at=job.created_at,
        )

    async def get_job(
        self,
        job_id: str,
        employer_id: Optional[str] = None,
    ) -> JobResponse:
        """
        获取岗位详情

        Args:
            job_id: 岗位 ID
            employer_id: 雇主 ID (用于验证权限，可选)

        Returns:
            岗位详情

        Raises:
            ValueError: 岗位不存在或无权限访问
        """
        job_uuid = uuid.UUID(job_id)
        job = await self.repository.get_by_id_with_employer(job_uuid)

        if not job:
            raise ValueError("岗位不存在")

        # 如果提供了雇主 ID，验证权限
        if employer_id and str(job.employer_id) != employer_id:
            raise PermissionError("无权访问此岗位")

        # 增加浏览次数
        job.view_count += 1
        await self.db.flush()

        return self._job_to_response(job)

    async def update_job(
        self,
        job_id: str,
        employer_id: str,
        data: JobUpdateRequest,
    ) -> JobResponse:
        """
        更新岗位

        仅在 status=draft 时允许修改。

        Args:
            job_id: 岗位 ID
            employer_id: 雇主 ID
            data: 更新请求

        Returns:
            更新后的岗位详情

        Raises:
            ValueError: 岗位不存在
            PermissionError: 无权限
            ValueError: 状态不允许修改
        """
        job_uuid = uuid.UUID(job_id)
        job = await self.repository.get_by_id(job_uuid)

        if not job:
            raise ValueError("岗位不存在")

        if str(job.employer_id) != employer_id:
            raise PermissionError("无权修改此岗位")

        if job.status != JobStatus.DRAFT:
            raise ValueError("只有草稿状态的岗位可以修改")

        job = await self.repository.update(job, data)
        return self._job_to_response(job)

    async def publish_job(
        self,
        job_id: str,
        employer_id: str,
        expires_at: Optional[datetime] = None,
    ) -> JobPublishResponse:
        """
        发布岗位

        Args:
            job_id: 岗位 ID
            employer_id: 雇主 ID
            expires_at: 过期时间 (可选)

        Returns:
            发布响应

        Raises:
            ValueError: 岗位不存在
            PermissionError: 无权限
            ValueError: 状态不允许发布
        """
        job_uuid = uuid.UUID(job_id)
        job = await self.repository.get_by_id(job_uuid)

        if not job:
            raise ValueError("岗位不存在")

        if str(job.employer_id) != employer_id:
            raise PermissionError("无权发布此岗位")

        if job.status != JobStatus.DRAFT:
            raise ValueError("只有草稿状态的岗位可以发布")

        job = await self.repository.publish(job, expires_at)

        # 发送 Kafka 消息
        kafka = await get_kafka()
        if kafka:
            await kafka.send("job.published", {
                "event_type": "job.published",
                "job_id": str(job.id),
                "employer_id": employer_id,
                "job_title": job.job_title,
                "status": job.status,
                "published_at": job.published_at.isoformat() if job.published_at else None,
                "expires_at": job.expires_at.isoformat() if job.expires_at else None,
            })

        return JobPublishResponse(
            job_id=str(job.id),
            status=JobStatusEnum.PUBLISHED,
            published_at=job.published_at,
        )

    async def list_jobs(
        self,
        employer_id: Optional[str] = None,
        status: Optional[str] = None,
        cursor: Optional[str] = None,
        limit: int = 20,
        public_listing: bool = False,
    ) -> JobListResponse:
        """
        获取岗位列表

        Args:
            employer_id: 雇主 ID (可选，用于筛选自己的岗位)
            status: 按状态筛选 (可选)
            cursor: 分页游标 (可选)
            limit: 每页数量
            public_listing: 是否为公开列表 (已发布岗位)

        Returns:
            岗位列表响应
        """
        if public_listing:
            jobs, next_cursor = await self.repository.list_active(cursor, limit)
        elif employer_id:
            employer_uuid = uuid.UUID(employer_id)
            jobs, next_cursor = await self.repository.list_by_employer(
                employer_uuid, status, cursor, limit
            )
        else:
            raise ValueError("必须提供 employer_id 或设置 public_listing=True")

        items = [self._job_to_response(job) for job in jobs]

        return JobListResponse(
            items=items,
            next_cursor=next_cursor,
        )


# ==================== 导出 ====================
__all__ = [
    "JobRepository",
    "JobService",
    "KafkaProducer",
    "init_kafka",
    "get_kafka",
    "close_kafka",
]
