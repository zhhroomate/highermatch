"""
HigherMatch™ Job Service - Jobs Router
======================================

岗位管理 API 路由。

提供 RESTful API:
- POST /api/v1/jobs - 创建岗位
- GET /api/v1/jobs - 岗位列表 (cursor 分页)
- GET /api/v1/jobs/:job_id - 岗位详情
- PUT /api/v1/jobs/:job_id - 更新岗位
- POST /api/v1/jobs/:job_id/publish - 发布岗位

RBAC:
- 所有接口需要 employer 角色 JWT
- 雇主只能操作自己的岗位

版本: 1.0.0
"""

import logging
from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.job_service import JobService
from app.schemas.job import (
    JobCreateRequest,
    JobUpdateRequest,
    JobPublishRequest,
    JobListQuery,
    JobCreateResponse,
    JobResponse,
    JobPublishResponse,
    JobListResponse,
    JobStatus,
    ErrorResponse,
    ErrorDetail,
)

# ==================== 日志配置 ====================
logger = logging.getLogger(__name__)

# ==================== 路由配置 ====================
router = APIRouter(
    prefix="/api/v1/jobs",
    tags=["Jobs"],
)

# ==================== 安全依赖 ====================
security = HTTPBearer(auto_error=False)

# JWT 配置 (应该从环境变量读取)
JWT_SECRET_KEY = "your-secret-key-change-in-production"
JWT_ALGORITHM = "HS256"


class TokenPayload(BaseModel):
    """Token 载荷"""
    sub: str
    role: str
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
            sub=payload.get("sub"),
            role=payload.get("role"),
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


# ==================== 服务依赖 ====================

async def get_db():
    """获取数据库会话"""
    from app.main import get_db as main_get_db
    async for session in main_get_db():
        yield session


async def get_job_service(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> JobService:
    """获取岗位服务"""
    return JobService(db)


# ==================== 路由定义 ====================


@router.post(
    "",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"model": ErrorResponse, "description": "未认证"},
        403: {"model": ErrorResponse, "description": "权限不足"},
        422: {"model": ErrorResponse, "description": "参数验证失败"},
    },
    summary="创建岗位",
    description="创建新岗位，创建后状态为草稿 (draft)。异步发送 Kafka 消息到 topic=job.created",
)
async def create_job(
    request: JobCreateRequest,
    current_user: CurrentEmployer,
    job_service: Annotated[JobService, Depends(get_job_service)],
) -> dict:
    """
    创建岗位

    - **job_title**: 岗位名称
    - **requirement**: 岗位要求 (技能、工作年限、地点、薪资等)
    - **jd_html**: 富文本职位描述 (可选)
    - **is_urgent**: 是否急招 (可选)

    创建成功后异步发送 Kafka 消息到 `job.created` topic。
    """
    try:
        response = await job_service.create_job(
            employer_id=current_user.sub,
            data=request,
        )

        return {
            "success": True,
            "data": {
                "job_id": response.job_id,
                "status": response.status.value,
                "created_at": response.created_at.isoformat(),
            }
        }

    except ValueError as e:
        logger.warning(f"Create job failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "error": {
                    "code": "JOB_1001",
                    "message": str(e)
                }
            },
        )

    except Exception as e:
        logger.error(f"Create job error: {e}", exc_info=True)
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


@router.get(
    "",
    response_model=dict,
    responses={
        401: {"model": ErrorResponse, "description": "未认证"},
        403: {"model": ErrorResponse, "description": "权限不足"},
    },
    summary="获取岗位列表",
    description="获取当前用户的岗位列表，支持 cursor 分页和状态筛选。",
)
async def list_jobs(
    current_user: CurrentEmployer,
    job_service: Annotated[JobService, Depends(get_job_service)],
    cursor: Annotated[Optional[str], Query(description="分页游标")] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="每页数量")] = 20,
    status_filter: Annotated[
        Optional[str],
        Query(alias="status", description="按状态筛选: draft, published, closed, archived")
    ] = None,
) -> dict:
    """
    获取岗位列表

    - **cursor**: 分页游标 (base64 编码)
    - **limit**: 每页数量 (默认 20，最大 100)
    - **status**: 按状态筛选 (可选)

    返回岗位列表和下一页游标。
    """
    try:
        # 验证状态参数
        job_status = None
        if status_filter:
            try:
                job_status = JobStatus(status_filter).value
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "success": False,
                        "error": {
                            "code": "JOB_1002",
                            "message": f"无效的状态值: {status_filter}"
                        }
                    },
                )

        response = await job_service.list_jobs(
            employer_id=current_user.sub,
            status=job_status,
            cursor=cursor,
            limit=limit,
        )

        return {
            "success": True,
            "data": {
                "items": [
                    {
                        **item.model_dump(mode="json"),
                        "created_at": item.created_at.isoformat() if item.created_at else None,
                        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
                        "published_at": item.published_at.isoformat() if item.published_at else None,
                        "expires_at": item.expires_at.isoformat() if item.expires_at else None,
                    }
                    for item in response.items
                ],
                "next_cursor": response.next_cursor,
            }
        }

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"List jobs error: {e}", exc_info=True)
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


@router.get(
    "/{job_id}",
    response_model=dict,
    responses={
        401: {"model": ErrorResponse, "description": "未认证"},
        403: {"model": ErrorResponse, "description": "无权访问"},
        404: {"model": ErrorResponse, "description": "岗位不存在"},
    },
    summary="获取岗位详情",
    description="获取指定岗位的详细信息，只能查看自己公司的岗位。",
)
async def get_job(
    job_id: str,
    current_user: CurrentEmployer,
    job_service: Annotated[JobService, Depends(get_job_service)],
) -> dict:
    """
    获取岗位详情

    只能查看自己公司的岗位。

    返回完整的岗位信息，包括要求、薪资、状态等。
    """
    try:
        response = await job_service.get_job(
            job_id=job_id,
            employer_id=current_user.sub,
        )

        return {
            "success": True,
            "data": {
                **response.model_dump(mode="json"),
                "created_at": response.created_at.isoformat() if response.created_at else None,
                "updated_at": response.updated_at.isoformat() if response.updated_at else None,
                "published_at": response.published_at.isoformat() if response.published_at else None,
                "expires_at": response.expires_at.isoformat() if response.expires_at else None,
            }
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "error": {
                    "code": "JOB_1003",
                    "message": str(e)
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
        logger.error(f"Get job error: {e}", exc_info=True)
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


@router.put(
    "/{job_id}",
    response_model=dict,
    responses={
        401: {"model": ErrorResponse, "description": "未认证"},
        403: {"model": ErrorResponse, "description": "无权修改"},
        404: {"model": ErrorResponse, "description": "岗位不存在"},
        422: {"model": ErrorResponse, "description": "状态不允许修改"},
    },
    summary="更新岗位",
    description="更新岗位信息，仅在 status=draft 时允许修改。",
)
async def update_job(
    job_id: str,
    request: JobUpdateRequest,
    current_user: CurrentEmployer,
    job_service: Annotated[JobService, Depends(get_job_service)],
) -> dict:
    """
    更新岗位

    仅在 status=draft (草稿) 时允许修改。
    发布后的岗位不能修改基本信息，只能关闭或归档。

    支持部分更新，只传入需要修改的字段。
    """
    try:
        response = await job_service.update_job(
            job_id=job_id,
            employer_id=current_user.sub,
            data=request,
        )

        return {
            "success": True,
            "data": {
                **response.model_dump(mode="json"),
                "created_at": response.created_at.isoformat() if response.created_at else None,
                "updated_at": response.updated_at.isoformat() if response.updated_at else None,
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
                        "code": "JOB_1003",
                        "message": error_message
                    }
                },
            )
        elif "草稿状态" in error_message or "修改" in error_message:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "success": False,
                    "error": {
                        "code": "JOB_1004",
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
                        "code": "JOB_1001",
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
        logger.error(f"Update job error: {e}", exc_info=True)
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
    "/{job_id}/publish",
    response_model=dict,
    responses={
        401: {"model": ErrorResponse, "description": "未认证"},
        403: {"model": ErrorResponse, "description": "无权发布"},
        404: {"model": ErrorResponse, "description": "岗位不存在"},
        422: {"model": ErrorResponse, "description": "状态不允许发布"},
    },
    summary="发布岗位",
    description="将岗位状态从 draft 改为 published。发送 Kafka 消息到 topic=job.published",
)
async def publish_job(
    job_id: str,
    current_user: CurrentEmployer,
    job_service: Annotated[JobService, Depends(get_job_service)],
    request: JobPublishRequest = None,
) -> dict:
    """
    发布岗位

    将岗位从草稿状态发布为已发布状态。
    发布后岗位将显示在公开列表中。

    成功发送 Kafka 消息到 `job.published` topic。

    - **expires_at**: 岗位过期时间 (可选，默认 30 天)
    """
    try:
        expires_at = request.expires_at if request else None

        response = await job_service.publish_job(
            job_id=job_id,
            employer_id=current_user.sub,
            expires_at=expires_at,
        )

        return {
            "success": True,
            "data": {
                "job_id": response.job_id,
                "status": response.status.value,
                "published_at": response.published_at.isoformat() if response.published_at else None,
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
                        "code": "JOB_1003",
                        "message": error_message
                    }
                },
            )
        elif "草稿状态" in error_message or "发布" in error_message:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "success": False,
                    "error": {
                        "code": "JOB_1005",
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
                        "code": "JOB_1001",
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
        logger.error(f"Publish job error: {e}", exc_info=True)
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
