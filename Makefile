.PHONY: help dev test lint format check docker-up docker-down docker-build clean

# ── Default ──────────────────────────────────────────────────────
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Backend ──────────────────────────────────────────────────────
dev-backend: ## Start all A2A agents (backend only)
	cd backend && source .venv/bin/activate && python run_all.py

test: ## Run all tests
	cd backend && source .venv/bin/activate && python -m pytest tests/ -v --tb=short

test-watch: ## Run tests in watch mode
	cd backend && source .venv/bin/activate && python -m pytest tests/ -v --tb=short -f

lint: ## Run linter (ruff check)
	cd backend && source .venv/bin/activate && ruff check .

format: ## Format code (ruff format)
	cd backend && source .venv/bin/activate && ruff format .

format-check: ## Check formatting without changing files
	cd backend && source .venv/bin/activate && ruff format --check .

check: ## Run all checks (lint + format + tests)
	cd backend && bash check.sh

# ── Frontend ─────────────────────────────────────────────────────
dev-frontend: ## Start frontend dev server
	cd frontend && npm run dev

build-frontend: ## Build frontend for production
	cd frontend && npm run build

# ── Full Stack ───────────────────────────────────────────────────
dev: ## Start both backend and frontend (background)
	@echo "🚀 Starting backend agents..."
	@cd backend && source .venv/bin/activate && python run_all.py &
	@sleep 3
	@echo "🌐 Starting frontend..."
	@cd frontend && npm run dev &
	@echo ""
	@echo "✅ System running!"
	@echo "   Frontend: http://localhost:3000"
	@echo "   Agents:   http://localhost:9001-9004"
	@echo ""
	@wait

# ── Docker ───────────────────────────────────────────────────────
docker-build: ## Build Docker images
	docker compose build

docker-up: ## Start system with Docker
	docker compose up -d
	@echo ""
	@echo "✅ Docker containers running!"
	@echo "   Frontend: http://localhost:3000"
	@echo "   Agents:   http://localhost:9001-9004"

docker-down: ## Stop Docker containers
	docker compose down

docker-logs: ## View Docker logs
	docker compose logs -f

docker-restart: ## Restart Docker containers
	docker compose restart

# ── Setup ────────────────────────────────────────────────────────
setup: ## Initial project setup (create venv + install deps)
	cd backend && uv venv && source .venv/bin/activate && uv pip install -r requirements.txt pytest pytest-asyncio ruff
	cd frontend && npm install
	@echo ""
	@echo "✅ Setup complete! Run 'make dev' to start."

# ── Clean ────────────────────────────────────────────────────────
clean: ## Clean build artifacts
	rm -rf backend/.venv backend/__pycache__ backend/**/__pycache__
	rm -rf backend/.pytest_cache
	rm -rf frontend/.next frontend/node_modules
	rm -rf __pycache__
	@echo "🧹 Cleaned!"
