"""
HigherMatch™ Shared Models
==========================

SQLAlchemy 2.0 ORM 模型定义。
基于 Declarative Base，与 shared.core.db.Base 配合使用。

包含 6 张核心业务表:
1. Employer - 雇主/企业
2. Candidate - 候选人
3. Job - 职位
4. MatchResult - 匹配结果
5. Invoice - 账单
6. Guarantee - 担保

版本: 1.0.0

使用示例:
    from shared.models import Employer, Candidate, Job, MatchResult

    # 查询雇主
    result = await db.execute(select(Employer).where(Employer.id == employer_id))

    # 查询职位及雇主信息
    result = await db.execute(
        select(Job).where(Job.employer_id == employer_id)
    )

    # 查询匹配结果及关联数据
    result = await db.execute(
        select(MatchResult)
        .options(
            selectinload(MatchResult.job),
            selectinload(MatchResult.candidate)
        )
        .where(MatchResult.pipeline_stage == 'ai_recommended')
    )
"""

import uuid
from datetime import datetime, date
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)
from sqlalchemy.sql import func

from shared.core.db import Base

# ==================== 枚举类型定义 ====================

# KYC 状态枚举
class KYCStatus:
    """KYC 认证状态枚举"""
    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"


# 职位状态枚举
class JobStatus:
    """职位发布状态枚举"""
    DRAFT = "draft"
    PUBLISHED = "published"
    CLOSED = "closed"
    ARCHIVED = "archived"


# 求职状态枚举
class JobSearchStatus:
    """候选人求职状态枚举"""
    NOT_LOOKING = "not_looking"
    PASSIVE = "passive"
    ACTIVE = "active"
    URGENT = "urgent"


# 匹配管道阶段枚举
class PipelineStage:
    """匹配管道阶段枚举"""
    AI_RECOMMENDED = "ai_recommended"
    EMPLOYER_REVIEWED = "employer_reviewed"
    INTERVIEW_SCHEDULED = "interview_scheduled"
    INTERVIEW_COMPLETED = "interview_completed"
    OFFER_SENT = "offer_sent"
    OFFER_ACCEPTED = "offer_accepted"
    ONBOARDED = "onboarded"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


# 发票状态枚举
class InvoiceStatus:
    """账单状态枚举"""
    PENDING = "pending"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


# 担保状态枚举
class GuaranteeStatus:
    """担保状态枚举"""
    ACTIVE = "active"
    EXPIRED = "expired"
    CLAIMED = "claimed"
    REJECTED = "rejected"


# 支付方式枚举
class PaymentMethod:
    """支付方式枚举"""
    BANK_TRANSFER = "bank_transfer"
    CREDIT_CARD = "credit_card"
    ALIPAY = "alipay"
    WECHAT_PAY = "wechat_pay"
    CORPORATE_ACCOUNT = "corporate_account"


# 职位类型枚举
class EmploymentType:
    """职位类型枚举"""
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERNSHIP = "internship"


# 工作地点类型枚举
class WorkLocationType:
    """工作地点类型枚举"""
    ONSITE = "onsite"
    REMOTE = "remote"
    HYBRID = "hybrid"


# ==================== Base Model Mixin ====================


class TimestampMixin:
    """时间戳混入类"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="更新时间"
    )


class UUIDPrimaryKey:
    """UUID 主键混入类"""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        comment="主键 UUID"
    )


class SoftDeleteMixin:
    """软删除混入类"""

    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="是否已删除"
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="删除时间"
    )


# ==================== 1. Employer Model ====================


class Employer(Base, UUIDPrimaryKey, TimestampMixin):
    """
    雇主/企业模型

    存储雇主/企业的基本信息、KYC 状态和财务信息。

    关系:
        - one-to-many: Employer -> Job
        - one-to-many: Employer -> MatchResult
        - one-to-many: Employer -> Invoice
        - one-to-many: Employer -> Guarantee

    使用示例:
        employer = Employer(
            company_name="HigherMatch Tech",
            industry="Technology",
            contact_name="Zhang Wei",
            contact_phone="+86-138-0000-0001"
        )
    """

    __tablename__ = "employers"

    # 企业基本信息
    company_name: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
        comment="公司名称"
    )
    industry: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="行业"
    )
    company_size: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="公司规模: 1-50, 51-200, 201-500, 501-1000, 1000+"
    )
    company_description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="公司简介"
    )
    company_website: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="公司网站"
    )
    company_logo_url: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="公司 Logo URL"
    )

    # KYC 认证状态
    kyc_status: Mapped[str] = mapped_column(
        String(20),
        default=KYCStatus.PENDING,
        nullable=False,
        comment="KYC 状态: pending, in_review, approved, rejected"
    )
    kyc_submitted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="KYC 提交时间"
    )
    kyc_verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="KYC 认证时间"
    )
    kyc_rejection_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="KYC 拒绝原因"
    )

    # 联系信息
    contact_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="联系人姓名"
    )
    contact_email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="联系人邮箱"
    )
    contact_phone: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="联系电话"
    )
    contact_title: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="联系人职位"
    )

    # 财务信息 (金额单位: 分)
    credit_balance: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
        comment="账户余额 (分)"
    )
    total_spent: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
        comment="累计消费 (分)"
    )
    pending_payment: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
        comment="待结算金额 (分)"
    )

    # 地址信息
    province: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="省份"
    )
    city: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="城市"
    )
    district: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="区县"
    )
    address_detail: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="详细地址"
    )
    business_license_url: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="营业执照 URL"
    )

    # 审核信息
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="是否已认证"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="是否启用"
    )

    # ==================== 关系定义 ====================
    jobs: Mapped[list["Job"]] = relationship(
        "Job",
        back_populates="employer",
        lazy="selectin",
        cascade="all, delete-orphan"
    )
    match_results: Mapped[list["MatchResult"]] = relationship(
        "MatchResult",
        back_populates="employer",
        lazy="selectin",
        cascade="all, delete-orphan"
    )
    invoices: Mapped[list["Invoice"]] = relationship(
        "Invoice",
        back_populates="employer",
        lazy="selectin",
        cascade="all, delete-orphan"
    )
    guarantees: Mapped[list["Guarantee"]] = relationship(
        "Guarantee",
        back_populates="employer",
        lazy="selectin",
        cascade="all, delete-orphan"
    )

    # ==================== 约束和索引 ====================
    __table_args__ = (
        CheckConstraint("credit_balance >= 0", name="ck_employers_credit_balance"),
        CheckConstraint("total_spent >= 0", name="ck_employers_total_spent"),
        Index("ix_employers_company_name", "company_name"),
        Index("ix_employers_industry", "industry"),
        Index("ix_employers_kyc_status", "kyc_status"),
        Index("ix_employers_contact_phone", "contact_phone"),
    )

    def __repr__(self) -> str:
        return f"<Employer(id={self.id}, company_name={self.company_name})>"


# ==================== 2. Candidate Model ====================


class Candidate(Base, UUIDPrimaryKey, TimestampMixin):
    """
    候选人模型

    存储候选人的基本信息、求职状态和画像数据。

    关系:
        - one-to-many: Candidate -> Job (作为期望职位)
        - one-to-many: Candidate -> MatchResult
        - one-to-many: Candidate -> Guarantee

    使用示例:
        candidate = Candidate(
            phone_hash="abc123...",
            email="candidate@example.com",
            name="Zhang San",
            profile={"skills": ["Python", "FastAPI"]}
        )
    """

    __tablename__ = "candidates"

    # 联系方式
    phone_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        comment="手机号哈希 (用于登录)"
    )
    email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="邮箱"
    )
    email_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="邮箱是否已验证"
    )

    # 基本信息
    name: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="姓名"
    )
    avatar_url: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="头像 URL"
    )
    gender: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        comment="性别"
    )
    birth_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="出生日期"
    )
    age: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="年龄"
    )

    # 地理位置
    current_province: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="当前所在省份"
    )
    current_city: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="当前所在城市"
    )
    current_district: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="当前所在区县"
    )

    # 求职状态
    job_search_status: Mapped[str] = mapped_column(
        String(20),
        default=JobSearchStatus.PASSIVE,
        nullable=False,
        comment="求职状态"
    )

    # 画像数据 (JSONB)
    profile: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
        comment="候选人画像 (JSON)"
    )

    # 向量嵌入 ID (关联 Qdrant)
    embedding_vector_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Qdrant 向量 ID"
    )

    # 认证信息
    verification_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="认证分数 0.0-1.0"
    )

    # 简历信息
    resume_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="简历 ID"
    )
    resume_url: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="简历 URL"
    )
    resume_parsed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="简历解析时间"
    )

    # 完成度
    profile_completeness: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        comment="资料完整度 0.0-1.0"
    )

    # 期望工作
    expected_salary_min: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="期望最低薪资 (月薪/分)"
    )
    expected_salary_max: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="期望最高薪资 (月薪/分)"
    )
    preferred_job_titles: Mapped[Optional[list[str]]] = mapped_column(
        ARRAY(String),
        nullable=True,
        comment="期望职位列表"
    )
    preferred_locations: Mapped[Optional[list[str]]] = mapped_column(
        ARRAY(String),
        nullable=True,
        comment="期望工作地点列表"
    )
    preferred_industries: Mapped[Optional[list[str]]] = mapped_column(
        ARRAY(String),
        nullable=True,
        comment="期望行业列表"
    )

    # 状态
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="是否启用"
    )
    is_hidden: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="是否隐藏"
    )

    # ==================== 关系定义 ====================
    match_results: Mapped[list["MatchResult"]] = relationship(
        "MatchResult",
        back_populates="candidate",
        lazy="selectin",
        cascade="all, delete-orphan"
    )
    guarantees: Mapped[list["Guarantee"]] = relationship(
        "Guarantee",
        back_populates="candidate",
        lazy="selectin",
        cascade="all, delete-orphan"
    )

    # ==================== 约束和索引 ====================
    __table_args__ = (
        CheckConstraint(
            "age IS NULL OR (age >= 18 AND age <= 100)",
            name="ck_candidates_age"
        ),
        CheckConstraint(
            "profile_completeness >= 0.0 AND profile_completeness <= 1.0",
            name="ck_candidates_profile_completeness"
        ),
        Index("ix_candidates_email", "email"),
        Index("ix_candidates_job_search_status", "job_search_status"),
        Index("ix_candidates_profile_completeness", "profile_completeness"),
        Index("ix_candidates_embedding", "embedding_vector_id"),
    )

    def __repr__(self) -> str:
        return f"<Candidate(id={self.id}, name={self.name})>"


# ==================== 3. Job Model ====================


class Job(Base, UUIDPrimaryKey, TimestampMixin, SoftDeleteMixin):
    """
    职位模型

    存储职位的基本信息、要求和工作条件。

    关系:
        - many-to-one: Job -> Employer
        - one-to-many: Job -> MatchResult
        - one-to-many: Job -> Invoice
        - one-to-many: Job -> Guarantee

    使用示例:
        job = Job(
            employer_id=employer_uuid,
            job_title="Senior Python Engineer",
            requirement={"skills": ["Python", "FastAPI"]},
            salary_min=3000000,
            salary_max=5000000
        )
    """

    __tablename__ = "jobs"

    # 雇主外键
    employer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employers.id", ondelete="RESTRICT"),
        nullable=False,
        comment="雇主 ID"
    )

    # 职位基本信息
    job_title: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
        comment="职位名称"
    )
    job_category: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="职位类别"
    )
    job_tags: Mapped[Optional[list[str]]] = mapped_column(
        ARRAY(String),
        nullable=True,
        comment="职位标签: 远程, 高薪, 急招"
    )

    # 职位要求 (JSONB)
    requirement: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
        comment="职位要求详情 (JSON)"
    )

    # 职位详情 HTML
    jd_html: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="富文本职位描述"
    )

    # 职位类型
    employment_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="职位类型"
    )

    # 工作地点
    work_location_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="工作地点类型"
    )
    work_province: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="工作省份"
    )
    work_city: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="工作城市"
    )
    work_district: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="工作区县"
    )
    work_address_detail: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="详细工作地址"
    )

    # 薪资范围 (单位: 月薪/分)
    salary_min: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="最低薪资 (分/月)"
    )
    salary_max: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="最高薪资 (分/月)"
    )
    salary_negotiable: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="薪资是否可协商"
    )
    salary_show_type: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="薪资显示类型"
    )

    # 佣金配置
    commission_rate: Mapped[float] = mapped_column(
        Float,
        default=0.10,
        nullable=False,
        comment="佣金率 0.0-1.0"
    )
    commission_fixed_amount: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        nullable=True,
        comment="固定佣金金额 (分)"
    )

    # 紧急标识
    is_urgent: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="是否急招"
    )
    urgent_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="急招截止时间"
    )

    # 发布状态
    status: Mapped[str] = mapped_column(
        String(20),
        default=JobStatus.DRAFT,
        nullable=False,
        comment="职位状态"
    )

    # 投递限制
    max_applications: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="最大接收申请数"
    )
    current_applications: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="当前申请数"
    )

    # 查看统计
    view_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="浏览次数"
    )
    apply_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="申请次数"
    )

    # 发布时间
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="发布时间"
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="过期时间"
    )

    # ==================== 关系定义 ====================
    employer: Mapped["Employer"] = relationship(
        "Employer",
        back_populates="jobs",
        lazy="selectin"
    )
    match_results: Mapped[list["MatchResult"]] = relationship(
        "MatchResult",
        back_populates="job",
        lazy="selectin",
        cascade="all, delete-orphan"
    )
    invoices: Mapped[list["Invoice"]] = relationship(
        "Invoice",
        back_populates="job",
        lazy="selectin",
        cascade="all, delete-orphan"
    )
    guarantees: Mapped[list["Guarantee"]] = relationship(
        "Guarantee",
        back_populates="job",
        lazy="selectin",
        cascade="all, delete-orphan"
    )

    # ==================== 约束和索引 ====================
    __table_args__ = (
        CheckConstraint(
            "salary_min IS NULL OR salary_max IS NULL OR salary_min <= salary_max",
            name="ck_jobs_salary"
        ),
        CheckConstraint(
            "commission_rate >= 0.0 AND commission_rate <= 1.0",
            name="ck_jobs_commission_rate"
        ),
        Index("ix_jobs_employer_id", "employer_id"),
        Index("ix_jobs_job_title", "job_title"),
        Index("ix_jobs_status", "status"),
        Index("ix_jobs_work_city", "work_city"),
    )

    def __repr__(self) -> str:
        return f"<Job(id={self.id}, job_title={self.job_title})>"


# ==================== 4. MatchResult Model ====================


class MatchResult(Base, UUIDPrimaryKey, TimestampMixin, SoftDeleteMixin):
    """
    匹配结果模型

    存储候选人与职位的匹配结果和管道进度。

    关系:
        - many-to-one: MatchResult -> Job
        - many-to-one: MatchResult -> Candidate
        - many-to-one: MatchResult -> Employer
        - one-to-one: MatchResult -> Invoice (可选)
        - one-to-one: MatchResult -> Guarantee (可选)

    使用示例:
        match = MatchResult(
            job_id=job_uuid,
            candidate_id=candidate_uuid,
            employer_id=employer_uuid,
            overall_score=0.85,
            score_breakdown={"skill_match": 0.9, "experience_match": 0.8}
        )
    """

    __tablename__ = "match_results"

    # 外键
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        comment="职位 ID"
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        comment="候选人 ID"
    )
    employer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employers.id", ondelete="CASCADE"),
        nullable=False,
        comment="雇主 ID"
    )

    # 匹配管道阶段
    pipeline_stage: Mapped[str] = mapped_column(
        String(30),
        default=PipelineStage.AI_RECOMMENDED,
        nullable=False,
        comment="管道阶段"
    )

    # 总体匹配分数
    overall_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="总体匹配分数 0.0-1.0"
    )

    # 分数细分 (JSONB)
    score_breakdown: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
        comment="分数细分详情 (JSON)"
    )

    # 匹配原因 (数组)
    match_reasons: Mapped[Optional[list[str]]] = mapped_column(
        ARRAY(Text),
        nullable=True,
        comment="匹配原因列表"
    )

    # 拒绝原因
    rejection_reasons: Mapped[Optional[list[str]]] = mapped_column(
        ARRAY(Text),
        nullable=True,
        comment="拒绝原因列表"
    )

    # AI 生成的推荐理由
    ai_recommendation: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="AI 推荐理由"
    )

    # 薪资信息
    offer_amount: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Offer 金额 (月薪/分)"
    )
    last_salary: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="上一份工作薪资 (月薪/分)"
    )

    # 入职信息
    onboard_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="入职日期"
    )
    probation_end_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="试用期结束日期"
    )

    # 时间线记录 (JSONB)
    timeline: Mapped[list] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
        comment="操作时间线 (JSON)"
    )

    # 备注
    internal_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="内部备注"
    )

    # ==================== 关系定义 ====================
    job: Mapped["Job"] = relationship(
        "Job",
        back_populates="match_results",
        lazy="selectin"
    )
    candidate: Mapped["Candidate"] = relationship(
        "Candidate",
        back_populates="match_results",
        lazy="selectin"
    )
    employer: Mapped["Employer"] = relationship(
        "Employer",
        back_populates="match_results",
        lazy="selectin"
    )
    invoice: Mapped[Optional["Invoice"]] = relationship(
        "Invoice",
        back_populates="match_result",
        lazy="selectin",
        uselist=False
    )
    guarantee: Mapped[Optional["Guarantee"]] = relationship(
        "Guarantee",
        back_populates="match_result",
        lazy="selectin",
        uselist=False
    )

    # ==================== 约束和索引 ====================
    __table_args__ = (
        UniqueConstraint("job_id", "candidate_id", name="uq_match_results_job_candidate"),
        CheckConstraint(
            "overall_score >= 0.0 AND overall_score <= 1.0",
            name="ck_match_results_score"
        ),
        Index("ix_match_results_job_id", "job_id"),
        Index("ix_match_results_candidate_id", "candidate_id"),
        Index("ix_match_results_employer_id", "employer_id"),
        Index("ix_match_results_pipeline_stage", "pipeline_stage"),
        Index("ix_match_results_overall_score", "overall_score"),
        Index("ix_match_results_job_stage", "job_id", "pipeline_stage"),
    )

    def __repr__(self) -> str:
        return f"<MatchResult(id={self.id}, score={self.overall_score})>"


# ==================== 5. Invoice Model ====================


class Invoice(Base, UUIDPrimaryKey, TimestampMixin):
    """
    账单/发票模型

    存储交易账单和支付信息。

    关系:
        - many-to-one: Invoice -> Employer
        - many-to-one: Invoice -> Job
        - many-to-one: Invoice -> MatchResult
        - one-to-one: Invoice -> Guarantee

    使用示例:
        invoice = Invoice(
            employer_id=employer_uuid,
            job_id=job_uuid,
            match_id=match_uuid,
            base_fee=500000,
            total_fee=500000,
            status=InvoiceStatus.PENDING
        )
    """

    __tablename__ = "invoices"

    # 外键
    employer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employers.id", ondelete="RESTRICT"),
        nullable=False,
        comment="雇主 ID"
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="RESTRICT"),
        nullable=False,
        comment="职位 ID"
    )
    match_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("match_results.id", ondelete="RESTRICT"),
        nullable=False,
        comment="匹配记录 ID"
    )

    # 账单编号
    invoice_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        comment="账单编号"
    )

    # 费用明细 (单位: 分)
    base_fee: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
        comment="基础服务费 (分)"
    )
    screening_fee: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
        comment="筛选费 (分)"
    )
    interview_fee: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
        comment="面试安排费 (分)"
    )
    offer_fee: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
        comment="Offer 服务费 (分)"
    )
    guarantee_fee: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
        comment="保障服务费 (分)"
    )
    urgent_premium: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
        comment="急招溢价 (分)"
    )
    discount_amount: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
        comment="折扣金额 (分)"
    )

    # 计算字段 (由数据库自动计算)
    subtotal: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        server_default=text("0"),
        comment="小计 (分)"
    )
    total_fee: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        server_default=text("0"),
        comment="总费用 (分)"
    )

    # 佣金配置
    commission_rate: Mapped[float] = mapped_column(
        Float,
        default=0.10,
        nullable=False,
        comment="佣金率 0.0-1.0"
    )
    commission_amount: Mapped[int] = mapped_column(
        BigInteger,
        nullable=True,
        comment="佣金金额 (分)"
    )

    # 发票状态
    status: Mapped[str] = mapped_column(
        String(20),
        default=InvoiceStatus.PENDING,
        nullable=False,
        comment="账单状态"
    )

    # 支付信息
    payment_method: Mapped[Optional[str]] = mapped_column(
        String(30),
        nullable=True,
        comment="支付方式"
    )
    payment_reference: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="支付参考号"
    )
    payment_deadline: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="支付截止时间"
    )

    # 支付时间
    paid_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="支付时间"
    )

    # 发票抬头信息
    invoice_title: Mapped[Optional[str]] = mapped_column(
        String(300),
        nullable=True,
        comment="发票抬头"
    )
    invoice_tax_number: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="发票税号"
    )
    invoice_content: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="发票内容"
    )

    # 备注
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="备注"
    )

    # 退款信息
    refund_amount: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        nullable=True,
        comment="退款金额 (分)"
    )
    refund_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="退款原因"
    )
    refunded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="退款时间"
    )

    # ==================== 关系定义 ====================
    employer: Mapped["Employer"] = relationship(
        "Employer",
        back_populates="invoices",
        lazy="selectin"
    )
    job: Mapped["Job"] = relationship(
        "Job",
        back_populates="invoices",
        lazy="selectin"
    )
    match_result: Mapped["MatchResult"] = relationship(
        "MatchResult",
        back_populates="invoice",
        lazy="selectin"
    )
    guarantee: Mapped[Optional["Guarantee"]] = relationship(
        "Guarantee",
        back_populates="invoice",
        lazy="selectin",
        uselist=False
    )

    # ==================== 约束和索引 ====================
    __table_args__ = (
        CheckConstraint("base_fee >= 0", name="ck_invoices_base_fee"),
        CheckConstraint("total_fee >= 0", name="ck_invoices_total_fee"),
        CheckConstraint("refund_amount IS NULL OR refund_amount >= 0", name="ck_invoices_refund"),
        Index("ix_invoices_employer_id", "employer_id"),
        Index("ix_invoices_job_id", "job_id"),
        Index("ix_invoices_match_id", "match_id"),
        Index("ix_invoices_status", "status"),
        Index("ix_invoices_invoice_number", "invoice_number"),
    )

    def __repr__(self) -> str:
        return f"<Invoice(id={self.id}, total_fee={self.total_fee})>"


# ==================== 6. Guarantee Model ====================


class Guarantee(Base, UUIDPrimaryKey, TimestampMixin):
    """
    担保服务模型

    存储入职保障服务的条款和状态。

    关系:
        - many-to-one: Guarantee -> Invoice
        - many-to-one: Guarantee -> MatchResult
        - many-to-one: Guarantee -> Employer
        - many-to-one: Guarantee -> Candidate
        - many-to-one: Guarantee -> Job

    使用示例:
        guarantee = Guarantee(
            invoice_id=invoice_uuid,
            match_id=match_uuid,
            employer_id=employer_uuid,
            candidate_id=candidate_uuid,
            job_id=job_uuid,
            start_date=date(2024, 1, 1),
            expiry_date=date(2024, 4, 1),
            compensation_amount=1000000
        )
    """

    __tablename__ = "guarantees"

    # 外键
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="RESTRICT"),
        nullable=False,
        comment="账单 ID"
    )
    match_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("match_results.id", ondelete="RESTRICT"),
        nullable=False,
        comment="匹配记录 ID"
    )
    employer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employers.id", ondelete="RESTRICT"),
        nullable=False,
        comment="雇主 ID"
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidates.id", ondelete="RESTRICT"),
        nullable=False,
        comment="候选人 ID"
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="RESTRICT"),
        nullable=False,
        comment="职位 ID"
    )

    # 担保编号
    guarantee_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        comment="担保编号"
    )

    # 担保期限
    start_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="担保开始日期"
    )
    expiry_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="担保到期日期"
    )
    guarantee_months: Mapped[int] = mapped_column(
        Integer,
        default=3,
        nullable=False,
        comment="担保月数"
    )

    # 赔付配置
    compensation_amount: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        comment="赔付金额 (分)"
    )
    compensation_ratio: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="赔付比例 0.0-1.0"
    )

    # 担保状态
    status: Mapped[str] = mapped_column(
        String(20),
        default=GuaranteeStatus.ACTIVE,
        nullable=False,
        comment="担保状态"
    )

    # 赔付条款 (JSONB)
    terms: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
        comment="赔付条款详情 (JSON)"
    )

    # 认领信息
    claim_submitted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="赔付申请提交时间"
    )
    claim_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="赔付原因"
    )
    claim_status: Mapped[Optional[str]] = mapped_column(
        String(30),
        nullable=True,
        comment="赔付处理状态"
    )
    claim_resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="赔付处理完成时间"
    )
    claim_resolution_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="赔付处理备注"
    )

    # 证据材料
    evidence_url: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="证据材料 URL"
    )
    additional_evidence_urls: Mapped[Optional[list[str]]] = mapped_column(
        ARRAY(Text),
        nullable=True,
        comment="额外证据材料 URLs"
    )

    # 赔付处理
    approved_compensation: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        nullable=True,
        comment="批准赔付金额 (分)"
    )
    compensation_paid_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="赔付支付时间"
    )
    compensation_payment_reference: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="赔付支付参考号"
    )

    # 备注
    internal_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="内部备注"
    )

    # 候选人/雇主确认
    candidate_confirmed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="候选人是否确认"
    )
    candidate_confirmed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="候选人确认时间"
    )
    employer_confirmed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="雇主是否确认"
    )
    employer_confirmed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="雇主确认时间"
    )

    # ==================== 关系定义 ====================
    invoice: Mapped["Invoice"] = relationship(
        "Invoice",
        back_populates="guarantee",
        lazy="selectin"
    )
    match_result: Mapped["MatchResult"] = relationship(
        "MatchResult",
        back_populates="guarantee",
        lazy="selectin"
    )
    employer: Mapped["Employer"] = relationship(
        "Employer",
        back_populates="guarantees",
        lazy="selectin"
    )
    candidate: Mapped["Candidate"] = relationship(
        "Candidate",
        back_populates="guarantees",
        lazy="selectin"
    )
    job: Mapped["Job"] = relationship(
        "Job",
        back_populates="guarantees",
        lazy="selectin"
    )

    # ==================== 约束和索引 ====================
    __table_args__ = (
        CheckConstraint(
            "expiry_date > start_date",
            name="ck_guarantees_date"
        ),
        CheckConstraint(
            "compensation_amount > 0",
            name="ck_guarantees_compensation"
        ),
        Index("ix_guarantees_invoice_id", "invoice_id"),
        Index("ix_guarantees_match_id", "match_id"),
        Index("ix_guarantees_employer_id", "employer_id"),
        Index("ix_guarantees_candidate_id", "candidate_id"),
        Index("ix_guarantees_status", "status"),
        Index("ix_guarantees_guarantee_number", "guarantee_number"),
    )

    def __repr__(self) -> str:
        return f"<Guarantee(id={self.id}, status={self.status})>"


# ==================== 模型导出 ====================
__all__ = [
    # 枚举类
    "KYCStatus",
    "JobStatus",
    "JobSearchStatus",
    "PipelineStage",
    "InvoiceStatus",
    "GuaranteeStatus",
    "PaymentMethod",
    "EmploymentType",
    "WorkLocationType",
    # Mixin 类
    "TimestampMixin",
    "UUIDPrimaryKey",
    "SoftDeleteMixin",
    # 模型类
    "Employer",
    "Candidate",
    "Job",
    "MatchResult",
    "Invoice",
    "Guarantee",
]
