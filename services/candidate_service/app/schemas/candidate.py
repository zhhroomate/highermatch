"""
HigherMatch™ Candidate Service - Schemas
=========================================

Pydantic 模型定义，用于 API 请求/响应验证。

版本: 1.0.0
"""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


# ==================== 简历解析相关 ====================
class ResumeParseResponse(BaseModel):
    """简历解析响应"""
    success: bool = Field(description="解析是否成功")
    candidate_id: int = Field(description="候选人 ID")
    resume_id: str = Field(description="简历 ID")
    data: Optional[dict] = Field(default=None, description="解析后的数据")
    error: Optional[str] = Field(default=None, description="错误信息")
    from_cache: bool = Field(default=False, description="是否来自缓存")


# ==================== 候选人档案相关 ====================
class EducationItem(BaseModel):
    """教育经历"""
    school: str = Field(description="学校名称")
    degree: Optional[str] = Field(default=None, description="学位")
    major: Optional[str] = Field(default=None, description="专业")
    start_date: Optional[str] = Field(default=None, description="开始时间")
    end_date: Optional[str] = Field(default=None, description="结束时间")


class WorkHistoryItem(BaseModel):
    """工作经历"""
    company: str = Field(description="公司名称")
    title: str = Field(description="职位名称")
    start_date: Optional[str] = Field(default=None, description="开始时间")
    end_date: Optional[str] = Field(default=None, description="结束时间")
    description: Optional[str] = Field(default=None, description="工作描述")


class CandidateProfileResponse(BaseModel):
    """候选人档案响应"""
    user_id: str = Field(description="用户 ID")
    name: Optional[str] = Field(default=None, description="姓名")
    email: Optional[str] = Field(default=None, description="邮箱")
    phone: Optional[str] = Field(default=None, description="电话")
    avatar_url: Optional[str] = Field(default=None, description="头像 URL")
    gender: Optional[str] = Field(default=None, description="性别")
    age: Optional[int] = Field(default=None, description="年龄")
    birth_date: Optional[date] = Field(default=None, description="出生日期")

    # 地理位置
    current_province: Optional[str] = Field(default=None, description="当前所在省份")
    current_city: Optional[str] = Field(default=None, description="当前所在城市")
    current_district: Optional[str] = Field(default=None, description="当前所在区县")

    # 求职状态
    job_search_status: str = Field(description="求职状态")

    # 画像数据
    education: list[EducationItem] = Field(default_factory=list, description="教育经历")
    work_history: list[WorkHistoryItem] = Field(default_factory=list, description="工作经历")
    skills: list[str] = Field(default_factory=list, description="技能列表")
    certifications: list[str] = Field(default_factory=list, description="证书")
    summary: Optional[str] = Field(default=None, description="个人简介")
    total_years_exp: int = Field(default=0, description="总工作年限")

    # 简历信息
    resume_id: Optional[str] = Field(default=None, description="简历 ID")
    resume_url: Optional[str] = Field(default=None, description="简历 URL")
    resume_parsed_at: Optional[datetime] = Field(default=None, description="简历解析时间")

    # 期望工作
    expected_salary_min: Optional[int] = Field(default=None, description="期望最低薪资 (分/月)")
    expected_salary_max: Optional[int] = Field(default=None, description="期望最高薪资 (分/月)")
    preferred_job_titles: list[str] = Field(default_factory=list, description="期望职位")
    preferred_locations: list[str] = Field(default_factory=list, description="期望地点")
    preferred_industries: list[str] = Field(default_factory=list, description="期望行业")

    # 完成度
    profile_completeness: float = Field(description="资料完整度 0.0-1.0")
    completeness_breakdown: dict = Field(
        default_factory=dict,
        description="完整度明细"
    )

    # 状态
    is_active: bool = Field(default=True, description="是否启用")
    is_verified: bool = Field(default=False, description="是否认证")
    verification_score: Optional[float] = Field(default=None, description="认证分数")

    # 时间戳
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="更新时间")


class CandidateProfileUpdateRequest(BaseModel):
    """候选人档案更新请求"""
    # 基本信息
    name: Optional[str] = Field(default=None, max_length=200, description="姓名")
    avatar_url: Optional[str] = Field(default=None, max_length=500, description="头像 URL")
    gender: Optional[str] = Field(default=None, description="性别")
    birth_date: Optional[date] = Field(default=None, description="出生日期")

    # 地理位置
    current_province: Optional[str] = Field(default=None, max_length=50, description="当前所在省份")
    current_city: Optional[str] = Field(default=None, max_length=50, description="当前所在城市")
    current_district: Optional[str] = Field(default=None, max_length=50, description="当前所在区县")

    # 求职状态
    job_search_status: Optional[str] = Field(
        default=None,
        description="求职状态: not_looking, passive, active, urgent"
    )

    # 画像数据
    education: Optional[list[EducationItem]] = Field(default=None, description="教育经历")
    work_history: Optional[list[WorkHistoryItem]] = Field(default=None, description="工作经历")
    skills: Optional[list[str]] = Field(default=None, description="技能列表")
    certifications: Optional[list[str]] = Field(default=None, description="证书")
    summary: Optional[str] = Field(default=None, max_length=2000, description="个人简介")

    # 期望工作
    expected_salary_min: Optional[int] = Field(default=None, ge=0, description="期望最低薪资 (分/月)")
    expected_salary_max: Optional[int] = Field(default=None, ge=0, description="期望最高薪资 (分/月)")
    preferred_job_titles: Optional[list[str]] = Field(default=None, description="期望职位")
    preferred_locations: Optional[list[str]] = Field(default=None, description="期望地点")
    preferred_industries: Optional[list[str]] = Field(default=None, description="期望行业")


class CandidateProfileUpdateResponse(BaseModel):
    """候选人档案更新响应"""
    success: bool = Field(description="更新是否成功")
    message: str = Field(description="消息")
    updated_fields: list[str] = Field(default_factory=list, description="更新的字段列表")
    profile_completeness: float = Field(description="新的资料完整度")


# ==================== 职位推荐相关 ====================
class RecommendedJob(BaseModel):
    """推荐的职位"""
    job_id: str = Field(description="职位 ID")
    job_title: str = Field(description="职位名称")
    company_name: str = Field(description="公司名称")
    company_logo_url: Optional[str] = Field(default=None, description="公司 Logo")
    work_city: Optional[str] = Field(description="工作城市")
    work_location_type: str = Field(description="工作地点类型")
    salary_min: Optional[int] = Field(default=None, description="最低薪资 (分/月)")
    salary_max: Optional[int] = Field(default=None, description="最高薪资 (分/月)")
    employment_type: Optional[str] = Field(default=None, description="职位类型")
    match_score: float = Field(description="匹配分数 0.0-1.0")
    match_reasons: list[str] = Field(default_factory=list, description="匹配原因")
    is_urgent: bool = Field(default=False, description="是否急招")
    published_at: Optional[datetime] = Field(default=None, description="发布时间")


class CandidateRecommendationsResponse(BaseModel):
    """职位推荐响应"""
    candidate_id: str = Field(description="候选人 ID")
    total_count: int = Field(description="推荐总数")
    jobs: list[RecommendedJob] = Field(default_factory=list, description="推荐的职位列表")
    search_params: dict = Field(default_factory=dict, description="搜索参数")


# ==================== 申请相关 ====================
class ApplicationCreateRequest(BaseModel):
    """创建申请请求"""
    job_id: str = Field(description="职位 ID")


class ApplicationResponse(BaseModel):
    """申请响应"""
    success: bool = Field(description="申请是否成功")
    application_id: Optional[str] = Field(default=None, description="申请记录 ID")
    job_id: str = Field(description="职位 ID")
    candidate_id: str = Field(description="候选人 ID")
    pipeline_stage: str = Field(description="管道阶段")
    message: str = Field(description="消息")


# ==================== 通用响应 ====================
class ErrorDetail(BaseModel):
    """错误详情"""
    code: str = Field(description="错误码")
    message: str = Field(description="错误消息")
    details: Optional[dict] = Field(default=None, description="附加详情")


class APIResponse(BaseModel):
    """通用 API 响应"""
    success: bool = Field(default=True, description="是否成功")
    data: Optional[dict] = Field(default=None, description="响应数据")
    error: Optional[ErrorDetail] = Field(default=None, description="错误信息")


# ==================== 健康检查 ====================
class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str = Field(description="服务状态")
    service: str = Field(description="服务名称")
    version: str = Field(description="版本号")
    database: str = Field(description="数据库状态")
    redis: str = Field(description="Redis 状态")


# ==================== 导出 ====================
__all__ = [
    # 简历解析
    "ResumeParseResponse",
    # 候选人档案
    "EducationItem",
    "WorkHistoryItem",
    "CandidateProfileResponse",
    "CandidateProfileUpdateRequest",
    "CandidateProfileUpdateResponse",
    # 职位推荐
    "RecommendedJob",
    "CandidateRecommendationsResponse",
    # 申请
    "ApplicationCreateRequest",
    "ApplicationResponse",
    # 通用
    "APIResponse",
    "ErrorDetail",
    "HealthResponse",
]
