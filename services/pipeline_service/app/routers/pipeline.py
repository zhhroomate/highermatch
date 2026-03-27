"""
HigherMatch™ Pipeline Service - Pipeline Router
================================================

招聘管道管理 API 路由。

提供 RESTful API:
- GET /api/v1/pipeline/:job_id - 获取岗位招聘管道
- POST /api/v1/pipeline/move - 移动候选人到不同阶段

RBAC:
- 所有接口需要 employer 角色 JWT
- 雇主只能操作自己岗位下的候选人

版本: 1.0.0
"""

import logging
from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.pipeline_service import PipelineService
from app.services.websocket import get_websocket_manager
from app.schemas.pipeline import (
    PipelineStage,
    PipelineMoveRequest,
    PipelineResponse,
    PipelineMoveResponse,
    ErrorResponse,
    PipelineError,
)


# ==================== 日志配置 ====================
logger = logging.getLogger(__name__)

# ==================== 路由配置 ====================
router = APIRouter(
    prefix="/api/v1/pipeline",
    tags=["Pipeline"],
)

# ==================== 安全依赖 ====================
security = HTTPBearer(auto_error=False)

# JWT 配置 (应该从环境变量读取)
JWT_SECRET_KEY = "your-secret-key-change-in-production"
JWT_ALGORITHM = "HS256"


class TokenPayload(BaseModel):
    """Token 载荷"""
    sub: str = ""          # 用户 ID (employer_id)
    role: str = ""          # 用户角色
    email: Optional[str] = None


async def get_current_user(
    credentials: Annotated[
        Optional[HTTPAuthorizationCredentials],
        Depends(security)
    ] = None,
) -> TokenPayload:
    """
    获取当前用户

    从 Authorization Header 中提取 Bearer Token 并验证。

    Args:
        credentials: HTTP Bearer 凭证

    Returns:
        TokenPayload

    Raises:
        HTTPException: Token 无效或缺失
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "success": False,
                "error": {
                    "code": "AUTH_2000",
                    "message": "缺少认证凭证，请登录后重试"
                }
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM]
        )

        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "success": False,
                    "error": {
                        "code": "AUTH_2001",
                        "message": "无效的 Token 类型"
                    }
                },
                headers={"WWW-Authenticate": "Bearer"},
            )

        return TokenPayload(
            sub=payload.get("sub", ""),
            role=payload.get("role", ""),
            email=payload.get("email"),
        )

    except JWTError as e:
        logger.warning(f"Token verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "success": False,
                "error": {
                    "code": "AUTH_2001",
                    "message": "Token 无效或已过期"
                }
            },
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_role(allowed_roles: list[str]):
    """
    角色权限依赖工厂

    Args:
        allowed_roles: 允许的角色列表

    Returns:
        依赖函数
    """
    async def role_checker(
        current_user: Annotated[TokenPayload, Depends(get_current_user)]
    ) -> TokenPayload:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "success": False,
                    "error": {
                        "code": "AUTH_2003",
                        "message": f"权限不足，需要角色: {', '.join(allowed_roles)}"
                    }
                },
            )
        return current_user
    return role_checker


# 类型别名
CurrentEmployer = Annotated[TokenPayload, Depends(require_role(["employer", "admin"]))]


# ==================== 数据库依赖 ====================

async def get_db():
    """获取数据库会话"""
    from app.main import get_db as main_get_db
    async for session in main_get_db():
        yield session


async def get_pipeline_service(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> PipelineService:
    """获取管道服务"""
    return PipelineService(db)


# ==================== 辅助函数 ====================

def serialize_datetime(dt: Optional[datetime]) -> Optional[str]:
    """序列化日期时间"""
    if dt is None:
        return None
    return dt.isoformat()


def serialize_pipeline_response(response: PipelineResponse) -> dict:
    """序列化管道响应"""
    return {
        "job_id": response.job_id,
        "job_title": response.job_title,
        "columns": [
            {
                "stage": col.stage.value,
                "cards": [
                    {
                        "match_id": card.match_id,
                        "candidate": {
                            "candidate_id": card.candidate.candidate_id,
                            "name": card.candidate.name,
                            "avatar_url": card.candidate.avatar_url,
                            "current_city": card.candidate.current_city,
                            "current_province": card.candidate.current_province,
                            "years_exp": card.candidate.years_exp,
                            "skills": card.candidate.skills,
                            "profile_completeness": card.candidate.profile_completeness,
                            "verification_score": card.candidate.verification_score,
                        },
                        "overall_score": card.overall_score,
                        "score_breakdown": {
                            "skill_match": card.score_breakdown.skill_match,
                            "experience_match": card.score_breakdown.experience_match,
                            "location_match": card.score_breakdown.location_match,
                            "salary_match": card.score_breakdown.salary_match,
                            "culture_match": card.score_breakdown.culture_match,
                        },
                        "ai_recommendation": card.ai_recommendation,
                        "match_reasons": card.match_reasons,
                        "pipeline_stage": card.pipeline_stage.value,
                        "timeline": card.timeline,
                        "created_at": serialize_datetime(card.created_at),
                        "updated_at": serialize_datetime(card.updated_at),
                    }
                    for card in col.cards
                ],
                "count": col.count,
            }
            for col in response.columns
        ],
        "total_candidates": response.total_candidates,
    }


# ==================== 路由定义 ====================


@router.get(
    "/{job_id}",
    response_model=dict,
    responses={
        401: {"model": ErrorResponse, "description": "未认证"},
        403: {"model": ErrorResponse, "description": "无权访问"},
        404: {"model": ErrorResponse, "description": "岗位不存在"},
    },
    summary="获取招聘管道",
    description="获取指定岗位的招聘管道，按 pipeline_stage 分组返回候选人信息。",
)
async def get_pipeline(
    job_id: str,
    current_user: CurrentEmployer,
    pipeline_service: Annotated[PipelineService, Depends(get_pipeline_service)],
) -> dict:
    """
    获取招聘管道

    返回岗位下所有候选人，按管道阶段分组。

    - 阶段: ai_recommended, invited, interviewing, offer, onboarded, rejected
    - 每个候选人卡片包含脱敏后的简要信息
    - 包含匹配分数和 AI 推荐理由

    **权限**: 仅限发布该岗位的雇主访问。
    """
    try:
        response = await pipeline_service.get_pipeline(
            job_id=job_id,
            employer_id=current_user.sub,
        )

        return {
            "success": True,
            "data": serialize_pipeline_response(response),
        }

    except ValueError as e:
        error_message = str(e)
        if "不存在" in error_message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "success": False,
                    "error": {
                        "code": "PIPELINE_1001",
                        "message": error_message
                    }
                },
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "error": {
                        "code": "PIPELINE_1002",
                        "message": error_message
                    }
                },
            )

    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "success": False,
                "error": {
                    "code": "AUTH_2003",
                    "message": str(e)
                }
            },
        )

    except Exception as e:
        logger.error(f"Get pipeline error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": {
                    "code": "SYS_1000",
                    "message": "服务器内部错误，请稍后重试"
                }
            },
        )


@router.post(
    "/move",
    response_model=dict,
    responses={
        401: {"model": ErrorResponse, "description": "未认证"},
        403: {"model": ErrorResponse, "description": "无权操作"},
        404: {"model": ErrorResponse, "description": "匹配记录不存在"},
        422: {"model": ErrorResponse, "description": "阶段不匹配"},
    },
    summary="移动候选人",
    description="将候选人从一个管道阶段移动到另一个阶段。触发 WebSocket 广播。",
)
async def move_candidate(
    request: PipelineMoveRequest,
    current_user: CurrentEmployer,
    pipeline_service: Annotated[PipelineService, Depends(get_pipeline_service)],
) -> dict:
    """
    移动候选人到不同阶段

    用于前端 Kanban 拖拽操作。

    - **match_id**: 匹配记录 ID
    - **from_stage**: 原阶段
    - **to_stage**: 目标阶段

    **权限**: 仅限该岗位的雇主操作。

    **副作用**:
    - 更新候选人的 pipeline_stage
    - 追加时间线记录
    - 触发 WebSocket 广播 (占位实现)
    """
    try:
        response = await pipeline_service.move_candidate(
            match_id=request.match_id,
            from_stage=request.from_stage,
            to_stage=request.to_stage,
            employer_id=current_user.sub,
        )

        # 获取岗位 ID 用于 WebSocket 广播
        # 需要从 pipeline_service 获取 job_id
        job_id = None
        try:
            from app.services.pipeline_service import PipelineRepository
            import uuid as uuid_module
            repo = PipelineRepository(pipeline_service.db)
            match = await repo.get_match_result_with_details(
                uuid_module.UUID(request.match_id)
            )
            if match:
                job_id = str(match.job_id)
        except Exception as e:
            logger.warning(f"Failed to get job_id for WebSocket broadcast: {e}")

        # 触发 WebSocket 广播
        if job_id:
            ws_manager = get_websocket_manager()
            await ws_manager.broadcast_pipeline_update(
                job_id=job_id,
                match_id=request.match_id,
                to_stage=request.to_stage.value,
                operator_id=current_user.sub,
            )
            logger.info(f"WebSocket broadcast sent for match {request.match_id} to room job_{job_id}")

        return {
            "success": True,
            "data": {
                "match_id": response.match_id,
                "from_stage": response.from_stage.value,
                "to_stage": response.to_stage.value,
                "updated_at": serialize_datetime(response.updated_at),
                "message": response.message,
            }
        }

    except ValueError as e:
        error_message = str(e)
        if "不存在" in error_message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "success": False,
                    "error": {
                        "code": "PIPELINE_1003",
                        "message": error_message
                    }
                },
            )
        else:
            # 阶段不匹配等验证错误
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "success": False,
                    "error": {
                        "code": "PIPELINE_1004",
                        "message": error_message
                    }
                },
            )

    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "success": False,
                "error": {
                    "code": "AUTH_2003",
                    "message": str(e)
                }
            },
        )

    except Exception as e:
        logger.error(f"Move candidate error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": {
                    "code": "SYS_1000",
                    "message": "服务器内部错误，请稍后重试"
                }
            },
        )


# ==================== 导出 ====================
__all__ = [
    "router",
    "get_current_user",
    "require_role",
    "TokenPayload",
]
