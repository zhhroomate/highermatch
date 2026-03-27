---
AIGC:
    ContentProducer: Minimax Agent AI
    ContentPropagator: Minimax Agent AI
    Label: AIGC
    ProduceID: "00000000000000000000000000000000"
    PropagateID: "00000000000000000000000000000000"
    ReservedCode1: 3044022032374d23753f2624f3260259147ab15cebf80ae0974a7ce1d3dc8128d2b6595e0220044a339d7ddd407384eb4a624e829a62cffa2a4675eac6a45f45534d3f2369b3
    ReservedCode2: 30450220169a7f7d27701ce4af19827787edfbbebef5085973dfbb54ebb6f2f87b8c0377022100fabeb18899e5f68c83bc6be5c23e576f3c51249ba76558132b19fe87c1d48b3e
---

# HigherMatch™ AI 招聘平台

> **让每一次招聘都精准匹配，让每一位人才都能找到理想的舞台**

HigherMatch™ 是一款基于人工智能的智能招聘平台，通过先进的 NLP 和向量检索技术，为企业提供从岗位发布到候选人入职的全流程自动化解决方案。

---

## 🏗️ 系统架构

### 微服务架构图

```mermaid
graph TB
    subgraph Frontend["前端层"]
        EMP[employer-portal<br/>雇主端]
        CAND[candidate-portal<br/>候选人端]
    end

    subgraph Gateway["网关层"]
        NGINX[Nginx API Gateway<br/>:80]
    end

    subgraph Auth["认证服务"]
        USER[user-service<br/>:8001]
        JWT[JWT Auth]
    end

    subgraph Core["核心业务服务"]
        JOB[job-service<br/>:8002]
        MATCH[matching-service<br/>:8003]
        PIPELINE[pipeline-service<br/>:8004]
        BILLING[billing-service<br/>:8005]
        GUARANTEE[guarantee-service<br/>:8006]
    end

    subgraph AI["AI 服务层"]
        AI_SVC[ai-service<br/>:8007]
        RESUME[resume-parser]
        EMBEDDING[embedding-service<br/>:8008]
        ADVISOR[advisor-service<br/>:8009]
        VERIFY[verification-service<br/>:8010]
    end

    subgraph Infrastructure["基础设施层"]
        PG[(PostgreSQL<br/>:5432)]
        REDIS[(Redis<br/>:6379)]
        KAFKA[(Kafka<br/>:9092)]
        QDRANT[(Qdrant<br/>:6333)]
    end

    %% Frontend to Gateway
    EMP --> NGINX
    CAND --> NGINX

    %% Gateway routing
    NGINX --> USER
    NGINX --> JOB
    NGINX --> MATCH
    NGINX --> PIPELINE
    NGINX --> BILLING
    NGINX --> GUARANTEE
    NGINX --> AI_SVC
    NGINX --> EMBEDDING
    NGINX --> ADVISOR
    NGINX --> VERIFY

    %% Auth dependencies
    USER --> JWT
    USER --> PG
    USER --> REDIS

    %% Core service dependencies
    JOB --> PG
    JOB --> REDIS
    JOB --> KAFKA
    JOB --> QDRANT

    MATCH --> PG
    MATCH --> KAFKA
    MATCH --> QDRANT

    PIPELINE --> PG
    PIPELINE --> REDIS

    BILLING --> PG
    BILLING --> KAFKA

    GUARANTEE --> PG
    GUARANTEE --> KAFKA

    %% AI service dependencies
    AI_SVC --> PG
    AI_SVC --> KAFKA

    RESUME --> AI_SVC
    EMBEDDING --> QDRANT
    EMBEDDING --> KAFKA

    ADVISOR --> PG
    ADVISOR --> KAFKA

    VERIFY --> PG

    %% Kafka event flow
    KAFKA --> BILLING
    KAFKA --> GUARANTEE
    KAFKA --> NOTIFY[notification-service<br/>:8011]
```

### 技术栈概览

| 层级 | 技术 | 说明 |
|------|------|------|
| **前端** | React 18 + TypeScript + Vite | 双端应用 |
| **网关** | Nginx | 反向代理 + 负载均衡 |
| **后端** | FastAPI + SQLAlchemy 2.0 | 异步 Python 服务 |
| **数据库** | PostgreSQL 15 | 主数据存储 |
| **缓存** | Redis 7 | 会话 + 缓存 |
| **消息队列** | Apache Kafka | 事件驱动架构 |
| **向量数据库** | Qdrant | 语义检索 |

---

## 🚀 快速开始

### 前置要求

| 要求 | 最低版本 | 推荐版本 |
|------|----------|----------|
| Docker Engine | 24.0+ | Latest |
| Docker Compose | v2.20+ | Latest |
| 内存 | 4 GB | 8 GB |
| 磁盘空间 | 20 GB | 50 GB |

### 启动步骤

#### 1. 克隆项目

```bash
git clone https://github.com/your-org/highermatch.git
cd highermatch
```

#### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，配置必要的密钥
vim .env
```

#### 3. 启动所有服务

```bash
# 首次启动 (构建 + 运行)
docker compose up -d --build

# 后续启动 (仅运行)
docker compose up -d
```

#### 4. 验证服务状态

```bash
# 查看所有服务状态
docker compose ps

# 检查健康状态
curl http://localhost/health

# 查看实时日志
docker compose logs -f
```

#### 5. 访问应用

| 服务 | URL | 说明 |
|------|-----|------|
| 雇主端 | http://localhost | 主站点 (Nginx) |
| 雇主端 | http://localhost:5173 | 开发模式 |
| 候选人端 | http://localhost:5174 | 开发模式 |
| API 文档 | http://localhost:8001/docs | User Service |
| API 文档 | http://localhost:8002/docs | Job Service |
| API 文档 | http://localhost:8007/docs | AI Service |

---

## ⚙️ 环境变量说明

### .env 文件配置

```bash
# =============================================
# HigherMatch™ 环境变量配置
# =============================================

# ============ 基础配置 ============

# 项目名称
PROJECT_NAME=highermatch
ENVIRONMENT=development

# 日志级别 (DEBUG/INFO/WARNING/ERROR)
LOG_LEVEL=INFO

# ============ 数据库配置 ============

# PostgreSQL
POSTGRES_USER=highermatch
POSTGRES_PASSWORD=your_secure_password_here
POSTGRES_DB=highermatch_dev
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# 数据库连接 URL (Docker 内部)
DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}

# ============ Redis 配置 ============

REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password_here
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0

# ============ Kafka 配置 ============

KAFKA_BOOTSTRAP_SERVERS=kafka:29092
KAFKA_ZOOKEEPER_CONNECT=zookeeper:2181
KAFKA_CONSUMER_GROUP=highermatch-group

# ============ Qdrant 配置 ============

QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_URL=http://qdrant:6333

# ============ JWT 配置 ============

# JWT 密钥 (生产环境务必修改!)
JWT_SECRET_KEY=change-this-to-a-very-long-random-string-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# ============ AI 服务配置 ============

# OpenAI API Key (必需)
OPENAI_API_KEY=sk-1c9b15f7bdc74b349fc9ff1e613a86e2  # 千问模型Key
OPENAI_MODEL=qianwen-1
OPENAI_MAX_TOKENS=2000
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qianwen-1
LLM_TIMEOUT=60

# ============ 服务端口 ============

USER_SERVICE_PORT=8001
JOB_SERVICE_PORT=8002
MATCHING_SERVICE_PORT=8003
PIPELINE_SERVICE_PORT=8004
BILLING_SERVICE_PORT=8005
GUARANTEE_SERVICE_PORT=8006
AI_SERVICE_PORT=8007
EMBEDDING_SERVICE_PORT=8008
ADVISOR_SERVICE_PORT=8009
VERIFY_SERVICE_PORT=8010
NOTIFICATION_SERVICE_PORT=8011

# ============ CORS 配置 ============

# 允许的前端域名
CORS_ORIGINS=http://localhost:5173,http://localhost:5174,http://localhost

# ============ 文件存储 ============

# 简历文件存储路径
RESUME_UPLOAD_DIR=/app/uploads/resumes
MAX_FILE_SIZE_MB=10

# ============ Nginx 配置 ============

NGINX_PORT=80
NGINX_WORKER_PROCESSES=auto
NGINX_WORKER_CONNECTIONS=1024
```

### 必需的环境变量

| 变量名 | 必需 | 说明 | 示例 |
|--------|------|------|------|
| `POSTGRES_PASSWORD` | ✅ | PostgreSQL 密码 | `MySecurePass123!` |
| `REDIS_PASSWORD` | ✅ | Redis 密码 | `RedisPass456!` |
| `JWT_SECRET_KEY` | ✅ | JWT 签名密钥 | 64位随机字符串 |
| `OPENAI_API_KEY` | ✅ | OpenAI/千问兼容 API Key | `sk-...` |
| `LLM_BASE_URL` | ✅ | 千问 OpenAI 兼容模式 URL | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| `LLM_MODEL` | ✅ | 千问模型名称 | `qianwen-1` |

---

## 📁 项目结构

```
highermatch/
├── .env.example                    # 环境变量模板
├── docker-compose.yml              # Docker Compose 配置
├── Makefile                        # 开发辅助命令
│
├── nginx/                          # Nginx 配置
│   ├── nginx.conf                  # 主配置
│   └── conf.d/                     # 站点配置
│       └── default.conf
│
├── scripts/                        # 脚本
│   └── init-db.sql                # 数据库初始化
│
├── docs/                           # 文档
│   ├── troubleshooting.md          # 联调排查 SOP
│   └── demo_script.md             # 验收演示脚本
│
├── frontend/                        # 前端应用
│   ├── employer-portal/            # 雇主端 (React)
│   └── candidate-portal/           # 候选人端 (React Mobile)
│
├── services/                       # 后端微服务
│   ├── user_service/               # 用户认证服务
│   ├── job_service/               # 职位管理服务
│   ├── matching_service/          # 智能匹配服务
│   ├── pipeline_service/          # 招聘管道服务
│   ├── billing_service/           # 账单服务
│   ├── guarantee_service/          # 保障服务
│   ├── ai_service/                # AI 服务
│   ├── embedding_service/          # 向量嵌入服务
│   ├── advisor_service/            # AI 职业顾问服务
│   ├── verification_service/        # 认证服务
│   └── notification_service/        # 通知服务
│
├── shared/                          # 共享代码
│   ├── models/                     # 共享数据模型
│   └── utils/                      # 共享工具函数
│
├── tests/                           # 测试
│   ├── e2e/                        # E2E 测试
│   └── test_matching.py
│
└── .github/
    └── workflows/
        └── ci.yml                  # CI/CD 配置
```

---

## 🔧 开发命令

使用 `make` 命令简化开发流程：

```bash
# Docker 操作
make up              # 启动所有服务
make down            # 停止所有服务
make logs            # 查看日志

# 测试
make test            # 运行所有测试
make test-e2e        # 运行 E2E 测试
make test-backend    # 后端单元测试

# 开发
make dev-backend     # 启动后端开发服务器
make dev-frontend   # 启动前端开发服务器

# 代码质量
make lint            # 代码检查
make format          # 代码格式化
make health          # 健康检查
```

完整命令列表请查看 [Makefile](Makefile)。

---

## 🌐 API 服务列表

| 服务 | 端口 | 主要功能 |
|------|------|----------|
| user-service | 8001 | 用户注册、登录、JWT 认证 |
| job-service | 8002 | 职位 CRUD、AI-JD 提取 |
| matching-service | 8003 | 候选人匹配、向量检索 |
| pipeline-service | 8004 | 招聘管道看板、WebSocket |
| billing-service | 8005 | 账单生成、支付回调 |
| guarantee-service | 8006 | 90 天求职保障 |
| ai-service | 8007 | NLU、简历解析 |
| embedding-service | 8008 | 向量化嵌入 |
| advisor-service | 8009 | AI 职业顾问 |
| verification-service | 8010 | 学历、工作经历认证 |
| notification-service | 8011 | 邮件、站内信通知 |

---

## 📊 核心业务流程

### TC-001: 雇主完整招聘流程

```mermaid
sequenceDiagram
    participant E as 雇主端
    participant API as API Gateway
    participant JOB as Job Service
    participant MATCH as Matching Service
    participant AI as AI Service
    participant QDRANT as Qdrant
    participant KAFKA as Kafka
    participant BILL as Billing Service

    E->>API: 1. 输入岗位需求 (语音/文本)
    API->>JOB: 创建职位
    JOB->>AI: 提取 JD 结构化信息
    AI-->>JOB: JD 解析结果
    JOB-->>E: 岗位发布成功

    Note over E,KAFKA: 异步: AI 匹配候选人

    JOB->>MATCH: 触发匹配任务
    MATCH->>QDRANT: 向量相似度检索
    QDRANT-->>MATCH: Top-K 候选人
    MATCH->>KAFKA: 发布 match.completed 事件

    E->>API: 2. 查询 Shortlist
    API->>MATCH: 获取匹配列表
    MATCH-->>E: 候选人列表

    E->>API: 3. 拖拽移动候选人
    API->>PIPELINE: 更新管道状态
    PIPELINE-->>E: WebSocket 广播更新

    E->>API: 4. 确认入职
    API->>KAFKA: 发布 onboarding.confirmed
    KAFKA->>BILL: 计算账单
    BILL-->>E: 生成发票

    Note over E,BILL: 90天保障期生效
```

---

## 🧪 测试

### 运行测试

```bash
# 安装测试依赖
pip install -r tests/e2e/requirements.txt
playwright install chromium

# 运行所有测试
make test

# 运行 E2E 测试
make test-e2e

# 运行带界面的 E2E 测试 (调试)
make test-e2e-headed
```

### 测试用例

| 用例编号 | 描述 | 覆盖范围 |
|----------|------|----------|
| TC-001 | 雇主完整招聘流程 | 端到端 |
| TC-002 | 候选人申请流程 | 端到端 |

---

## 📝 团队鸣谢

本项目由 **HigherMatch™ 实习生团队** 共同开发完成。

### 核心贡献者

| 角色 | 贡献内容 |
|------|----------|
| 🏗️ **系统架构** | 微服务拆分、Kafka 事件驱动设计 |
| 🎨 **前端开发** | 雇主端、候选人端双端应用 |
| ⚙️ **后端开发** | 7 个微服务实现 |
| 🤖 **AI 工程** | NLP 解析、向量匹配、AI 顾问 |
| 📊 **DevOps** | Docker Compose、CI/CD 流水线 |
| 📝 **测试** | 单元测试、E2E 测试 |
| 📚 **文档** | 技术文档、API 文档 |

### 技术指导

- 感谢所有导师的技术指导与代码 Review
- 感谢开源社区提供的优秀工具

---

## 📄 License

Copyright © 2024 **HigherMatch™**. All rights reserved.

本项目仅供学习与研究使用。

---

## 🔗 相关链接

- 📖 [API 文档](http://localhost:8001/docs)
- 🐛 [问题反馈](https://github.com/your-org/highermatch/issues)
- 📦 [Docker Hub](https://hub.docker.com/u/highermatch)

---

<p align="center">
  <strong>HigherMatch™</strong> - 让每一次招聘都精准匹配
</p>
