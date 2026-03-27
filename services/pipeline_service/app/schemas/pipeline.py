"""
HigherMatch™ Pipeline Service - Pipeline Schemas
==============================================

Pydantic 数据模型，用于招聘管道管理接口的请求和响应验证。

版本: 1.0.0
"""

from datetime import datetime, date
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ==================== 枚举定义 ====================


class PipelineStage(str, Enum):
    """
    招聘管道阶段枚举

    对应前端 Kanban 看板的列。
    """
    AI_RECOMMENDED = "ai_recommended"       # AI 推荐
    INVITED = "invited"                     # 已邀请 (雇主查看后)
    INTERVIEWING = "interviewing"           # 面试中
    OFFER = "offer"                         # Offer 阶段
    ONBOARDED = "onboarded"                 # 已入职
    REJECTED = "rejected"                   # 已拒绝

    @classmethod
    def from_legacy(cls, value: str) -> "PipelineStage":
        """
        从旧版阶段名称转换

        兼容旧的 pipeline_stage 值。
        """
        mapping = {
            "ai_recommended": cls.AI_RECOMMENDED,
            "employer_reviewed": cls.INVITED,
            "interview_scheduled": cls.INTERVIEWING,
            "interview_completed": cls.INTERVIEWING,
            "offer_sent": cls.OFFER,
            "offer_accepted": cls.OFFER,
            "onboarded": cls.ONBOARDED,
            "rejected": cls.REJECTED,
            "withdrawn": cls.REJECTED,
        }
        return mapping.get(value, cls.AI_RECOMMENDED)

    @classmethod
    def all_stages(cls) -> list["PipelineStage"]:
        """获取所有阶段"""
        return list(cls)

    @classmethod
    def kanban_stages(cls) -> list["PipelineStage"]:
        """获取 Kanban 看板显示的阶段"""
        return [
            cls.AI_RECOMMENDED,
            cls.INVITED,
            cls.INTERVIEWING,
            cls.OFFER,
            cls.ONBOARDED,
            cls.REJECTED,
        ]


# ==================== 请求模型 ====================


class PipelineMoveRequest(BaseModel):
    """
    管道移动请求

    将候选人从当前阶段移动到新阶段。

    Attributes:
        match_id: 匹配记录 ID
        from_stage: 原阶段
        to_stage: 目标阶段
    """

    match_id: str = Field(
        ...,
        description="匹配记录 ID (UUID)",
        examples=["550e8400-e29b-41d4-a716-446655440000"]
    )
    from_stage: PipelineStage = Field(
        ...,
        description="原管道阶段"
    )
    to_stage: PipelineStage = Field(
        ...,
        description="目标管道阶段"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "match_id": "550e8400-e29b-41d4-a716-446655440000",
                "from_stage": "ai_recommended",
                "to_stage": "invited"
            }
        }
    }


# ==================== 响应模型 ====================


class ScoreBreakdown(BaseModel):
    """分数细分详情"""

    skill_match: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="技能匹配度")
    experience_match: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="经验匹配度")
    location_match: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="地点匹配度")
    salary_match: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="薪资匹配度")
    culture_match: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="文化匹配度")


class CandidateBrief(BaseModel):
    """
    候选人简要信息 (脱敏数据)

    用于管道看板展示，不包含敏感信息。

    Attributes:
        candidate_id: 候选人 ID
        name: 姓名 (脱敏)
        avatar_url: 头像 URL
        current_city: 当前城市
        current_province: 当前省份
        years_exp: 工作年限 (从 profile 中提取)
        skills: 核心技能 (从 profile 中提取)
        profile_completeness: 资料完整度
        verification_score: 认证分数
    """

    candidate_id: str = Field(..., description="候选人 ID")
    name: Optional[str] = Field(default=None, description="姓名 (脱敏)")
    avatar_url: Optional[str] = Field(default=None, description="头像 URL")
    current_city: Optional[str] = Field(default=None, description="当前城市")
    current_province: Optional[str] = Field(default=None, description="当前省份")
    years_exp: Optional[int] = Field(default=None, description="工作年限")
    skills: list[str] = Field(default_factory=list, description="核心技能")
    profile_completeness: float = Field(default=0.0, description="资料完整度")
    verification_score: Optional[float] = Field(default=None, description="认证分数")

    class Config:
        from_attributes = True


class PipelineCard(BaseModel):
    """
    管道卡片

    代表 Kanban 看板上的一个候选人卡片。

    Attributes:
        match_id: 匹配记录 ID
        candidate: 候选人简要信息
        overall_score: 总体匹配分数 (0.0-1.0)
        score_breakdown: 分数细分
        ai_recommendation: AI 推荐理由
        match_reasons: 匹配原因
        pipeline_stage: 当前阶段
        timeline: 操作时间线
        created_at: 创建时间
        updated_at: 更新时间
    """

    match_id: str = Field(..., description="匹配记录 ID")
    candidate: CandidateBrief = Field(..., description="候选人简要信息")
    overall_score: float = Field(..., ge=0.0, le=1.0, description="总体匹配分数")
    score_breakdown: ScoreBreakdown = Field(..., description="分数细分")
    ai_recommendation: Optional[str] = Field(default=None, description="AI 推荐理由")
    match_reasons: list[str] = Field(default_factory=list, description="匹配原因")
    pipeline_stage: PipelineStage = Field(..., description="当前阶段")
    timeline: list[dict] = Field(default_factory=list, description="操作时间线")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: Optional[datetime] = Field(default=None, description="更新时间")

    class Config:
        from_attributes = True


class PipelineColumn(BaseModel):
    """
    管道列

    对应 Kanban 看板的一列 (一个阶段)。

    Attributes:
        stage: 阶段
        cards: 该阶段的所有卡片
        count: 卡片数量
    """

    stage: PipelineStage = Field(..., description="管道阶段")
    cards: list[PipelineCard] = Field(default_factory=list, description="候选人卡片列表")
    count: int = Field(..., description="卡片数量")


class PipelineResponse(BaseModel):
    """
    管道响应

    包含岗位的完整招聘管道，按阶段分组。

    Attributes:
        job_id: 岗位 ID
        job_title: 岗位名称
        columns: 管道列列表
        total_candidates: 候选人总数
    """

    job_id: str = Field(..., description="岗位 ID")
    job_title: str = Field(..., description="岗位名称")
    columns: list[PipelineColumn] = Field(default_factory=list, description="管道列列表")
    total_candidates: int = Field(..., description="候选人总数")


class PipelineMoveResponse(BaseModel):
    """
    管道移动响应

    Attributes:
        match_id: 匹配记录 ID
        from_stage: 原阶段
        to_stage: 目标阶段
        updated_at: 更新时间
        message: 操作结果消息
    """

    match_id: str = Field(..., description="匹配记录 ID")
    from_stage: PipelineStage = Field(..., description="原阶段")
    to_stage: PipelineStage = Field(..., description="目标阶段")
    updated_at: datetime = Field(..., description="更新时间")
    message: str = Field(default="Move successful", description="操作结果消息")


class PipelineError(BaseModel):
    """管道操作错误"""

    code: str = Field(..., description="错误码")
    message: str = Field(..., description="错误消息")
    details: Optional[dict] = Field(default=None, description="附加详情")


# ==================== 统一响应模型 ====================


class SuccessResponse(BaseModel):
    """统一成功响应"""

    success: bool = Field(default=True)
    data: Any = Field(..., description="响应数据")


class ErrorResponse(BaseModel):
    """统一错误响应"""

    success: bool = Field(default=False)
    error: PipelineError


# ==================== 导出 ====================
__all__ = [
    # 枚举
    "PipelineStage",

    # 请求模型
    "PipelineMoveRequest",

    # 响应模型
    "ScoreBreakdown",
    "CandidateBrief",
    "PipelineCard",
    "PipelineColumn",
    "PipelineResponse",
    "PipelineMoveResponse",
    "PipelineError",

    # 统一响应
    "SuccessResponse",
    "ErrorResponse",
]
