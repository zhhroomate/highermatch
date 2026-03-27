from __future__ import annotations

"""
HigherMatch™ Shared Core - Redis Module
========================================

异步 Redis 客户端封装模块。
提供统一的缓存操作接口和连接管理。

版本: 1.0.0

使用示例:
    from shared.core.redis import get_redis, RedisCache

    # 获取 Redis 客户端
    redis = await get_redis()

    # 基本操作
    await redis.set("key", "value", ex=3600)
    value = await redis.get("key")

    # 使用缓存类
    cache = RedisCache()
    await cache.set("user:1", user_data, ttl=300)
    data = await cache.get("user:1")
"""

import json
import logging
from contextlib import asynccontextmanager
from typing import (
    Any,
    AsyncGenerator,
    Callable,
    Optional,
    TypeVar,
    Union,
    overload,
)

import redis.asyncio as redis
from redis.asyncio import Redis
from redis.asyncio.client import Pipeline
from redis.exceptions import RedisError

from shared.core.config import Settings, get_settings
from shared.core.exceptions import ExternalServiceException

# ==================== 日志配置 ====================
logger = logging.getLogger(__name__)

# ==================== 类型定义 ====================
T = TypeVar("T")
JSONType = Union[str, int, float, bool, None, dict, list]


# ==================== Redis 连接管理 ====================
class RedisManager:
    """
    Redis 连接管理器

    管理全局 Redis 连接池，支持连接复用和健康检查。
    """

    def __init__(self) -> None:
        self._client: Optional[Redis] = None
        self._settings: Optional[Settings] = None

    def _get_settings(self) -> Settings:
        """获取配置"""
        if self._settings is None:
            self._settings = get_settings()
        return self._settings

    async def connect(self) -> Redis:
        """
        建立 Redis 连接

        Returns:
            Redis 客户端实例
        """
        if self._client is None:
            settings = self._get_settings()
            logger.info(
                f"Connecting to Redis: {settings.redis.host}:{settings.redis.port}"
            )

            self._client = redis.Redis(
                host=settings.redis.host,
                port=settings.redis.port,
                password=settings.redis.password or None,
                db=settings.redis.db,
                encoding="utf-8",
                encoding_errors="strict",
                decode_responses=True,  # 自动解码响应
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30,
            )

            # 测试连接
            try:
                await self._client.ping()
                logger.info("Redis connection established successfully")
            except RedisError as e:
                logger.error(f"Redis connection failed: {e}")
                self._client = None
                raise ExternalServiceException(
                    code="EXT_5001",
                    message="Redis 连接失败",
                    details={"error": str(e)}
                )

        return self._client

    async def disconnect(self) -> None:
        """关闭 Redis 连接"""
        if self._client is not None:
            logger.info("Closing Redis connection...")
            await self._client.close()
            self._client = None
            logger.info("Redis connection closed")

    async def health_check(self) -> bool:
        """
        检查 Redis 连接健康状态

        Returns:
            True: 连接正常
            False: 连接异常
        """
        try:
            if self._client is None:
                await self.connect()
            await self._client.ping()
            return True
        except RedisError as e:
            logger.error(f"Redis health check failed: {e}")
            return False

    @property
    def client(self) -> Optional[Redis]:
        """获取当前客户端实例"""
        return self._client


# 全局 Redis 管理器实例
_redis_manager = RedisManager()


async def get_redis() -> Redis:
    """
    获取 Redis 客户端实例

    Returns:
        Redis 异步客户端
    """
    return await _redis_manager.connect()


async def close_redis() -> None:
    """关闭 Redis 连接"""
    await _redis_manager.disconnect()


async def redis_health_check() -> bool:
    """Redis 健康检查"""
    return await _redis_manager.health_check()


# ==================== 缓存操作类 ====================
class RedisCache:
    """
    Redis 缓存操作封装类

    提供常用的缓存操作方法，支持 JSON 序列化。
    """

    # 默认 TTL (秒)
    DEFAULT_TTL = 3600  # 1小时
    SHORT_TTL = 300    # 5分钟
    LONG_TTL = 86400   # 24小时

    def __init__(self, prefix: str = "hm") -> None:
        """
        初始化缓存类

        Args:
            prefix: 键前缀，用于隔离不同服务的缓存
        """
        self.prefix = prefix
        self._redis: Optional[Redis] = None

    async def _get_client(self) -> Redis:
        """获取 Redis 客户端"""
        if self._redis is None:
            self._redis = await get_redis()
        return self._redis

    def _make_key(self, key: str) -> str:
        """生成带前缀的键名"""
        return f"{self.prefix}:{key}"

    # ==================== 基本操作 ====================
    async def get(
        self,
        key: str,
        default: Optional[T] = None,
    ) -> Optional[T]:
        """
        获取缓存值

        Args:
            key: 缓存键
            default: 默认值

        Returns:
            缓存值或默认值
        """
        try:
            client = await self._get_client()
            value = await client.get(self._make_key(key))

            if value is None:
                return default

            # 尝试解析 JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value  # type: ignore

        except RedisError as e:
            logger.error(f"Redis GET error: {e}")
            return default

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        nx: bool = False,
        xx: bool = False,
    ) -> bool:
        """
        设置缓存值

        Args:
            key: 缓存键
            value: 缓存值 (会自动序列化为 JSON)
            ttl: 过期时间 (秒)，默认 1 小时
            nx: 仅在键不存在时设置
            xx: 仅在键存在时设置

        Returns:
            True: 设置成功
            False: 设置失败
        """
        try:
            client = await self._get_client()
            cache_key = self._make_key(key)

            # 序列化值
            if not isinstance(value, str):
                value = json.dumps(value, ensure_ascii=False)

            await client.set(
                cache_key,
                value,
                ex=ttl or self.DEFAULT_TTL,
                nx=nx,
                xx=xx,
            )
            return True

        except RedisError as e:
            logger.error(f"Redis SET error: {e}")
            return False

    async def delete(self, *keys: str) -> int:
        """
        删除缓存

        Args:
            keys: 要删除的缓存键

        Returns:
            删除的键数量
        """
        try:
            client = await self._get_client()
            cache_keys = [self._make_key(k) for k in keys]
            return await client.delete(*cache_keys)

        except RedisError as e:
            logger.error(f"Redis DELETE error: {e}")
            return 0

    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        try:
            client = await self._get_client()
            return await client.exists(self._make_key(key)) > 0
        except RedisError as e:
            logger.error(f"Redis EXISTS error: {e}")
            return False

    async def expire(self, key: str, ttl: int) -> bool:
        """设置键的过期时间"""
        try:
            client = await self._get_client()
            return await client.expire(self._make_key(key), ttl)
        except RedisError as e:
            logger.error(f"Redis EXPIRE error: {e}")
            return False

    async def ttl(self, key: str) -> int:
        """获取键的剩余过期时间"""
        try:
            client = await self._get_client()
            return await client.ttl(self._make_key(key))
        except RedisError as e:
            logger.error(f"Redis TTL error: {e}")
            return -2

    # ==================== 计数操作 ====================
    async def incr(self, key: str, amount: int = 1) -> int:
        """递增计数器"""
        try:
            client = await self._get_client()
            return await client.incr(self._make_key(key), amount)
        except RedisError as e:
            logger.error(f"Redis INCR error: {e}")
            return 0

    async def decr(self, key: str, amount: int = 1) -> int:
        """递减计数器"""
        try:
            client = await self._get_client()
            return await client.decr(self._make_key(key), amount)
        except RedisError as e:
            logger.error(f"Redis DECR error: {e}")
            return 0

    # ==================== 哈希操作 ====================
    async def hget(
        self,
        key: str,
        field: str,
        default: Optional[T] = None,
    ) -> Optional[T]:
        """获取哈希字段值"""
        try:
            client = await self._get_client()
            value = await client.hget(self._make_key(key), field)

            if value is None:
                return default

            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value  # type: ignore

        except RedisError as e:
            logger.error(f"Redis HGET error: {e}")
            return default

    async def hset(
        self,
        key: str,
        field: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """设置哈希字段值"""
        try:
            client = await self._get_client()
            cache_key = self._make_key(key)

            # 序列化值
            if not isinstance(value, str):
                value = json.dumps(value, ensure_ascii=False)

            await client.hset(cache_key, field, value)

            if ttl:
                await client.expire(cache_key, ttl)

            return True

        except RedisError as e:
            logger.error(f"Redis HSET error: {e}")
            return False

    async def hgetall(self, key: str) -> dict[str, Any]:
        """获取哈希所有字段"""
        try:
            client = await self._get_client()
            data = await client.hgetall(self._make_key(key))

            # 尝试解析 JSON 值
            result = {}
            for k, v in data.items():
                try:
                    result[k] = json.loads(v)
                except (json.JSONDecodeError, TypeError):
                    result[k] = v

            return result

        except RedisError as e:
            logger.error(f"Redis HGETALL error: {e}")
            return {}

    async def hdel(self, key: str, *fields: str) -> int:
        """删除哈希字段"""
        try:
            client = await self._get_client()
            return await client.hdel(self._make_key(key), *fields)
        except RedisError as e:
            logger.error(f"Redis HDEL error: {e}")
            return 0

    # ==================== 列表操作 ====================
    async def lpush(self, key: str, *values: Any, ttl: Optional[int] = None) -> int:
        """左推入列表"""
        try:
            client = await self._get_client()
            cache_key = self._make_key(key)

            serialized = [
                json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else v
                for v in values
            ]

            length = await client.lpush(cache_key, *serialized)

            if ttl:
                await client.expire(cache_key, ttl)

            return length

        except RedisError as e:
            logger.error(f"Redis LPUSH error: {e}")
            return 0

    async def rpush(self, key: str, *values: Any, ttl: Optional[int] = None) -> int:
        """右推入列表"""
        try:
            client = await self._get_client()
            cache_key = self._make_key(key)

            serialized = [
                json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else v
                for v in values
            ]

            length = await client.rpush(cache_key, *serialized)

            if ttl:
                await client.expire(cache_key, ttl)

            return length

        except RedisError as e:
            logger.error(f"Redis RPUSH error: {e}")
            return 0

    async def lrange(
        self,
        key: str,
        start: int = 0,
        end: int = -1,
    ) -> list[Any]:
        """获取列表范围"""
        try:
            client = await self._get_client()
            data = await client.lrange(self._make_key(key), start, end)

            # 尝试解析 JSON
            result = []
            for item in data:
                try:
                    result.append(json.loads(item))
                except (json.JSONDecodeError, TypeError):
                    result.append(item)

            return result

        except RedisError as e:
            logger.error(f"Redis LRANGE error: {e}")
            return []

    # ==================== 集合操作 ====================
    async def sadd(self, key: str, *members: Any, ttl: Optional[int] = None) -> int:
        """添加集合成员"""
        try:
            client = await self._get_client()
            cache_key = self._make_key(key)

            serialized = [
                json.dumps(m, ensure_ascii=False) if not isinstance(m, str) else m
                for m in members
            ]

            count = await client.sadd(cache_key, *serialized)

            if ttl:
                await client.expire(cache_key, ttl)

            return count

        except RedisError as e:
            logger.error(f"Redis SADD error: {e}")
            return 0

    async def smembers(self, key: str) -> set[Any]:
        """获取集合所有成员"""
        try:
            client = await self._get_client()
            data = await client.smembers(self._make_key(key))

            result = set()
            for item in data:
                try:
                    result.add(json.loads(item))
                except (json.JSONDecodeError, TypeError):
                    result.add(item)

            return result

        except RedisError as e:
            logger.error(f"Redis SMEMBERS error: {e}")
            return set()

    # ==================== 分布式锁 ====================
    async def lock(
        self,
        key: str,
        timeout: int = 10,
        blocking_timeout: float = -1,
    ) -> Optional[redis.Lock]:
        """
        获取分布式锁

        Args:
            key: 锁键
            timeout: 锁超时时间 (秒)
            blocking_timeout: 阻塞等待时间 (-1 表示无限)

        Returns:
            Lock 对象或 None
        """
        try:
            client = await self._get_client()
            lock = client.lock(
                self._make_key(key),
                timeout=timeout,
                blocking_timeout=blocking_timeout,
            )

            # 尝试获取锁
            if await lock.acquire():
                return lock

            return None

        except RedisError as e:
            logger.error(f"Redis LOCK error: {e}")
            return None

    # ==================== 缓存装饰器 ====================
    def cached(
        self,
        key_prefix: str,
        ttl: int = 300,
        unless: Optional[Callable[..., bool]] = None,
    ) -> Callable:
        """
        缓存装饰器

        使用示例:
            @cache.cached(key_prefix="user", ttl=600)
            async def get_user(user_id: int):
                return await db.get_user(user_id)

        Args:
            key_prefix: 缓存键前缀
            ttl: 过期时间 (秒)
            unless: 条件函数，返回 True 时跳过缓存
        """
        def decorator(func: Callable) -> Callable:
            async def wrapper(*args: Any, **kwargs: Any) -> Any:
                # 构建缓存键
                cache_key = f"{key_prefix}:{':'.join(str(a) for a in args)}"

                # 检查 unless 条件
                if unless and unless(*args, **kwargs):
                    return await func(*args, **kwargs)

                # 尝试从缓存获取
                cached_value = await self.get(cache_key)
                if cached_value is not None:
                    logger.debug(f"Cache hit: {cache_key}")
                    return cached_value

                # 执行函数
                result = await func(*args, **kwargs)

                # 存入缓存
                await self.set(cache_key, result, ttl=ttl)
                logger.debug(f"Cache set: {cache_key}")

                return result

            return wrapper
        return decorator


# ==================== 全局缓存实例 ====================
# 各服务可创建自己的缓存实例
class RedisClient:
    """Compatibility wrapper for services that use a direct Redis client."""

    def __init__(self, redis_url: str):
        self._client = redis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            health_check_interval=30,
        )

    async def ping(self) -> bool:
        return await self._client.ping()

    async def get(self, key: str) -> Any:
        return await self._client.get(key)

    async def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        return await self._client.set(key, value, ex=ex)

    async def setex(self, key: str, ttl: int, value: Any) -> bool:
        return await self._client.setex(key, ttl, value)

    async def close(self) -> None:
        await self._client.close()


def create_cache(prefix: str = "hm") -> RedisCache:
    """创建缓存实例"""
    return RedisCache(prefix=prefix)


# 默认缓存实例
cache = RedisCache(prefix="hm")


# ==================== 导出 ====================
__all__ = [
    # 连接管理
    "RedisManager",
    "get_redis",
    "close_redis",
    "redis_health_check",

    # 缓存类
    "RedisCache",
    "RedisClient",
    "create_cache",
    "cache",

    # 类型
    "JSONType",
    "Redis",
    "Pipeline",
]
