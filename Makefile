# ═══════════════════════════════════════════════════════════════
# AetherAI Platform - Ultimate Edition 2026
# Makefile
# ═══════════════════════════════════════════════════════════════

.PHONY: help setup dev infra services frontend backend test lint format clean deploy k8s-install

# Colors
BLUE := \033[36m
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
NC := \033[0m

help: ## Show this help message
	@echo "$(GREEN)AetherAI Platform - Ultimate Edition 2026$(NC)"
	@echo ""
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(BLUE)%-20s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# ─── Setup ────────────────────────────────────────────────────
setup: ## Initial project setup
	@echo "$(GREEN)🔧 Setting up AetherAI Platform...$(NC)"
	@cp .env.example .env
	@echo "$(YELLOW)⚠️  Please edit .env with your credentials$(NC)"
	@mkdir -p logs tmp data
	@echo "$(GREEN)✅ Setup complete!$(NC)"

install: ## Install all dependencies
	@echo "$(GREEN)📦 Installing dependencies...$(NC)"
	@cd frontend && npm install
	@cd backend/auth-service && pip install -r requirements.txt
	@cd backend/chat-service && pip install -r requirements.txt
	@cd backend/agent-service && pip install -r requirements.txt
	@cd backend/model-service && pip install -r requirements.txt
	@cd backend/memory-service && pip install -r requirements.txt
	@cd backend/rag-service && pip install -r requirements.txt
	@cd backend/workspace-service && pip install -r requirements.txt
	@cd backend/billing-service && pip install -r requirements.txt
	@cd backend/mcp-service && pip install -r requirements.txt
	@cd backend/a2a-service && pip install -r requirements.txt
	@cd backend/analytics-service && pip install -r requirements.txt
	@cd backend/admin-service && pip install -r requirements.txt
	@cd sdks/python && pip install -e .
	@cd sdks/javascript && npm install
	@echo "$(GREEN)✅ Dependencies installed!$(NC)"

# ─── Development ──────────────────────────────────────────────
dev: ## Start development environment
	@echo "$(GREEN)🚀 Starting development environment...$(NC)"
	@docker-compose up -d postgres redis qdrant neo4j clickhouse elasticsearch minio
	@echo "$(GREEN)✅ Infrastructure started!$(NC)"
	@echo "$(YELLOW)⏳ Waiting for services to be ready...$(NC)"
	@sleep 10
	@docker-compose ps

infra: ## Start infrastructure only
	@docker-compose up -d postgres redis qdrant neo4j clickhouse elasticsearch minio

infra-logs: ## View infrastructure logs
	@docker-compose logs -f postgres redis qdrant neo4j clickhouse elasticsearch minio

infra-stop: ## Stop infrastructure
	@docker-compose stop postgres redis qdrant neo4j clickhouse elasticsearch minio

# ─── Services ─────────────────────────────────────────────────
services: ## Start all backend services
	@echo "$(GREEN)🚀 Starting all services...$(NC)"
	@docker-compose up -d --build
	@echo "$(GREEN)✅ All services started!$(NC)"
	@echo "  🌐 Web App:     http://localhost:3000"
	@echo "  🔌 API Gateway: http://localhost:8080"
	@echo "  📊 Grafana:     http://localhost:3001"
	@echo "  📈 Prometheus:  http://localhost:9090"
	@echo "  🔍 Jaeger:      http://localhost:16686"

services-build: ## Build all services
	@docker-compose build --parallel

services-logs: ## View all service logs
	@docker-compose logs -f api-gateway frontend auth-service chat-service agent-service model-service memory-service rag-service workspace-service billing-service mcp-service a2a-service analytics-service admin-service

services-stop: ## Stop all services
	@docker-compose stop

services-down: ## Stop and remove all services
	@docker-compose down

services-restart: ## Restart all services
	@docker-compose restart

# ─── Individual Services ──────────────────────────────────────
auth: ## Start auth service
	@docker-compose up -d auth-service

chat: ## Start chat service
	@docker-compose up -d chat-service

agent: ## Start agent service
	@docker-compose up -d agent-service

model: ## Start model service
	@docker-compose up -d model-service

memory: ## Start memory service
	@docker-compose up -d memory-service

rag: ## Start RAG service
	@docker-compose up -d rag-service

workspace: ## Start workspace service
	@docker-compose up -d workspace-service

billing: ## Start billing service
	@docker-compose up -d billing-service

mcp: ## Start MCP service
	@docker-compose up -d mcp-service

a2a: ## Start A2A service
	@docker-compose up -d a2a-service

analytics: ## Start analytics service
	@docker-compose up -d analytics-service

admin: ## Start admin service
	@docker-compose up -d admin-service

# ─── Frontend ─────────────────────────────────────────────────
frontend-dev: ## Start frontend in development mode
	@cd frontend && npm run dev

frontend-build: ## Build frontend for production
	@cd frontend && npm run build

frontend-start: ## Start frontend in production mode
	@cd frontend && npm start

# ─── AI Core ──────────────────────────────────────────────────
vllm: ## Start vLLM (requires GPU)
	@docker-compose --profile gpu up -d vllm

ollama: ## Start Ollama (requires GPU)
	@docker-compose --profile gpu up -d ollama

# ─── Testing ──────────────────────────────────────────────────
test: ## Run all tests
	@echo "$(GREEN)🧪 Running all tests...$(NC)"
	@cd tests/backend && python -m pytest -v
	@cd tests/frontend && npm test
	@cd tests/integration && python -m pytest -v
	@echo "$(GREEN)✅ All tests passed!$(NC)"

test-backend: ## Run backend tests
	@cd tests/backend && python -m pytest -v

test-frontend: ## Run frontend tests
	@cd tests/frontend && npm test

test-integration: ## Run integration tests
	@cd tests/integration && python -m pytest -v

test-e2e: ## Run E2E tests
	@cd tests/e2e && npx playwright test

# ─── Linting & Formatting ─────────────────────────────────────
lint: ## Run linters
	@echo "$(GREEN)🔍 Running linters...$(NC)"
	@cd frontend && npx next lint
	@find backend -name "*.py" -exec flake8 {} +
	@find ai-core -name "*.py" -exec flake8 {} +
	@echo "$(GREEN)✅ Linting complete!$(NC)"

format: ## Format all code
	@echo "$(GREEN)✨ Formatting code...$(NC)"
	@cd frontend && npx prettier --write "src/**/*.{ts,tsx,js,jsx,json,css,md}"
	@find backend -name "*.py" -exec black {} +
	@find ai-core -name "*.py" -exec black {} +
	@find sdks/python -name "*.py" -exec black {} +
	@echo "$(GREEN)✅ Formatting complete!$(NC)"

# ─── Database ─────────────────────────────────────────────────
migrate: ## Run database migrations
	@echo "$(GREEN)🗄️  Running migrations...$(NC)"
	@docker-compose exec -T postgres psql -U aether -d aether_platform < database/migrations/001_init.sql
	@echo "$(GREEN)✅ Migrations complete!$(NC)"

seed: ## Seed database with initial data
	@echo "$(GREEN)🌱 Seeding database...$(NC)"
	@docker-compose exec -T postgres psql -U aether -d aether_platform < database/seeds/001_default_data.sql
	@echo "$(GREEN)✅ Seeding complete!$(NC)"

db-reset: ## Reset database (DANGER: drops all data)
	@echo "$(RED)⚠️  This will delete all data!$(NC)"
	@read -p "Are you sure? [y/N] " confirm && [ $$confirm = y ] || exit 1
	@docker-compose down -v
	@docker-compose up -d postgres
	@sleep 5
	@$(MAKE) migrate
	@$(MAKE) seed

# ─── Monitoring ───────────────────────────────────────────────
logs: ## View all logs
	@docker-compose logs -f

logs-service: ## View specific service logs (usage: make logs-service SERVICE=auth-service)
	@docker-compose logs -f $(SERVICE)

status: ## Show service status
	@docker-compose ps

health: ## Check health of all services
	@echo "$(GREEN)🏥 Checking service health...$(NC)"
	@curl -s http://localhost:8080/health || echo "$(RED)❌ API Gateway unhealthy$(NC)"
	@curl -s http://localhost:3000/api/health || echo "$(RED)❌ Frontend unhealthy$(NC)"
	@echo "$(GREEN)✅ Health check complete!$(NC)"

# ─── Deployment ───────────────────────────────────────────────
docker-push: ## Push Docker images to registry
	@echo "$(GREEN)📤 Pushing images...$(NC)"
	@docker-compose build
	@docker tag aether-platform-frontend aetherai/frontend:latest
	@docker tag aether-platform-api-gateway aetherai/api-gateway:latest
	@docker tag aether-platform-auth-service aetherai/auth-service:latest
	@docker tag aether-platform-chat-service aetherai/chat-service:latest
	@docker tag aether-platform-agent-service aetherai/agent-service:latest
	@docker tag aether-platform-model-service aetherai/model-service:latest
	@docker tag aether-platform-memory-service aetherai/memory-service:latest
	@docker tag aether-platform-rag-service aetherai/rag-service:latest
	@docker tag aether-platform-workspace-service aetherai/workspace-service:latest
	@docker tag aether-platform-billing-service aetherai/billing-service:latest
	@docker tag aether-platform-mcp-service aetherai/mcp-service:latest
	@docker tag aether-platform-a2a-service aetherai/a2a-service:latest
	@docker tag aether-platform-analytics-service aetherai/analytics-service:latest
	@docker tag aether-platform-admin-service aetherai/admin-service:latest
	@docker push aetherai/frontend:latest
	@docker push aetherai/api-gateway:latest
	@docker push aetherai/auth-service:latest
	@docker push aetherai/chat-service:latest
	@docker push aetherai/agent-service:latest
	@docker push aetherai/model-service:latest
	@docker push aetherai/memory-service:latest
	@docker push aetherai/rag-service:latest
	@docker push aetherai/workspace-service:latest
	@docker push aetherai/billing-service:latest
	@docker push aetherai/mcp-service:latest
	@docker push aetherai/a2a-service:latest
	@docker push aetherai/analytics-service:latest
	@docker push aetherai/admin-service:latest
	@echo "$(GREEN)✅ Images pushed!$(NC)"

k8s-deploy: ## Deploy to Kubernetes
	@echo "$(GREEN)☸️  Deploying to Kubernetes...$(NC)"
	@kubectl apply -f infra/k8s/
	@kubectl apply -f infra/helm/aether-platform/templates/
	@echo "$(GREEN)✅ Kubernetes deployment complete!$(NC)"

k8s-delete: ## Delete Kubernetes deployment
	@kubectl delete -f infra/k8s/
	@kubectl delete -f infra/helm/aether-platform/templates/

terraform-init: ## Initialize Terraform
	@cd infra/terraform && terraform init

terraform-plan: ## Plan Terraform changes
	@cd infra/terraform && terraform plan

terraform-apply: ## Apply Terraform changes
	@cd infra/terraform && terraform apply

# ─── SDKs ─────────────────────────────────────────────────────
sdk-python: ## Build Python SDK
	@cd sdks/python && python setup.py sdist bdist_wheel

sdk-js: ## Build JavaScript SDK
	@cd sdks/javascript && npm run build

sdk-go: ## Build Go SDK
	@cd sdks/go && go build ./...

sdk-rust: ## Build Rust SDK
	@cd sdks/rust && cargo build --release

sdk-java: ## Build Java SDK
	@cd sdks/java && mvn clean package

# ─── Cleanup ──────────────────────────────────────────────────
clean: ## Clean build artifacts
	@echo "$(GREEN)🧹 Cleaning up...$(NC)"
	@docker-compose down -v --remove-orphans
	@docker system prune -f
	@rm -rf frontend/.next frontend/node_modules
	@rm -rf backend/**/__pycache__ backend/**/.pytest_cache
	@rm -rf ai-core/**/__pycache__
	@rm -rf sdks/python/build sdks/python/dist sdks/python/*.egg-info
	@rm -rf sdks/javascript/dist sdks/javascript/node_modules
	@rm -rf logs/* tmp/*
	@echo "$(GREEN)✅ Cleanup complete!$(NC)"

clean-all: ## Deep clean everything (DANGER)
	@echo "$(RED)⚠️  This will remove ALL Docker data!$(NC)"
	@read -p "Are you sure? [y/N] " confirm && [ $$confirm = y ] || exit 1
	@$(MAKE) clean
	@docker volume prune -f
	@docker network prune -f

# ─── Utilities ────────────────────────────────────────────────
backup: ## Backup database
	@echo "$(GREEN)💾 Backing up database...$(NC)"
	@docker-compose exec -T postgres pg_dump -U aether aether_platform > backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "$(GREEN)✅ Backup complete!$(NC)"

restore: ## Restore database (usage: make restore FILE=backup.sql)
	@echo "$(GREEN)📥 Restoring database...$(NC)"
	@docker-compose exec -T postgres psql -U aether -d aether_platform < $(FILE)
	@echo "$(GREEN)✅ Restore complete!$(NC)"

shell-%: ## Open shell in service (usage: make shell-auth-service)
	@docker-compose exec $(subst shell-,,$@) /bin/sh

# ─── Release ──────────────────────────────────────────────────
release: ## Create a new release
	@echo "$(GREEN)🏷️  Creating release...$(NC)"
	@read -p "Version (e.g., 1.0.0): " version; 	git tag -a v$$version -m "Release v$$version"; 	git push origin v$$version; 	echo "$(GREEN)✅ Release v$$version created!$(NC)"
