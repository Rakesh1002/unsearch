#!/bin/bash

# Verification Script for UnSearch Platform Setup
# This script verifies that the monorepo is properly set up and ready for deployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "🔍 UnSearch Platform Setup Verification"
echo "========================================"
echo ""

CHECKS_PASSED=0
CHECKS_FAILED=0

# Helper function for checks
check() {
    local name=$1
    local condition=$2
    
    echo -n "  Checking $name... "
    
    if eval "$condition"; then
        echo -e "${GREEN}✓${NC}"
        CHECKS_PASSED=$((CHECKS_PASSED + 1))
        return 0
    else
        echo -e "${RED}✗${NC}"
        CHECKS_FAILED=$((CHECKS_FAILED + 1))
        return 1
    fi
}

# Phase 1: Project Structure
echo -e "${BLUE}📁 Phase 1: Project Structure${NC}"
echo "--------------------------------"

check "Root package.json exists" "[ -f package.json ]"
check "Turborepo configuration" "[ -f turbo.json ]"
check "Backend directory" "[ -d apps/backend ]"
check "Frontend directory" "[ -d apps/web ]"
check "Shared package" "[ -d packages/shared ]"
check "GitHub workflow" "[ -f .github/workflows/deploy.yml ]"
check "Vercel configuration" "[ -f vercel.json ]"
check "Documentation" "[ -d docs ]"

echo ""

# Phase 2: Backend Structure
echo -e "${BLUE}🔧 Phase 2: Backend Structure${NC}"
echo "--------------------------------"

check "Backend main.py" "[ -f apps/backend/app/main.py ]"
check "Backend requirements" "[ -f apps/backend/requirements.txt ]"
check "Backend Dockerfile" "[ -f apps/backend/Dockerfile ]"
check "Database models" "[ -f apps/backend/app/models/database.py ]"
check "Auth service" "[ -f apps/backend/app/services/auth_service.py ]"
check "API routes" "[ -d apps/backend/app/api ]"
check "Alembic migrations" "[ -d apps/backend/alembic ]"
check "Docker compose" "[ -f apps/backend/docker-compose.yml ]"

echo ""

# Phase 3: Frontend Structure
echo -e "${BLUE}🌐 Phase 3: Frontend Structure${NC}"
echo "--------------------------------"

check "Frontend package.json" "[ -f apps/web/package.json ]"
check "Next.js config" "[ -f apps/web/next.config.ts ]"
check "App directory" "[ -d apps/web/src/app ]"
check "Components directory" "[ -d apps/web/src/components ]"
check "API client" "[ -f apps/web/src/lib/api.ts ]"
check "Auth context" "[ -f apps/web/src/lib/auth-context.tsx ]"
check "Login page" "[ -f apps/web/src/app/auth/login/page.tsx ]"
check "Dashboard page" "[ -f apps/web/src/app/dashboard/page.tsx ]"

echo ""

# Phase 4: Shared Package
echo -e "${BLUE}📦 Phase 4: Shared Package${NC}"
echo "--------------------------------"

check "Shared package.json" "[ -f packages/shared/package.json ]"
check "TypeScript config" "[ -f packages/shared/tsconfig.json ]"
check "Auth types" "[ -f packages/shared/src/types/auth.ts ]"
check "API types" "[ -f packages/shared/src/types/api.ts ]"
check "Billing types" "[ -f packages/shared/src/types/billing.ts ]"

echo ""

# Phase 5: Build Tests
echo -e "${BLUE}🏗️ Phase 5: Build Tests${NC}"
echo "--------------------------------"

echo -n "  Testing shared package build... "
if (cd packages/shared && npm run build > /dev/null 2>&1); then
    echo -e "${GREEN}✓${NC}"
    CHECKS_PASSED=$((CHECKS_PASSED + 1))
else
    echo -e "${RED}✗${NC}"
    CHECKS_FAILED=$((CHECKS_FAILED + 1))
fi

echo -n "  Testing frontend build... "
if (cd apps/web && npm run build > /dev/null 2>&1); then
    echo -e "${GREEN}✓${NC}"
    CHECKS_PASSED=$((CHECKS_PASSED + 1))
else
    echo -e "${RED}✗${NC}"
    CHECKS_FAILED=$((CHECKS_FAILED + 1))
fi

echo -n "  Testing Turborepo build... "
if npm run build > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC}"
    CHECKS_PASSED=$((CHECKS_PASSED + 1))
else
    echo -e "${RED}✗${NC}"
    CHECKS_FAILED=$((CHECKS_FAILED + 1))
fi

echo ""

# Phase 6: Dependencies Check
echo -e "${BLUE}📚 Phase 6: Dependencies${NC}"
echo "--------------------------------"

echo -n "  Checking Node modules... "
if [ -d node_modules ] && [ -d apps/web/node_modules ]; then
    echo -e "${GREEN}✓${NC}"
    CHECKS_PASSED=$((CHECKS_PASSED + 1))
else
    echo -e "${YELLOW}⚠${NC} Run 'npm install' to install dependencies"
    CHECKS_FAILED=$((CHECKS_FAILED + 1))
fi

echo -n "  Checking Python venv... "
if [ -d apps/backend/venv ] || [ -d venv ]; then
    echo -e "${GREEN}✓${NC}"
    CHECKS_PASSED=$((CHECKS_PASSED + 1))
else
    echo -e "${YELLOW}⚠${NC} Python virtual environment not found"
fi

echo ""

# Phase 7: Documentation
echo -e "${BLUE}📖 Phase 7: Documentation${NC}"
echo "--------------------------------"

check "README.md" "[ -f README.md ]"
check "Environment variables doc" "[ -f ENV_VARIABLES.md ]"
check "Deployment guide" "[ -f DEPLOYMENT_GUIDE.md ]"
check "Mintlify config" "[ -f docs/mint.json ]"
check "API introduction" "[ -f docs/introduction.mdx ]"
check "Quickstart guide" "[ -f docs/quickstart.mdx ]"

echo ""

# Phase 8: Configuration Files
echo -e "${BLUE}⚙️ Phase 8: Configuration Files${NC}"
echo "--------------------------------"

check "TypeScript config (root)" "[ -f tsconfig.json ] || true"
check "ESLint config (web)" "[ -f apps/web/eslint.config.mjs ]"
check "Tailwind config (web)" "[ -f apps/web/postcss.config.mjs ]"
check "Docker files" "[ -f apps/backend/Dockerfile ]"
check "Python tests" "[ -d apps/backend/tests ]"
check "Alembic config" "[ -f apps/backend/alembic.ini ]"

echo ""

# Phase 9: Environment Setup
echo -e "${BLUE}🔐 Phase 9: Environment Setup${NC}"
echo "--------------------------------"

echo -n "  Backend .env file... "
if [ -f apps/backend/.env ]; then
    echo -e "${GREEN}✓${NC}"
    CHECKS_PASSED=$((CHECKS_PASSED + 1))
else
    echo -e "${YELLOW}⚠${NC} Create apps/backend/.env (see ENV_VARIABLES.md)"
fi

echo -n "  Frontend .env.local file... "
if [ -f apps/web/.env.local ]; then
    echo -e "${GREEN}✓${NC}"
    CHECKS_PASSED=$((CHECKS_PASSED + 1))
else
    echo -e "${YELLOW}⚠${NC} Create apps/web/.env.local (see ENV_VARIABLES.md)"
fi

echo ""

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${BLUE}📊 Verification Summary${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "Checks Passed: ${GREEN}$CHECKS_PASSED${NC}"
echo -e "Checks Failed: ${RED}$CHECKS_FAILED${NC}"

TOTAL_CHECKS=$((CHECKS_PASSED + CHECKS_FAILED))
if [ $TOTAL_CHECKS -gt 0 ]; then
    SUCCESS_RATE=$((CHECKS_PASSED * 100 / TOTAL_CHECKS))
    echo "Success Rate: $SUCCESS_RATE%"
fi

echo ""

if [ $CHECKS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed! Your monorepo is properly set up.${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Create environment files (see ENV_VARIABLES.md)"
    echo "2. Start services: npm run dev"
    echo "3. Deploy to production (see DEPLOYMENT_GUIDE.md)"
else
    echo -e "${YELLOW}⚠️ Some checks failed. Please review the issues above.${NC}"
    echo ""
    echo "Common fixes:"
    echo "1. Run 'npm install' to install dependencies"
    echo "2. Create missing environment files"
    echo "3. Check file paths and permissions"
fi

echo ""
echo "📚 Resources:"
echo "  - Environment setup: ENV_VARIABLES.md"
echo "  - Deployment guide: DEPLOYMENT_GUIDE.md"
echo "  - API documentation: docs/"

exit $CHECKS_FAILED
