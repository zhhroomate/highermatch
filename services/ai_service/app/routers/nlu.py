"""
NLU routes for the AI service.
"""

import logging
import os
from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel, Field

from app.services.nlu_service import NLUParseResponse, NLUService, create_nlu_service


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/nlu",
    tags=["NLU"],
)

security = HTTPBearer(auto_error=False)


def _get_jwt_secret_key() -> str:
    return os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production")


def _get_jwt_algorithm() -> str:
    return os.getenv("JWT_ALGORITHM", "HS256")


class TokenPayload(BaseModel):
    sub: str = ""
    role: str = ""
    email: Optional[str] = None


async def get_current_user(
    credentials: Annotated[
        Optional[HTTPAuthorizationCredentials],
        Depends(security),
    ] = None,
) -> TokenPayload:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "success": False,
                "error": {
                    "code": "AUTH_2000",
                    "message": "缺少认证凭证",
                },
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            _get_jwt_secret_key(),
            algorithms=[_get_jwt_algorithm()],
        )
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "success": False,
                    "error": {
                        "code": "AUTH_2001",
                        "message": "无效的 Token 类型",
                    },
                },
                headers={"WWW-Authenticate": "Bearer"},
            )

        return TokenPayload(
            sub=str(payload.get("sub", "")),
            role=payload.get("role", ""),
            email=payload.get("email"),
        )
    except HTTPException:
        raise
    except JWTError as exc:
        logger.warning("Token verification failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "success": False,
                "error": {
                    "code": "AUTH_2001",
                    "message": "Token 无效或已过期",
                },
            },
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def require_role(allowed_roles: list[str]):
    async def role_checker(
        current_user: Annotated[TokenPayload, Depends(get_current_user)],
    ) -> TokenPayload:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "success": False,
                    "error": {
                        "code": "AUTH_2003",
                        "message": f"权限不足，需要角色 {', '.join(allowed_roles)}",
                    },
                },
            )
        return current_user

    return role_checker


AuthenticatedUser = Annotated[TokenPayload, Depends(get_current_user)]


class NLUParseRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="自然语言职位描述",
        examples=["3年Python工程师，成都"],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "text": "3年Python工程师，成都",
            }
        }
    }


class NLUParseSuccessResponse(BaseModel):
    success: bool = Field(default=True)
    data: NLUParseResponse
    cached: bool = Field(default=False, description="是否来自缓存")
    processing_time_ms: int = Field(default=0, description="处理耗时(毫秒)")


def get_nlu_service() -> NLUService:
    return create_nlu_service()


@router.post(
    "/parse",
    response_model=dict,
    responses={
        200: {"description": "解析成功"},
        400: {"description": "输入无效"},
        401: {"description": "未认证"},
        422: {"description": "解析失败"},
        500: {"description": "服务错误"},
    },
)
async def parse_job_requirement(
    request: NLUParseRequest,
    current_user: AuthenticatedUser,
    nlu_service: Annotated[NLUService, Depends(get_nlu_service)],
) -> dict:
    start_time = datetime.now(timezone.utc)

    try:
        result = await nlu_service.parse(text=request.text)
        processing_time = int(
            (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        )

        response = {
            "success": True,
            "data": {
                "job_requirement_draft": {
                    "job_title": result.job_requirement_draft.job_title,
                    "skills": result.job_requirement_draft.skills,
                    "years_exp_min": result.job_requirement_draft.years_exp_min,
                    "years_exp_max": result.job_requirement_draft.years_exp_max,
                    "location": result.job_requirement_draft.location,
                    "salary_min": result.job_requirement_draft.salary_min,
                    "salary_max": result.job_requirement_draft.salary_max,
                    "industry": result.job_requirement_draft.industry,
                },
                "confidence_scores": {
                    "job_title": result.confidence_scores.job_title,
                    "skills": result.confidence_scores.skills,
                    "years_exp": result.confidence_scores.years_exp,
                    "location": result.confidence_scores.location,
                    "salary": result.confidence_scores.salary,
                    "industry": result.confidence_scores.industry,
                },
                "clarification_questions": [
                    {
                        "field": question.field,
                        "question": question.question,
                        "reason": question.reason,
                    }
                    for question in result.clarification_questions
                ],
            },
            "cached": False,
            "processing_time_ms": processing_time,
        }

        logger.info(
            "NLU parse success: user=%s, title=%s, time=%sms",
            current_user.sub,
            result.job_requirement_draft.job_title,
            processing_time,
        )
        return response
    except ValueError as exc:
        logger.warning("NLU parse validation error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "error": {
                    "code": "NLU_1001",
                    "message": str(exc),
                },
            },
        ) from exc
    except Exception as exc:
        logger.error("NLU parse error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "success": False,
                "error": {
                    "code": "NLU_1002",
                    "message": f"解析失败: {exc}",
                },
            },
        ) from exc


@router.get("/health")
async def nlu_health_check() -> dict:
    from app.services.nlu_service import get_cache

    redis_status = "unknown"
    try:
        cache = await get_cache()
        redis_status = "healthy" if cache.is_connected() else "disconnected"
    except Exception:
        redis_status = "unhealthy"

    return {
        "status": "healthy",
        "service": "nlu",
        "redis": redis_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


__all__ = [
    "router",
    "NLUParseRequest",
    "get_current_user",
    "require_role",
    "TokenPayload",
]
