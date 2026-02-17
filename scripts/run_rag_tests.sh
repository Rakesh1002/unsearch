#!/bin/bash
#
# RAG Pipeline Test Runner
# Runs all RAG-related tests with appropriate markers
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}RAG Pipeline Test Suite${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Change to project directory
cd "$(dirname "$0")/.."

# Check if pytest is available
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}pytest is not installed. Please install with:${NC}"
    echo "  pip install pytest pytest-asyncio pytest-cov"
    exit 1
fi

# Default test mode
TEST_MODE="${1:-all}"

run_unit_tests() {
    echo -e "\n${YELLOW}Running RAG Unit Tests...${NC}\n"
    pytest tests/unit/test_rag_service.py -v --tb=short "$@"
}

run_integration_tests() {
    echo -e "\n${YELLOW}Running RAG Integration Tests...${NC}\n"
    pytest tests/integration/test_rag_api.py -v --tb=short "$@"
}

run_all_tests() {
    echo -e "\n${YELLOW}Running All RAG Tests...${NC}\n"
    pytest tests/unit/test_rag_service.py tests/integration/test_rag_api.py -v --tb=short "$@"
}

run_with_coverage() {
    echo -e "\n${YELLOW}Running RAG Tests with Coverage...${NC}\n"
    pytest tests/unit/test_rag_service.py tests/integration/test_rag_api.py \
        -v --tb=short \
        --cov=app/services/rag \
        --cov=app/api/v1/rag \
        --cov=app/models/rag \
        --cov-report=term-missing \
        --cov-report=html:coverage_rag \
        "$@"
    
    echo -e "\n${GREEN}Coverage report generated at: coverage_rag/index.html${NC}"
}

case "$TEST_MODE" in
    unit)
        run_unit_tests "${@:2}"
        ;;
    integration)
        run_integration_tests "${@:2}"
        ;;
    coverage)
        run_with_coverage "${@:2}"
        ;;
    all|*)
        run_all_tests "${@:2}"
        ;;
esac

echo -e "\n${GREEN}Tests completed!${NC}"
