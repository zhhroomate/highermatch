"""
HigherMatch™ User Service - Security Module
==========================================

安全工具模块，包含:
- JWT 令牌管理 (python-jose)
- 密码哈希 (bcrypt)
- 手机号 AES-256 加密
- Redis 登录限制

版本: 1.0.0
"""

import base64
import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import bcrypt
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from jose import JWTError, jwt
from passlib.context import CryptContext

# ==================== 配置常量 ====================

# JWT 配置
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# AES-256 配置
AES_KEY_LENGTH = 32  # 256 bits
AES_IV_LENGTH = 12   # 96 bits for GCM
AES_TAG_LENGTH = 16   # 128 bits

# 登录限制配置
LOGIN_MAX_ATTEMPTS = 5
LOGIN_LOCKOUT_MINUTES = 10
LOGIN_ATTEMPT_WINDOW = 600  # 10分钟窗口(秒)


# ==================== 密码哈希 ====================

class PasswordHasher:
    """
    密码哈希工具类

    使用 bcrypt 算法进行密码哈希和验证。
    """

    def __init__(self, rounds: int = 12) -> None:
        """
        初始化密码哈希器

        Args:
            rounds: bcrypt 轮数，默认 12
        """
        self.rounds = rounds
        self._context = CryptContext(
            schemes=["bcrypt"],
            deprecated="auto",
            bcrypt__rounds=rounds
        )

    def hash(self, password: str) -> str:
        """
        对密码进行哈希

        Args:
            password: 明文密码

        Returns:
            哈希后的密码字符串
        """
        password_bytes = password.encode("utf-8")
        salt = bcrypt.gensalt(rounds=self.rounds)
        hashed = bcrypt.hashpw(password_bytes, salt)
        return hashed.decode("utf-8")

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        """
        验证密码是否正确

        Args:
            plain_password: 明文密码
            hashed_password: 哈希后的密码

        Returns:
            True: 密码正确
            False: 密码错误
        """
        try:
            password_bytes = plain_password.encode("utf-8")
            hashed_bytes = hashed_password.encode("utf-8")
            return bcrypt.checkpw(password_bytes, hashed_bytes)
        except Exception:
            return False

    def needs_rehash(self, hashed_password: str) -> bool:
        """
        检查是否需要重新哈希

        Args:
            hashed_password: 哈希后的密码

        Returns:
            True: 需要重新哈希
            False: 不需要
        """
        try:
            return bcrypt.checkpw(
                b"dummy",
                hashed_password.encode("utf-8")
            )
        except Exception:
            return True


# 全局密码哈希器实例
password_hasher = PasswordHasher(rounds=12)


def hash_password(password: str) -> str:
    """快捷函数：哈希密码"""
    return password_hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """快捷函数：验证密码"""
    return password_hasher.verify(plain_password, hashed_password)


# ==================== AES-256 加密 ====================


class PhoneEncryptor:
    """
    手机号加密工具类

    使用 AES-256-GCM 进行加密，保证机密性和完整性。
    """

    def __init__(self, key: Optional[bytes] = None) -> None:
        """
        初始化加密器

        Args:
            key: 256位密钥，如果为 None 则从环境变量获取
        """
        if key is None:
            key_str = os.getenv("PHONE_ENCRYPTION_KEY", "")
            if not key_str:
                # 生成随机密钥 (仅用于开发)
                key = secrets.token_bytes(AES_KEY_LENGTH)
            else:
                # 从 base64 编码的环境变量解码
                key = base64.b64decode(key_str)

        if len(key) != AES_KEY_LENGTH:
            raise ValueError(f"Key must be {AES_KEY_LENGTH} bytes")

        self._key = key
        self._aesgcm = AESGCM(key)

    def encrypt(self, phone: str) -> str:
        """
        加密手机号

        Args:
            phone: 明文手机号

        Returns:
            Base64 编码的密文 (IV + 密文 + Tag)
        """
        # 生成随机 IV
        iv = os.urandom(AES_IV_LENGTH)

        # 加密
        plaintext = phone.encode("utf-8")
        ciphertext = self._aesgcm.encrypt(iv, plaintext, None)

        # 组合: IV + 密文
        combined = iv + ciphertext

        # 返回 Base64 编码
        return base64.b64encode(combined).decode("utf-8")

    def decrypt(self, encrypted_phone: str) -> str:
        """
        解密手机号

        Args:
            encrypted_phone: Base64 编码的密文

        Returns:
            明文手机号
        """
        # Base64 解码
        combined = base64.b64decode(encrypted_phone)

        # 分离 IV 和密文
        iv = combined[:AES_IV_LENGTH]
        ciphertext = combined[AES_IV_LENGTH:]

        # 解密
        plaintext = self._aesgcm.decrypt(iv, ciphertext, None)

        return plaintext.decode("utf-8")

    def hash(self, phone: str) -> str:
        """
        生成手机号哈希 (用于索引和查询)

        Args:
            phone: 明文手机号

        Returns:
            SHA-256 哈希值
        """
        # 添加盐值
        salt = os.getenv("PHONE_HASH_SALT", "highermatch_salt")
        salted = f"{salt}:{phone}".encode("utf-8")
        return hashlib.sha256(salted).hexdigest()


# 全局加密器实例
_phone_encryptor: Optional[PhoneEncryptor] = None


def get_phone_encryptor() -> PhoneEncryptor:
    """获取手机号加密器单例"""
    global _phone_encryptor
    if _phone_encryptor is None:
        _phone_encryptor = PhoneEncryptor()
    return _phone_encryptor


def encrypt_phone(phone: str) -> str:
    """快捷函数：加密手机号"""
    return get_phone_encryptor().encrypt(phone)


def decrypt_phone(encrypted_phone: str) -> str:
    """快捷函数：解密手机号"""
    return get_phone_encryptor().decrypt(encrypted_phone)


def hash_phone(phone: str) -> str:
    """快捷函数：哈希手机号"""
    return get_phone_encryptor().hash(phone)


# ==================== JWT 令牌管理 ====================


class JWTManager:
    """
    JWT 令牌管理器

    支持 Access Token 和 Refresh Token。
    """

    def __init__(
        self,
        secret_key: str,
        algorithm: str = JWT_ALGORITHM,
        access_token_expire_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES,
        refresh_token_expire_days: int = REFRESH_TOKEN_EXPIRE_DAYS,
    ) -> None:
        """
        初始化 JWT 管理器

        Args:
            secret_key: JWT 签名密钥
            algorithm: 加密算法，默认 HS256
            access_token_expire_minutes: Access Token 过期时间(分钟)
            refresh_token_expire_days: Refresh Token 过期时间(天)
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days

    def create_access_token(
        self,
        subject: str,
        role: str,
        additional_claims: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        创建 Access Token

        Args:
            subject: Token 主体 (用户 ID)
            role: 用户角色
            additional_claims: 额外的声明

        Returns:
            JWT 字符串
        """
        now = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=self.access_token_expire_minutes)

        payload = {
            "sub": subject,
            "role": role,
            "type": "access",
            "iat": now,
            "exp": expire,
        }

        if additional_claims:
            payload.update(additional_claims)

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(
        self,
        subject: str,
        additional_claims: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        创建 Refresh Token

        Args:
            subject: Token 主体 (用户 ID)
            additional_claims: 额外的声明

        Returns:
            JWT 字符串
        """
        now = datetime.now(timezone.utc)
        expire = now + timedelta(days=self.refresh_token_expire_days)

        # 生成 Token ID 用于撤销
        token_id = secrets.token_urlsafe(16)

        payload = {
            "sub": subject,
            "type": "refresh",
            "jti": token_id,
            "iat": now,
            "exp": expire,
        }

        if additional_claims:
            payload.update(additional_claims)

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def decode_token(self, token: str) -> dict[str, Any]:
        """
        解码 JWT Token

        Args:
            token: JWT 字符串

        Returns:
            Token 载荷字典

        Raises:
            JWTError: Token 无效或过期
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            return payload
        except JWTError as e:
            raise JWTError(f"Invalid token: {e}")

    def verify_access_token(self, token: str) -> dict[str, Any]:
        """
        验证 Access Token

        Args:
            token: JWT 字符串

        Returns:
            Token 载荷字典

        Raises:
            JWTError: Token 无效或类型错误
        """
        payload = self.decode_token(token)

        if payload.get("type") != "access":
            raise JWTError("Invalid token type, expected access token")

        return payload

    def verify_refresh_token(self, token: str) -> dict[str, Any]:
        """
        验证 Refresh Token

        Args:
            token: JWT 字符串

        Returns:
            Token 载荷字典

        Raises:
            JWTError: Token 无效或类型错误
        """
        payload = self.decode_token(token)

        if payload.get("type") != "refresh":
            raise JWTError("Invalid token type, expected refresh token")

        return payload

    def get_token_subject(self, token: str) -> str:
        """
        获取 Token 的主体 (用户 ID)

        Args:
            token: JWT 字符串

        Returns:
            用户 ID
        """
        payload = self.decode_token(token)
        return payload.get("sub", "")


# JWT 管理器实例 (需要从配置初始化)
_jwt_manager: Optional[JWTManager] = None


def init_jwt_manager(
    secret_key: str,
    algorithm: str = JWT_ALGORITHM,
    access_token_expire_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES,
    refresh_token_expire_days: int = REFRESH_TOKEN_EXPIRE_DAYS,
) -> JWTManager:
    """
    初始化 JWT 管理器

    Args:
        secret_key: JWT 签名密钥
        algorithm: 加密算法
        access_token_expire_minutes: Access Token 过期时间
        refresh_token_expire_days: Refresh Token 过期时间

    Returns:
        JWTManager 实例
    """
    global _jwt_manager
    _jwt_manager = JWTManager(
        secret_key=secret_key,
        algorithm=algorithm,
        access_token_expire_minutes=access_token_expire_minutes,
        refresh_token_expire_days=refresh_token_expire_days,
    )
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
        raise RuntimeError("JWT manager not initialized. Call init_jwt_manager() first.")
    return _jwt_manager


def create_access_token(
    subject: str,
    role: str,
    additional_claims: Optional[dict[str, Any]] = None,
) -> str:
    """快捷函数：创建 Access Token"""
    return get_jwt_manager().create_access_token(subject, role, additional_claims)


def create_refresh_token(
    subject: str,
    additional_claims: Optional[dict[str, Any]] = None,
) -> str:
    """快捷函数：创建 Refresh Token"""
    return get_jwt_manager().create_refresh_token(subject, additional_claims)


def verify_access_token(token: str) -> dict[str, Any]:
    """快捷函数：验证 Access Token"""
    return get_jwt_manager().verify_access_token(token)


def verify_refresh_token(token: str) -> dict[str, Any]:
    """快捷函数：验证 Refresh Token"""
    return get_jwt_manager().verify_refresh_token(token)


# ==================== 登录限制 ====================


class LoginRateLimiter:
    """
    登录频率限制器

    使用 Redis 记录登录失败次数，超过限制后锁定账号。
    """

    def __init__(
        self,
        max_attempts: int = LOGIN_MAX_ATTEMPTS,
        lockout_minutes: int = LOGIN_LOCKOUT_MINUTES,
    ) -> None:
        """
        初始化限制器

        Args:
            max_attempts: 最大失败次数
            lockout_minutes: 锁定时长(分钟)
        """
        self.max_attempts = max_attempts
        self.lockout_minutes = lockout_minutes

    def _get_redis_key(self, identifier: str) -> str:
        """获取 Redis 键名"""
        return f"login_attempts:{identifier}"

    def _get_lock_key(self, identifier: str) -> str:
        """获取锁定键名"""
        return f"login_locked:{identifier}"

    async def record_failure(self, identifier: str, redis_client) -> int:
        """
        记录登录失败

        Args:
            identifier: 标识符 (邮箱或手机号)
            redis_client: Redis 客户端

        Returns:
            当前失败次数
        """
        key = self._get_redis_key(identifier)
        lock_key = self._get_lock_key(identifier)

        # 增加失败计数
        attempts = await redis_client.incr(key)

        # 设置过期时间
        if attempts == 1:
            await redis_client.expire(key, LOGIN_ATTEMPT_WINDOW)

        # 检查是否达到限制
        if attempts >= self.max_attempts:
            # 设置锁定
            await redis_client.setex(
                lock_key,
                self.lockout_minutes * 60,
                "locked"
            )
            # 清除失败计数
            await redis_client.delete(key)

        return attempts

    async def record_success(self, identifier: str, redis_client) -> None:
        """
        记录登录成功

        Args:
            identifier: 标识符
            redis_client: Redis 客户端
        """
        key = self._get_redis_key(identifier)
        lock_key = self._get_lock_key(identifier)

        # 清除失败计数和锁定
        await redis_client.delete(key, lock_key)

    async def is_locked(self, identifier: str, redis_client) -> bool:
        """
        检查是否被锁定

        Args:
            identifier: 标识符
            redis_client: Redis 客户端

        Returns:
            True: 被锁定
            False: 未被锁定
        """
        lock_key = self._get_lock_key(identifier)
        return await redis_client.exists(lock_key) > 0

    async def get_remaining_attempts(self, identifier: str, redis_client) -> int:
        """
        获取剩余尝试次数

        Args:
            identifier: 标识符
            redis_client: Redis 客户端

        Returns:
            剩余尝试次数
        """
        key = self._get_redis_key(identifier)
        attempts = await redis_client.get(key)
        if attempts is None:
            return self.max_attempts
        return max(0, self.max_attempts - int(attempts))

    async def get_lockout_remaining_seconds(self, identifier: str, redis_client) -> int:
        """
        获取锁定剩余秒数

        Args:
            identifier: 标识符
            redis_client: Redis 客户端

        Returns:
            剩余秒数
        """
        lock_key = self._get_lock_key(identifier)
        ttl = await redis_client.ttl(lock_key)
        return max(0, ttl)


# 全局限流器实例
login_rate_limiter = LoginRateLimiter()


# ==================== Token 生成 ====================


def generate_verification_code(length: int = 6) -> str:
    """
    生成验证码

    Args:
        length: 验证码长度

    Returns:
        验证码字符串
    """
    return "".join(secrets.choice("0123456789") for _ in range(length))


def generate_api_key() -> str:
    """
    生成 API Key

    Returns:
        API Key 字符串
    """
    return f"hm_{secrets.token_urlsafe(32)}"


# ==================== 导出 ====================
__all__ = [
    # 密码哈希
    "PasswordHasher",
    "password_hasher",
    "hash_password",
    "verify_password",

    # AES 加密
    "PhoneEncryptor",
    "get_phone_encryptor",
    "encrypt_phone",
    "decrypt_phone",
    "hash_phone",

    # JWT
    "JWTManager",
    "init_jwt_manager",
    "get_jwt_manager",
    "create_access_token",
    "create_refresh_token",
    "verify_access_token",
    "verify_refresh_token",

    # 登录限制
    "LoginRateLimiter",
    "login_rate_limiter",

    # 工具
    "generate_verification_code",
    "generate_api_key",

    # 常量
    "JWT_ALGORITHM",
    "ACCESS_TOKEN_EXPIRE_MINUTES",
    "REFRESH_TOKEN_EXPIRE_DAYS",
]
