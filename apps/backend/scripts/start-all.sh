#!/bin/bash
# Start SearXNG, initialize services, and run API/workers locally

set -euo pipefail

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT_DIR"

# Load env if present
if [ -f .env ]; then
	set -o allexport
	source .env
	set +o allexport
fi

# Sensible defaults
: "${ENVIRONMENT:=development}"
: "${SEARXNG_URL:=http://localhost:8080}"
: "${WORKERS:=4}"

# Ensure CORS JSON lists are valid if provided as plain strings
export ALLOWED_ORIGINS=${ALLOWED_ORIGINS:-'["*"]'}
export CORS_METHODS=${CORS_METHODS:-'["GET","POST","PUT","DELETE","OPTIONS"]'}
export CORS_HEADERS=${CORS_HEADERS:-'["*"]'}

# 1) Start SearXNG via Docker if not already running
if ! docker ps --format '{{.Names}}' | grep -q '^unsearch-searxng$'; then
	echo "🐳 Starting SearXNG..."
	docker compose up -d searxng
fi

echo "⏳ Waiting for SearXNG to become healthy..."
SEARX_ATTEMPTS=30
until curl -fsS "${SEARXNG_URL%/}/healthz" >/dev/null 2>&1 || [ $SEARX_ATTEMPTS -le 0 ]; do
	SEARX_ATTEMPTS=$((SEARX_ATTEMPTS-1))
	sleep 2
	docker ps --format '{{.Names}}: {{.Status}}' | grep unsearch-searxng || true
	echo -n "."

done

echo ""

# 2) Run DB migrations (handles Neon sslmode gracefully in code)
echo "🗄️  Running Alembic migrations..."
poetry run alembic upgrade head || {
	echo "⚠️ Alembic failed; ensure DATABASE_URL is set and reachable."; exit 1; }

# 3) Start services
# API
echo "🚀 Starting API on :8000"
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 &
API_PID=$!

# Celery worker
if [ -n "${CELERY_BROKER_URL:-}" ]; then
	echo "👷 Starting Celery worker"
	poetry run celery -A app.workers.tasks worker --loglevel=info --concurrency="${WORKERS}" &
	WORKER_PID=$!
fi

# Celery beat
if [ -n "${CELERY_BROKER_URL:-}" ]; then
	echo "⏰ Starting Celery beat"
	poetry run celery -A app.workers.tasks beat --loglevel=info &
	BEAT_PID=$!
fi

trap 'echo "🧹 Stopping..."; kill ${API_PID:-0} ${WORKER_PID:-0} ${BEAT_PID:-0} 2>/dev/null || true' INT TERM

# 4) Health check loop
sleep 2
if curl -fsS http://localhost:8000/health >/dev/null; then
	echo "✅ API is healthy"
else
	echo "❌ API health check failed"
fi

wait
