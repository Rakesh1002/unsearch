#!/bin/bash
#
# Service Verification Script
# Verifies that all services (SearXNG, Redis, PostgreSQL, API) are running correctly
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SEARXNG_URL="${SEARXNG_URL:-http://localhost:8080}"
API_URL="${API_URL:-http://localhost:8000}"
REDIS_URL="${REDIS_URL:-redis://localhost:6379}"
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"

# Counters
PASSED=0
FAILED=0
WARNINGS=0

# Functions
print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_check() {
    echo -e "${YELLOW}[CHECK]${NC} $1"
}

print_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((PASSED++))
}

print_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((FAILED++))
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
    ((WARNINGS++))
}

# Check if a command exists
check_command() {
    if command -v "$1" &> /dev/null; then
        return 0
    else
        return 1
    fi
}

# Check HTTP endpoint
check_http_endpoint() {
    local url=$1
    local name=$2
    local expected_status=${3:-200}
    
    print_check "Testing $name at $url"
    
    if check_command curl; then
        response=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "$url" 2>/dev/null || echo "000")
        
        if [ "$response" = "$expected_status" ]; then
            print_pass "$name is responding (HTTP $response)"
            return 0
        elif [ "$response" = "000" ]; then
            print_fail "$name is not reachable"
            return 1
        else
            print_warn "$name returned HTTP $response (expected $expected_status)"
            return 1
        fi
    else
        print_warn "curl not available, skipping HTTP check"
        return 1
    fi
}

# Check TCP port
check_tcp_port() {
    local host=$1
    local port=$2
    local name=$3
    
    print_check "Testing $name on $host:$port"
    
    if check_command nc; then
        if nc -z -w 5 "$host" "$port" 2>/dev/null; then
            print_pass "$name port is open"
            return 0
        else
            print_fail "$name port is not reachable"
            return 1
        fi
    elif check_command timeout; then
        if timeout 5 bash -c "</dev/tcp/$host/$port" 2>/dev/null; then
            print_pass "$name port is open"
            return 0
        else
            print_fail "$name port is not reachable"
            return 1
        fi
    else
        print_warn "nc or timeout not available, skipping port check"
        return 1
    fi
}

# Check Redis
check_redis() {
    local host=$(echo "$REDIS_URL" | sed -E 's|redis://([^:]+):.*|\1|')
    local port=$(echo "$REDIS_URL" | sed -E 's|redis://[^:]+:([0-9]+).*|\1|')
    
    print_check "Testing Redis connection"
    
    if check_command redis-cli; then
        if redis-cli -h "$host" -p "$port" ping 2>/dev/null | grep -q "PONG"; then
            print_pass "Redis is responding to PING"
            return 0
        else
            print_fail "Redis is not responding"
            return 1
        fi
    else
        # Fall back to TCP check
        check_tcp_port "$host" "$port" "Redis"
    fi
}

# Check PostgreSQL
check_postgres() {
    print_check "Testing PostgreSQL connection"
    
    if check_command pg_isready; then
        if pg_isready -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -q 2>/dev/null; then
            print_pass "PostgreSQL is ready for connections"
            return 0
        else
            print_fail "PostgreSQL is not ready"
            return 1
        fi
    else
        # Fall back to TCP check
        check_tcp_port "$POSTGRES_HOST" "$POSTGRES_PORT" "PostgreSQL"
    fi
}

# Check SearXNG
check_searxng() {
    print_check "Testing SearXNG service"
    
    # Check health endpoint
    if check_http_endpoint "${SEARXNG_URL}/healthz" "SearXNG health"; then
        # Also test search functionality
        print_check "Testing SearXNG search functionality"
        
        if check_command curl; then
            response=$(curl -s "${SEARXNG_URL}/search?q=test&format=json" 2>/dev/null)
            
            if echo "$response" | grep -q "results"; then
                print_pass "SearXNG search is working"
                return 0
            else
                print_warn "SearXNG search response may not be valid"
                return 1
            fi
        fi
    fi
    
    return 1
}

# Check API
check_api() {
    print_check "Testing API service"
    
    # Check health endpoint
    check_http_endpoint "${API_URL}/health" "API health"
    
    # Check docs endpoint
    check_http_endpoint "${API_URL}/docs" "API documentation"
    
    # Check OpenAPI endpoint
    check_http_endpoint "${API_URL}/openapi.json" "OpenAPI spec"
}

# Check Docker containers
check_docker_containers() {
    print_check "Checking Docker containers"
    
    if check_command docker; then
        if docker info &>/dev/null; then
            # List running containers
            containers=$(docker ps --format "{{.Names}}: {{.Status}}" 2>/dev/null)
            
            if [ -n "$containers" ]; then
                echo -e "\nRunning containers:"
                echo "$containers" | while read line; do
                    if echo "$line" | grep -q "Up"; then
                        echo -e "  ${GREEN}✓${NC} $line"
                    else
                        echo -e "  ${RED}✗${NC} $line"
                    fi
                done
                
                # Check for expected containers
                for container in "searxng" "redis" "postgres" "api"; do
                    if docker ps --format "{{.Names}}" | grep -q "$container"; then
                        print_pass "Container '$container' is running"
                    else
                        print_warn "Container '$container' not found or not running"
                    fi
                done
            else
                print_warn "No running containers found"
            fi
        else
            print_warn "Docker is installed but not running or permission denied"
        fi
    else
        print_warn "Docker not available, skipping container checks"
    fi
}

# Main execution
main() {
    print_header "UnSearch Service Verification"
    
    echo "Configuration:"
    echo "  SEARXNG_URL: $SEARXNG_URL"
    echo "  API_URL: $API_URL"
    echo "  REDIS_URL: $REDIS_URL"
    echo "  POSTGRES_HOST: $POSTGRES_HOST:$POSTGRES_PORT"
    echo ""
    
    # Check Docker containers
    print_header "Docker Containers"
    check_docker_containers
    
    # Check individual services
    print_header "Service Health Checks"
    
    check_postgres
    check_redis
    check_searxng
    check_api
    
    # Summary
    print_header "Verification Summary"
    
    echo -e "  ${GREEN}Passed:${NC}   $PASSED"
    echo -e "  ${RED}Failed:${NC}   $FAILED"
    echo -e "  ${YELLOW}Warnings:${NC} $WARNINGS"
    echo ""
    
    if [ $FAILED -eq 0 ]; then
        echo -e "${GREEN}All critical checks passed!${NC}"
        exit 0
    else
        echo -e "${RED}Some checks failed. Please review the output above.${NC}"
        exit 1
    fi
}

# Run main
main "$@"
