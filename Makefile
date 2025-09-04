# SearchScrape API Makefile
# Convenience commands for development and deployment

.PHONY: help setup install test lint format clean dev docker deploy monitor

# Default target
help:
	@echo "SearchScrape API - Available commands:"
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make setup     - Set up development environment"
	@echo "  make install   - Install dependencies"
	@echo ""
	@echo "Development:"
	@echo "  make dev       - Start development server"
	@echo "  make worker    - Start Celery worker"
	@echo "  make flower    - Start Flower monitoring"
	@echo ""
	@echo "Testing:"
	@echo "  make test      - Run all tests"
	@echo "  make test-unit - Run unit tests only"
	@echo "  make test-integration - Run integration tests"
	@echo "  make test-performance - Run performance tests"
	@echo "  make test-coverage - Run tests with coverage"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint      - Run code linting"
	@echo "  make format    - Format code"
	@echo "  make typecheck - Run type checking"
	@echo ""
	@echo "Database:"
	@echo "  make migrate   - Run database migrations"
	@echo "  make migration - Create new migration"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build - Build Docker image"
	@echo "  make docker-up    - Start services with Docker Compose"
	@echo "  make docker-down  - Stop Docker services"
	@echo ""
	@echo "Deployment:"
	@echo "  make deploy-local - Deploy locally"
	@echo "  make deploy-staging - Deploy to staging"
	@echo "  make deploy-prod - Deploy to production"
	@echo ""
	@echo "Monitoring:"
	@echo "  make monitor   - Check API health"
	@echo "  make logs      - View application logs"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean     - Clean up temporary files"

# Setup and installation
setup:
	@echo "🚀 Setting up development environment..."
	@./scripts/setup.sh

install:
	@echo "📥 Installing dependencies..."
	@pip install -r requirements.txt

# Development
dev:
	@echo "🔧 Starting development server..."
	@uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

worker:
	@echo "👷 Starting Celery worker..."
	@celery -A app.workers.tasks worker --loglevel=info

flower:
	@echo "🌸 Starting Flower monitoring..."
	@celery -A app.workers.tasks flower

# Testing
test:
	@echo "🧪 Running all tests..."
	@./scripts/test.sh all

test-unit:
	@echo "🔬 Running unit tests..."
	@./scripts/test.sh unit

test-integration:
	@echo "🔗 Running integration tests..."
	@./scripts/test.sh integration

test-performance:
	@echo "⚡ Running performance tests..."
	@./scripts/test.sh performance

test-coverage:
	@echo "📊 Running tests with coverage..."
	@./scripts/test.sh coverage

# Code quality
lint:
	@echo "🔍 Running linting..."
	@flake8 app/ tests/
	@isort --check-only app/ tests/
	@black --check app/ tests/

format:
	@echo "✨ Formatting code..."
	@isort app/ tests/
	@black app/ tests/

typecheck:
	@echo "🔎 Running type checking..."
	@mypy app/

# Database
migrate:
	@echo "🗄️ Running database migrations..."
	@alembic upgrade head

migration:
	@echo "📝 Creating new migration..."
	@read -p "Migration message: " msg; alembic revision --autogenerate -m "$$msg"

# Docker
docker-build:
	@echo "🐳 Building Docker image..."
	@docker build -t searchscrape/api:latest .

docker-up:
	@echo "🚀 Starting services with Docker Compose..."
	@docker-compose up -d

docker-down:
	@echo "🛑 Stopping Docker services..."
	@docker-compose down

docker-logs:
	@echo "📋 Showing Docker logs..."
	@docker-compose logs -f

# Deployment
deploy-local:
	@echo "🏠 Deploying locally..."
	@./scripts/deploy.sh latest local

deploy-staging:
	@echo "🎭 Deploying to staging..."
	@./scripts/deploy.sh latest staging

deploy-prod:
	@echo "🏭 Deploying to production..."
	@./scripts/deploy.sh latest production

# Monitoring
monitor:
	@echo "🔍 Checking API health..."
	@./scripts/monitor.sh

monitor-continuous:
	@echo "🔄 Starting continuous monitoring..."
	@./scripts/monitor.sh http://localhost:8000 30 monitor

logs:
	@echo "📋 Showing application logs..."
	@docker-compose logs -f api

# Cleanup
clean:
	@echo "🧹 Cleaning up..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@rm -rf .pytest_cache htmlcov .coverage 2>/dev/null || true
	@rm -f test.db 2>/dev/null || true
	@echo "✅ Cleanup complete"

# Environment setup
env:
	@if [ ! -f .env ]; then \
		echo "📝 Creating .env file..."; \
		cp .env.example .env; \
		echo "⚠️  Please edit .env file with your configuration"; \
	else \
		echo "✅ .env file already exists"; \
	fi

# Security checks
security:
	@echo "🔒 Running security checks..."
	@pip-audit || echo "⚠️ pip-audit not installed. Run: pip install pip-audit"

# Pre-commit setup
pre-commit:
	@echo "🔧 Setting up pre-commit hooks..."
	@pre-commit install

# Quick development setup
dev-setup: env install migrate
	@echo "🎉 Development setup complete!"
	@echo "Next steps:"
	@echo "  1. Edit .env file with your configuration"
	@echo "  2. Start services: make docker-up"
	@echo "  3. Run the API: make dev"

# Production deployment check
prod-check:
	@echo "🔍 Running production readiness checks..."
	@echo "Checking configuration..."
	@python -c "from app.config import get_settings; s=get_settings(); print('✅ Configuration loaded')"
	@echo "Checking dependencies..."
	@pip check
	@echo "Running security audit..."
	@make security
	@echo "Running tests..."
	@make test-unit
	@echo "✅ Production checks complete"
