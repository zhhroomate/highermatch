"""
HigherMatch™ Advisor Service - Advisor Router
=============================================

AI 职业顾问 API 路由。

接口:
1. POST /api/v1/advisor/chat - 聊天接口

版本: 1.0.0
"""

import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func, String
from sqlalchemy.ext.asyncio import AsyncSession

import sys
sys.path.insert(0, "/workspace/highermatch")
from shared.auth_middleware import get_current_user, TokenPayload, require_role
from shared.models import Candidate

from app.services.advisor_service import (
    AdvisorChatRequest,
    AdvisorChatResponse,
    get_advisor,
)

# ==================== 日志配置 ====================
logger = logging.getLogger(__name__)

# ==================== 路由实例 ====================
router = APIRouter(prefix="/api/v1/advisor", tags=["Advisor"])


# ==================== 1. 聊天接口 ====================
@router.post(
    "/chat",
    response_model=AdvisorChatResponse,
    summary="AI 职业顾问聊天",
    description="与 AI 职业顾问对话，获取个性化职业发展建议"
)
async def chat_with_advisor(
    request: AdvisorChatRequest,
    user: Annotated[TokenPayload, Depends(require_role(["candidate"]))],
    db: AsyncSession = Depends(),
):
    """
    AI 职业顾问聊天接口

    需要 candidate 角色权限。

    业务逻辑:
    1. 获取当前候选人的 profile 数据
    2. 组装 System Prompt，赋予资深猎头与职业规划师角色
    3. 将候选人的竞争力分析、市场分位数等数据注入上下文
    4. 调用 LLM 生成回复
    5. 若用户有求职意向，从 VDB 检索 Top-3 匹配岗位

    Args:
        request: 聊天请求 (message, context_id)
        user: 当前用户 (来自 JWT)
        db: 数据库会话

    Returns:
        AdvisorChatResponse:
        - success: 是否成功
        - data.reply: 回复内容 (Markdown)
        - data.action_cards: 行动卡片列表 (如有求职意向)
        - data.analysis: 竞争力分析
        - data.intent_detected: 是否检测到求职意向
    """
    # 1. 获取候选人 profile 数据
    stmt = select(Candidate).where(
        func.cast(Candidate.id, String) == user.sub
    )
    result = await db.execute(stmt)
    candidate = result.scalar_one_or_none()

    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "error": {
                    "code": "CANDIDATE_NOT_FOUND",
                    "message": "候选人记录不存在"
                }
            }
        )

    # 2. 构建候选人画像字典
    candidate_profile = _build_profile_dict(candidate)

    # 3. 调用职业顾问服务
    advisor = get_advisor()

    try:
        response = await advisor.chat(
            message=request.message,
            candidate_profile=candidate_profile,
            context_id=request.context_id,
        )

        return response

    except Exception as e:
        logger.error(f"Advisor chat error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": {
                    "code": "ADVISOR_ERROR",
                    "message": f"顾问服务错误: {str(e)}"
                }
            }
        )


# ==================== 辅助函数 ====================
def _build_profile_dict(candidate: Candidate) -> dict:
    """
    将 Candidate 模型转换为字典

    Args:
        candidate: Candidate 模型实例

    Returns:
        候选人画像字典
    """
    # 获取画像数据
    profile_data = candidate.profile or {}

    # 解析教育经历
    education_list = profile_data.get("education", [])

    # 解析工作经历
    work_history_list = profile_data.get("work_history", [])

    # 构建返回字典
    return {
        "id": str(candidate.id),
        "name": candidate.name,
        "email": candidate.email,
        "current_city": candidate.current_city,
        "current_province": candidate.current_province,
        "age": candidate.age,
        "gender": candidate.gender,
        "birth_date": str(candidate.birth_date) if candidate.birth_date else None,

        # 求职状态
        "job_search_status": candidate.job_search_status,

        # 技能
        "skills": profile_data.get("skills", []),
        "certifications": profile_data.get("certifications", []),

        # 教育经历
        "education": education_list,

        # 工作经历
        "work_history": work_history_list,
        "total_years_exp": profile_data.get("total_years_exp", 0),

        # 简历信息
        "resume_id": str(candidate.resume_id) if candidate.resume_id else None,
        "resume_parsed_at": candidate.resume_parsed_at.isoformat() if candidate.resume_parsed_at else None,

        # 期望工作
        "expected_salary_min": candidate.expected_salary_min,
        "expected_salary_max": candidate.expected_salary_max,
        "preferred_job_titles": candidate.preferred_job_titles or [],
        "preferred_locations": candidate.preferred_locations or [],
        "preferred_industries": candidate.preferred_industries or [],

        # 完成度
        "profile_completeness": candidate.profile_completeness,

        # 认证
        "verification_score": candidate.verification_score,
    }


# ==================== 健康检查 ====================
@router.get("/health", summary="服务健康检查")
async def advisor_health():
    """AI 职业顾问服务健康检查"""
    return {
        "status": "healthy",
        "service": "advisor",
        "version": "1.0.0",
    }


# ==================== 导出 ====================
__all__ = ["router"]
