"""
HigherMatch™ Shared Auth Middleware
===================================

全局鉴权与权限控制 (RBAC) 中间件。

提供:
- JWT Token 解析与验证
- Refresh Token 轮换 (Rotation)
- 基于角色的访问控制 (RBAC)
- FastAPI Depends 依赖注入

所有微服务可直接引入使用。

版本: 1.0.0

使用示例:
    from shared.auth_middleware import (
        get_current_user,
        require_role,
        TokenPayload,
    )

    # 基础鉴权
    @app.get("/profile")
    async def get_profile(user: TokenPayload = Depends(get_current_user)):
        return {"user_id": user.sub, "role": user.role}

    # 角色权限控制
    @app.post("/jobs")
    async def create_job(
        job_data: JobCreate,
        user: TokenPayload = Depends(require_role(["employer", "admin"]))
    ):
        return {"created_by": user.sub}
"""

import logging
import secrets
from datetime import datetime, timedelta, timezone
from enum import Enum
from functools import wraps
from typing import Annotated, Callable, Optional

import redis.asyncio as redis
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel, Field

# ==================== 日志配置 ====================
logger = logging.getLogger(__name__)


# ==================== 错误码枚举 ====================
class AuthErrorCode(str, Enum):
    """认证错误码"""
    UNAUTHORIZED = "AUTH_2000"           # 未认证
    INVALID_TOKEN = "AUTH_2001"          # 无效 Token
    TOKEN_EXPIRED = "AUTH_2002"          # Token 过期
    FORBIDDEN = "AUTH_2003"              # 无权限
    INSUFFICIENT_PERMISSION = "AUTH_2004"  # 权限不足
    REFRESH_TOKEN_REVOKED = "AUTH_2005"  # Refresh Token 已撤销


# ==================== 配置常量 ====================
JWT_ALGORITHM = "HS256"  # 注意: 实际生产应使用 RS256
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7
TOKEN_ISSUER = "highermatch"
TOKEN_AUDIENCE = "highermatch-api"

# Refresh Token 存储配置
REFRESH_TOKEN_PREFIX = "refresh_token:"
REFRESH_TOKEN_TTL = REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600  # 秒


# ==================== Pydantic 模型 ====================


class TokenType(str, Enum):
    """Token 类型"""
    ACCESS = "access"
    REFRESH = "refresh"


class UserRole(str, Enum):
    """用户角色枚举"""
    ADMIN = "admin"
    EMPLOYER = "employer"
    CANDIDATE = "candidate"
    GUEST = "guest"


class TokenPayload(BaseModel):
    """
    Token 载荷

    从 JWT 中解码提取的用户信息。

    Attributes:
        sub: 用户 ID (Subject)
        role: 用户角色
        email: 用户邮箱 (可选)
        type: Token 类型
        exp: 过期时间 (Unix timestamp)
        iat: 签发时间 (Unix timestamp)
        jti: Token ID (用于 Refresh Token)
    """

    sub: str = Field(..., description="用户 ID")
    role: str = Field(..., description="用户角色")
    email: Optional[str] = Field(default=None, description="用户邮箱")
    type: str = Field(default=TokenType.ACCESS.value, description="Token 类型")
    exp: Optional[int] = Field(default=None, description="过期时间")
    iat: Optional[int] = Field(default=None, description="签发时间")
    jti: Optional[str] = Field(default=None, description="Token ID")


class AuthUser(BaseModel):
    """
    认证用户信息

    比 TokenPayload 包含更多用户详情。
    """

    user_id: str = Field(..., description="用户 ID")
    role: str = Field(..., description="用户角色")
    email: Optional[str] = Field(default=None, description="用户邮箱")
    is_verified: bool = Field(default=False, description="是否已验证")
    permissions: list[str] = Field(default_factory=list, description="权限列表")


class TokenPair(BaseModel):
    """Token 对"""

    access_token: str = Field(..., description="Access Token")
    refresh_token: str = Field(..., description="Refresh Token")
    token_type: str = Field(default="bearer", description="Token 类型")
    expires_in: int = Field(..., description="过期时间(秒)")


class TokenRefreshRequest(BaseModel):
    """Token 刷新请求"""

    refresh_token: str = Field(..., description="Refresh Token")


class TokenRefreshResponse(BaseModel):
    """Token 刷新响应"""

    success: bool = Field(default=True)
    data: TokenPair


class ErrorDetail(BaseModel):
    """错误详情"""

    code: str = Field(..., description="错误码")
    message: str = Field(..., description="错误消息")
    details: Optional[dict] = Field(default=None, description="附加详情")


class ErrorResponse(BaseModel):
    """错误响应"""

    success: bool = Field(default=False)
    error: ErrorDetail


# ==================== JWT 管理器 ====================


class JWTManager:
    """
    JWT 令牌管理器

    支持 Access Token 和 Refresh Token 的创建与验证。
    """

    def __init__(
        self,
        secret_key: str,
        algorithm: str = JWT_ALGORITHM,
        issuer: str = TOKEN_ISSUER,
        audience: str = TOKEN_AUDIENCE,
        access_token_expire_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES,
        refresh_token_expire_days: int = REFRESH_TOKEN_EXPIRE_DAYS,
    ) -> None:
        """
        初始化 JWT 管理器

        Args:
            secret_key: JWT 签名密钥
            algorithm: 加密算法
            issuer: Token 签发者
            audience: Token 受众
            access_token_expire_minutes: Access Token 过期时间(分钟)
            refresh_token_expire_days: Refresh Token 过期时间(天)
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.issuer = issuer
        self.audience = audience
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days

    def _get_current_time(self) -> datetime:
        """获取当前时间 (UTC)"""
        return datetime.now(timezone.utc)

    def create_access_token(
        self,
        subject: str,
        role: str,
        email: Optional[str] = None,
        additional_claims: Optional[dict] = None,
    ) -> str:
        """
        创建 Access Token

        Args:
            subject: 用户 ID
            role: 用户角色
            email: 用户邮箱 (可选)
            additional_claims: 额外的声明

        Returns:
            JWT 字符串
        """
        now = self._get_current_time()
        expire = now + timedelta(minutes=self.access_token_expire_minutes)

        payload = {
            "sub": subject,
            "role": role,
            "type": TokenType.ACCESS.value,
            "iss": self.issuer,
            "aud": self.audience,
            "iat": int(now.timestamp()),
            "exp": int(expire.timestamp()),
        }

        if email:
            payload["email"] = email

        if additional_claims:
            payload.update(additional_claims)

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(self, subject: str) -> tuple[str, str]:
        """
        创建 Refresh Token

        使用 Token Rotation 策略: 每次刷新都会生成新的 Refresh Token，
        旧的 Token 立即失效。这提供了更好的安全性。

        Args:
            subject: 用户 ID

        Returns:
            (refresh_token, token_id) 元组
        """
        now = self._get_current_time()
        expire = now + timedelta(days=self.refresh_token_expire_days)

        # 生成唯一的 Token ID (用于撤销)
        token_id = secrets.token_urlsafe(32)

        payload = {
            "sub": subject,
            "type": TokenType.REFRESH.value,
            "iss": self.issuer,
            "aud": self.audience,
            "iat": int(now.timestamp()),
            "exp": int(expire.timestamp()),
            "jti": token_id,  # Token ID 用于追踪和撤销
        }

        refresh_token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

        return refresh_token, token_id

    def create_token_pair(
        self,
        subject: str,
        role: str,
        email: Optional[str] = None,
    ) -> TokenPair:
        """
        创建 Token 对 (Access + Refresh)

        Args:
            subject: 用户 ID
            role: 用户角色
            email: 用户邮箱 (可选)

        Returns:
            TokenPair 对象
        """
        access_token = self.create_access_token(subject, role, email)
        refresh_token, _ = self.create_refresh_token(subject)

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=self.access_token_expire_minutes * 60,
        )

    def decode_token(self, token: str) -> dict:
        """
        解码 Token (不验证类型)

        Args:
            token: JWT 字符串

        Returns:
            Token 载荷字典
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                audience=self.audience,
                issuer=self.issuer,
            )
            return payload
        except JWTError as e:
            raise JWTError(f"Invalid token: {e}")

    def verify_access_token(self, token: str) -> TokenPayload:
        """
        验证 Access Token

        Args:
            token: JWT 字符串

        Returns:
            TokenPayload 对象

        Raises:
            JWTError: Token 无效或类型错误
        """
        payload = self.decode_token(token)

        if payload.get("type") != TokenType.ACCESS.value:
            raise JWTError("Invalid token type, expected access token")

        return TokenPayload(**payload)

    def verify_refresh_token(self, token: str) -> TokenPayload:
        """
        验证 Refresh Token

        Args:
            token: JWT 字符串

        Returns:
            TokenPayload 对象

        Raises:
            JWTError: Token 无效或类型错误
        """
        payload = self.decode_token(token)

        if payload.get("type") != TokenType.REFRESH.value:
            raise JWTError("Invalid token type, expected refresh token")

        return TokenPayload(**payload)


# ==================== 全局 JWT 管理器实例 ====================
_jwt_manager: Optional[JWTManager] = None
_redis_client: Optional[redis.Redis] = None


def init_auth(
    secret_key: str,
    redis_url: Optional[str] = None,
    algorithm: str = JWT_ALGORITHM,
) -> JWTManager:
    """
    初始化认证模块

    Args:
        secret_key: JWT 签名密钥
        redis_url: Redis 连接 URL (用于 Refresh Token 存储)
        algorithm: JWT 算法

    Returns:
        JWTManager 实例
    """
    global _jwt_manager, _redis_client

    _jwt_manager = JWTManager(
        secret_key=secret_key,
        algorithm=algorithm,
    )

    if redis_url:
        _redis_client = redis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True,
        )

    logger.info("Auth module initialized")

    return _jwt_manager


def get_jwt_manager() -> JWTManager:
    """
    获取 JWT 管理器实例

    Returns:
        JWTManager 实例

    Raises:
        RuntimeError: 如果未初始化
    """
    if _jwt_manager is None:
        raise RuntimeError(
            "Auth module not initialized. Call init_auth() first."
        )
    return _jwt_manager


def get_redis_client() -> Optional[redis.Redis]:
    """获取 Redis 客户端"""
    return _redis_client


# ==================== Token 存储 (Redis) ====================


class RefreshTokenStore:
    """
    Refresh Token 存储

    使用 Redis 存储已发放的 Refresh Token，支持 Token Rotation 和撤销。
    """

    def __init__(self, redis_client: redis.Redis) -> None:
        """
        初始化 Token 存储

        Args:
            redis_client: Redis 客户端
        """
        self.redis = redis_client

    def _get_key(self, token_id: str) -> str:
        """获取 Redis 键名"""
        return f"{REFRESH_TOKEN_PREFIX}{token_id}"

    async def store(
        self,
        token_id: str,
        user_id: str,
        ttl: int = REFRESH_TOKEN_TTL,
    ) -> None:
        """
        存储 Refresh Token

        Args:
            token_id: Token ID
            user_id: 用户 ID
            ttl: 过期时间(秒)
        """
        key = self._get_key(token_id)
        await self.redis.setex(key, ttl, user_id)
        logger.debug(f"Refresh token stored: {token_id[:8]}... for user {user_id}")

    async def verify(self, token_id: str) -> Optional[str]:
        """
        验证 Refresh Token 是否有效

        Args:
            token_id: Token ID

        Returns:
            用户 ID 或 None (Token 无效或已过期)
        """
        key = self._get_key(token_id)
        user_id = await self.redis.get(key)
        return user_id

    async def revoke(self, token_id: str) -> bool:
        """
        撤销 Refresh Token

        Args:
            token_id: Token ID

        Returns:
            True: 撤销成功
            False: Token 不存在
        """
        key = self._get_key(token_id)
        result = await self.redis.delete(key)
        logger.debug(f"Refresh token revoked: {token_id[:8]}...")
        return result > 0

    async def revoke_all_for_user(self, user_id: str) -> int:
        """
        撤销用户的所有 Refresh Token

        Args:
            user_id: 用户 ID

        Returns:
            撤销的 Token 数量
        """
        pattern = f"{REFRESH_TOKEN_PREFIX}*"
        count = 0

        async for key in self.redis.scan_iter(match=pattern):
            value = await self.redis.get(key)
            if value == user_id:
                await self.redis.delete(key)
                count += 1

        logger.info(f"Revoked {count} refresh tokens for user {user_id}")
        return count

    async def cleanup_expired(self) -> None:
        """清理过期 Token (Redis 自动过期，无需手动清理)"""
        pass


def get_token_store() -> Optional[RefreshTokenStore]:
    """
    获取 Token 存储实例

    Returns:
        RefreshTokenStore 实例或 None (Redis 未配置)
    """
    client = get_redis_client()
    if client is None:
        return None
    return RefreshTokenStore(client)


# ==================== 认证依赖 ====================

# HTTP Bearer 安全方案
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[
        Optional[HTTPAuthorizationCredentials],
        Depends(bearer_scheme)
    ] = None,
) -> TokenPayload:
    """
    获取当前用户 (基础鉴权)

    验证 Access Token 的有效性，返回 Token 载荷。
    只要 Token 有效即可通过，适用于需要用户身份但不需要特定角色的场景。

    Args:
        credentials: HTTP Bearer 凭证

    Returns:
        TokenPayload 对象

    Raises:
        HTTPException: Token 无效或缺失
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "success": False,
                "error": {
                    "code": AuthErrorCode.UNAUTHORIZED.value,
                    "message": "缺少认证凭证，请登录后重试"
                }
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        jwt_manager = get_jwt_manager()
        payload = jwt_manager.verify_access_token(token)
        return payload

    except JWTError as e:
        logger.warning(f"Token verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "success": False,
                "error": {
                    "code": AuthErrorCode.INVALID_TOKEN.value,
                    "message": "Token 无效或已过期"
                }
            },
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_role(
    allowed_roles: list[str],
    require_all: bool = False,
) -> Callable:
    """
    角色权限依赖工厂函数

    创建高阶依赖注入函数，验证用户角色是否在允许的列表中。

    Args:
        allowed_roles: 允许的角色列表
        require_all: 是否需要拥有所有角色 (默认 False，只需一个匹配)

    Returns:
        依赖注入函数

    Raises:
        HTTPException: 角色验证失败

    使用示例:
        # 只需要一个角色匹配
        @app.post("/jobs")
        async def create_job(
            job: JobCreate,
            user: TokenPayload = Depends(require_role(["employer", "admin"]))
        ):
            pass

        # 需要所有角色匹配
        @app.delete("/users")
        async def delete_user(
            user: TokenPayload = Depends(require_role(["admin"], require_all=True))
        ):
            pass
    """
    def role_checker(
        current_user: Annotated[TokenPayload, Depends(get_current_user)]
    ) -> TokenPayload:
        """
        角色验证依赖

        Args:
            current_user: 当前用户 (由 get_current_user 提供)

        Returns:
            TokenPayload 如果验证通过

        Raises:
            HTTPException: 角色验证失败
        """
        user_role = current_user.role

        if require_all:
            # 需要拥有所有指定角色
            if user_role not in allowed_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "success": False,
                        "error": {
                            "code": AuthErrorCode.FORBIDDEN.value,
                            "message": f"此操作需要以下角色之一: {', '.join(allowed_roles)}"
                        }
                    },
                )
        else:
            # 只需要一个角色匹配
            if user_role not in allowed_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "success": False,
                        "error": {
                            "code": AuthErrorCode.INSUFFICIENT_PERMISSION.value,
                            "message": f"权限不足，需要角色: {', '.join(allowed_roles)}"
                        }
                    },
                )

        return current_user

    return role_checker


def require_permission(
    permission: str,
) -> Callable:
    """
    权限检查依赖工厂函数

    验证用户是否拥有指定权限。

    Args:
        permission: 权限标识符

    Returns:
        依赖注入函数

    使用示例:
        @app.delete("/jobs/{job_id}")
        async def delete_job(
            job_id: int,
            user: TokenPayload = Depends(require_permission("job:delete"))
        ):
            pass
    """
    def permission_checker(
        current_user: Annotated[TokenPayload, Depends(get_current_user)]
    ) -> TokenPayload:
        """
        权限验证依赖

        Note: 实际权限验证需要从数据库或缓存获取用户权限列表。
        这里仅作基础框架演示。
        """
        # TODO: 从用户信息中获取权限列表
        # permissions = await get_user_permissions(current_user.sub)

        # 示例: 管理员拥有所有权限
        if current_user.role == UserRole.ADMIN.value:
            return current_user

        # TODO: 实现实际的权限验证逻辑
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "success": False,
                "error": {
                    "code": AuthErrorCode.INSUFFICIENT_PERMISSION.value,
                    "message": f"缺少权限: {permission}"
                }
            },
        )

    return permission_checker


# ==================== 便捷类型别名 ====================

# 基础鉴权依赖
AuthenticatedUser = Annotated[TokenPayload, Depends(get_current_user)]

# 角色鉴权依赖 (可变参数)
def EmployerOnly() -> TokenPayload:
    """仅雇主"""
    return require_role([UserRole.EMPLOYER.value, UserRole.ADMIN.value])


def CandidateOnly() -> TokenPayload:
    """仅候选人"""
    return require_role([UserRole.CANDIDATE.value])


def AdminOnly() -> TokenPayload:
    """仅管理员"""
    return require_role([UserRole.ADMIN.value])


def EmployerOrAdmin() -> TokenPayload:
    """雇主或管理员"""
    return require_role([UserRole.EMPLOYER.value, UserRole.ADMIN.value])


# ==================== Token 刷新服务 ====================


class TokenRefreshService:
    """
    Token 刷新服务

    实现 Refresh Token Rotation 策略:
    1. 验证旧的 Refresh Token
    2. 检查 Redis 中 Token 是否有效
    3. 撤销旧 Token
    4. 生成新的 Token 对
    """

    def __init__(self) -> None:
        self.jwt_manager = get_jwt_manager()
        self.token_store = get_token_store()

    async def refresh(
        self,
        refresh_token: str,
    ) -> TokenRefreshResponse:
        """
        刷新 Token

        Args:
            refresh_token: Refresh Token

        Returns:
            新的 Token 对

        Raises:
            HTTPException: Refresh Token 无效或已撤销
        """
        try:
            # 1. 验证 Refresh Token 格式
            payload = self.jwt_manager.verify_refresh_token(refresh_token)
            token_id = payload.jti
            user_id = payload.sub

            if not token_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={
                        "success": False,
                        "error": {
                            "code": AuthErrorCode.INVALID_TOKEN.value,
                            "message": "无效的 Refresh Token"
                        }
                    },
                )

            # 2. 检查 Redis 中 Token 是否存在
            if self.token_store:
                stored_user_id = await self.token_store.verify(token_id)
                if stored_user_id is None:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail={
                            "success": False,
                            "error": {
                                "code": AuthErrorCode.REFRESH_TOKEN_REVOKED.value,
                                "message": "Refresh Token 已失效，请重新登录"
                            }
                        },
                    )

                # 3. 撤销旧 Token (实现 Rotation)
                await self.token_store.revoke(token_id)
                logger.info(f"Old refresh token revoked for user {user_id}")

            # 4. 生成新的 Token 对
            new_token_pair = self.jwt_manager.create_token_pair(
                subject=user_id,
                role=payload.role,
                email=payload.email,
            )

            # 5. 存储新的 Refresh Token
            if self.token_store:
                new_payload = self.jwt_manager.verify_refresh_token(
                    new_token_pair.refresh_token
                )
                await self.token_store.store(
                    token_id=new_payload.jti,
                    user_id=user_id,
                )

            logger.info(f"Token refreshed for user {user_id}")

            return TokenRefreshResponse(
                success=True,
                data=new_token_pair,
            )

        except JWTError as e:
            logger.warning(f"Token refresh failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "success": False,
                    "error": {
                        "code": AuthErrorCode.INVALID_TOKEN.value,
                        "message": "Refresh Token 无效或已过期"
                    }
                },
            )


# ==================== 辅助函数 ====================


def create_tokens_for_user(
    user_id: str,
    role: str,
    email: Optional[str] = None,
) -> TokenPair:
    """
    为用户创建 Token 对

    Args:
        user_id: 用户 ID
        role: 用户角色
        email: 用户邮箱 (可选)

    Returns:
        TokenPair 对象
    """
    jwt_manager = get_jwt_manager()
    return jwt_manager.create_token_pair(user_id, role, email)


async def revoke_user_tokens(user_id: str) -> int:
    """
    撤销用户的所有 Token

    Args:
        user_id: 用户 ID

    Returns:
        撤销的 Token 数量
    """
    token_store = get_token_store()
    if token_store:
        return await token_store.revoke_all_for_user(user_id)
    return 0


# ==================== 导出 ====================
__all__ = [
    # 枚举
    "AuthErrorCode",
    "TokenType",
    "UserRole",

    # Pydantic 模型
    "TokenPayload",
    "AuthUser",
    "TokenPair",
    "TokenRefreshRequest",
    "TokenRefreshResponse",
    "ErrorDetail",
    "ErrorResponse",

    # JWT 管理
    "JWTManager",
    "init_auth",
    "get_jwt_manager",
    "get_redis_client",

    # Token 存储
    "RefreshTokenStore",
    "get_token_store",

    # 认证依赖
    "get_current_user",
    "require_role",
    "require_permission",

    # 类型别名
    "AuthenticatedUser",
    "EmployerOnly",
    "CandidateOnly",
    "AdminOnly",
    "EmployerOrAdmin",

    # Token 服务
    "TokenRefreshService",

    # 辅助函数
    "create_tokens_for_user",
    "revoke_user_tokens",
]
