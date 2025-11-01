#!/bin/bash

# End-to-End Test Script for UnSearch Platform
# This script tests the entire stack: Backend API + Frontend

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"
TEST_EMAIL="test_$(date +%s)@example.com"
TEST_PASSWORD="TestPassword123!"

echo "🧪 Starting End-to-End Tests"
echo "Backend URL: $BACKEND_URL"
echo "Frontend URL: $FRONTEND_URL"
echo "Test Email: $TEST_EMAIL"
echo ""

# Track test results
TESTS_PASSED=0
TESTS_FAILED=0

# Helper functions
test_endpoint() {
    local name=$1
    local method=$2
    local url=$3
    local data=$4
    local expected_status=$5
    local auth_token=$6
    
    echo -n "Testing $name... "
    
    if [ -n "$auth_token" ]; then
        RESPONSE=$(curl -s -w "\n%{http_code}" -X $method "$url" \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer $auth_token" \
            -d "$data" 2>/dev/null)
    else
        RESPONSE=$(curl -s -w "\n%{http_code}" -X $method "$url" \
            -H "Content-Type: application/json" \
            -d "$data" 2>/dev/null)
    fi
    
    HTTP_STATUS=$(echo "$RESPONSE" | tail -n 1)
    BODY=$(echo "$RESPONSE" | head -n -1)
    
    if [ "$HTTP_STATUS" = "$expected_status" ]; then
        echo -e "${GREEN}✓${NC} (Status: $HTTP_STATUS)"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        echo "$BODY" > /tmp/last_response.json
        return 0
    else
        echo -e "${RED}✗${NC} (Expected: $expected_status, Got: $HTTP_STATUS)"
        echo "Response: $BODY"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

check_service() {
    local name=$1
    local url=$2
    
    echo -n "Checking $name... "
    
    if curl -s -f -o /dev/null "$url" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} Online"
        return 0
    else
        echo -e "${RED}✗${NC} Offline"
        return 1
    fi
}

# Phase 1: Service Health Checks
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 Phase 1: Service Health Checks"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

check_service "Backend API" "$BACKEND_URL/health"
check_service "Frontend" "$FRONTEND_URL"
check_service "API Docs" "$BACKEND_URL/docs"

echo ""

# Phase 2: Backend API Tests
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔧 Phase 2: Backend API Tests"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Test user registration
echo -e "\n${YELLOW}Testing Authentication Flow:${NC}"
test_endpoint "User Registration" "POST" "$BACKEND_URL/api/v1/auth/register" \
    "{\"email\":\"$TEST_EMAIL\",\"password\":\"$TEST_PASSWORD\",\"full_name\":\"Test User\"}" \
    "201" ""

# Test user login
test_endpoint "User Login" "POST" "$BACKEND_URL/api/v1/auth/login" \
    "{\"email\":\"$TEST_EMAIL\",\"password\":\"$TEST_PASSWORD\"}" \
    "200" ""

# Extract tokens from login response
if [ -f /tmp/last_response.json ]; then
    ACCESS_TOKEN=$(python3 -c "import json; print(json.load(open('/tmp/last_response.json'))['access_token'])" 2>/dev/null || echo "")
    if [ -n "$ACCESS_TOKEN" ]; then
        echo -e "${GREEN}✓${NC} Access token obtained"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "${RED}✗${NC} Failed to extract access token"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
fi

# Test authenticated endpoints
echo -e "\n${YELLOW}Testing Authenticated Endpoints:${NC}"
test_endpoint "Get Current User" "GET" "$BACKEND_URL/api/v1/auth/me" \
    "" "200" "$ACCESS_TOKEN"

test_endpoint "Create API Key" "POST" "$BACKEND_URL/api/v1/auth/api-keys" \
    "{\"name\":\"Test API Key\",\"description\":\"E2E Test Key\"}" \
    "200" "$ACCESS_TOKEN"

# Extract API key
if [ -f /tmp/last_response.json ]; then
    API_KEY=$(python3 -c "import json; print(json.load(open('/tmp/last_response.json'))['key'])" 2>/dev/null || echo "")
    if [ -n "$API_KEY" ]; then
        echo -e "${GREEN}✓${NC} API key created: ${API_KEY:0:20}..."
        TESTS_PASSED=$((TESTS_PASSED + 1))
    fi
fi

test_endpoint "List API Keys" "GET" "$BACKEND_URL/api/v1/auth/api-keys" \
    "" "200" "$ACCESS_TOKEN"

# Test search endpoints (if API key was created)
if [ -n "$API_KEY" ]; then
    echo -e "\n${YELLOW}Testing Search Endpoints:${NC}"
    test_endpoint "Search Engines" "GET" "$BACKEND_URL/api/v1/search/engines" \
        "" "200" "$ACCESS_TOKEN"
    
    # Note: Actual search might fail without SearXNG, but endpoint should respond
    test_endpoint "Basic Search" "POST" "$BACKEND_URL/api/v1/search" \
        "{\"query\":\"test search\",\"max_results\":5}" \
        "200" "$ACCESS_TOKEN" || true
fi

# Test billing endpoints
echo -e "\n${YELLOW}Testing Billing Endpoints:${NC}"
test_endpoint "Get Plans" "GET" "$BACKEND_URL/api/v1/billing/plans" \
    "" "200" "$ACCESS_TOKEN"

test_endpoint "Get Subscription" "GET" "$BACKEND_URL/api/v1/billing/subscription" \
    "" "200" "$ACCESS_TOKEN"

test_endpoint "Get Usage" "GET" "$BACKEND_URL/api/v1/billing/usage" \
    "" "200" "$ACCESS_TOKEN"

echo ""

# Phase 3: Frontend Tests
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🌐 Phase 3: Frontend Tests"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check frontend pages
check_page() {
    local name=$1
    local url=$2
    
    echo -n "Checking $name page... "
    
    RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$url")
    
    if [ "$RESPONSE" = "200" ]; then
        echo -e "${GREEN}✓${NC}"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "${RED}✗${NC} (Status: $RESPONSE)"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

check_page "Home" "$FRONTEND_URL"
check_page "Login" "$FRONTEND_URL/auth/login"
check_page "Register" "$FRONTEND_URL/auth/register"
# Dashboard requires auth, so it should redirect
check_page "Dashboard (redirect expected)" "$FRONTEND_URL/dashboard"

echo ""

# Phase 4: Integration Tests
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔗 Phase 4: Integration Tests"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo -n "Testing CORS configuration... "
CORS_RESPONSE=$(curl -s -I -X OPTIONS "$BACKEND_URL/api/v1/auth/login" \
    -H "Origin: $FRONTEND_URL" \
    -H "Access-Control-Request-Method: POST" 2>/dev/null | grep -i "access-control-allow-origin" || echo "")

if [ -n "$CORS_RESPONSE" ]; then
    echo -e "${GREEN}✓${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${YELLOW}⚠${NC} CORS headers not found (may be normal in dev)"
fi

echo ""

# Phase 5: Performance Tests
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⚡ Phase 5: Performance Tests"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo -n "Testing API response time... "
START_TIME=$(date +%s%N)
curl -s -o /dev/null "$BACKEND_URL/health"
END_TIME=$(date +%s%N)
RESPONSE_TIME=$(( ($END_TIME - $START_TIME) / 1000000 ))

if [ $RESPONSE_TIME -lt 1000 ]; then
    echo -e "${GREEN}✓${NC} ${RESPONSE_TIME}ms"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${YELLOW}⚠${NC} ${RESPONSE_TIME}ms (slow)"
fi

echo ""

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Test Summary"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "Tests Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Tests Failed: ${RED}$TESTS_FAILED${NC}"
TOTAL_TESTS=$((TESTS_PASSED + TESTS_FAILED))
SUCCESS_RATE=$((TESTS_PASSED * 100 / TOTAL_TESTS))
echo "Success Rate: $SUCCESS_RATE%"

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "\n${GREEN}✅ All tests passed! The system is ready for deployment.${NC}"
    exit 0
else
    echo -e "\n${RED}❌ Some tests failed. Please review the errors above.${NC}"
    exit 1
fi
