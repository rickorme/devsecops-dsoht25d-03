# Root Makefile

# -- Installation Commands --
.PHONY: install install-backend migrate-backend install-frontend seed-database install-playwright install-playwright-deps-only

# Installation (Handles both stacks)
install: install-backend install-frontend ## Install both backend and frontend dependencies
	 
install-backend: ## Install backend dependencies and run database migrations
	@echo "🚀 Installing Backend dependencies..."
	cd backend && uv sync
	@echo "🔄 Running Backend Migrations..."
	cd backend && uv run alembic upgrade head

# -- Database Commands --
.PHONY: migrate-backend seed-database db-reset db-refresh

migrate-backend: ## Run backend database migrations (without installing dependencies)
	@echo "🔄 Running Backend Migrations..."
	cd backend && uv run alembic upgrade head	

seed-database: ## Seed the backend database with test data
	@echo "🌱 Seeding Backend Database..."
	cd backend && uv run python scripts/create_test_users.py

db-reset: ## Reset database (drop all tables and recreate)
	@echo "🔄 Resetting database..."
	cd backend && uv run python scripts/reset_db.py
	@echo "✅ Database reset complete"

db-refresh: db-reset migrate-backend seed-database ## Full refresh: reset + migrate + seed
	@echo "🔄 Database refreshed successfully"	

install-frontend: ## Install frontend dependencies
	@echo "🚀 Installing Frontend dependencies..."
	cd frontend && npm install

install-playwright: ## Install Playwright browsers (for E2E tests), used in CI
	@echo "🎭 Installing Playwright Browsers..."
	cd backend && uv run python -m playwright install --with-deps chromium

install-playwright-deps-only: ## Install only Playwright system dependencies (without browsers), used in CI (when we have a cache hit for the browsers
	@echo "🎭 Installing Playwright System Dependencies (without browsers)..."
	cd backend && uv run python -m playwright install-deps chromium	


# -- Testing and Quality Control --
.PHONY: test-backend lint-backend audit-frontend lint-frontend format-backend \
		security-backend test-frontend-unit test-e2e test-e2e-headed 

test-backend: ## Run backend unit and integration tests (pytest)
	@echo "🧪 Running Backend Tests..."
	cd backend && uv run pytest tests/unit/ -v && uv run pytest tests/integration/ -v

lint-backend: ## Run backend linters (Ruff for formatting and linting, Mypy for type checking)
	@echo "🔍 Running Linters (Ruff + Mypy)..."
	cd backend && uv run ruff check .
	cd backend && uv run mypy .

audit-frontend: ## Run frontend security audit (npm audit)
	@echo "🛡️ Running Frontend Security Audit (npm audit)..."
	cd frontend && npm audit --omit=dev

lint-frontend: ## Run frontend linter (ESLint)
	@echo "🔍 Running Linter (eslint)..."
	cd frontend && npm run lint

format-backend: ## Format backend code (Ruff)
	@echo "🎨 Formatting Code (Ruff)..."
	cd backend && uv run ruff format .

security-backend: ## Run backend security scans (Bandit for static analysis, Safety for dependency vulnerabilities)
	@echo "🛡️ Running Security Scans (Bandit + Safety)..."
	cd backend && uv run bandit -c pyproject.toml -r .
	# cd backend && uv run safety scan

test-frontend-unit: ## Run frontend unit tests (Vitest)
	@echo "🧪 Running Frontend Unit Tests (Vitest)..."
	cd frontend && npm run test:run

test-e2e: ## Run end-to-end tests (Playwright in headless mode)
	@echo "🎭 Running E2E Tests..."
	cd backend && uv run pytest tests/e2e/step_defs/

test-e2e-headed: ## Run headed end-to-end tests with Playwright in a virtual screen (using xvfb-run)
	@echo "🎭 Running Headed Tests in Virtual Screen..."
# 	cd backend && xvfb-run --auto-servernum --server-args="-screen 1 1280x960x24" uv run pytest tests/e2e/step_defs/ --headed --slowmo 1500	
	cd backend && DISPLAY=:1 uv run pytest tests/e2e/step_defs --headed --slowmo 1500	


# -- Execution --
.PHONY: run-backend run-backend-for-ci run-frontend

run-backend: ## Start FastAPI server (accessible outside container)
	@echo "🐍 Starting FastAPI Backend..."
	# --host 0.0.0.0 is crucial for Docker/DevContainers so you can access it from Windows	
	cd backend && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 1. Load the .env file so the Makefile can see TEST_DATABASE_URL
-include ./backend/.env
export

run-test-backend: ## Start FastAPI server connected to TEST database (used for E2E tests)
	# 2. Assign the value of TEST_DATABASE_URL to the DATABASE_URL env var so FastAPI uses the test database when it starts up
	cd backend && DATABASE_URL="$(TEST_DATABASE_URL)" uv run uvicorn app.main:app --port 8000 --reload

run-backend-for-ci: ## Start FastAPI server for CI (runs in background)
	@echo "🐍 Starting FastAPI Backend for CI..."
	cd backend && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 &
          
	echo "Waiting for backend to start..."
	sleep 10

run-frontend: ## Start React dev server
	@echo "⚛️ Starting React Frontend..."
	cd frontend && npm run dev

run-playwright-codegen: ## Start Playwright code generator for E2E tests (generates test code as you interact with the UI)
	@echo "🎬 Starting Playwright Code Generator..."
	cd backend && uv run playwright codegen http://localhost:3000


# -- Environment Setup --
.PHONY: setup-env secrets

setup-env: ## Setup .env files from templates (creates them if they don't exist, but does not overwrite existing ones)
	@echo "🔧 Setting up environment files..."
	@if [ ! -f backend/.env ]; then \
		echo "📋 Creating backend/.env from template..."; \
		cp backend/.env.example backend/.env; \
		echo "✅ backend/.env created. Please update with real secrets!"; \
	else \
		echo "✅ backend/.env already exists"; \
	fi
	@if [ ! -f frontend/.env ]; then \
		echo "📋 Creating frontend/.env from template..."; \
		cp frontend/.env.example frontend/.env; \
		echo "✅ frontend/.env created"; \
	else \
		echo "✅ frontend/.env already exists"; \
	fi
	@echo ""
	@echo "🔐 Next: Generate secrets using:"
	@echo "   make secrets"
	@echo "   OR: python3 generate-secrets.py"
	@echo "   OR: bash generate-secrets.sh"

secrets: ## Generate secure secrets for .env files (like JWT secret keys, random passwords, etc.)
	@echo "🔐 Generating secure secrets..."
	@python3 generate-secrets.py


# -- Maintenance --
.PHONY: clean

clean:
	@echo "🧹 Cleaning up artifacts..."
	cd backend && rm -rf .venv .pytest_cache .ruff_cache .mypy_cache __pycache__
	cd frontend && rm -rf node_modules build

.PHONY: help
help: ## Display this help screen
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'