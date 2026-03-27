---
AIGC:
    ContentProducer: Minimax Agent AI
    ContentPropagator: Minimax Agent AI
    Label: AIGC
    ProduceID: "00000000000000000000000000000000"
    PropagateID: "00000000000000000000000000000000"
    ReservedCode1: 3044022078128467983a08b7cd6a54e9c2e7d646799cb31728f846bf3b1b1c5db8167bc202206b2a474d3e308b930d318ccc1a0fb81a3126e3a017da3c9a02d3e436864a5e11
    ReservedCode2: 30460221008a40987b50dc24df64175cc48d2315360fe751fd4a0ee8bebea083173ca548fe022100f404ca2665f763105dca2e5b23f2f82e1a1e0a995474cf1bee088bfcbab0b603
---

# HigherMatch™ E2E Tests

Playwright E2E 测试套件，用于验证 HigherMatch™ AI 招聘平台的端到端功能。

## 测试用例

### TC-001: 雇主完整招聘流程
- 雇主登录
- 创建岗位（文本模式）
- 等待 AI 匹配候选人
- 管道看板操作
- 模拟入职确认
- 验证账单生成

### TC-002: 候选人流程
- 候选人登录
- 上传简历
- 验证档案完成度
- 申请岗位
- 追踪申请状态

## 环境要求

### 前端服务
```bash
# 雇主端
cd frontend/employer-portal
pnpm dev  # http://localhost:5173

# 候选人端
cd frontend/candidate-portal
pnpm dev  # http://localhost:5174
```

### 后端服务
```bash
# 启动所有后端服务
docker-compose up -d

# 或单独启动
cd services/user_service && uvicorn app.main:app --port 8001
cd services/job_service && uvicorn app.main:app --port 8002
cd services/pipeline_service && uvicorn app.main:app --port 8003
```

### 基础设施
```bash
# PostgreSQL, Redis, Kafka, Qdrant
docker-compose up -d postgres redis kafka qdrant
```

## 安装依赖

```bash
cd tests/e2e
pip install -r requirements.txt

# 安装 Playwright 浏览器
playwright install chromium
```

## 运行测试

### 运行所有测试
```bash
pytest tests/e2e/ -v
```

### 运行特定测试用例
```bash
# TC-001 雇主流程
pytest tests/e2e/test_tc001.py -v

# TC-002 候选人流程
pytest tests/e2e/test_tc002.py -v
```

### 运行完整流程测试
```bash
pytest tests/e2e/ -v -m full_flow
```

### 运行特定标记的测试
```bash
# 仅雇主测试
pytest tests/e2e/ -v -m employer

# 仅候选人测试
pytest tests/e2e/ -v -m candidate
```

### 带界面运行（调试）
```bash
pytest tests/e2e/test_tc001.py -v --headed
```

### 并行运行
```bash
pytest tests/e2e/ -v -n auto
```

## 环境变量

```bash
# .env 文件
EMPLOYER_PORTAL_URL=http://localhost:5173
CANDIDATE_PORTAL_URL=http://localhost:5174
API_BASE_URL=http://localhost:8000
```

## 测试报告

### HTML 报告
```bash
pytest tests/e2e/ -v --html=report.html --self-contained-html
```

### 覆盖率报告
```bash
pytest tests/e2e/ -v --cov=tests/e2e --cov-report=html
```

## 常见问题

### 1. 浏览器安装失败
```bash
# 使用国内镜像
playwright install chromium --mirror=https://npmmirror.com/mirrors/playwright/
```

### 2. 测试超时
增加超时时间或检查服务是否正常运行：
```bash
# 检查服务
curl http://localhost:5173  # 雇主端
curl http://localhost:5174  # 候选人端
curl http://localhost:8000/health  # API
```

### 3. 上传文件失败
确保测试用 PDF 文件存在：
```bash
ls tests/e2e/dummy_resume.pdf
```

## 目录结构

```
tests/e2e/
├── __init__.py
├── conftest.py              # Pytest fixtures
├── playwright.config.py      # Playwright 配置
├── pytest.ini               # Pytest 配置
├── requirements.txt         # Python 依赖
├── README.md                # 本文件
├── dummy_resume.pdf         # 测试用简历
├── test_tc001.py           # TC-001 雇主流程
└── test_tc002.py           # TC-002 候选人流程
```

## 编写新测试

### 添加新测试用例
```python
import pytest

class TestNewFlow:
    @pytest.mark.asyncio
    async def test_new_flow(self, page):
        await page.goto("http://localhost:5173")
        # 测试逻辑...
```

### 添加新 Fixture
在 `conftest.py` 中添加：
```python
@pytest_asyncio.fixture
async def new_fixture():
    # Setup
    yield value
    # Teardown
```

## CI/CD 集成

### GitHub Actions
```yaml
- name: Run E2E Tests
  run: |
    pip install -r tests/e2e/requirements.txt
    playwright install chromium
    pytest tests/e2e/ -v --html=report.html
```

## 联系方式

如有测试相关问题，请联系 QA 团队。
