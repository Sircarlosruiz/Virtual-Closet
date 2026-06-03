# Virtual Closet — NikaCommerce
# Makefile for development, testing, and deployment

.PHONY: help dev dev-backend dev-frontend test test-backend test-frontend \
        db-up db-down db-migrate db-seed db-reset lint lint-backend lint-frontend \
        build build-frontend build-backend install install-backend install-frontend \
        fix-backend-venv docker-up docker-down docker-build docker-catvton docker-fashn \
        docker-tryoff tryoff-restart tryoff-test clean

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

dev: ## Run full stack in Docker (postgres, minio, rabbitmq, celery, API + FE with hot reload)
	@echo "TryOff needs the GPU model: run 'make flux-restart' in another terminal (or --profile tryoff)."
	$(DOCKER_COMPOSE) up --build

dev-models: ## Run TryOff GPU model (one GPU service at a time to avoid OOM)
	@echo "Nota: no levantes fashn y tryoff-model a la vez en la misma GPU."
	$(DOCKER_COMPOSE) --profile tryoff up tryoff-model

dev-backend: ## Run backend locally with hot reload (requires make docker-up for infra)
	cd $(BACKEND_DIR) && uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload

dev-frontend: ## Run frontend locally (requires backend reachable at localhost:8000)
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
