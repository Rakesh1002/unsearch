#!/bin/bash
"""
Deployment script for SearchScrape API.
"""

set -e

# Configuration
APP_NAME="searchscrape-api"
DOCKER_IMAGE="searchscrape/api"
DOCKER_TAG="${1:-latest}"

echo "🚀 Deploying SearchScrape API..."
echo "📦 Image: $DOCKER_IMAGE:$DOCKER_TAG"

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker first."
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "Dockerfile" ]; then
    echo "❌ Dockerfile not found. Please run from project root."
    exit 1
fi

# Build Docker image
echo "🔨 Building Docker image..."
docker build -t "$DOCKER_IMAGE:$DOCKER_TAG" .

# Tag as latest if not already latest
if [ "$DOCKER_TAG" != "latest" ]; then
    docker tag "$DOCKER_IMAGE:$DOCKER_TAG" "$DOCKER_IMAGE:latest"
fi

echo "✅ Docker image built successfully"

# Check deployment type
case "${2:-local}" in
    "local")
        echo "🏠 Deploying locally with Docker Compose..."
        
        # Stop existing containers
        docker-compose down
        
        # Start services
        docker-compose up -d
        
        # Wait for services to be ready
        echo "⏳ Waiting for services to start..."
        sleep 10
        
        # Check health
        echo "🏥 Checking service health..."
        if curl -f http://localhost:8000/health > /dev/null 2>&1; then
            echo "✅ API is healthy"
        else
            echo "⚠️ API health check failed"
        fi
        
        echo "🎉 Local deployment complete!"
        echo "📖 API Documentation: http://localhost:8000/docs"
        echo "📊 Metrics: http://localhost:8000/metrics"
        ;;
        
    "staging")
        echo "🎭 Deploying to staging..."
        
        # Push to registry (configure your registry)
        # docker push "$DOCKER_IMAGE:$DOCKER_TAG"
        
        # Deploy to staging environment
        # kubectl apply -f k8s/staging/
        
        echo "⚠️ Staging deployment not fully implemented"
        echo "💡 Configure your staging environment in this script"
        ;;
        
    "production")
        echo "🏭 Deploying to production..."
        
        # Safety check
        read -p "⚠️ Are you sure you want to deploy to production? (yes/no): " confirm
        if [ "$confirm" != "yes" ]; then
            echo "❌ Production deployment cancelled"
            exit 1
        fi
        
        # Push to registry
        # docker push "$DOCKER_IMAGE:$DOCKER_TAG"
        
        # Deploy to production environment
        # kubectl apply -f k8s/production/
        
        echo "⚠️ Production deployment not fully implemented"
        echo "💡 Configure your production environment in this script"
        ;;
        
    *)
        echo "❌ Unknown deployment target: $2"
        echo "📖 Usage: $0 [tag] [local|staging|production]"
        exit 1
        ;;
esac

echo "🎉 Deployment script completed!"