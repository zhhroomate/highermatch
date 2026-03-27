"""
HigherMatch™ User Service - Auth Tests
======================================

认证服务单元测试套件。

测试用例覆盖:
1-3. 注册: 雇主正常注册、候选人正常注册、重复邮箱注册报错 (409)
4-7. 登录: 正常登录返回双 Token、密码错误报错 (401)、
         连续 5 次密码错误被 Redis 锁定 (429)、锁定状态下使用正确密码依然被拒
8-10. Token: 使用有效 Access Token 获取 /me 成功、使用过期 Token 报错 (401)、
        使用伪造 Token 报错 (401)
11-12. Refresh & RBAC: 使用有效 Refresh Token 换取新 Token 成功、
        测试 require_role 拦截逻辑（模拟 Candidate Token 访问要求 Employer 角色的 Mock 路由，返回 403）

版本: 1.0.0
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient

from conftest import (
    create_expired_token,
    create_forged_token,
)


# ==================== 1-3. 注册测试 ====================

class TestRegistration:
    """用户注册测试"""

    @pytest.mark.asyncio
    async def test_register_employer_success(
        self,
        client: AsyncClient,
        employer_email: str,
        test_user_password: str,
        test_phone: str,
    ):
        """
        测试用例 1: 雇主正常注册成功

        预期结果:
        - HTTP 201 Created
        - 返回 user_id, role, access_token, refresh_token
        """
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "role": "employer",
                "email": employer_email,
                "phone": test_phone,
                "password": test_user_password,
                "company_name": "Tech Corp Ltd.",
                "company_size": "51-200",
            }
        )

        assert response.status_code == 201
        data = response.json()

        # 验证成功响应
        assert data["success"] is True
        assert "user_id" in data["data"]
        assert data["data"]["role"] == "employer"

        # 验证 Token
        assert "token" in data["data"]
        assert "access_token" in data["data"]["token"]
        assert "refresh_token" in data["data"]["token"]
        assert data["data"]["token"]["token_type"] == "bearer"

        # Token 应该至少有 20 个字符 (JWT 格式)
        assert len(data["data"]["token"]["access_token"]) > 20

    @pytest.mark.asyncio
    async def test_register_candidate_success(
        self,
        client: AsyncClient,
        candidate_email: str,
        test_user_password: str,
    ):
        """
        测试用例 2: 候选人正常注册成功

        预期结果:
        - HTTP 201 Created
        - 返回 user_id, role, access_token, refresh_token
        """
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "role": "candidate",
                "email": candidate_email,
                "phone": "13900139000",
                "password": test_user_password,
                "name": "John Doe",
            }
        )

        assert response.status_code == 201
        data = response.json()

        # 验证成功响应
        assert data["success"] is True
        assert "user_id" in data["data"]
        assert data["data"]["role"] == "candidate"

        # 验证 Token
        assert "token" in data["data"]
        assert "access_token" in data["data"]["token"]
        assert "refresh_token" in data["data"]["token"]

    @pytest.mark.asyncio
    async def test_register_duplicate_email_conflict(
        self,
        client: AsyncClient,
        registered_employer: dict,
        test_user_password: str,
    ):
        """
        测试用例 3: 重复邮箱注册返回 409 Conflict

        预期结果:
        - HTTP 409 Conflict
        - 返回错误码 AUTH_3002
        """
        # 尝试使用已注册的邮箱再次注册
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "role": "candidate",  # 尝试不同角色
                "email": registered_employer["email"],  # 使用已存在的邮箱
                "phone": "13700137000",
                "password": test_user_password,
                "name": "Another User",
            }
        )

        assert response.status_code == 409
        data = response.json()

        # 验证错误响应
        assert data["detail"]["success"] is False
        assert data["detail"]["error"]["code"] == "AUTH_3002"
        assert "邮箱" in data["detail"]["error"]["message"]


# ==================== 4-7. 登录测试 ====================

class TestLogin:
    """用户登录测试"""

    @pytest.mark.asyncio
    async def test_login_success_returns_tokens(
        self,
        client: AsyncClient,
        registered_employer: dict,
    ):
        """
        测试用例 4: 正常登录返回双 Token

        预期结果:
        - HTTP 200 OK
        - 返回 access_token, refresh_token, user_id, role
        """
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": registered_employer["email"],
                "password": registered_employer["password"],
            }
        )

        assert response.status_code == 200
        data = response.json()

        # 验证成功响应
        assert data["success"] is True
        assert "access_token" in data["data"]
        assert "refresh_token" in data["data"]
        assert data["data"]["user_id"] == registered_employer["user_id"]
        assert data["data"]["role"] == "employer"
        assert data["data"]["token_type"] == "bearer"

        # Token 应该至少有 20 个字符
        assert len(data["data"]["access_token"]) > 20
        assert len(data["data"]["refresh_token"]) > 20

    @pytest.mark.asyncio
    async def test_login_wrong_password_returns_401(
        self,
        client: AsyncClient,
        registered_employer: dict,
    ):
        """
        测试用例 5: 密码错误返回 401 Unauthorized

        预期结果:
        - HTTP 401 Unauthorized
        - 返回错误码 AUTH_2001
        """
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": registered_employer["email"],
                "password": "WrongPassword123",  # 错误密码
            }
        )

        assert response.status_code == 401
        data = response.json()

        # 验证错误响应
        assert data["detail"]["success"] is False
        assert data["detail"]["error"]["code"] == "AUTH_2001"
        assert "remaining_attempts" in data["detail"]["error"]["details"]

    @pytest.mark.asyncio
    async def test_login_5_failures_triggers_lockout_429(
        self,
        client: AsyncClient,
        registered_employer: dict,
    ):
        """
        测试用例 6: 连续 5 次密码错误触发账号锁定 (429)

        预期结果:
        - HTTP 429 Too Many Requests
        - 返回锁定信息 (retry_after, locked_until)
        """
        wrong_password = "WrongPass123"

        # 连续 5 次错误登录
        for i in range(4):
            response = await client.post(
                "/api/v1/auth/login",
                json={
                    "email": registered_employer["email"],
                    "password": wrong_password,
                }
            )
            # 前 4 次应该返回 401
            assert response.status_code == 401

        # 第 5 次应该触发锁定
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": registered_employer["email"],
                "password": wrong_password,
            }
        )

        assert response.status_code == 429
        data = response.json()

        # 验证锁定响应
        assert data["detail"]["success"] is False
        assert data["detail"]["error"]["code"] == "AUTH_2004"
        assert "retry_after" in data["detail"]
        assert "locked_until" in data["detail"]
        assert data["detail"]["retry_after"] > 0

    @pytest.mark.asyncio
    async def test_login_locked_account_rejects_correct_password(
        self,
        client: AsyncClient,
        registered_employer: dict,
    ):
        """
        测试用例 7: 账号锁定后使用正确密码依然被拒 (429)

        预期结果:
        - HTTP 429 Too Many Requests
        - 即使使用正确密码也无法登录
        """
        wrong_password = "WrongPass123"

        # 连续 5 次错误登录触发锁定
        for _ in range(5):
            await client.post(
                "/api/v1/auth/login",
                json={
                    "email": registered_employer["email"],
                    "password": wrong_password,
                }
            )

        # 锁定后使用正确密码尝试登录
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": registered_employer["email"],
                "password": registered_employer["password"],  # 正确密码
            }
        )

        # 应该仍然返回 429 锁定
        assert response.status_code == 429
        data = response.json()
        assert data["detail"]["error"]["code"] == "AUTH_2004"


# ==================== 8-10. Token 测试 ====================

class TestToken:
    """Token 验证测试"""

    @pytest.mark.asyncio
    async def test_get_me_with_valid_token_success(
        self,
        client: AsyncClient,
        registered_employer: dict,
    ):
        """
        测试用例 8: 使用有效 Access Token 获取 /me 成功

        预期结果:
        - HTTP 200 OK
        - 返回用户信息 (user_id, email, role)
        """
        access_token = registered_employer["access_token"]

        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == 200
        data = response.json()

        # 验证响应
        assert data["success"] is True
        assert data["data"]["id"] == registered_employer["user_id"]
        assert data["data"]["email"] == registered_employer["email"]
        assert data["data"]["role"] == "employer"

    @pytest.mark.asyncio
    async def test_get_me_with_expired_token_returns_401(
        self,
        client: AsyncClient,
        registered_employer: dict,
    ):
        """
        测试用例 9: 使用过期 Token 返回 401 Unauthorized

        预期结果:
        - HTTP 401 Unauthorized
        - 返回错误码 AUTH_2001
        """
        # 创建过期 token
        expired_token = create_expired_token(
            registered_employer["user_id"],
            "employer"
        )

        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"}
        )

        assert response.status_code == 401
        data = response.json()

        # 验证错误响应
        assert data["detail"]["success"] is False
        assert data["detail"]["error"]["code"] == "AUTH_2001"

    @pytest.mark.asyncio
    async def test_get_me_with_forged_token_returns_401(
        self,
        client: AsyncClient,
        registered_employer: dict,
    ):
        """
        测试用例 10: 使用伪造 Token 返回 401 Unauthorized

        预期结果:
        - HTTP 401 Unauthorized
        - 返回错误码 AUTH_2001
        """
        # 创建伪造 token (使用错误密钥签名)
        forged_token = create_forged_token(
            registered_employer["user_id"],
            "employer"
        )

        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {forged_token}"}
        )

        assert response.status_code == 401
        data = response.json()

        # 验证错误响应
        assert data["detail"]["success"] is False
        assert data["detail"]["error"]["code"] == "AUTH_2001"


# ==================== 11-12. Refresh & RBAC 测试 ====================

class TestTokenRefresh:
    """Token 刷新测试"""

    @pytest.mark.asyncio
    async def test_refresh_token_success(
        self,
        client: AsyncClient,
        registered_employer: dict,
    ):
        """
        测试用例 11: 使用有效 Refresh Token 换取新 Token 成功

        预期结果:
        - HTTP 200 OK
        - 返回新的 access_token 和 refresh_token
        - 新 Token 应该与旧 Token 不同
        """
        refresh_token = registered_employer["refresh_token"]
        old_access_token = registered_employer["access_token"]

        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )

        assert response.status_code == 200
        data = response.json()

        # 验证响应
        assert data["success"] is True
        assert "access_token" in data["data"]
        assert "refresh_token" in data["data"]
        assert data["data"]["token_type"] == "bearer"

        # 新 Token 应该与旧 Token 不同
        new_access_token = data["data"]["access_token"]
        assert new_access_token != old_access_token
        assert len(new_access_token) > 20


class TestRBAC:
    """RBAC 权限控制测试"""

    @pytest.mark.asyncio
    async def test_require_role_candidate_accessing_employer_route_returns_403(
        self,
        client: AsyncClient,
        registered_candidate: dict,
        mock_app_with_rbac_routes,
    ):
        """
        测试用例 12: Candidate Token 访问要求 Employer 角色的路由返回 403

        预期结果:
        - HTTP 403 Forbidden
        - 返回错误码 AUTH_2003 或 AUTH_2004
        """
        candidate_token = registered_candidate["access_token"]

        # 尝试访问仅允许 employer 角色的路由
        response = await client.post(
            "/api/v1/jobs",
            headers={"Authorization": f"Bearer {candidate_token}"},
            json={
                "title": "Software Engineer",
                "description": "Job description",
                "salary_min": 10000,
                "salary_max": 20000,
            }
        )

        # 验证权限不足
        assert response.status_code == 403
        data = response.json()

        # 验证错误响应
        assert data["detail"]["success"] is False
        assert data["detail"]["error"]["code"] in ["AUTH_2003", "AUTH_2004"]
        assert "权限" in data["detail"]["error"]["message"] or "需要" in data["detail"]["error"]["message"]


# ==================== 辅助 Mock 应用 (RBAC 测试用) ====================

@pytest_asyncio.fixture
async def mock_app_with_rbac_routes(client: AsyncClient, app):
    """添加 RBAC 测试路由的 mock 应用"""
    from fastapi import Depends, FastAPI
    from fastapi.testclient import TestClient
    from shared.auth_middleware import init_auth, require_role, TokenPayload
    from app.routers import auth
    from app.services.auth_service import AuthService
    from conftest import mock_redis, mock_db

    # 初始化认证模块
    init_auth("test-secret-key-for-unit-testing-only")

    # 添加测试路由到应用
    @app.post("/api/v1/jobs")
    async def create_job(
        title: str,
        description: str,
        salary_min: int,
        salary_max: int,
        current_user: TokenPayload = Depends(require_role(["employer", "admin"]))
    ):
        """仅雇主/管理员可访问的岗位创建路由"""
        return {
            "success": True,
            "message": f"Job '{title}' created by {current_user.sub}",
            "role": current_user.role,
        }

    return app


# ==================== 额外测试用例 (补充覆盖) ====================

class TestRegistrationValidation:
    """注册参数验证测试"""

    @pytest.mark.asyncio
    async def test_register_invalid_email_format(self, client: AsyncClient):
        """测试无效邮箱格式"""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "role": "candidate",
                "email": "invalid-email",
                "phone": "13800138001",
                "password": "Test1234",
            }
        )

        assert response.status_code == 422  # Pydantic 验证错误

    @pytest.mark.asyncio
    async def test_register_weak_password(self, client: AsyncClient):
        """测试弱密码 (无字母)"""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "role": "candidate",
                "email": "test2@example.com",
                "phone": "13800138002",
                "password": "12345678",  # 无字母
            }
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_weak_password_no_digit(self, client: AsyncClient):
        """测试弱密码 (无数字)"""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "role": "candidate",
                "email": "test3@example.com",
                "phone": "13800138003",
                "password": "abcdefgh",  # 无数字
            }
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_employer_without_company_name(self, client: AsyncClient):
        """测试雇主注册缺少公司名称"""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "role": "employer",
                "email": "test4@example.com",
                "phone": "13800138004",
                "password": "Test1234",
                # 缺少 company_name
            }
        )

        assert response.status_code == 422


class TestLoginValidation:
    """登录参数验证测试"""

    @pytest.mark.asyncio
    async def test_login_invalid_email_format(self, client: AsyncClient):
        """测试无效邮箱格式"""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "not-an-email",
                "password": "Test1234",
            }
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: AsyncClient):
        """测试不存在的用户登录"""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "Test1234",
            }
        )

        assert response.status_code == 401
        data = response.json()
        assert data["detail"]["error"]["code"] == "AUTH_2001"


class TestTokenValidation:
    """Token 验证测试"""

    @pytest.mark.asyncio
    async def test_get_me_without_token_returns_401(self, client: AsyncClient):
        """测试不带 Token 访问 /me"""
        response = await client.get("/api/v1/auth/me")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_with_invalid_token_returns_401(self, client: AsyncClient):
        """测试使用无效 Refresh Token"""
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid-token"}
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_with_access_token_returns_401(self, client: AsyncClient, registered_employer: dict):
        """测试使用 Access Token 代替 Refresh Token"""
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": registered_employer["access_token"]}
        )

        assert response.status_code == 401


class TestHealthCheck:
    """健康检查测试"""

    @pytest.mark.asyncio
    async def test_auth_health_check(self, client: AsyncClient):
        """测试认证服务健康检查"""
        response = await client.get("/api/v1/auth/health")

        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "auth"
        assert "status" in data
        assert "timestamp" in data


# ==================== 测试运行入口 ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
