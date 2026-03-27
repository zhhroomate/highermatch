# HigherMatch™ AI 招聘平台 - Makefile
# ===================================
#
# 本 Makefile 提供本地开发的常用命令
#
# 使用方法:
#   make [target]
#
# 版本: 1.0.0

# ==================== 默认目标 ====================

.DEFAULT_GOAL := help

# ==================== 颜色定义 ====================

BOLD := \033[1m
GREEN := \033[0;32m
YELLOW := \033[0;33m
BLUE := \033[0;34m
RED := \033[0;31m
NC := \033[0m # No Color

# ==================== 变量定义 ====================

# Docker
COMPOSE := docker-compose
COMPOSE_FILES := -f docker-compose.yml
DOCKER_NETWORK := highermatch-network

# 服务
BACKEND_SERVICES := user-service job-service ai-service pipeline-service billing-service guarantee-service notification-service
FRONTEND_SERVICES := employer-portal candidate-portal
ALL_SERVICES := $(BACKEND_SERVICES) $(FRONTEND_SERVICES)

# 测试
PYTEST := pytest
VITEST := pnpm --filter
TEST_DIR := tests/e2e

# ==================== 帮助信息 ====================

.PHONY: help
help: ## 显示帮助信息
	@echo ""
	@echo "$(BOLD)$(BLUE)HigherMatch™ AI 招聘平台 - 开发命令$(NC)"
	@echo ""
	@echo "$(BOLD)用法:$(NC)"
	@echo "  make $(GREEN)<target>$(NC)"
	@echo ""
	@echo "$(BOLD)Docker Compose 命令:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(BOLD)开发命令:$(NC)"
	@grep -E '^dev_[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(BOLD)测试命令:$(NC)"
	@grep -E '^test_[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(BOLD)构建命令:$(NC)"
	@grep -E '^build_[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""

# ==================== Docker Compose 命令 ====================

.PHONY: up
up: ## 启动所有容器 (后台运行)
	@echo "$(GREEN)启动所有服务...$(NC)"
	$(COMPOSE) $(COMPOSE_FILES) up -d
	@echo "$(GREEN)等待服务启动...$(NC)"
	@sleep 10
	@echo "$(GREEN)服务状态:$(NC)"
	@$(COMPOSE) $(COMPOSE_FILES) ps

.PHONY: up-build
up-build: ## 构建并启动所有容器
	@echo "$(GREEN)构建并启动所有服务...$(NC)"
	$(COMPOSE) $(COMPOSE_FILES) up -d --build
	@echo "$(GREEN)等待服务启动...$(NC)"
	@sleep 15
	@echo "$(GREEN)服务状态:$(NC)"
	@$(COMPOSE) $(COMPOSE_FILES) ps

.PHONY: down
down: ## 停止所有容器
	@echo "$(YELLOW)停止所有服务...$(NC)"
	$(COMPOSE) $(COMPOSE_FILES) down
	@echo "$(GREEN)所有服务已停止$(NC)"

.PHONY: restart
restart: down up ## 重启所有容器

.PHONY: logs
logs: ## 查看所有容器日志
	$(COMPOSE) $(COMPOSE_FILES) logs -f --tail=100

.PHONY: logs-service
logs-service: ## 查看指定服务日志 (用法: make logs-service SERVICE=user-service)
	@if [ -z "$(SERVICE)" ]; then \
		echo "$(RED)请指定服务名: make logs-service SERVICE=user-service$(NC)"; \
	else \
		$(COMPOSE) $(COMPOSE_FILES) logs -f $(SERVICE) --tail=100; \
	fi

.PHONY: ps
ps: ## 查看容器状态
	$(COMPOSE) $(COMPOSE_FILES) ps

.PHONY: top
top: ## 查看容器资源使用
	$(COMPOSE) $(COMPOSE_FILES) top

.PHONY: clean
clean: ## 清理未使用的 Docker 资源
	@echo "$(YELLOW)清理 Docker 资源...$(NC)"
	docker system prune -f
	docker volume prune -f
	@echo "$(GREEN)清理完成$(NC)"

.PHONY: clean-all
clean-all: down ## 清理所有 Docker 资源 (包括数据卷)
	@echo "$(YELLOW)清理所有 Docker 资源...$(NC)"
	$(COMPOSE) $(COMPOSE_FILES) down -v --rmi all
	docker system prune -af
	@echo "$(GREEN)清理完成$(NC)"

# ==================== 服务特定命令 ====================

.PHONY: up-service
up-service: ## 启动指定服务 (用法: make up-service SERVICE=user-service)
	@if [ -z "$(SERVICE)" ]; then \
		echo "$(RED)请指定服务名: make up-service SERVICE=user-service$(NC)"; \
	else \
		$(COMPOSE) $(COMPOSE_FILES) up -d $(SERVICE); \
	fi

.PHONY: down-service
down-service: ## 停止指定服务 (用法: make down-service SERVICE=user-service)
	@if [ -z "$(SERVICE)" ]; then \
		echo "$(RED)请指定服务名: make down-service SERVICE=user-service$(NC)"; \
	else \
		$(COMPOSE) $(COMPOSE_FILES) stop $(SERVICE); \
	fi

.PHONY: restart-service
restart-service: ## 重启指定服务 (用法: make restart-service SERVICE=user-service)
	@if [ -z "$(SERVICE)" ]; then \
		echo "$(RED)请指定服务名: make restart-service SERVICE=user-service$(NC)"; \
	else \
		$(COMPOSE) $(COMPOSE_FILES) restart $(SERVICE); \
	fi

.PHONY: logs-service
logs-service: ## 查看指定服务日志 (用法: make logs-service SERVICE=user-service)
	@if [ -z "$(SERVICE)" ]; then \
		echo "$(RED)请指定服务名: make logs-service SERVICE=user-service$(NC)"; \
	else \
		$(COMPOSE) $(COMPOSE_FILES) logs -f $(SERVICE); \
	fi

# ==================== 数据库命令 ====================

.PHONY: db-init
db-init: ## 初始化数据库
	@echo "$(GREEN)初始化数据库...$(NC)"
	$(COMPOSE) $(COMPOSE_FILES) exec postgres psql -U highermatch -d highermatch_dev -f /docker-entrypoint-initdb.d/init-db.sql

.PHONY: db-migrate
db-migrate: ## 运行数据库迁移
	@echo "$(GREEN)运行数据库迁移...$(NC)"
	@for service in $(BACKEND_SERVICES); do \
		echo "$(BLUE)迁移 $$service ...$(NC)"; \
		$(COMPOSE) $(COMPOSE_FILES) exec $$service alembic upgrade head || true; \
	done

.PHONY: db-reset
db-reset: down clean-all ## 重置数据库 (谨慎使用!)
	@echo "$(RED)警告: 将删除所有数据并重新初始化数据库!$(NC)"
	@read -p "确认继续? (yes/no): " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		$(COMPOSE) $(COMPOSE_FILES) up -d postgres; \
		sleep 5; \
		$(MAKE) db-init; \
		$(MAKE) up; \
	else \
		echo "取消操作"; \
	fi

.PHONY: db-shell
db-shell: ## 连接数据库 shell
	$(COMPOSE) $(COMPOSE_FILES) exec postgres psql -U highermatch -d highermatch_dev

# ==================== 开发命令 ====================

.PHONY: dev-backend
dev-backend: ## 启动后端开发服务器
	@echo "$(GREEN)启动后端开发服务器...$(NC)"
	cd services/user_service && uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload &
	cd services/job_service && uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload &
	cd services/pipeline_service && uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload &
	cd services/billing_service && uvicorn app.main:app --host 0.0.0.0 --port 8005 --reload &
	wait

.PHONY: dev-frontend
dev-frontend: ## 启动前端开发服务器
	@echo "$(GREEN)启动前端开发服务器...$(NC)"
	cd frontend/employer-portal && pnpm dev &
	cd frontend/candidate-portal && pnpm dev &
	wait

.PHONY: dev-all
dev-all: ## 启动所有开发服务器
	@echo "$(GREEN)启动所有开发服务器...$(NC)"
	$(MAKE) up
	$(MAKE) dev-backend &
	$(MAKE) dev-frontend &
	wait

# ==================== 测试命令 ====================

.PHONY: test
test: test-backend test-frontend ## 运行所有测试

.PHONY: test-backend
test-backend: ## 运行后端单元测试
	@echo "$(GREEN)运行后端单元测试...$(NC)"
	@for service in $(BACKEND_SERVICES); do \
		echo "$(BLUE)测试 $$service ...$(NC)"; \
		cd services/$$service && $(PYTEST) tests/ -v --cov=app --cov-report=term-missing || true; \
		cd ../..; \
	done

.PHONY: test-frontend
test-frontend: ## 运行前端测试
	@echo "$(GREEN)运行前端测试...$(NC)"
	@cd frontend/employer-portal && pnpm test --run || true
	@cd frontend/candidate-portal && pnpm test --run || true

.PHONY: test-e2e
test-e2e: ## 运行 E2E 测试
	@echo "$(GREEN)运行 E2E 测试...$(NC)"
	@if ! docker ps | grep -q highermatch; then \
		echo "$(YELLOW)Docker 服务未运行，正在启动...$(NC)"; \
		$(MAKE) up; \
		sleep 20; \
	fi
	cd $(TEST_DIR) && pip install -r requirements.txt -q
	playwright install chromium
	EMPLOYER_PORTAL_URL=http://localhost \
	CANDIDATE_PORTAL_URL=http://localhost:5174 \
	API_BASE_URL=http://localhost:8000 \
	$(PYTEST) -v --timeout=300

.PHONY: test-e2e-headed
test-e2e-headed: ## 运行 E2E 测试 (带界面)
	@echo "$(GREEN)运行 E2E 测试 (带界面)...$(NC)"
	@if ! docker ps | grep -q highermatch; then \
		echo "$(YELLOW)Docker 服务未运行，正在启动...$(NC)"; \
		$(MAKE) up; \
		sleep 20; \
	fi
	cd $(TEST_DIR) && pip install -r requirements.txt -q
	PLAYWRIGHT_HEADED=1 $(PYTEST) -v --timeout=300

.PHONY: test-coverage
test-coverage: ## 生成测试覆盖率报告
	@echo "$(GREEN)生成测试覆盖率报告...$(NC)"
	@for service in $(BACKEND_SERVICES); do \
		echo "$(BLUE)覆盖率报告 $$service ...$(NC)"; \
		cd services/$$service && $(PYTEST) tests/ --cov=app --cov-report=html --cov-report=xml || true; \
		cd ../..; \
	done
	@echo "$(GREEN)覆盖率报告已生成在各服务的 htmlcov/ 目录$(NC)"

.PHONY: test-single
test-single: ## 运行单个测试文件 (用法: make test-single SERVICE=user-service TEST_FILE=test_auth.py)
	@if [ -z "$(SERVICE)" ] || [ -z "$(TEST_FILE)" ]; then \
		echo "$(RED)请指定服务名和测试文件: make test-single SERVICE=user-service TEST_FILE=test_auth.py$(NC)"; \
	else \
		cd services/$(SERVICE) && $(PYTEST) tests/$(TEST_FILE) -v; \
	fi

# ==================== 构建命令 ====================

.PHONY: build
build: build-backend build-frontend ## 构建所有镜像

.PHONY: build-backend
build-backend: ## 构建后端镜像
	@echo "$(GREEN)构建后端镜像...$(NC)"
	$(COMPOSE) $(COMPOSE_FILES) build $(BACKEND_SERVICES)

.PHONY: build-frontend
build-frontend: ## 构建前端镜像
	@echo "$(GREEN)构建前端镜像...$(NC)"
	$(COMPOSE) $(COMPOSE_FILES) build employer-portal candidate-portal

.PHONY: build-service
build-service: ## 构建指定服务镜像 (用法: make build-service SERVICE=user-service)
	@if [ -z "$(SERVICE)" ]; then \
		echo "$(RED)请指定服务名: make build-service SERVICE=user-service$(NC)"; \
	else \
		$(COMPOSE) $(COMPOSE_FILES) build $(SERVICE); \
	fi

.PHONY: rebuild
rebuild: down build up ## 重新构建并启动

.PHONY: rebuild-service
rebuild-service: ## 重新构建指定服务 (用法: make rebuild-service SERVICE=user-service)
	@if [ -z "$(SERVICE)" ]; then \
		echo "$(RED)请指定服务名: make rebuild-service SERVICE=user-service$(NC)"; \
	else \
		$(COMPOSE) $(COMPOSE_FILES) rm -f $(SERVICE); \
		$(COMPOSE) $(COMPOSE_FILES) build $(SERVICE); \
		$(COMPOSE) $(COMPOSE_FILES) up -d $(SERVICE); \
	fi

# ==================== Docker Hub 命令 ====================

.PHONY: docker-login
docker-login: ## 登录 Docker Hub
	@echo "$(GREEN)登录 Docker Hub...$(NC)"
	@read -p "Docker Hub 用户名: " username; \
	 docker login -u $$username

.PHONY: docker-push
docker-push: ## 推送镜像到 Docker Hub
	@echo "$(GREEN)推送镜像到 Docker Hub...$(NC)"
	@read -p "Docker Hub 用户名: " username; \
	docker tag highermatch-user-service:latest $$username/highermatch-user-service:latest; \
	docker tag highermatch-job-service:latest $$username/highermatch-job-service:latest; \
	docker tag highermatch-ai-service:latest $$username/highermatch-ai-service:latest; \
	docker tag highermatch-employer-portal:latest $$username/highermatch-employer-portal:latest; \
	docker tag highermatch-candidate-portal:latest $$username/highermatch-candidate-portal:latest; \
	docker push $$username/highermatch-user-service:latest; \
	docker push $$username/highermatch-job-service:latest; \
	docker push $$username/highermatch-ai-service:latest; \
	docker push $$username/highermatch-employer-portal:latest; \
	docker push $$username/highermatch-candidate-portal:latest; \
	echo "$(GREEN)推送完成!$(NC)"

# ==================== 代码质量命令 ====================

.PHONY: lint
lint: lint-python lint-js ## 运行代码检查

.PHONY: lint-python
lint-python: ## Python 代码检查
	@echo "$(GREEN)Python 代码检查...$(NC)"
	pip install black flake8 mypy isort
	black --check services/
	isort --check-only services/
	flake8 services/ --max-line-length=120 --ignore=E501,W503

.PHONY: lint-js
lint-js: ## JavaScript 代码检查
	@echo "$(GREEN)JavaScript 代码检查...$(NC)"
	cd frontend/employer-portal && pnpm lint || true
	cd frontend/candidate-portal && pnpm lint || true

.PHONY: format
format: format-python format-js ## 格式化代码

.PHONY: format-python
format-python: ## 格式化 Python 代码
	@echo "$(GREEN)格式化 Python 代码...$(NC)"
	pip install black isort
	black services/
	isort services/

.PHONY: format-js
format-js: ## 格式化 JavaScript 代码
	@echo "$(GREEN)格式化 JavaScript 代码...$(NC)"
	cd frontend/employer-portal && pnpm format || true
	cd frontend/candidate-portal && pnpm format || true

# ==================== 健康检查 ====================

.PHONY: health
health: ## 检查所有服务健康状态
	@echo "$(GREEN)检查服务健康状态...$(NC)"
	@echo ""
	@echo "$(BOLD)后端服务:$(NC)"
	@curl -s http://localhost:8001/health | jq -r '.status' 2>/dev/null && echo " user-service" || echo "$(RED)✗ user-service$(NC)"
	@curl -s http://localhost:8002/health | jq -r '.status' 2>/dev/null && echo " job-service" || echo "$(RED)✗ job-service$(NC)"
	@curl -s http://localhost:8004/health | jq -r '.status' 2>/dev/null && echo " ai-service" || echo "$(RED)✗ ai-service$(NC)"
	@echo ""
	@echo "$(BOLD)前端服务:$(NC)"
	@curl -s -o /dev/null -w "%{http_code}" http://localhost:5173 | grep -q "200" && echo "$(GREEN)✓ employer-portal (5173)$(NC)" || echo "$(RED)✗ employer-portal$(NC)"
	@curl -s -o /dev/null -w "%{http_code}" http://localhost:5174 | grep -q "200" && echo "$(GREEN)✓ candidate-portal (5174)$(NC)" || echo "$(RED)✗ candidate-portal$(NC)"
	@echo ""
	@echo "$(BOLD)基础设施:$(NC)"
	@docker ps --filter "name=highermatch-postgres" --filter "status=running" | grep -q postgres && echo "$(GREEN)✓ PostgreSQL (5432)$(NC)" || echo "$(RED)✗ PostgreSQL$(NC)"
	@docker ps --filter "name=highermatch-redis" --filter "status=running" | grep -q redis && echo "$(GREEN)✓ Redis (6379)$(NC)" || echo "$(RED)✗ Redis$(NC)"
	@docker ps --filter "name=highermatch-kafka" --filter "status=running" | grep -q kafka && echo "$(GREEN)✓ Kafka (9092)$(NC)" || echo "$(RED)✗ Kafka$(NC)"
	@docker ps --filter "name=highermatch-qdrant" --filter "status=running" | grep -q qdrant && echo "$(GREEN)✓ Qdrant (6333)$(NC)" || echo "$(RED)✗ Qdrant$(NC)"

# ==================== 杂项命令 ====================

.PHONY: install-deps
install-deps: ## 安装所有依赖
	@echo "$(GREEN)安装后端依赖...$(NC)"
	@for service in $(BACKEND_SERVICES); do \
		pip install -r services/$$service/requirements.txt; \
	done
	@echo "$(GREEN)安装前端依赖...$(NC)"
	cd frontend/employer-portal && pnpm install
	cd frontend/candidate-portal && pnpm install
	@echo "$(GREEN)安装 E2E 测试依赖...$(NC)"
	pip install -r $(TEST_DIR)/requirements.txt
	@echo "$(GREEN)所有依赖安装完成!$(NC)"

.PHONY: docker-pull
docker-pull: ## 拉取最新镜像
	@echo "$(GREEN)拉取最新镜像...$(NC)"
	$(COMPOSE) $(COMPOSE_FILES) pull

.PHONY: docker-clean
docker-clean: ## 清理 Docker 资源
	@echo "$(YELLOW)清理 Docker 资源...$(NC)"
	docker system prune -f
	docker volume prune -f
	@echo "$(GREEN)清理完成!$(NC)"

.PHONY: ssh-service
ssh-service: ## SSH 进入服务容器 (用法: make ssh-service SERVICE=user-service)
	@if [ -z "$(SERVICE)" ]; then \
		echo "$(RED)请指定服务名: make ssh-service SERVICE=user-service$(NC)"; \
	else \
		$(COMPOSE) $(COMPOSE_FILES) exec $(SERVICE) /bin/sh; \
	fi

.PHONY: version
version: ## 显示版本信息
	@echo "$(BOLD)HigherMatch™ AI 招聘平台$(NC)"
	@echo "版本: 1.0.0"
	@echo "Docker Compose: $$($(COMPOSE) --version)"
	@echo "Python: $$(python3 --version)"
	@echo "Node.js: $$(node --version)"
	@echo "pnpm: $$(pnpm --version)"

# ==================== Git 命令 ====================

.PHONY: git-status
git-status: ## 显示 Git 状态
	git status

.PHONY: git-commit
git-commit: ## 提交代码 (用法: make git-commit MSG="提交信息")
	@if [ -z "$(MSG)" ]; then \
		echo "$(RED)请提供提交信息: make git-commit MSG=\"提交信息\"$(NC)"; \
	else \
		git add .; \
		git commit -m "$(MSG)"; \
		echo "$(GREEN)提交完成!$(NC)"; \
	fi

.PHONY: git-push
git-push: ## 推送到远程仓库
	git push origin $$(git branch --show-current)

.PHONY: git-pull
git-pull: ## 从远程仓库拉取
	git pull origin $$(git branch --show-current)
