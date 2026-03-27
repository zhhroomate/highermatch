---
AIGC:
    ContentProducer: Minimax Agent AI
    ContentPropagator: Minimax Agent AI
    Label: AIGC
    ProduceID: "00000000000000000000000000000000"
    PropagateID: "00000000000000000000000000000000"
    ReservedCode1: 3046022100860e28d616d5436c220e9449729d739af9335de7e424f6393ae57587b2340312022100e5db436ce8a5a5034a266b30bb509108fe6d13672e01f245b6ca2f0a370b4569
    ReservedCode2: 3045022100b62d719870971692521a278ec5b9b0c8a299ea5577669242da835d031697128302202a0b57df4a8a09f119263fc45111634f71bbb9c1d408aeed0793df912e82e01d
---

# HigherMatch™ FastAPI Service Template

标准 FastAPI 微服务模板，所有微服务 (User Service, Job Service, AI Service) 应基于此模板创建。

## 📁 文件结构

```
template/
├── main.py           # FastAPI 应用工厂模板
├── Dockerfile         # 多阶段构建 Dockerfile
├── requirements.txt  # Python 依赖
└── README.md         # 本文档
```

## 🚀 快速开始

### 1. 创建新服务

```bash
# 复制模板到新服务目录
cp -r template services/my-service

# 进入目录
cd services/my-service
```

### 2. 修改配置

编辑 `app/main.py`，修改服务名称：

```python
class ServiceConfig:
    SERVICE_NAME: str = "my-service"  # 修改为实际服务名
    SERVICE_PORT: int = 8001          # 修改为实际端口
```

### 3. 构建 Docker 镜像

```bash
# 直接构建
docker build -t highermatch-my-service .

# 或使用 docker-compose
docker-compose build my-service
```

### 4. 运行服务

```bash
# Docker 运行
docker run -d -p 8001:8001 --env-file .env highermatch-my-service

# 本地运行
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

## 📋 功能特性

| 功能 | 说明 |
|------|------|
| **Lifespan 管理** | 自动管理数据库、Redis 连接的生命周期 |
| **CORS 中间件** | 配置跨域资源共享 |
| **异常处理器** | 全局统一异常处理和错误响应 |
| **健康检查** | `/health`, `/ready`, `/live` 三个端点 |
| **配置管理** | 支持环境变量和 .env 文件 |

## 🔧 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `SERVICE_NAME` | highermatch-service | 服务名称 |
| `SERVICE_PORT` | 8000 | 服务端口 |
| `DATABASE_URL` | (见配置) | PostgreSQL 连接字符串 |
| `REDIS_URL` | (见配置) | Redis 连接字符串 |
| `CORS_ORIGINS` | http://localhost:3000 | 允许的跨域源 |

## 📡 API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 完整健康检查 |
| `/ready` | GET | 就绪检查 (K8s) |
| `/live` | GET | 存活检查 (K8s) |
| `/docs` | GET | Swagger UI |
| `/redoc` | GET | ReDoc 文档 |

## 🐳 Docker 构建参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `SERVICE_NAME` | highermatch-service | 服务名称 |
| `SERVICE_PORT` | 8000 | 暴露端口 |
| `UID` | 1001 | 运行用户 ID |
| `GID` | 1001 | 运行组 ID |

## 📝 示例: 添加路由

在 `app/routers/` 目录下创建路由文件：

```python
# app/routers/users.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from shared.core import get_db

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/{user_id}")
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    return {"user_id": user_id}
```

在 `app/main.py` 中注册路由：

```python
from app.routers import users

app.include_router(users.router)
```

## 📝 示例: 使用异常

```python
from shared.core import NotFoundException

@router.get("/{user_id}")
async def get_user(user_id: int):
    user = await get_user_from_db(user_id)
    if not user:
        raise NotFoundException(
            code="USER_001",
            message="用户不存在",
            details={"user_id": user_id}
        )
    return user
```

## 📝 示例: 使用缓存

```python
from shared.core import cache

@router.get("/popular")
async def get_popular_users():
    # 尝试从缓存获取
    cached = await cache.get("popular_users")
    if cached:
        return cached

    # 获取数据
    users = await fetch_popular_users()

    # 存入缓存 (5分钟)
    await cache.set("popular_users", users, ttl=300)

    return users
```

## 🔒 安全说明

⚠️ **生产环境必须修改以下配置:**

1. `JWT_SECRET_KEY` - 使用随机生成的密钥
2. `DATABASE_PASSWORD` - 使用强密码
3. 禁用 DEBUG 模式

## 📄 许可证

Copyright © 2024 HigherMatch™. All rights reserved.
