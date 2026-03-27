"""
HigherMatch™ User Service - Auth Schemas
========================================

Pydantic 数据模型，用于认证接口的请求和响应验证。

版本: 1.0.0
"""

import re
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


# ==================== 枚举定义 ====================


class UserRole(str, Enum):
    """用户角色枚举"""
    EMPLOYER = "employer"
    CANDIDATE = "candidate"


class TokenType(str, Enum):
    """Token 类型枚举"""
    ACCESS = "access"
    REFRESH = "refresh"


# ==================== 请求模型 ====================


class RegisterRequest(BaseModel):
    """
    用户注册请求

    Attributes:
        role: 用户角色 (employer/candidate)
        email: 邮箱地址
        phone: 手机号
        password: 密码 (8-32字符，包含字母和数字)
        company_name: 公司名称 (雇主必填)
        company_size: 公司规模 (雇主可选)
        name: 姓名 (候选人可选)
    """

    role: UserRole = Field(
        ...,
        description="用户角色",
        examples=["employer", "candidate"]
    )
    email: EmailStr = Field(
        ...,
        description="邮箱地址",
        examples=["user@example.com"]
    )
    phone: str = Field(
        ...,
        description="手机号",
        min_length=11,
        max_length=20,
        examples=["13800138000"]
    )
    password: str = Field(
        ...,
        description="密码 (8-32字符)",
        min_length=8,
        max_length=32
    )
    company_name: Optional[str] = Field(
        default=None,
        description="公司名称 (雇主必填)",
        max_length=300,
        examples=["HigherMatch Tech Inc."]
    )
    company_size: Optional[str] = Field(
        default=None,
        description="公司规模",
        examples=["51-200"]
    )
    name: Optional[str] = Field(
        default=None,
        description="姓名 (候选人)",
        max_length=200,
        examples=["张三"]
    )

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """验证手机号格式"""
        # 移除空格和连字符
        phone = re.sub(r"[\s\-]", "", v)

        # 验证手机号格式 (中国手机号)
        if re.match(r"^1[3-9]\d{9}$", phone):
            return phone

        # 国际手机号格式
        if re.match(r"^\+[1-9]\d{6,14}$", phone):
            return phone

        raise ValueError("Invalid phone number format")

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """验证密码强度"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")

        if len(v) > 32:
            raise ValueError("Password must be at most 32 characters")

        # 必须包含字母和数字
        if not re.search(r"[A-Za-z]", v):
            raise ValueError("Password must contain at least one letter")

        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")

        return v

    @field_validator("company_name")
    @classmethod
    def validate_company_name(cls, v: Optional[str], info) -> Optional[str]:
        """验证公司名称 (雇主必填)"""
        # 如果 role 是 employer，company_name 必填
        if info.data.get("role") == UserRole.EMPLOYER and not v:
            raise ValueError("Company name is required for employers")
        return v


class LoginRequest(BaseModel):
    """
    用户登录请求

    Attributes:
        email: 邮箱地址
        password: 密码
    """

    email: EmailStr = Field(
        ...,
        description="邮箱地址",
        examples=["user@example.com"]
    )
    password: str = Field(
        ...,
        description="密码",
        min_length=1
    )


class RefreshTokenRequest(BaseModel):
    """
    刷新 Token 请求

    Attributes:
        refresh_token: Refresh Token
    """

    refresh_token: str = Field(
        ...,
        description="Refresh Token"
    )


# ==================== 响应模型 ====================


class TokenResponse(BaseModel):
    """
    Token 响应

    Attributes:
        access_token: Access Token
        refresh_token: Refresh Token
        token_type: Token 类型
        expires_in: 过期时间(秒)
    """

    access_token: str = Field(
        ...,
        description="Access Token (JWT)"
    )
    refresh_token: str = Field(
        ...,
        description="Refresh Token (JWT)"
    )
    token_type: str = Field(
        default="bearer",
        description="Token 类型"
    )
    expires_in: int = Field(
        ...,
        description="Access Token 过期时间(秒)"
    )


class RegisterResponse(BaseModel):
    """
    注册响应

    Attributes:
        user_id: 用户 ID
        role: 用户角色
        token: 登录 Token
    """

    user_id: str = Field(
        ...,
        description="用户 ID (UUID)"
    )
    role: UserRole = Field(
        ...,
        description="用户角色"
    )
    token: TokenResponse = Field(
        ...,
        description="登录 Token"
    )


class LoginResponse(BaseModel):
    """
    登录响应

    Attributes:
        access_token: Access Token
        refresh_token: Refresh Token
        user_id: 用户 ID
        role: 用户角色
    """

    access_token: str = Field(
        ...,
        description="Access Token (JWT)"
    )
    refresh_token: str = Field(
        ...,
        description="Refresh Token (JWT)"
    )
    token_type: str = Field(
        default="bearer",
        description="Token 类型"
    )
    user_id: str = Field(
        ...,
        description="用户 ID (UUID)"
    )
    role: UserRole = Field(
        ...,
        description="用户角色"
    )


class RefreshTokenResponse(BaseModel):
    """
    刷新 Token 响应

    Attributes:
        access_token: 新的 Access Token
        refresh_token: 新的 Refresh Token
        token_type: Token 类型
        expires_in: 过期时间(秒)
    """

    access_token: str = Field(
        ...,
        description="新的 Access Token"
    )
    refresh_token: str = Field(
        ...,
        description="新的 Refresh Token"
    )
    token_type: str = Field(
        default="bearer",
        description="Token 类型"
    )
    expires_in: int = Field(
        ...,
        description="过期时间(秒)"
    )


class UserInfo(BaseModel):
    """
    用户信息

    Attributes:
        id: 用户 ID
        email: 邮箱
        phone: 手机号 (加密)
        role: 角色
        name: 姓名/公司名
        is_verified: 是否已验证
        created_at: 创建时间
    """

    id: str = Field(..., description="用户 ID")
    email: str = Field(..., description="邮箱")
    phone: Optional[str] = Field(default=None, description="加密手机号")
    role: UserRole = Field(..., description="角色")
    name: Optional[str] = Field(default=None, description="姓名/公司名")
    is_verified: bool = Field(default=False, description="是否验证")
    created_at: datetime = Field(..., description="创建时间")

    class Config:
        from_attributes = True


class UserMeResponse(BaseModel):
    """
    获取当前用户信息响应

    Attributes:
        success: 是否成功
        data: 用户信息
    """

    success: bool = Field(default=True)
    data: UserInfo


# ==================== 统一响应模型 ====================


class SuccessResponse(BaseModel):
    """
    统一成功响应

    Attributes:
        success: 是否成功 (固定 true)
        data: 响应数据
        message: 附加消息 (可选)
    """

    success: bool = Field(default=True)
    data: Any = Field(..., description="响应数据")
    message: Optional[str] = Field(default=None, description="附加消息")


class ErrorDetail(BaseModel):
    """
    错误详情

    Attributes:
        code: 错误码
        message: 错误消息
        details: 附加详情 (可选)
    """

    code: str = Field(..., description="错误码")
    message: str = Field(..., description="错误消息")
    details: Optional[dict[str, Any]] = Field(default=None, description="附加详情")


class ErrorResponse(BaseModel):
    """
    统一错误响应

    Attributes:
        success: 是否成功 (固定 false)
        error: 错误详情
    """

    success: bool = Field(default=False)
    error: ErrorDetail


# ==================== 锁定响应模型 ====================


class AccountLockedResponse(BaseModel):
    """
    账号锁定响应

    Attributes:
        success: 是否成功 (固定 false)
        error: 错误详情
        locked_until: 锁定截止时间
        retry_after: 重试等待秒数
    """

    success: bool = Field(default=False)
    error: ErrorDetail
    locked_until: datetime = Field(..., description="锁定截止时间")
    retry_after: int = Field(..., description="等待秒数")


# ==================== 导出 ====================
__all__ = [
    # 枚举
    "UserRole",
    "TokenType",

    # 请求模型
    "RegisterRequest",
    "LoginRequest",
    "RefreshTokenRequest",

    # 响应模型
    "TokenResponse",
    "RegisterResponse",
    "LoginResponse",
    "RefreshTokenResponse",
    "UserInfo",
    "UserMeResponse",

    # 统一响应模型
    "SuccessResponse",
    "ErrorDetail",
    "ErrorResponse",
    "AccountLockedResponse",
]
