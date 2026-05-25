#!/bin/bash
#
# UnSearch Rebuild & Redeploy Script
# Rebuilds frontend and restarts all services
#

set -e

cd /root/unsearch

echo "================================"
echo "  UnSearch Rebuild & Redeploy"
echo "================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Build frontend
echo -e "${YELLOW}[1/3]${NC} Building frontend..."
cd apps/web
pnpm build
cd /root/unsearch
echo -e "${GREEN}✓${NC} Frontend built"

# Step 2: Restart PM2 services
echo ""
echo -e "${YELLOW}[2/3]${NC} Restarting services..."
pm2 reload ecosystem.config.js
echo -e "${GREEN}✓${NC} Services restarted"

# Step 3: Verify health
echo ""
echo -e "${YELLOW}[3/3]${NC} Checking health..."
sleep 3

# Check backend
if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Backend healthy"
else
    echo -e "${YELLOW}⚠${NC} Backend not responding yet (may still be starting)"
fi

# Check frontend
if curl -sf http://localhost:3000 > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Frontend healthy"
else
    echo -e "${YELLOW}⚠${NC} Frontend not responding yet (may still be starting)"
fi

echo ""
echo "================================"
echo -e "${GREEN}  Deploy complete!${NC}"
echo "================================"
echo ""
echo "Services:"
pm2 list
