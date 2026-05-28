#!/bin/bash
"""
Setup script for UnSearch API development environment.
"""

set -e

echo "🚀 Setting up UnSearch API development environment..."

# Check if Python 3.11+ is available
python_version=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
required_version="3.11"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python 3.11+ is required. Found: $python_version"
    exit 1
fi

echo "✅ Python version: $python_version"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r backend/requirements.txt

# Copy environment file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your configuration"
fi

# Check if Docker is available
if command -v docker &> /dev/null; then
    echo "🐳 Docker found"
    
    # Check if docker-compose is available
    if command -v docker-compose &> /dev/null; then
        echo "🐙 Docker Compose found"
        echo "💡 You can start services with: docker-compose up -d"
    fi
else
    echo "⚠️  Docker not found. You'll need to set up services manually."
fi

# Run database migrations (from backend/ where alembic.ini lives)
echo "🗄️ Running database migrations..."
if command -v alembic &> /dev/null; then
    (cd backend && alembic upgrade head)
else
    echo "⚠️  Alembic not found in PATH. Skipping migrations."
fi

# Download NLTK data
echo "📚 Downloading NLTK data..."
python3 -c "
import nltk
try:
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
    print('✅ NLTK data downloaded')
except Exception as e:
    print(f'⚠️ Could not download NLTK data: {e}')
"

echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your configuration"
echo "2. Start services: docker-compose up -d (if using Docker)"
echo "3. Run the API: python -m app.main"
echo "4. Visit http://localhost:8000/docs for API documentation"
echo ""
echo "For development:"
echo "- Run tests: pytest"
echo "- Start Celery worker: celery -A app.workers.tasks worker --loglevel=info"
echo "- Monitor with Flower: celery -A app.workers.tasks flower"
