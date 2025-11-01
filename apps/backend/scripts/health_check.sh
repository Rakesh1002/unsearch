#!/bin/bash

# Health check script for UnSearch API
# Can be used for monitoring and automated health checks

set -e

# Configuration
API_URL=${API_URL:-"http://localhost:8000"}
TIMEOUT=${TIMEOUT:-10}

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "UnSearch API Health Check"
echo "============================="
echo ""

# Function to check service
check_service() {
    local name=$1
    local url=$2
    local expected=$3
    
    printf "Checking %-20s" "$name..."
    
    response=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout $TIMEOUT "$url" || echo "000")
    
    if [ "$response" = "$expected" ]; then
        echo -e "${GREEN}✓ OK${NC}"
        return 0
    else
        echo -e "${RED}✗ FAILED (HTTP $response)${NC}"
        return 1
    fi
}

# Check basic health
check_service "Basic Health" "$API_URL/health" "200"

# Check detailed health
echo ""
echo "Detailed Health Check:"
health_response=$(curl -s --connect-timeout $TIMEOUT "$API_URL/api/v1/search/health" || echo "{}")

if command -v jq >/dev/null 2>&1; then
    status=$(echo "$health_response" | jq -r '.status' 2>/dev/null || echo "unknown")
    
    if [ "$status" = "healthy" ]; then
        echo -e "Overall Status: ${GREEN}$status${NC}"
    elif [ "$status" = "degraded" ]; then
        echo -e "Overall Status: ${YELLOW}$status${NC}"
    else
        echo -e "Overall Status: ${RED}$status${NC}"
    fi
    
    echo ""
    echo "Service Status:"
    echo "$health_response" | jq -r '.services | to_entries[] | "- \(.key): \(.value.status) (latency: \(.value.latency_ms)ms)"' 2>/dev/null || echo "Failed to parse service status"
else
    echo "$health_response"
fi

# Check API docs
echo ""
check_service "API Documentation" "$API_URL/docs" "200"

# Check metrics endpoint
check_service "Metrics Endpoint" "$API_URL/metrics" "200"

# Performance check
echo ""
echo "Performance Check:"
start_time=$(date +%s%N)
response=$(curl -s -X POST "$API_URL/api/v1/search" \
    -H "Content-Type: application/json" \
    -H "X-API-Key: test-key" \
    -d '{"query":"test","engines":["google"],"max_results":1,"scrape_content":false}' \
    --connect-timeout $TIMEOUT || echo "{}")
end_time=$(date +%s%N)

if command -v jq >/dev/null 2>&1 && [ -n "$response" ]; then
    request_id=$(echo "$response" | jq -r '.request_id' 2>/dev/null || echo "N/A")
    processing_time=$(echo "$response" | jq -r '.processing_time_ms' 2>/dev/null || echo "N/A")
    
    total_time=$((($end_time - $start_time) / 1000000))
    
    echo "- Request ID: $request_id"
    echo "- Server Processing Time: ${processing_time}ms"
    echo "- Total Round Trip Time: ${total_time}ms"
fi

echo ""
echo "Health check completed."
