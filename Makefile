# Virtual Closet — NikaCommerce
# Makefile for development, testing, and deployment

.PHONY: help dev dev-backend dev-frontend test test-backend test-frontend \
        db-up db-down db-migrate db-seed db-reset lint lint-backend lint-frontend \
        build build-frontend build-backend install install-backend install-frontend \
        fix-backend-venv docker-up docker-down docker-build clean

# Variables
BACKEND_DIR := backend
FRONTEND_DIR := frontend
DOCKER_COMPOSE := docker compose

# Default target
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ========================
# Development
# ========================

dev: ## Run both backend and frontend in development mode
	@echo "Starting backend and frontend..."
	@$(MAKE) -j2 dev-backend dev-frontend

dev-backend: ## Run backend FastAPI server with hot reload
	cd $(BACKEND_DIR) && uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload

dev-frontend: ## Run Next.js frontend dev server
	cd $(FRONTEND_DIR) && pnpm dev

# ========================
# Database
# ========================

db-up: ## Start PostgreSQL with Docker compose
	$(DOCKER_COMPOSE) up -d postgres

db-down: ## Stop PostgreSQL
	$(DOCKER_COMPOSE) down

db-migrate: ## Run Alembic migrations
	cd $(BACKEND_DIR) && uv run alembic upgrade head

db-seed: ## Seed ejemplo desde docs/imgs (usage: make db-seed EMAIL=tu@email.com)
	@test -n "$(EMAIL)" || (echo "Uso: make db-seed EMAIL=tu@email.com (mayorista ya registrado en la app)" && exit 1)
	@test -f docs/imgs/modelo.jpeg || (echo "Falta docs/imgs/modelo.jpeg" && exit 1)
	@test -f docs/imgs/producto_1.jpeg || (echo "Falta docs/imgs/producto_1.jpeg" && exit 1)
	$(DOCKER_COMPOSE) up -d postgres minio fastapi
	@echo "Seed modelos IA (docs/imgs/modelo.jpeg)..."
	$(DOCKER_COMPOSE) exec -T fastapi uv run python scripts/seed_modelos_ia.py
	@echo "Seed prenda de ejemplo (docs/imgs/producto_1.jpeg)..."
	$(DOCKER_COMPOSE) exec -T fastapi uv run python scripts/seed_prenda_ejemplo.py "$(EMAIL)"

db-reset: ## Drop and recreate all tables (WARNING: loses data)
	cd $(BACKEND_DIR) && uv run alembic downgrade base
	cd $(BACKEND_DIR) && uv run alembic upgrade head

db-migrate-create: ## Create a new migration (usage: make db-migrate-create msg="add_user_field")
	cd $(BACKEND_DIR) && uv run alembic revision --autogenerate -m "$(msg)"

# ========================
# Testing
# ========================

test: test-backend test-frontend ## Run all tests

test-backend: ## Run backend pytest tests
	cd $(BACKEND_DIR) && uv run pytest tests/ -v

test-frontend: ## Run frontend tests
	cd $(FRONTEND_DIR) && pnpm test

# ========================
# Linting
# ========================

lint: lint-backend lint-frontend ## Lint all code

lint-backend: ## Lint backend Python code
	cd $(BACKEND_DIR) && uv run python -m py_compile main.py

lint-frontend: ## Lint frontend TypeScript/React code
	cd $(FRONTEND_DIR) && pnpm lint

# ========================
# Building
# ========================

build: build-backend build-frontend ## Build all projects

build-backend: ## Verify backend dependencies resolve
	cd $(BACKEND_DIR) && uv sync

build-frontend: ## Build Next.js production bundle
	cd $(FRONTEND_DIR) && pnpm build

# ========================
# Installation
# ========================

install: install-backend install-frontend ## Install all dependencies

install-backend: ## Install backend Python dependencies
	cd $(BACKEND_DIR) && uv sync

fix-backend-venv: ## Remove Docker-corrupted .venv and recreate (no sudo)
	docker run --rm -v $$(pwd)/$(BACKEND_DIR):/app alpine sh -c 'rm -rf /app/.venv'
	cd $(BACKEND_DIR) && uv sync

install-frontend: ## Install frontend npm dependencies
	cd $(FRONTEND_DIR) && pnpm install

# ========================
# Docker
# ========================

docker-up: ## Start infra only (postgres, minio, rabbitmq, celery). Use docker-app for containerized FE/BE
	$(DOCKER_COMPOSE) up -d postgres minio rabbitmq celery_worker

docker-catvton:
	$(DOCKER_COMPOSE) up --profile gpu up catvton

docker-app: ## Start full stack including frontend and fastapi containers
	$(DOCKER_COMPOSE) --profile app up -d

docker-down: ## Stop all docker compose services
	$(DOCKER_COMPOSE) down

docker-build: ## Build all docker compose images
	$(DOCKER_COMPOSE) build

docker-logs: ## Show docker compose logs
	$(DOCKER_COMPOSE) logs -f

docker-infra: ## Alias for docker-up (infra only; run make dev for local FE/BE)
	$(MAKE) docker-up

# ========================
# Cleanup
# ========================

clean: ## Remove build artifacts and caches
	rm -rf $(BACKEND_DIR)/.pytest_cache
	rm -rf $(BACKEND_DIR)/.mypy_cache
	rm -rf $(BACKEND_DIR)/__pycache__
	rm -rf $(BACKEND_DIR)/**/__pycache__
	rm -rf $(FRONTEND_DIR)/.next
	rm -rf $(FRONTEND_DIR)/node_modules/.cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
