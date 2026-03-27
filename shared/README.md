---
AIGC:
    ContentProducer: Minimax Agent AI
    ContentPropagator: Minimax Agent AI
    Label: AIGC
    ProduceID: "00000000000000000000000000000000"
    PropagateID: "00000000000000000000000000000000"
    ReservedCode1: 304402202eff9109db4426e714af864f935376909e27c24a914f7e024a42f776f1ebcd57022078e944ef016cd0539a1e8d4136ad1767915fd9265a85132622087253fd78ceb5
    ReservedCode2: 304502205b068dad62e2f577df82e9c064a8defd88e082bc4a15d9eca499efb7f8f9b1a202210080a5a0bcc2cb089b7f4e5653db4e0810fbbcdce7f3cefe64113f1f605294a96b
---

# HigherMatch™ Shared Core Library

微服务共享基础库

## 安装

```bash
pip install -e ./shared
```

## 模块结构

```
shared/
├── core/           # 核心模块
│   ├── config.py      # 全局配置 (pydantic-settings)
│   ├── db.py          # 数据库连接 (SQLAlchemy 2.0 async)
│   ├── exceptions.py  # 异常处理和错误响应
│   └── redis.py       # Redis 缓存封装
├── models/        # ORM 模型基类
└── schemas/       # Pydantic Schema
```

## 快速开始

### 1. 配置

```python
from shared.core import get_settings, Settings

settings = get_settings()
db_url = settings.database.async_url
```

### 2. 数据库

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from shared.core import get_db, Base

# 在应用中使用
@app.get("/users/{user_id}")
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()
```

### 3. 异常处理

```python
from shared.core import BusinessException, NotFoundException

raise NotFoundException(
    code="USER_001",
    message="用户不存在",
    details={"user_id": 123}
)
```

### 4. Redis 缓存

```python
from shared.core import cache

# 设置缓存
await cache.set("user:1", user_data, ttl=300)

# 获取缓存
data = await cache.get("user:1")
```

## 许可证

MIT License
