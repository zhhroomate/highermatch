# =============================================================================
# HigherMatch™ - FastAPI Service Dockerfile Template
# =============================================================================
#
# 多阶段构建 Docker 镜像
# - 第一阶段: 构建依赖
# - 第二阶段: 生产运行
#
# 使用方法:
#   1. 复制此 Dockerfile 到服务目录
#   2. 根据需要修改 ARG SERVICE_NAME 和 EXPOSE 端口
#   3. 确保 requirements.txt 存在
#
# 构建命令:
#   docker build -t highermatch-user-service .
#
# 运行命令:
#   docker run -d -p 8001:8001 --env-file .env highermatch-user-service
#
# =============================================================================

# ==================== 第一阶段: 构建依赖 ====================
FROM python:3.11-slim AS builder

# 设置构建参数
ARG SERVICE_NAME=highermatch-service
ARG SERVICE_PORT=8000
ARG PYTHONUNBUFFERED=1
ARG PYTHONDONTWRITEBYTECODE=1
ARG PIP_NO_CACHE_DIR=1
ARG PIP_DISABLE_PIP_VERSION_CHECK=1

# 设置环境变量
ENV PYTHONUNBUFFERED=${PYTHONUNBUFFERED} \
    PYTHONDONTWRITEBYTECODE=${PYTHONDONTWRITEBYTECODE} \
    PIP_NO_CACHE_DIR=${PIP_NO_CACHE_DIR} \
    PIP_DISABLE_PIP_VERSION_CHECK=${PIP_DISABLE_PIP_VERSION_CHECK}

# 安装构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    # 系统工具
    curl \
    # PostgreSQL 客户端库 (用于 asyncpg)
    libpq-dev \
    # 编译工具 (用于某些 Python 包)
    build-essential \
    # 区域设置 (用于时区支持)
    locales \
    # tzdata 用于设置默认时区
    && locale-gen en_US.UTF-8 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 设置默认区域
ENV LANG=en_US.UTF-8 \
    LC_ALL=en_US.UTF-8 \
    TZ=Asia/Shanghai

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 预下载 Python 依赖到 wheel 缓存
RUN pip install --upgrade pip && \
    pip wheel --no-cache-dir --wheel-dir=/app/wheels -r requirements.txt

# ==================== 第二阶段: 生产运行 ====================
FROM python:3.11-slim AS production

# 设置构建参数
ARG SERVICE_NAME=highermatch-service
ARG SERVICE_PORT=8000
ARG UID=1001
ARG GID=1001

# 标签
LABEL service="${SERVICE_NAME}" \
      maintainer="HigherMatch Team <tech@highermatch.com>" \
      description="HigherMatch™ ${SERVICE_NAME} Docker Image"

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    LANG=en_US.UTF-8 \
    LC_ALL=en_US.UTF-8 \
    TZ=Asia/Shanghai \
    SERVICE_NAME=${SERVICE_NAME} \
    SERVICE_PORT=${SERVICE_PORT}

# 创建非 root 用户和组
RUN groupadd --gid ${GID} appgroup && \
    useradd --uid ${UID} --gid ${GID} --shell /bin/bash --create-home appuser

# 安装运行时依赖 (不包括构建工具)
RUN apt-get update && apt-get install -y --no-install-recommends \
    # 运行时库
    libpq5 \
    # tzdata 用于时区支持
    tzdata \
    # 基础网络工具
    curl \
    ca-certificates \
    # 清理
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 设置时区为上海
RUN ln -snf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && \
    echo "Asia/Shanghai" > /etc/timezone

# 设置工作目录
WORKDIR /app

# 复制预下载的 wheel 文件
COPY --from=builder /app/wheels /wheels

# 从 wheel 安装 Python 依赖
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --no-index --find-links=/wheels /wheels/*.whl && \
    rm -rf /wheels

# 复制应用代码
COPY --chown=appuser:appgroup ./app ./app

# 创建日志目录
RUN mkdir -p /app/logs && \
    chown -R appuser:appgroup /app/logs

# 创建上传目录 (如果需要)
RUN mkdir -p /app/uploads && \
    chown -R appuser:appgroup /app/uploads

# 切换到非 root 用户
USER appuser

# ==================== 端口配置 ====================
# 暴露服务端口 (可被 docker run -p 参数覆盖)
EXPOSE ${SERVICE_PORT}

# ==================== 健康检查 ====================
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:${SERVICE_PORT}/health || exit 1

# ==================== 启动命令 ====================
# 默认启动命令，可通过 docker run 参数覆盖
# CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "${SERVICE_PORT}"]

# 启动脚本 (可选)
# 包含更复杂的启动逻辑，如等待依赖服务就绪
CMD ["sh", "-c", "python -m uvicorn app.main:app --host 0.0.0.0 --port ${SERVICE_PORT} --workers 1"]

# =============================================================================
# 构建说明
# =============================================================================
# 使用此 Dockerfile 时，请确保项目结构如下:
#
# your-service/
# ├── Dockerfile
# ├── requirements.txt
# └── app/
#     ├── __init__.py
#     ├── main.py          <- 复制 template/main.py
#     ├── routers/
#     ├── models/
#     ├── schemas/
#     └── services/
#
# 构建多架构镜像 (可选):
#   docker buildx build --platform linux/amd64,linux/arm64 -t highermatch-service:latest .
#
# 使用 docker-compose 构建 (推荐):
#   docker-compose build your-service
# =============================================================================
