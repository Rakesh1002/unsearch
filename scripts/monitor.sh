#!/bin/bash
"""
Monitoring and health check script for UnSearch API.
"""

set -e

API_URL="${1:-http://localhost:8000}"
CHECK_INTERVAL="${2:-30}"

echo "🔍 Starting UnSearch API monitoring..."
echo "🌐 API URL: $API_URL"
echo "⏱️ Check interval: ${CHECK_INTERVAL}s"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check API health
check_health() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    # Check main health endpoint
    if response=$(curl -s -w "HTTPSTATUS:%{http_code};TIME:%{time_total}" "$API_URL/health" 2>/dev/null); then
        http_code=$(echo $response | grep -o "HTTPSTATUS:[0-9]*" | cut -d: -f2)
        time_total=$(echo $response | grep -o "TIME:[0-9.]*" | cut -d: -f2)
        body=$(echo $response | sed -E 's/HTTPSTATUS:[0-9]*;TIME:[0-9.]*$//')
        
        if [ "$http_code" = "200" ]; then
            status=$(echo $body | grep -o '"status":"[^"]*' | cut -d'"' -f4)
            if [ "$status" = "healthy" ]; then
                echo -e "${GREEN}✅ [$timestamp] API healthy - Response time: ${time_total}s${NC}"
                return 0
            else
                echo -e "${YELLOW}⚠️ [$timestamp] API degraded - Status: $status${NC}"
                return 1
            fi
        else
            echo -e "${RED}❌ [$timestamp] API unhealthy - HTTP $http_code${NC}"
            return 2
        fi
    else
        echo -e "${RED}❌ [$timestamp] API unreachable${NC}"
        return 3
    fi
}

# Function to check metrics endpoint
check_metrics() {
    if curl -s "$API_URL/metrics" > /dev/null 2>&1; then
        echo -e "${GREEN}📊 Metrics endpoint accessible${NC}"
    else
        echo -e "${YELLOW}⚠️ Metrics endpoint not accessible${NC}"
    fi
}

# Function to check API endpoints
check_endpoints() {
    echo "🔍 Checking API endpoints..."
    
    # Check docs
    if curl -s "$API_URL/docs" > /dev/null 2>&1; then
        echo -e "${GREEN}📚 Documentation accessible${NC}"
    else
        echo -e "${YELLOW}⚠️ Documentation not accessible${NC}"
    fi
    
    # Check OpenAPI schema
    if curl -s "$API_URL/openapi.json" > /dev/null 2>&1; then
        echo -e "${GREEN}📋 OpenAPI schema accessible${NC}"
    else
        echo -e "${YELLOW}⚠️ OpenAPI schema not accessible${NC}"
    fi
}

# Function to show system resources
show_resources() {
    if command -v docker &> /dev/null; then
        echo "🐳 Docker container status:"
        docker ps --filter "name=unsearch" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
        
        echo ""
        echo "💾 Container resource usage:"
        docker stats --no-stream --filter "name=unsearch" --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"
    fi
}

# Function for continuous monitoring
continuous_monitor() {
    echo "🔄 Starting continuous monitoring (Press Ctrl+C to stop)..."
    
    while true; do
        check_health
        sleep $CHECK_INTERVAL
    done
}

# Function for single check
single_check() {
    echo "🏥 Performing health check..."
    check_health
    
    echo ""
    check_metrics
    
    echo ""
    check_endpoints
    
    echo ""
    show_resources
    
    echo ""
    echo "🔗 Useful URLs:"
    echo "  • API Health: $API_URL/health"
    echo "  • Documentation: $API_URL/docs"
    echo "  • Metrics: $API_URL/metrics"
    echo "  • OpenAPI Schema: $API_URL/openapi.json"
}

# Handle script arguments
case "${3:-check}" in
    "monitor")
        continuous_monitor
        ;;
    "check"|*)
        single_check
        ;;
esac
