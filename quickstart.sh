#!/bin/bash
# UnSearch Quick Start Script
# Usage: curl -fsSL https://raw.githubusercontent.com/Rakesh1002/unsearch/main/quickstart.sh | bash

set -e

echo "======================================"
echo "  UnSearch - Verifiable Retrieval"
echo "  for AI Agents (Apache 2.0)"
echo "======================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed.${NC}"
    echo "Install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check Docker Compose
if ! docker compose version &> /dev/null; then
    echo -e "${RED}Error: Docker Compose is not available.${NC}"
    echo "Make sure you have Docker Compose V2 installed."
    exit 1
fi

echo -e "${BLUE}Checking Docker...${NC} ✓"

# Create directory
INSTALL_DIR="${UNSEARCH_DIR:-$HOME/unsearch}"
echo -e "${BLUE}Installing to:${NC} $INSTALL_DIR"

mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

# Download docker-compose file
echo -e "${BLUE}Downloading configuration...${NC}"
curl -fsSL https://raw.githubusercontent.com/Rakesh1002/unsearch/main/docker-compose.quickstart.yml -o docker-compose.yml

# Generate API key if not provided
if [ -z "$UNSEARCH_API_KEY" ]; then
    UNSEARCH_API_KEY="uns-$(openssl rand -hex 16)"
fi

# Create .env file
cat > .env <<EOF
# UnSearch Configuration
UNSEARCH_API_KEY=$UNSEARCH_API_KEY
SEARXNG_SECRET_KEY=$(openssl rand -hex 16)
EOF

echo -e "${BLUE}Starting services...${NC}"
docker compose up -d

echo ""
echo -e "${GREEN}======================================"
echo "  UnSearch is starting!"
echo "======================================${NC}"
echo ""
echo -e "API URL:      ${BLUE}http://localhost:8000${NC}"
echo -e "API Docs:     ${BLUE}http://localhost:8000/docs${NC}"
echo -e "API Key:      ${YELLOW}$UNSEARCH_API_KEY${NC}"
echo ""
echo -e "${YELLOW}Save your API key! You'll need it to make requests.${NC}"
echo ""
echo "Quick test:"
echo -e "${BLUE}curl -X POST http://localhost:8000/api/v1/agent/search \\
  -H 'Content-Type: application/json' \\
  -H 'X-API-Key: $UNSEARCH_API_KEY' \\
  -d '{\"query\": \"What is AI?\", \"max_results\": 3}'${NC}"
echo ""
echo "Python SDK:"
echo -e "${BLUE}pip install unsearch
from unsearch import UnSearchClient
client = UnSearchClient(api_key='$UNSEARCH_API_KEY', base_url='http://localhost:8000')
results = client.search('Hello world')${NC}"
echo ""
echo -e "View logs:    ${BLUE}docker compose logs -f api${NC}"
echo -e "Stop:         ${BLUE}docker compose down${NC}"
echo ""
echo -e "${GREEN}Happy searching!${NC}"
