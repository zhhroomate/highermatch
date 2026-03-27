"""
HigherMatch™ Shared Core - Exception Module
============================================

统一异常处理和错误响应格式定义。

版本: 1.0.0

错误码规范:
    1xxx - 通用错误
    2xxx - 认证授权错误
    3xxx - 业务逻辑错误
    4xxx - 资源相关错误
    5xxx - 外部服务错误

使用示例:
    from shared.core.exceptions import BusinessException, ErrorResponse

    raise BusinessException(
        code="JOB_001",
        message="职位不存在",
        details={"job_id": 123}
    )
"""

import logging
from typing import Any, Optional
from enum import Enum

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# ==================== 日志配置 ====================
logger = logging.getLogger(__name__)


# ==================== 错误码枚举 ====================
class ErrorCode(str, Enum):
    """
    HigherMatch 错误码枚举

    遵循 RESTful API 最佳实践，使用有意义的错误码。
    """

    # ========== 1xxx 通用错误 ==========
    INTERNAL_ERROR = "SYS_1000"          # 内部系统错误
    INVALID_PARAMETER = "SYS_1001"       # 参数错误
    VALIDATION_ERROR = "SYS_1002"       # 数据验证错误
    RATE_LIMIT_EXCEEDED = "SYS_1003"    # 请求频率超限
    SERVICE_UNAVAILABLE = "SYS_1004"     # 服务不可用

    # ========== 2xxx 认证授权错误 ==========
    UNAUTHORIZED = "AUTH_2000"           # 未认证
    INVALID_TOKEN = "AUTH_2001"          # 无效令牌
    TOKEN_EXPIRED = "AUTH_2002"          # 令牌过期
    FORBIDDEN = "AUTH_2003"              # 无权限
    INSUFFICIENT_PERMISSION = "AUTH_2004"  # 权限不足

    # ========== 3xxx 业务逻辑错误 ==========
    BUSINESS_ERROR = "BIZ_3000"          # 通用业务错误
    INVALID_OPERATION = "BIZ_3001"       # 无效操作
    DUPLICATE_ENTRY = "BIZ_3002"         # 重复记录
    DATA_CONFLICT = "BIZ_3003"           # 数据冲突

    # ========== 4xxx 资源相关错误 ==========
    NOT_FOUND = "RES_4000"               # 资源不存在
    EMPLOYER_NOT_FOUND = "RES_4001"      # 雇主不存在
    CANDIDATE_NOT_FOUND = "RES_4002"     # 候选人不存在
    JOB_NOT_FOUND = "RES_4003"           # 职位不存在
    MATCH_NOT_FOUND = "RES_4004"         # 匹配记录不存在
    INVOICE_NOT_FOUND = "RES_4005"       # 账单不存在

    # ========== 5xxx 外部服务错误 ==========
    DATABASE_ERROR = "EXT_5000"          # 数据库错误
    REDIS_ERROR = "EXT_5001"             # Redis 错误
    KAFKA_ERROR = "EXT_5002"             # Kafka 错误
    AI_SERVICE_ERROR = "EXT_5003"        # AI 服务错误
    EXTERNAL_API_ERROR = "EXT_5004"       # 外部 API 错误


# ==================== Pydantic 错误模型 ====================
class ErrorDetail(BaseModel):
    """
    错误详情模型

    Attributes:
        code: 错误码，如 "JOB_001"
        message: 用户友好的错误消息
        details: 附加的错误详情 (可选)
        field: 验证错误对应的字段名 (可选)
    """

    code: str = Field(
        ...,
        description="错误码",
        examples=["JOB_001"]
    )
    message: str = Field(
        ...,
        description="错误消息",
        max_length=500,
        examples=["职位不存在"]
    )
    details: Optional[dict[str, Any]] = Field(
        default=None,
        description="错误详情",
        examples=[{"job_id": 123}]
    )
    field: Optional[str] = Field(
        default=None,
        description="验证错误字段名",
        examples=["email"]
    )


class ErrorResponse(BaseModel):
    """
    统一错误响应格式

    HigherMatch 所有 API 错误响应均使用此格式。

    Response Format:
        {
            "success": false,
            "error": {
                "code": "JOB_001",
                "message": "职位不存在",
                "details": {"job_id": 123}
            }
        }
    """

    success: bool = Field(
        default=False,
        description="请求是否成功，错误时始终为 false"
    )
    error: ErrorDetail = Field(
        ...,
        description="错误详情"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": {
                    "code": "JOB_001",
                    "message": "职位不存在",
                    "details": {"job_id": 123}
                }
            }
        }


class SuccessResponse(BaseModel):
    """
    统一成功响应格式

    Attributes:
        success: 是否成功，始终为 true
        data: 响应数据
        message: 附加消息 (可选)
    """

    success: bool = Field(
        default=True,
        description="请求是否成功"
    )
    data: Optional[Any] = Field(
        default=None,
        description="响应数据"
    )
    message: Optional[str] = Field(
        default=None,
        description="附加消息",
        max_length=200
    )

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {"id": 1, "name": "John"},
                "message": "操作成功"
            }
        }


# ==================== 自定义异常类 ====================
class HigherMatchException(Exception):
    """
    HigherMatch 异常基类

    所有自定义异常应继承此类。
    """

    def __init__(
        self,
        code: str,
        message: str,
        details: Optional[dict[str, Any]] = None,
        status_code: int = status.HTTP_400_BAD_REQUEST,
    ) -> None:
        """
        初始化异常

        Args:
            code: 错误码
            message: 错误消息
            details: 附加详情
            status_code: HTTP 状态码
        """
        self.code = code
        self.message = message
        self.details = details
        self.status_code = status_code
        super().__init__(message)

    def to_error_response(self) -> ErrorResponse:
        """转换为错误响应模型"""
        return ErrorResponse(
            success=False,
            error=ErrorDetail(
                code=self.code,
                message=self.message,
                details=self.details,
            )
        )

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


class BusinessException(HigherMatchException):
    """
    业务逻辑异常

    用于处理业务规则验证失败等场景。
    """

    def __init__(
        self,
        code: str = ErrorCode.BUSINESS_ERROR,
        message: str = "业务处理失败",
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            details=details,
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class NotFoundException(HigherMatchException):
    """
    资源不存在异常

    用于处理查找资源失败等场景。
    """

    def __init__(
        self,
        code: str = ErrorCode.NOT_FOUND,
        message: str = "资源不存在",
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            details=details,
            status_code=status.HTTP_404_NOT_FOUND,
        )


class UnauthorizedException(HigherMatchException):
    """
    未认证异常

    用于处理登录验证失败等场景。
    """

    def __init__(
        self,
        code: str = ErrorCode.UNAUTHORIZED,
        message: str = "未认证",
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            details=details,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class ForbiddenException(HigherMatchException):
    """
    无权限异常

    用于处理权限验证失败等场景。
    """

    def __init__(
        self,
        code: str = ErrorCode.FORBIDDEN,
        message: str = "无权限访问",
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            details=details,
            status_code=status.HTTP_403_FORBIDDEN,
        )


class ValidationException(HigherMatchException):
    """
    数据验证异常

    用于处理请求参数验证失败等场景。
    """

    def __init__(
        self,
        message: str = "数据验证失败",
        details: Optional[dict[str, Any]] = None,
        field: Optional[str] = None,
    ) -> None:
        error_details = details or {}
        if field:
            error_details["field"] = field

        super().__init__(
            code=ErrorCode.VALIDATION_ERROR,
            message=message,
            details=error_details,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
        self.field = field


class DuplicateEntryException(HigherMatchException):
    """
    重复记录异常

    用于处理唯一约束冲突等场景。
    """

    def __init__(
        self,
        message: str = "记录已存在",
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            code=ErrorCode.DUPLICATE_ENTRY,
            message=message,
            details=details,
            status_code=status.HTTP_409_CONFLICT,
        )


class ExternalServiceException(HigherMatchException):
    """
    外部服务异常

    用于处理数据库、Redis、Kafka 等外部服务调用失败。
    """

    def __init__(
        self,
        code: str = ErrorCode.SERVICE_UNAVAILABLE,
        message: str = "外部服务调用失败",
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            details=details,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


# ==================== 异常处理器 ====================
async def highermatch_exception_handler(
    request: Request,
    exc: HigherMatchException,
) -> JSONResponse:
    """
    HigherMatch 自定义异常处理器

    将所有 HigherMatchException 转换为统一的 JSON 响应。
    """
    logger.warning(
        f"HigherMatchException: [{exc.code}] {exc.message}",
        extra={"details": exc.details, "path": request.url.path}
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_error_response().model_dump(),
    )


async def generic_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """
    通用异常处理器

    处理所有未被特定处理器捕获的异常。
    """
    logger.error(
        f"Unhandled exception: {exc}",
        exc_info=True,
        extra={"path": request.url.path}
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            success=False,
            error=ErrorDetail(
                code=ErrorCode.INTERNAL_ERROR,
                message="服务器内部错误，请稍后重试",
            )
        ).model_dump(),
    )


# ==================== 异常注册辅助函数 ====================
def register_exception_handlers(app: FastAPI) -> None:
    """
    向 FastAPI 应用注册异常处理器

    Args:
        app: FastAPI 应用实例
    """
    app.add_exception_handler(HigherMatchException, highermatch_exception_handler)
    # 注意: 不直接注册 generic_exception_handler
    # 保留给中间件或特殊处理


# ==================== 便捷异常抛出函数 ====================
def raise_not_found(
    resource: str,
    identifier: Any,
) -> None:
    """抛出资源不存在异常"""
    raise NotFoundException(
        code=ErrorCode.NOT_FOUND,
        message=f"{resource}不存在",
        details={resource.lower() + "_id": identifier}
    )


def raise_duplicate(
    resource: str,
    field: str,
    value: Any,
) -> None:
    """抛出重复记录异常"""
    raise DuplicateEntryException(
        message=f"{resource}已存在",
        details={field: value}
    )


def raise_unauthorized(
    message: str = "请先登录",
) -> None:
    """抛出未认证异常"""
    raise UnauthorizedException(message=message)


def raise_forbidden(
    message: str = "无权限访问此资源",
) -> None:
    """抛出无权限异常"""
    raise ForbiddenException(message=message)


# ==================== 导出 ====================
__all__ = [
    # 错误码枚举
    "ErrorCode",

    # 响应模型
    "ErrorDetail",
    "ErrorResponse",
    "SuccessResponse",

    # 异常类
    "HigherMatchException",
    "BusinessException",
    "NotFoundException",
    "UnauthorizedException",
    "ForbiddenException",
    "ValidationException",
    "DuplicateEntryException",
    "ExternalServiceException",

    # 异常处理器
    "highermatch_exception_handler",
    "generic_exception_handler",
    "register_exception_handlers",

    # 便捷函数
    "raise_not_found",
    "raise_duplicate",
    "raise_unauthorized",
    "raise_forbidden",
]
