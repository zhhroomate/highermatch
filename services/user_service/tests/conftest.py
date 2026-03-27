"""
HigherMatch™ User Service - Test Configuration
==============================================

测试配置和共享 fixtures。

版本: 1.0.0
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 设置测试环境变量
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-unit-testing-only"
os.environ["PHONE_ENCRYPTION_KEY"] = "dGVzdC1waG9uZS1lbmNyeXB0aW9uLWtleS0zMg=="
os.environ["REDIS_URL"] = "redis://localhost:6379"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://test:test@localhost:5432/highermatch_test"


# ==================== Event Loop Fixture ====================

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """创建事件循环 fixture (session 级别)"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ==================== Mock Redis Fixture ====================

class MockRedis:
    """Mock Redis 客户端"""

    def __init__(self):
        self._data: dict[str, str] = {}
        self._ttls: dict[str, int] = {}

    async def setex(self, key: str, ttl: int, value: str) -> None:
        """设置带过期时间的键值对"""
        self._data[key] = value
        self._ttls[key] = ttl

    async def get(self, key: str) -> str | None:
        """获取键值"""
        return self._data.get(key)

    async def delete(self, *keys: str) -> int:
        """删除键"""
        count = 0
        for key in keys:
            if key in self._data:
                del self._data[key]
                if key in self._ttls:
                    del self._ttls[key]
                count += 1
        return count

    async def incr(self, key: str) -> int:
        """递增"""
        if key not in self._data:
            self._data[key] = "0"
        self._data[key] = str(int(self._data[key]) + 1)
        return int(self._data[key])

    async def exists(self, key: str) -> int:
        """检查键是否存在"""
        return 1 if key in self._data else 0

    async def expire(self, key: str, seconds: int) -> bool:
        """设置过期时间"""
        if key in self._data:
            self._ttls[key] = seconds
            return True
        return False

    async def ttl(self, key: str) -> int:
        """获取剩余生存时间"""
        return self._ttls.get(key, -1)

    async def ping(self) -> bool:
        """Ping 命令"""
        return True

    async def scan_iter(self, match: str = "*") -> AsyncGenerator[str, None]:
        """扫描键"""
        import fnmatch
        pattern = match.replace("*", ".*")
        for key in list(self._data.keys()):
            if fnmatch.fnmatch(key, match):
                yield key

    async def flushdb(self) -> None:
        """清空数据库"""
        self._data.clear()
        self._ttls.clear()

    def clear(self) -> None:
        """同步清空 (用于 fixture teardown)"""
        self._data.clear()
        self._ttls.clear()


# ==================== Mock Database Fixture ====================

class MockUserRepository:
    """Mock 用户仓储"""

    def __init__(self):
        self._users: dict[str, dict] = {}

    async def get_by_email(self, email: str):
        """根据邮箱获取用户"""
        from tests.test_auth import TestUser
        for user_data in self._users.values():
            if user_data.get("email") == email:
                return TestUser(**user_data)
        return None

    async def get_by_id(self, user_id: str):
        """根据 ID 获取用户"""
        from tests.test_auth import TestUser
        if user_id in self._users:
            return TestUser(**self._users[user_id])
        return None

    async def get_by_phone_hash(self, phone_hash: str):
        """根据手机号哈希获取用户"""
        from tests.test_auth import TestUser
        for user_data in self._users.values():
            if user_data.get("phone_hash") == phone_hash:
                return TestUser(**user_data)
        return None

    async def create(self, user_data: dict):
        """创建用户"""
        from tests.test_auth import TestUser
        import uuid
        user_id = str(uuid.uuid4())
        user_data["id"] = user_id
        self._users[user_id] = user_data
        return TestUser(**user_data)

    def clear(self) -> None:
        """清空数据"""
        self._users.clear()


# ==================== Test User Model ====================

class TestUser:
    """测试用户模型"""

    def __init__(
        self,
        id: str,
        email: str,
        phone_hash: str,
        hashed_password: str,
        role: str,
        name: str = None,
        company_name: str = None,
        company_size: str = None,
        is_verified: bool = False,
        is_active: bool = True,
        created_at: datetime = None,
        updated_at: datetime = None,
    ):
        self.id = id
        self.email = email
        self.phone_hash = phone_hash
        self.hashed_password = hashed_password
        self.role = role
        self.name = name
        self.company_name = company_name
        self.company_size = company_size
        self.is_verified = is_verified
        self.is_active = is_active
        self.created_at = created_at or datetime.now(timezone.utc)
        self.updated_at = updated_at or datetime.now(timezone.utc)

    def to_user_info(self):
        """转换为用户信息"""
        from app.schemas.auth import UserInfo, UserRole
        return UserInfo(
            id=self.id,
            email=self.email,
            phone=self.phone_hash,  # 返回哈希作为加密后的手机号
            role=UserRole(self.role),
            name=self.name or self.company_name,
            is_verified=self.is_verified,
            created_at=self.created_at,
        )


# ==================== Application Fixture ====================

@pytest_asyncio.fixture
async def mock_redis() -> AsyncGenerator[MockRedis, None]:
    """Mock Redis 客户端 fixture"""
    redis = MockRedis()
    yield redis
    redis.clear()


@pytest_asyncio.fixture
async def mock_db() -> AsyncGenerator[MockUserRepository, None]:
    """Mock 数据库 fixture"""
    db = MockUserRepository()
    yield db
    db.clear()


@pytest_asyncio.fixture
async def app(mock_redis, mock_db):
    """创建 FastAPI 应用 fixture"""
    from fastapi import FastAPI, Depends
    from fastapi.testclient import TestClient
    from app.routers import auth
    from app.services.auth_service import AuthService, UserRepository
    from app.core.security import init_jwt_manager

    # 初始化 JWT 管理器
    init_jwt_manager("test-secret-key-for-unit-testing-only")

    # 创建应用
    application = FastAPI(title="HigherMatch Auth Service Test")

    # 添加路由
    application.include_router(auth.router)

    # 覆盖依赖
    async def override_get_redis():
        return mock_redis

    async def override_get_db():
        # 返回一个 mock session
        yield mock_db

    def override_get_auth_service():
        return AuthService(mock_db, mock_redis)

    application.dependency_overrides[auth.get_redis] = override_get_redis
    application.dependency_overrides[auth.get_db] = override_get_db
    application.dependency_overrides[auth.get_auth_service] = override_get_auth_service

    yield application


@pytest_asyncio.fixture
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    """HTTP 异步客户端 fixture"""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac


@pytest_asyncio.fixture
def test_user_password() -> str:
    """测试用户密码"""
    return "Test1234"


@pytest_asyncio.fixture
def employer_email() -> str:
    """雇主测试邮箱"""
    return "employer@test.com"


@pytest_asyncio.fixture
def candidate_email() -> str:
    """候选人测试邮箱"""
    return "candidate@test.com"


@pytest_asyncio.fixture
def test_phone() -> str:
    """测试手机号"""
    return "13800138000"


@pytest_asyncio.fixture
async def registered_employer(
    client: AsyncClient,
    employer_email: str,
    test_user_password: str,
    test_phone: str,
) -> dict:
    """已注册的雇主用户 fixture"""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "role": "employer",
            "email": employer_email,
            "phone": test_phone,
            "password": test_user_password,
            "company_name": "Test Company Ltd.",
            "company_size": "51-200",
        }
    )
    assert response.status_code == 201
    data = response.json()
    return {
        "user_id": data["data"]["user_id"],
        "email": employer_email,
        "password": test_user_password,
        "role": "employer",
        "access_token": data["data"]["token"]["access_token"],
        "refresh_token": data["data"]["token"]["refresh_token"],
    }


@pytest_asyncio.fixture
async def registered_candidate(
    client: AsyncClient,
    candidate_email: str,
    test_user_password: str,
) -> dict:
    """已注册的候选人用户 fixture"""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "role": "candidate",
            "email": candidate_email,
            "phone": "13900139000",
            "password": test_user_password,
            "name": "Test Candidate",
        }
    )
    assert response.status_code == 201
    data = response.json()
    return {
        "user_id": data["data"]["user_id"],
        "email": candidate_email,
        "password": test_user_password,
        "role": "candidate",
        "access_token": data["data"]["token"]["access_token"],
        "refresh_token": data["data"]["token"]["refresh_token"],
    }


# ==================== 测试工具函数 ====================

def create_expired_token(user_id: str, role: str) -> str:
    """创建过期的 Access Token"""
    from jose import jwt
    from datetime import datetime, timedelta, timezone

    secret = "test-secret-key-for-unit-testing-only"
    payload = {
        "sub": user_id,
        "role": role,
        "type": "access",
        "iat": datetime.now(timezone.utc) - timedelta(hours=1),
        "exp": datetime.now(timezone.utc) - timedelta(minutes=30),  # 已过期
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def create_forged_token(user_id: str, role: str) -> str:
    """创建伪造的 Token (使用错误的密钥签名)"""
    from jose import jwt
    from datetime import datetime, timedelta, timezone

    payload = {
        "sub": user_id,
        "role": role,
        "type": "access",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    # 使用不同的密钥签名
    return jwt.encode(payload, "wrong-secret-key", algorithm="HS256")
