"""
HigherMatch™ Verification Service - Verification Router
======================================================

候选人交叉验证 API 路由。

接口:
1. POST /api/v1/verification/trigger - 手动触发验证
2. GET /api/v1/verification/result/:candidate_id - 获取验证结果
3. POST /api/v1/verification/override - 人工覆写分数

版本: 1.0.0
"""

import logging
from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, String, func
from sqlalchemy.ext.asyncio import AsyncSession

import sys
sys.path.insert(0, "/workspace/highermatch")
from shared.auth_middleware import get_current_user, TokenPayload, require_role
from shared.models import Candidate

from app.services.verification_service import (
    get_verification_service,
    VerificationResult,
)
from app.schemas.verification import (
    VerificationTriggerRequest,
    VerificationTriggerResponse,
    VerificationResultResponse,
    VerificationResultData,
    VerificationDetails,
    EducationVerificationData,
    SkillConsistencyData,
    VerificationOverrideRequest,
    VerificationOverrideResponse,
    VerificationOverrideRecord,
    PendingOverrideListResponse,
    PendingOverrideItem,
)

# ==================== 日志配置 ====================
logger = logging.getLogger(__name__)

# ==================== 路由实例 ====================
router = APIRouter(prefix="/api/v1/verification", tags=["Verification"])


# ==================== 辅助函数 ====================
async def get_candidate_data(db: AsyncSession, candidate_id: str) -> dict:
    """
    获取候选人数据用于验证

    Args:
        db: 数据库会话
        candidate_id: 候选人 ID

    Returns:
        候选人数据字典

    Raises:
        HTTPException: 候选人不存在
    """
    stmt = select(Candidate).where(func.cast(Candidate.id, String) == candidate_id)
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

    # 构建验证所需的数据
    profile_data = candidate.profile or {}

    return {
        "education": profile_data.get("education", []),
        "skills": profile_data.get("skills", []),
        "work_history": profile_data.get("work_history", []),
        "total_years_exp": profile_data.get("total_years_exp", 0),
    }


def build_verification_result_data(result: VerificationResult) -> VerificationResultData:
    """
    构建验证结果数据

    Args:
        result: VerificationResult

    Returns:
        VerificationResultData
    """
    details = result.details or {}

    return VerificationResultData(
        candidate_id=result.candidate_id,
        education_score=result.education_score,
        skill_consistency_score=result.skill_consistency_score,
        verification_score=result.verification_score,
        requires_manual_override=result.requires_manual_override,
        is_verified=result.is_verified,
        verified_at=result.verified_at,
        details=VerificationDetails(
            education=EducationVerificationData(
                verified_schools=details.get("education", {}).get("verified_schools", []),
                failed_schools=details.get("education", {}).get("failed_schools", []),
                details=details.get("education", {}).get("details", ""),
            ),
            skill_consistency=SkillConsistencyData(
                matched_skills=details.get("skill_consistency", {}).get("matched_skills", []),
                unmatched_skills=details.get("skill_consistency", {}).get("unmatched_skills", []),
                analysis=details.get("skill_consistency", {}).get("analysis", ""),
            ),
            calculation=details.get("calculation", {}),
        ),
        error=result.error,
    )


# ==================== 1. 手动触发验证 ====================
@router.post(
    "/trigger",
    response_model=VerificationTriggerResponse,
    summary="手动触发验证",
    description="手动触发候选人的交叉验证"
)
async def trigger_verification(
    request: VerificationTriggerRequest,
    user: Annotated[TokenPayload, Depends(get_current_user)],
    db: AsyncSession = Depends(),
):
    """
    手动触发候选人验证

    权限: 任何已登录用户

    业务逻辑:
    1. 获取候选人数据
    2. 执行学历验证 (mock)
    3. 执行技能一致性验证 (LLM)
    4. 计算综合 verification_score
    5. 更新 candidates 表
    6. 标记 manual_override 需求 (如需要)
    """
    try:
        # 1. 获取候选人数据
        candidate_data = await get_candidate_data(db, request.candidate_id)

        # 2. 执行验证
        service = get_verification_service()
        result = await service.verify_candidate(
            candidate_id=request.candidate_id,
            candidate_data=candidate_data,
        )

        if result.error:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "success": False,
                    "error": {
                        "code": "VERIFICATION_FAILED",
                        "message": result.error
                    }
                }
            )

        # 3. 更新数据库
        stmt = select(Candidate).where(
            func.cast(Candidate.id, String) == request.candidate_id
        )
        result_db = await db.execute(stmt)
        candidate = result_db.scalar_one()

        candidate.verification_score = result.verification_score
        # 注意: manual_override 字段需要添加到模型中

        await db.commit()

        logger.info(
            f"Verification triggered: candidate={request.candidate_id}, "
            f"score={result.verification_score:.3f}"
        )

        return VerificationTriggerResponse(
            success=True,
            message="验证完成",
            candidate_id=request.candidate_id,
            verification_score=result.verification_score,
            requires_manual_override=result.requires_manual_override,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Verification trigger failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": {
                    "code": "VERIFICATION_ERROR",
                    "message": f"验证失败: {str(e)}"
                }
            }
        )


# ==================== 2. 获取验证结果 ====================
@router.get(
    "/result/{candidate_id}",
    response_model=VerificationResultResponse,
    summary="获取验证结果",
    description="获取候选人的验证结果"
)
async def get_verification_result(
    candidate_id: str,
    user: Annotated[TokenPayload, Depends(get_current_user)],
    db: AsyncSession = Depends(),
):
    """
    获取候选人验证结果

    权限: 任何已登录用户

    返回:
    - 学历验证分数
    - 技能一致性分数
    - 综合验证分数
    - 是否需要人工复核
    - 验证详情
    """
    try:
        # 1. 获取候选人记录
        stmt = select(Candidate).where(
            func.cast(Candidate.id, String) == candidate_id
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

        # 2. 获取验证数据
        candidate_data = await get_candidate_data(db, candidate_id)

        # 3. 执行验证 (获取最新结果)
        service = get_verification_service()
        verification_result = await service.verify_candidate(
            candidate_id=candidate_id,
            candidate_data=candidate_data,
        )

        # 4. 构建响应
        result_data = VerificationResultData(
            candidate_id=candidate_id,
            education_score=verification_result.education_score,
            skill_consistency_score=verification_result.skill_consistency_score,
            verification_score=verification_result.verification_score,
            requires_manual_override=verification_result.requires_manual_override,
            is_verified=candidate.verification_score is not None
                and candidate.verification_score >= 0.3
                if candidate.verification_score is not None
                else False,
            verified_at=candidate.updated_at or datetime.utcnow(),
            details=VerificationDetails(
                education=EducationVerificationData(
                    verified_schools=[],
                    failed_schools=[],
                    details="学历验证详情",
                ),
                skill_consistency=SkillConsistencyData(
                    matched_skills=[],
                    unmatched_skills=[],
                    analysis="技能一致性详情",
                ),
                calculation={
                    "formula": "education_score * 0.4 + skill_consistency_score * 0.6",
                    "education_weight": 0.4,
                    "skill_weight": 0.6,
                },
            ),
        )

        return VerificationResultResponse(
            success=True,
            data=result_data,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get verification result failed: {e}")
        return VerificationResultResponse(
            success=False,
            error=str(e),
        )


# ==================== 3. 人工覆写分数 ====================
@router.post(
    "/override",
    response_model=VerificationOverrideResponse,
    summary="人工覆写分数",
    description="运营人员人工覆写验证分数"
)
async def override_verification_score(
    request: VerificationOverrideRequest,
    user: Annotated[TokenPayload, Depends(require_role(["admin", "operator"]))],
    db: AsyncSession = Depends(),
):
    """
    人工覆写验证分数

    权限: admin 或 operator 角色

    用于:
    - 复核低分候选人
    - 特殊情况人工认定
    """
    try:
        # 1. 获取候选人记录
        stmt = select(Candidate).where(
            func.cast(Candidate.id, String) == request.candidate_id
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

        # 2. 保存原分数
        original_score = candidate.verification_score or 0.0

        # 3. 覆写分数
        candidate.verification_score = request.override_score
        # 覆写后标记为已验证 (除非覆写成低于阈值)
        # 注意: 需要在 Candidate 模型中添加 manual_override 字段

        await db.commit()

        # 4. 构建覆写记录
        override_record = VerificationOverrideRecord(
            candidate_id=request.candidate_id,
            original_score=original_score,
            override_score=request.override_score,
            reason=request.reason,
            override_by=request.override_by,
            override_at=datetime.utcnow(),
        )

        logger.info(
            f"Verification score overridden: candidate={request.candidate_id}, "
            f"original={original_score:.3f}, override={request.override_score:.3f}, "
            f"by={request.override_by}"
        )

        return VerificationOverrideResponse(
            success=True,
            message="分数覆写成功",
            record=override_record,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Override verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": {
                    "code": "OVERRIDE_ERROR",
                    "message": f"覆写失败: {str(e)}"
                }
            }
        )


# ==================== 额外: 待复核列表 ====================
@router.get(
    "/pending",
    response_model=PendingOverrideListResponse,
    summary="待复核列表",
    description="获取需要人工复核的候选人列表"
)
async def list_pending_overrides(
    user: Annotated[TokenPayload, Depends(require_role(["admin", "operator"]))],
    db: AsyncSession = Depends(),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
):
    """
    获取待复核候选人列表

    权限: admin 或 operator 角色

    返回 verification_score < 0.3 的候选人列表
    """
    # TODO: 实现实际的数据库查询
    # 需要在 Candidate 模型中添加 manual_override 字段

    # 模拟数据
    items = [
        PendingOverrideItem(
            candidate_id="candidate-001",
            candidate_name="张三",
            verification_score=0.25,
            education_score=0.8,
            skill_consistency_score=0.15,
            submitted_at=datetime.utcnow(),
            profile_completeness=0.65,
        ),
        PendingOverrideItem(
            candidate_id="candidate-002",
            candidate_name="李四",
            verification_score=0.18,
            education_score=0.6,
            skill_consistency_score=0.12,
            submitted_at=datetime.utcnow(),
            profile_completeness=0.55,
        ),
    ]

    return PendingOverrideListResponse(
        success=True,
        total=len(items),
        items=items,
        page=page,
        page_size=page_size,
    )


# ==================== 导出 ====================
__all__ = ["router"]
