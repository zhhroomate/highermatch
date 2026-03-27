"""
HigherMatch™ Job Service - Job Schemas
======================================

Pydantic 数据模型，用于岗位管理接口的请求和响应验证。

版本: 1.0.0
"""

import re
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ==================== 枚举定义 ====================


class JobStatus(str, Enum):
    """岗位状态枚举"""
    DRAFT = "draft"           # 草稿
    PUBLISHED = "published"   # 已发布
    CLOSED = "closed"         # 已关闭
    ARCHIVED = "archived"     # 已归档


class EmploymentType(str, Enum):
    """职位类型枚举"""
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERNSHIP = "internship"


class WorkLocationType(str, Enum):
    """工作地点类型枚举"""
    ONSITE = "onsite"         # 现场办公
    REMOTE = "remote"        # 远程办公
    HYBRID = "hybrid"        # 混合办公


# ==================== 请求模型 ====================


class JobRequirement(BaseModel):
    """
    岗位要求

    Attributes:
        skills: 技能列表
        years_exp_min: 最低工作年限
        years_exp_max: 最高工作年限
        location: 工作地点列表
        salary_min: 最低薪资 (月薪/分)
        salary_max: 最高薪资 (月薪/分)
        industry: 行业
        education: 学历要求
        language: 语言要求
    """

    skills: list[str] = Field(
        default_factory=list,
        description="技能要求列表",
        examples=[["Python", "FastAPI", "PostgreSQL"]]
    )
    years_exp_min: Optional[int] = Field(
        default=None,
        ge=0,
        le=50,
        description="最低工作年限"
    )
    years_exp_max: Optional[int] = Field(
        default=None,
        ge=0,
        le=50,
        description="最高工作年限"
    )
    location: list[str] = Field(
        default_factory=list,
        description="工作地点列表",
        examples=[["北京", "上海", "深圳"]]
    )
    salary_min: Optional[int] = Field(
        default=None,
        ge=0,
        description="最低薪资 (分/月)"
    )
    salary_max: Optional[int] = Field(
        default=None,
        ge=0,
        description="最高薪资 (分/月)"
    )
    industry: Optional[str] = Field(
        default=None,
        max_length=100,
        description="行业要求"
    )
    education: Optional[str] = Field(
        default=None,
        max_length=50,
        description="学历要求",
        examples=["本科", "硕士", "博士"]
    )
    language: Optional[str] = Field(
        default=None,
        max_length=50,
        description="语言要求"
    )

    @model_validator(mode="after")
    def validate_salary_range(self):
        """验证薪资范围"""
        if self.salary_min is not None and self.salary_max is not None:
            if self.salary_min > self.salary_max:
                raise ValueError("最低薪资不能大于最高薪资")
        return self

    @model_validator(mode="after")
    def validate_years_exp_range(self):
        """验证工作年限范围"""
        if self.years_exp_min is not None and self.years_exp_max is not None:
            if self.years_exp_min > self.years_exp_max:
                raise ValueError("最低工作年限不能大于最高工作年限")
        return self


class JobCreateRequest(BaseModel):
    """
    创建岗位请求

    Attributes:
        job_title: 岗位名称
        requirement: 岗位要求
        jd_html: 富文本职位描述 (可选)
        is_urgent: 是否急招 (可选)
        employment_type: 职位类型 (可选)
        work_location_type: 工作地点类型 (可选)
        work_province: 工作省份 (可选)
        work_city: 工作城市 (可选)
        work_district: 工作区县 (可选)
        salary_negotiable: 薪资是否可协商 (可选)
        commission_rate: 佣金率 (可选)
        max_applications: 最大接收申请数 (可选)
    """

    job_title: str = Field(
        ...,
        min_length=1,
        max_length=300,
        description="岗位名称",
        examples=["高级 Python 开发工程师"]
    )
    requirement: JobRequirement = Field(
        ...,
        description="岗位要求"
    )
    jd_html: Optional[str] = Field(
        default=None,
        description="富文本职位描述 (HTML)",
        max_length=50000
    )
    is_urgent: bool = Field(
        default=False,
        description="是否急招"
    )
    employment_type: Optional[EmploymentType] = Field(
        default=None,
        description="职位类型"
    )
    work_location_type: Optional[WorkLocationType] = Field(
        default=None,
        description="工作地点类型"
    )
    work_province: Optional[str] = Field(
        default=None,
        max_length=50,
        description="工作省份"
    )
    work_city: Optional[str] = Field(
        default=None,
        max_length=50,
        description="工作城市"
    )
    work_district: Optional[str] = Field(
        default=None,
        max_length=50,
        description="工作区县"
    )
    work_address_detail: Optional[str] = Field(
        default=None,
        max_length=500,
        description="详细工作地址"
    )
    salary_negotiable: bool = Field(
        default=False,
        description="薪资是否可协商"
    )
    commission_rate: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="佣金率 0.0-1.0"
    )
    max_applications: Optional[int] = Field(
        default=None,
        gt=0,
        description="最大接收申请数"
    )

    @field_validator("job_title")
    @classmethod
    def validate_job_title(cls, v: str) -> str:
        """验证岗位名称"""
        v = v.strip()
        if not v:
            raise ValueError("岗位名称不能为空")
        # 禁止特殊字符
        if re.search(r"[<>{}\[\]\\|]", v):
            raise ValueError("岗位名称包含非法字符")
        return v


class JobUpdateRequest(BaseModel):
    """
    更新岗位请求

    仅在 status=draft 时允许修改。
    所有字段可选，只更新提供的字段。
    """

    job_title: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=300,
        description="岗位名称"
    )
    requirement: Optional[JobRequirement] = Field(
        default=None,
        description="岗位要求"
    )
    jd_html: Optional[str] = Field(
        default=None,
        max_length=50000,
        description="富文本职位描述 (HTML)"
    )
    is_urgent: Optional[bool] = Field(
        default=None,
        description="是否急招"
    )
    employment_type: Optional[EmploymentType] = Field(
        default=None,
        description="职位类型"
    )
    work_location_type: Optional[WorkLocationType] = Field(
        default=None,
        description="工作地点类型"
    )
    work_province: Optional[str] = Field(
        default=None,
        max_length=50,
        description="工作省份"
    )
    work_city: Optional[str] = Field(
        default=None,
        max_length=50,
        description="工作城市"
    )
    work_district: Optional[str] = Field(
        default=None,
        max_length=50,
        description="工作区县"
    )
    work_address_detail: Optional[str] = Field(
        default=None,
        max_length=500,
        description="详细工作地址"
    )
    salary_negotiable: Optional[bool] = Field(
        default=None,
        description="薪资是否可协商"
    )
    commission_rate: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="佣金率 0.0-1.0"
    )
    max_applications: Optional[int] = Field(
        default=None,
        gt=0,
        description="最大接收申请数"
    )

    @field_validator("job_title")
    @classmethod
    def validate_job_title(cls, v: Optional[str]) -> Optional[str]:
        """验证岗位名称"""
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("岗位名称不能为空")
            if re.search(r"[<>{}\[\]\\|]", v):
                raise ValueError("岗位名称包含非法字符")
        return v


class JobPublishRequest(BaseModel):
    """
    发布岗位请求

    可选参数:
        expires_at: 过期时间 (可选，不提供则使用默认值)
    """

    expires_at: Optional[datetime] = Field(
        default=None,
        description="岗位过期时间"
    )


class JobListQuery(BaseModel):
    """
    岗位列表查询参数

    支持 cursor 分页和 status 筛选。
    """

    cursor: Optional[str] = Field(
        default=None,
        description="分页游标 (base64 编码的 job_id)"
    )
    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="每页数量"
    )
    status: Optional[JobStatus] = Field(
        default=None,
        description="按状态筛选"
    )


# ==================== 响应模型 ====================


class JobRequirementResponse(BaseModel):
    """岗位要求响应"""

    skills: list[str] = Field(default_factory=list)
    years_exp_min: Optional[int] = None
    years_exp_max: Optional[int] = None
    location: list[str] = Field(default_factory=list)
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    industry: Optional[str] = None
    education: Optional[str] = None
    language: Optional[str] = None


class JobResponse(BaseModel):
    """
    岗位详情响应

    Attributes:
        job_id: 岗位 ID
        employer_id: 雇主 ID
        job_title: 岗位名称
        job_category: 岗位类别
        job_tags: 岗位标签
        requirement: 岗位要求
        jd_html: 富文本职位描述
        status: 岗位状态
        employment_type: 职位类型
        work_location_type: 工作地点类型
        work_province: 工作省份
        work_city: 工作城市
        work_district: 工作区县
        work_address_detail: 详细工作地址
        salary_min: 最低薪资
        salary_max: 最高薪资
        salary_negotiable: 薪资是否可协商
        is_urgent: 是否急招
        urgent_expires_at: 急招截止时间
        commission_rate: 佣金率
        max_applications: 最大接收申请数
        current_applications: 当前申请数
        view_count: 浏览次数
        apply_count: 申请次数
        published_at: 发布时间
        expires_at: 过期时间
        created_at: 创建时间
        updated_at: 更新时间
    """

    job_id: str = Field(..., description="岗位 ID")
    employer_id: str = Field(..., description="雇主 ID")
    job_title: str = Field(..., description="岗位名称")
    job_category: Optional[str] = Field(default=None, description="岗位类别")
    job_tags: list[str] = Field(default_factory=list, description="岗位标签")
    requirement: JobRequirementResponse = Field(..., description="岗位要求")
    jd_html: Optional[str] = Field(default=None, description="富文本职位描述")
    status: JobStatus = Field(..., description="岗位状态")
    employment_type: Optional[str] = Field(default=None, description="职位类型")
    work_location_type: Optional[str] = Field(default=None, description="工作地点类型")
    work_province: Optional[str] = Field(default=None, description="工作省份")
    work_city: Optional[str] = Field(default=None, description="工作城市")
    work_district: Optional[str] = Field(default=None, description="工作区县")
    work_address_detail: Optional[str] = Field(default=None, description="详细工作地址")
    salary_min: Optional[int] = Field(default=None, description="最低薪资 (分/月)")
    salary_max: Optional[int] = Field(default=None, description="最高薪资 (分/月)")
    salary_negotiable: bool = Field(default=False, description="薪资是否可协商")
    is_urgent: bool = Field(default=False, description="是否急招")
    urgent_expires_at: Optional[datetime] = Field(default=None, description="急招截止时间")
    commission_rate: float = Field(default=0.10, description="佣金率")
    max_applications: Optional[int] = Field(default=None, description="最大接收申请数")
    current_applications: int = Field(default=0, description="当前申请数")
    view_count: int = Field(default=0, description="浏览次数")
    apply_count: int = Field(default=0, description="申请次数")
    published_at: Optional[datetime] = Field(default=None, description="发布时间")
    expires_at: Optional[datetime] = Field(default=None, description="过期时间")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: Optional[datetime] = Field(default=None, description="更新时间")

    class Config:
        from_attributes = True


class JobCreateResponse(BaseModel):
    """
    创建岗位响应

    Attributes:
        job_id: 岗位 ID
        status: 岗位状态 (draft)
        created_at: 创建时间
    """

    job_id: str = Field(..., description="岗位 ID")
    status: JobStatus = Field(default=JobStatus.DRAFT, description="岗位状态")
    created_at: datetime = Field(..., description="创建时间")


class JobPublishResponse(BaseModel):
    """
    发布岗位响应

    Attributes:
        job_id: 岗位 ID
        status: 岗位状态 (published)
        published_at: 发布时间
    """

    job_id: str = Field(..., description="岗位 ID")
    status: JobStatus = Field(default=JobStatus.PUBLISHED, description="岗位状态")
    published_at: datetime = Field(..., description="发布时间")


class JobListResponse(BaseModel):
    """
    岗位列表响应

    Attributes:
        items: 岗位列表
        next_cursor: 下一页游标 (无更多数据时为 None)
        total: 总数 (可选，用于参考)
    """

    items: list[JobResponse] = Field(..., description="岗位列表")
    next_cursor: Optional[str] = Field(default=None, description="下一页游标")
    total: Optional[int] = Field(default=None, description="总数")


# ==================== 统一响应模型 ====================


class SuccessResponse(BaseModel):
    """
    统一成功响应

    Attributes:
        success: 是否成功 (固定 True)
        data: 响应数据
    """

    success: bool = Field(default=True)
    data: Any = Field(..., description="响应数据")


class ErrorDetail(BaseModel):
    """错误详情"""

    code: str = Field(..., description="错误码")
    message: str = Field(..., description="错误消息")
    details: Optional[dict] = Field(default=None, description="附加详情")


class ErrorResponse(BaseModel):
    """统一错误响应"""

    success: bool = Field(default=False)
    error: ErrorDetail


# ==================== 导出 ====================
__all__ = [
    # 枚举
    "JobStatus",
    "EmploymentType",
    "WorkLocationType",

    # 请求模型
    "JobRequirement",
    "JobCreateRequest",
    "JobUpdateRequest",
    "JobPublishRequest",
    "JobListQuery",

    # 响应模型
    "JobRequirementResponse",
    "JobResponse",
    "JobCreateResponse",
    "JobPublishResponse",
    "JobListResponse",

    # 统一响应
    "SuccessResponse",
    "ErrorDetail",
    "ErrorResponse",
]
