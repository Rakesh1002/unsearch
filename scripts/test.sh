#!/bin/bash
# Test runner script for UnSearch API.

set -e

# Resolve repo root and cd into backend (where pytest.ini + tests/ live)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR/backend"

echo "🧪 Running UnSearch API tests..."

# Activate virtual environment if it exists (search root then backend)
if [ -d "$PROJECT_DIR/venv" ]; then
    echo "🔌 Activating virtual environment..."
    source "$PROJECT_DIR/venv/bin/activate"
elif [ -d "venv" ]; then
    source venv/bin/activate
fi

# Check if pytest is available
if ! command -v pytest &> /dev/null; then
    echo "❌ pytest not found. Installing..."
    pip install pytest pytest-asyncio pytest-cov
fi

# Set test environment variables
export TESTING=true
export DATABASE_URL="sqlite:///test.db"
export REDIS_URL="redis://localhost:6379/1"  # Use different Redis DB for tests
export SEARXNG_URL="http://localhost:8080"

echo "🔧 Test configuration:"
echo "  - Database: $DATABASE_URL"
echo "  - Redis: $REDIS_URL"
echo "  - SearXNG: $SEARXNG_URL"

# Run different test suites based on argument
case "${1:-all}" in
    "unit")
        echo "🔬 Running unit tests..."
        pytest tests/unit/ -v --tb=short
        ;;
    "integration")
        echo "🔗 Running integration tests..."
        pytest tests/integration/ -v --tb=short
        ;;
    "performance")
        echo "⚡ Running performance tests..."
        pytest tests/performance/ -v --tb=short -m "not slow"
        ;;
    "load")
        echo "🏋️ Running load tests..."
        pytest tests/performance/ -v --tb=short -m "slow"
        ;;
    "coverage")
        echo "📊 Running tests with coverage..."
        pytest tests/ --cov=app --cov-report=html --cov-report=term-missing
        echo "📈 Coverage report generated in htmlcov/"
        ;;
    "quick")
        echo "⚡ Running quick tests (unit only)..."
        pytest tests/unit/ -v --tb=line -x
        ;;
    "all"|*)
        echo "🎯 Running all tests..."
        pytest tests/ -v --tb=short
        ;;
esac

# Clean up test artifacts
echo "🧹 Cleaning up..."
if [ -f "test.db" ]; then
    rm test.db
fi

echo "✅ Tests completed!"
