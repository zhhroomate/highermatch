"""
HigherMatch™ Verification Service - Schemas
==========================================

验证服务 Pydantic 模型定义。

版本: 1.0.0
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ==================== 验证请求/响应 ====================
class VerificationTriggerRequest(BaseModel):
    """手动触发验证请求"""
    candidate_id: str = Field(..., description="候选人 ID")
    force_refresh: bool = Field(
        default=False,
        description="是否强制重新验证 (忽略缓存)"
    )


class EducationVerificationData(BaseModel):
    """学历验证数据"""
    verified_schools: list[str] = Field(default_factory=list, description="已验证院校")
    failed_schools: list[str] = Field(default_factory=list, description="未验证院校")
    details: str = Field(default="", description="验证详情")


class SkillConsistencyData(BaseModel):
    """技能一致性数据"""
    matched_skills: list[str] = Field(default_factory=list, description="已匹配技能")
    unmatched_skills: list[str] = Field(default_factory=list, description="未匹配技能")
    analysis: str = Field(default="", description="分析说明")


class VerificationDetails(BaseModel):
    """验证详情"""
    education: EducationVerificationData = Field(description="学历验证结果")
    skill_consistency: SkillConsistencyData = Field(description="技能一致性结果")
    calculation: dict = Field(description="计算公式")


class VerificationResultData(BaseModel):
    """验证结果数据"""
    candidate_id: str = Field(description="候选人 ID")
    education_score: float = Field(description="学历验证分数 0.0-1.0")
    skill_consistency_score: float = Field(description="技能一致性分数 0.0-1.0")
    verification_score: float = Field(description="综合验证分数 0.0-1.0")
    requires_manual_override: bool = Field(description="是否需要人工复核")
    is_verified: bool = Field(description="是否已验证通过")
    verified_at: datetime = Field(description="验证时间")
    details: VerificationDetails = Field(description="验证详情")
    error: Optional[str] = Field(default=None, description="错误信息")


class VerificationTriggerResponse(BaseModel):
    """触发验证响应"""
    success: bool = Field(description="是否成功")
    message: str = Field(description="消息")
    candidate_id: str = Field(description="候选人 ID")
    verification_score: float = Field(description="验证分数")
    requires_manual_override: bool = Field(description="是否需要人工复核")


class VerificationResultResponse(BaseModel):
    """获取验证结果响应"""
    success: bool = Field(description="是否成功")
    data: Optional[VerificationResultData] = Field(default=None, description="验证结果数据")
    error: Optional[str] = Field(default=None, description="错误信息")


# ==================== 人工覆写 ====================
class VerificationOverrideRequest(BaseModel):
    """人工覆写请求"""
    candidate_id: str = Field(..., description="候选人 ID")
    override_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="人工覆写分数 0.0-1.0"
    )
    reason: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="覆写原因"
    )
    override_by: str = Field(..., description="覆写操作人")


class VerificationOverrideRecord(BaseModel):
    """覆写记录"""
    candidate_id: str = Field(description="候选人 ID")
    original_score: float = Field(description="原分数")
    override_score: float = Field(description="覆写分数")
    reason: str = Field(description="覆写原因")
    override_by: str = Field(description="操作人")
    override_at: datetime = Field(description="覆写时间")


class VerificationOverrideResponse(BaseModel):
    """人工覆写响应"""
    success: bool = Field(description="是否成功")
    message: str = Field(description="消息")
    record: Optional[VerificationOverrideRecord] = Field(default=None, description="覆写记录")


# ==================== 待复核列表 ====================
class PendingOverrideItem(BaseModel):
    """待复核项"""
    candidate_id: str = Field(description="候选人 ID")
    candidate_name: Optional[str] = Field(default=None, description="候选人姓名")
    verification_score: float = Field(description="验证分数")
    education_score: float = Field(description="学历分数")
    skill_consistency_score: float = Field(description="技能一致性分数")
    submitted_at: datetime = Field(description="提交时间")
    profile_completeness: float = Field(description="简历完整度")


class PendingOverrideListResponse(BaseModel):
    """待复核列表响应"""
    success: bool = Field(description="是否成功")
    total: int = Field(description="待复核总数")
    items: list[PendingOverrideItem] = Field(default_factory=list, description="待复核列表")
    page: int = Field(default=1, description="当前页")
    page_size: int = Field(default=20, description="每页数量")


# ==================== 健康检查 ====================
class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str = Field(description="服务状态")
    service: str = Field(description="服务名称")
    version: str = Field(description="版本号")
    kafka_connected: bool = Field(description="Kafka 连接状态")


# ==================== 导出 ====================
__all__ = [
    # 验证请求/响应
    "VerificationTriggerRequest",
    "VerificationTriggerResponse",
    "VerificationResultResponse",
    # 验证数据
    "EducationVerificationData",
    "SkillConsistencyData",
    "VerificationDetails",
    "VerificationResultData",
    # 人工覆写
    "VerificationOverrideRequest",
    "VerificationOverrideResponse",
    "VerificationOverrideRecord",
    # 待复核
    "PendingOverrideItem",
    "PendingOverrideListResponse",
    # 健康检查
    "HealthResponse",
]
