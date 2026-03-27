"""
Authentication routes for the user service.
"""

import logging
from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import verify_access_token
from app.database import get_db as database_get_db
from app.redis_client import get_redis as redis_get_redis
from app.schemas.auth import (
    AccountLockedResponse,
    ErrorResponse,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    UserMeResponse,
)
from app.services.auth_service import (
    AccountLockedError,
    AuthError,
    AuthService,
    DuplicateError,
    InvalidCredentialsError,
    InvalidTokenError,
)


logger = logging.getLogger(__name__)

MSG_MISSING_CREDENTIALS = "\u7f3a\u5c11\u8ba4\u8bc1\u51ed\u8bc1"
MSG_INVALID_TOKEN = "Token \u65e0\u6548\u6216\u5df2\u8fc7\u671f"
MSG_INVALID_TOKEN_TYPE = "Token \u65e0\u6548"
MSG_INTERNAL_ERROR = "\u670d\u52a1\u5668\u5185\u90e8\u9519\u8bef\uff0c\u8bf7\u7a0d\u540e\u91cd\u8bd5"


router = APIRouter(
    prefix="/api/v1/auth",
    tags=["Authentication"],
)

security = HTTPBearer(auto_error=False)


async def get_redis():
    return await redis_get_redis()


async def get_db():
    async for db in database_get_db():
        yield db


async def get_auth_service(
    db=Depends(get_db),
    redis=Depends(get_redis),
) -> AuthService:
    return AuthService(db, redis)


async def get_current_user_id(
    credentials: Annotated[
        Optional[HTTPAuthorizationCredentials],
        Depends(security),
    ] = None,
) -> str:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "success": False,
                "error": {
                    "code": "AUTH_2000",
                    "message": MSG_MISSING_CREDENTIALS,
                },
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = verify_access_token(credentials.credentials)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "success": False,
                    "error": {
                        "code": "AUTH_2001",
                        "message": MSG_INVALID_TOKEN_TYPE,
                    },
                },
                headers={"WWW-Authenticate": "Bearer"},
            )
        return str(user_id)
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Token verification failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "success": False,
                "error": {
                    "code": "AUTH_2001",
                    "message": MSG_INVALID_TOKEN,
                },
            },
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def get_current_user(
    user_id: Annotated[str, Depends(get_current_user_id)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserMeResponse:
    try:
        return await auth_service.get_current_user(user_id)
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=exc.to_error_response().model_dump(),
        ) from exc
    except AuthError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.to_error_response().model_dump(),
        ) from exc


@router.post(
    "/register",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {"model": ErrorResponse, "description": "duplicate"},
        422: {"model": ErrorResponse, "description": "validation error"},
    },
)
async def register(
    request: RegisterRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> dict:
    try:
        response = await auth_service.register(request)
        return {
            "success": True,
            "data": {
                "user_id": response.user_id,
                "role": response.role.value,
                "token": {
                    "access_token": response.token.access_token,
                    "refresh_token": response.token.refresh_token,
                    "token_type": response.token.token_type,
                    "expires_in": response.token.expires_in,
                },
            },
        }
    except DuplicateError as exc:
        logger.warning("Registration duplicate error: %s", exc.message)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=exc.to_error_response().model_dump(),
        ) from exc
    except AuthError as exc:
        logger.warning("Registration failed: %s", exc.message)
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.to_error_response().model_dump(),
        ) from exc
    except Exception as exc:
        logger.error("Registration error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": {
                    "code": "SYS_1000",
                    "message": MSG_INTERNAL_ERROR,
                },
            },
        ) from exc


@router.post(
    "/login",
    response_model=dict,
    responses={
        401: {"model": ErrorResponse, "description": "invalid credentials"},
        429: {"model": AccountLockedResponse, "description": "locked"},
    },
)
async def login(
    request: LoginRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> dict:
    try:
        response = await auth_service.login(request)
        return {
            "success": True,
            "data": {
                "access_token": response.access_token,
                "refresh_token": response.refresh_token,
                "token_type": response.token_type,
                "user_id": response.user_id,
                "role": response.role.value,
            },
        }
    except AccountLockedError as exc:
        logger.warning("Login blocked: retry_after=%s", exc.retry_after)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "success": False,
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                },
                "locked_until": exc.locked_until.isoformat(),
                "retry_after": exc.retry_after,
            },
            headers={"Retry-After": str(exc.retry_after)},
        ) from exc
    except InvalidCredentialsError as exc:
        logger.warning("Login failed: invalid credentials")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "success": False,
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                },
            },
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except AuthError as exc:
        logger.warning("Login failed: %s", exc.message)
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.to_error_response().model_dump(),
        ) from exc
    except Exception as exc:
        logger.error("Login error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": {
                    "code": "SYS_1000",
                    "message": MSG_INTERNAL_ERROR,
                },
            },
        ) from exc


@router.post(
    "/refresh",
    response_model=dict,
    responses={401: {"model": ErrorResponse, "description": "invalid refresh token"}},
)
async def refresh_token(
    request: RefreshTokenRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> dict:
    try:
        response = await auth_service.refresh_token(request.refresh_token)
        return {
            "success": True,
            "data": {
                "access_token": response.access_token,
                "refresh_token": response.refresh_token,
                "token_type": response.token_type,
                "expires_in": response.expires_in,
            },
        }
    except InvalidTokenError as exc:
        logger.warning("Refresh failed: invalid token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=exc.to_error_response().model_dump(),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except AuthError as exc:
        logger.warning("Refresh failed: %s", exc.message)
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.to_error_response().model_dump(),
        ) from exc
    except Exception as exc:
        logger.error("Refresh error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": {
                    "code": "SYS_1000",
                    "message": MSG_INTERNAL_ERROR,
                },
            },
        ) from exc


@router.get(
    "/me",
    response_model=dict,
    responses={401: {"model": ErrorResponse, "description": "unauthorized"}},
)
async def get_me(
    current_user: Annotated[UserMeResponse, Depends(get_current_user)],
) -> dict:
    return current_user.model_dump()


@router.get("/health")
async def auth_health_check() -> dict:
    redis_status = "unknown"
    try:
        redis = await get_redis()
        if redis:
            await redis.ping()
            redis_status = "healthy"
        else:
            redis_status = "not_configured"
    except Exception:
        redis_status = "unhealthy"

    return {
        "status": "healthy" if redis_status != "unhealthy" else "degraded",
        "service": "auth",
        "redis": redis_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


__all__ = [
    "router",
    "get_auth_service",
    "get_current_user",
    "get_current_user_id",
    "get_db",
    "get_redis",
]
