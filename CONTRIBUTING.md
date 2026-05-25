# Contributing to UnSearch

Thank you for your interest in contributing to UnSearch! This guide will help you get started.

## Getting Started

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Git

### Development Setup

```bash
# Fork and clone the repo
git clone https://github.com/YOUR_USERNAME/unsearch.git
cd unsearch

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment config
cp .env.example .env
# Edit .env with your settings

# Start services (SearXNG, Redis, PostgreSQL)
docker compose up -d searxng redis postgres

# Run the API locally
uvicorn app.main:app --reload --port 8000
```

## Development Workflow

1. **Create a branch** from `main`:
   ```bash
   git checkout -b feature/your-feature
   ```

2. **Make your changes** following the code style guidelines below.

3. **Write tests** for any new functionality.

4. **Run the test suite**:
   ```bash
   # Unit tests
   pytest tests/unit/ -v --cov=app

   # Integration tests (requires running services)
   pytest tests/integration/ -v
   ```

5. **Run linting**:
   ```bash
   black --check app/ tests/
   isort --check-only app/ tests/
   flake8 app/ tests/ --max-line-length=120
   mypy app/ --ignore-missing-imports
   ```

6. **Submit a pull request** against `main`.

## Code Style

### Python

- **Formatter:** Black (line length: 120)
- **Import sorting:** isort
- **Linting:** Flake8
- **Type checking:** MyPy
- **Type hints:** Required for all function signatures
- **Models:** Use Pydantic for request/response models
- **Async:** Use `async def` for all API endpoint handlers

### Example

```python
from pydantic import BaseModel

class SearchRequest(BaseModel):
    query: str
    max_results: int = 10
    engines: list[str] | None = None

async def search(request: SearchRequest) -> SearchResponse:
    """Search the web using specified engines."""
    # Implementation
    pass
```

## Pull Request Guidelines

- Keep PRs focused on a single change
- Include tests for new features and bug fixes
- Update documentation if your change affects the API
- Reference any related issues in the PR description
- Ensure all CI checks pass before requesting review

## Reporting Issues

- Use [GitHub Issues](https://github.com/Rakesh1002/unsearch/issues) to report bugs
- Include steps to reproduce, expected behavior, and actual behavior
- Include your environment details (OS, Python version, Docker version)

## Project Structure

```
app/
├── api/v1/         # API route handlers
├── models/         # Pydantic models & ORM
├── services/       # Business logic
│   ├── core/       # Database, cache, search engine
│   ├── search/     # Search service
│   ├── scraping/   # Web scraping
│   └── ai/         # AI integration
├── middleware/      # Custom middleware
├── utils/          # Utilities
└── workers/        # Celery tasks
```

## License

By contributing to UnSearch, you agree that your contributions will be licensed under the Apache 2.0 License.
