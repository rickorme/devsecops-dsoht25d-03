# ============================================================================
# ROOT MAKEFILE - Full Stack Project (FastAPI + React)
# ============================================================================
# This Makefile manages both backend (Python/FastAPI) and frontend (React/TypeScript)
# from a single location.
#
# Project structure:
# ├── backend/         # FastAPI + Python
# ├── frontend/        # React + JavaScript  
# ├── Makefile         # THIS FILE
# └── generate-secrets.py
# ============================================================================

# ============================================================================
# CONFIGURATION
# ============================================================================
# Default ports
BACKEND_PORT = 8000
FRONTEND_PORT = 3000

# Load environment variables from backend/.env (if it exists)
-include ./backend/.env
export

# ============================================================================
# INSTALLATION COMMANDS
# ============================================================================
# Run `make install` first when you clone the project
# ----------------------------------------------------------------------------

.PHONY: install install-backend install-frontend install-playwright install-playwright-deps-only

install: install-backend install-frontend ## Install both backend and frontend dependencies
	@echo "✅ All dependencies installed successfully!"

install-backend: ## Install backend dependencies (Python/uv) and run migrations
	@echo "🐍 Installing Backend dependencies..."
	cd backend && uv sync
	@echo "🔄 Running database migrations..."
	cd backend && uv run alembic upgrade head
	@echo "✅ Backend ready!"

install-frontend: ## Install frontend dependencies (npm)
	@echo "⚛️ Installing Frontend dependencies..."
	cd frontend && npm install
	@echo "✅ Frontend ready!"

install-playwright: ## Install Playwright browsers for E2E tests (used in CI)
	@echo "🎭 Installing Playwright Browsers..."
	# Note: Playwright is installed in backend/ because we use Python bindings
	cd backend && uv run python -m playwright install --with-deps chromium
	@echo "✅ Playwright installed"

install-playwright-deps-only: ## Install Playwright system dependencies only (no browsers)
	@echo "🎭 Installing Playwright System Dependencies..."
	# Used in CI when we have a cache hit for browsers
	cd backend && uv run python -m playwright install-deps chromium
	@echo "✅ Playwright dependencies installed"

# ============================================================================
# DATABASE COMMANDS
# ============================================================================
# PostgreSQL database management
# ----------------------------------------------------------------------------

.PHONY: migrate-backend seed-database db-reset db-refresh

migrate-backend: ## Run database migrations
	@echo "🔄 Running migrations..."
	cd backend && uv run alembic upgrade head

seed-database: ## Populate database with test data
	@echo "🌱 Seeding database..."
	cd backend && uv run python scripts/create_test_users.py
	@echo "✅ Test data added"

db-reset: ## Reset database (drop all tables and recreate)
	@echo "⚠️  Resetting database..."
	cd backend && uv run python scripts/reset_db.py
	@echo "✅ Database reset complete"

db-refresh: db-reset migrate-backend seed-database ## Full refresh: reset + migrate + seed
	@echo "🔄 Database refresh complete"

# ============================================================================
# TESTING & QUALITY CONTROL
# ============================================================================
# All commands for testing, linting, and security checks
# ----------------------------------------------------------------------------

.PHONY: test-backend lint-backend security-backend format-backend
.PHONY: test-frontend-unit lint-frontend audit-frontend
.PHONY: test-e2e test-e2e-headed

## Backend Testing
test-backend: ## Run backend unit and integration tests
	@echo "🧪 Running Backend Tests..."
	cd backend && uv run pytest tests/unit/ -v
	cd backend && uv run pytest tests/integration/ -v
	@echo "✅ Backend tests passed"

lint-backend: ## Run backend linters (Ruff for linting, Mypy for type checking)
	@echo "🔍 Linting backend..."
	cd backend && uv run ruff check .
	cd backend && uv run mypy .
	@echo "✅ Backend linting complete"

security-backend: ## Run backend security scans (Bandit)
	@echo "🛡️ Scanning backend security..."
	cd backend && uv run bandit -c pyproject.toml -r .
	@echo "✅ Backend security scan complete"

format-backend: ## Format backend code with Ruff
	@echo "🎨 Formatting backend code..."
	cd backend && uv run ruff format .
	@echo "✅ Backend formatting complete"

## Frontend Testing
test-frontend-unit: ## Run frontend unit tests (Vitest)
	@echo "🧪 Running Frontend Unit Tests..."
	cd frontend && npm run test:run
	@echo "✅ Frontend unit tests passed"

lint-frontend: ## Run frontend linter (ESLint)
	@echo "🔍 Linting frontend..."
	cd frontend && npm run lint
	@echo "✅ Frontend linting complete"

audit-frontend: ## Run frontend security audit (npm audit)
	@echo "🛡️ Auditing frontend dependencies..."
	cd frontend && npm audit --omit=dev
	@echo "✅ Frontend audit complete"

## End-to-End Testing (Playwright)
# Note: E2E tests are in backend/ because they use Python + Playwright bindings
test-e2e: ## Run E2E tests in headless mode (for CI)
	@echo "🎭 Running E2E Tests..."
	cd backend && uv run pytest tests/e2e/step_defs/ -v
	@echo "✅ E2E tests complete"

test-e2e-headed: ## Run E2E tests with visible browser (for local debugging)
	@echo "🎭 Running Headed E2E Tests..."
	cd backend && DISPLAY=:1 uv run pytest tests/e2e/step_defs --headed --slowmo 1500 -v
	@echo "✅ Headed E2E tests complete"

# ============================================================================
# APPLICATION EXECUTION
# ============================================================================
# Commands to start development servers
# ----------------------------------------------------------------------------

.PHONY: run-backend run-backend-for-ci run-test-backend run-frontend run-playwright-codegen

run-backend: ## Start FastAPI development server
	@echo "🐍 Starting Backend on port $(BACKEND_PORT)..."
	# --host 0.0.0.0 is crucial for Docker/DevContainers
	cd backend && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port $(BACKEND_PORT)

run-backend-for-ci: ## Start backend for CI (runs in background)
	@echo "🐍 Starting Backend for CI..."
	cd backend && uv run uvicorn app.main:app --host 0.0.0.0 --port $(BACKEND_PORT) &
	@echo "⏳ Waiting for backend to start..."
	sleep 10
	@echo "✅ Backend running on port $(BACKEND_PORT)"

run-test-backend: ## Start backend with test database (for E2E tests)
	@echo "🐍 Starting Backend with TEST database..."
	cd backend && DATABASE_URL="$(TEST_DATABASE_URL)" uv run uvicorn app.main:app --port $(BACKEND_PORT) --reload

run-frontend: ## Start React development server
	@echo "⚛️ Starting Frontend on port $(FRONTEND_PORT)..."
	cd frontend && npm run dev

run-playwright-codegen: ## Start Playwright code generator (creates tests as you interact)
	@echo "🎬 Starting Playwright Code Generator..."
	@echo "📌 Make sure frontend is running on port $(FRONTEND_PORT)"
	cd backend && uv run playwright codegen http://localhost:$(FRONTEND_PORT)

# ============================================================================
# ENVIRONMENT SETUP
# ============================================================================
# First-time setup commands
# ----------------------------------------------------------------------------

.PHONY: setup-env secrets

setup-env: ## Create .env files from templates (doesn't overwrite existing)
	@echo "🔧 Setting up environment files..."
	@if [ ! -f backend/.env ]; then \
		echo "📋 Creating backend/.env from template..."; \
		cp backend/.env.example backend/.env; \
		echo "✅ backend/.env created. Update with real secrets!"; \
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
	@echo "🔐 Next step: Generate secure secrets with:"
	@echo "   make secrets"

secrets: ## Generate secure secrets for .env files (JWT keys, passwords, etc.)
	@echo "🔐 Generating secure secrets..."
	@python3 generate-secrets.py
	@echo "✅ Secrets generated. Check your .env files!"

# ============================================================================
# MAINTENANCE
# ============================================================================
# Cleanup and utility commands
# ----------------------------------------------------------------------------

.PHONY: clean help

clean: ## Clean up build artifacts and caches
	@echo "🧹 Cleaning up..."
	cd backend && rm -rf .venv .pytest_cache .ruff_cache .mypy_cache __pycache__
	cd frontend && rm -rf node_modules build dist
	@echo "✅ Cleanup complete"

help: ## Display this help message
	@echo "╔══════════════════════════════════════════════════════════════╗"
	@echo "║     🚀 AVAILABLE COMMANDS - Full Stack Project               ║"
	@echo "╚══════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "📦 INSTALLATION:"
	@grep -h -E '^install[a-zA-Z_-]*:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "   \033[36m%-25s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "🗄️  DATABASE:"
	@grep -h -E '^(db|migrate|seed)[a-zA-Z_-]*:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "   \033[36m%-25s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "🧪 TESTING & QUALITY:"
	@grep -h -E '^(test|lint|security|format|audit)[a-zA-Z_-]*:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "   \033[36m%-25s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "🚀 RUN APPLICATION:"
	@grep -h -E '^run[a-zA-Z_-]*:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "   \033[36m%-25s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "🔧 ENVIRONMENT:"
	@grep -h -E '^(setup|secrets)[a-zA-Z_-]*:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "   \033[36m%-25s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "🧹 MAINTENANCE:"
	@grep -h -E '^(clean|help)[a-zA-Z_-]*:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "   \033[36m%-25s\033[0m %s\n", $$1, $$2}'