# SearchScrape API

A production-ready web search and content scraping API built with FastAPI, SearXNG, and BeautifulSoup4. This API provides unified search and scraping capabilities through a single endpoint with enterprise-grade reliability, performance, and maintainability.

## 🚀 Features

- **Multi-Engine Search**: Powered by SearXNG with support for Google, Bing, DuckDuckGo, and more
- **Content Scraping**: Intelligent content extraction using BeautifulSoup4 with multiple strategies
- **User Authentication**: JWT-based authentication with registration, login, and API key management
- **Subscription Billing**: Stripe integration with Free and Pro plans
- **Usage Limits**: Plan-based usage tracking (Free: 1K searches, Pro: unlimited)
- **Redis Caching**: Multi-layer caching with compression for optimal performance
- **Async Processing**: Full async/await implementation with Celery for background tasks
- **Rate Limiting**: Plan-based rate limiting (Free: 100/hour, Pro: 1K/hour)
- **Payment Processing**: Stripe Checkout, billing portal, and webhook handling
- **Monitoring**: Prometheus metrics, structured logging, and health checks
- **Security**: Input validation, CORS, security headers, and XSS protection
- **Documentation**: Automatic OpenAPI documentation with Swagger UI

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI       │    │    SearXNG      │    │ BeautifulSoup4  │
│   API Gateway   │◄──►│ Search Engine   │    │ Content Scraper │
│  + Auth/Billing │    └─────────────────┘    └─────────────────┘
└─────────────────┘              │                       │
         │                       ▼                       ▼
         ▼              ┌─────────────────┐    ┌─────────────────┐
┌─────────────────┐    │   PostgreSQL    │    │     Celery      │
│     Redis       │    │  Users/Billing  │    │ Task Queue      │
│ Cache + Limits  │    │   + Metadata    │    └─────────────────┘
└─────────────────┘    └─────────────────┘              │
         │                       │                       ▼
         └───────────────────────┼─────────────► ┌─────────────────┐
                                 │               │     Stripe      │
                                 └──────────────►│   Payments      │
                                                 └─────────────────┘
```

## 💰 Subscription Plans

| Plan | Price | Searches/Month | Scrapes/Month | Rate Limit | Features |
|------|-------|---------------|---------------|------------|----------|
| **Free** | $0 | 1,000 | 10,000 | 100/hour | Basic API access |
| **Pro** | $20 | Unlimited | Unlimited | 1,000/hour | Priority support, webhooks |

## 📋 Requirements

- Python 3.11+
- Redis 6.0+
- PostgreSQL 12+
- SearXNG instance
- Stripe account (for billing)
- Docker & Docker Compose (optional)

## 🛠️ Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd searchscrape-api
make setup
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your configuration
```

### 3. Start Services (Docker)

```bash
make docker-up
```

### 4. Set up Billing (Optional)

```bash
# Install Stripe CLI
brew install stripe/stripe-cli/stripe

# Set up Stripe products and webhooks
./scripts/setup-stripe.sh

# Add Stripe keys to .env (from Stripe dashboard)
```

### 5. Run Database Migrations

```bash
make migrate
```

### 6. Start the API

```bash
make dev
```

The API will be available at:

- **API**: http://localhost:8000
- **Documentation**: http://localhost:8000/docs
- **Metrics**: http://localhost:8000/metrics

## 📖 API Usage

### 1. Register and Get API Key

```bash
# Register user
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123!",
    "full_name": "John Doe"
  }'

# Login to get JWT token
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123!"
  }'

# Create API key
curl -X POST "http://localhost:8000/api/v1/auth/api-keys" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production API Key",
    "description": "For production use"
  }'
```

### 2. Search with API Key

```bash
curl -X POST "http://localhost:8000/api/v1/search" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "python web scraping",
    "engines": ["google", "bing"],
    "max_results": 10,
    "scrape_content": true,
    "include_images": true,
    "include_links": true
  }'
```

### 3. Check Usage and Subscribe

```bash
# Check current usage
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "http://localhost:8000/api/v1/auth/usage"

# Upgrade to Pro plan
curl -X POST "http://localhost:8000/api/v1/billing/checkout-session" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "price_id": "price_pro_monthly",
    "success_url": "https://yourapp.com/success",
    "cancel_url": "https://yourapp.com/cancel"
  }'
```

### Async Processing

```bash
curl -X POST "http://localhost:8000/api/v1/search/" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "large dataset processing",
    "engines": ["google", "bing", "duckduckgo"],
    "max_results": 50,
    "scrape_content": true,
    "async_mode": true,
    "webhook_url": "https://your-api.com/webhook"
  }'
```

## 🔧 Configuration

Key environment variables:

```bash
# Core Settings
SEARXNG_URL=http://localhost:8080
DATABASE_URL=postgresql://user:pass@localhost:5432/searchscrape

# Authentication & Billing
SECRET_KEY=your-secret-key-here
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
REDIS_URL=redis://localhost:6379

# Security
API_KEYS=key1,key2,key3
RATE_LIMIT_DEFAULT=1000/hour

# Performance
SCRAPING_MAX_CONCURRENT=10
CACHE_DEFAULT_TTL=3600
WORKERS=4
```

See `.env.example` for complete configuration options.

## 🧪 Testing

```bash
# Run all tests
make test

# Run specific test suites
make test-unit
make test-integration
make test-performance

# Run with coverage
make test-coverage
```

## 📊 Monitoring

### Health Check

```bash
curl http://localhost:8000/health
```

### Metrics (Prometheus)

```bash
curl http://localhost:8000/metrics
```

### Application Monitoring

```bash
# Check API health
make monitor

# Continuous monitoring
make monitor-continuous

# View logs
make logs
```

## 🐳 Docker Deployment

### Development

```bash
make docker-up
```

### Production

```bash
# Build production image
make docker-build

# Deploy
make deploy-prod
```

## 🔐 Security

- **API Key Authentication**: Secure your API with API keys
- **Rate Limiting**: Prevent abuse with configurable rate limits
- **Input Validation**: Comprehensive input sanitization and validation
- **CORS Protection**: Configurable CORS policies
- **Security Headers**: Automatic security headers (HSTS, CSP, etc.)
- **Robots.txt Respect**: Optional robots.txt compliance for scraping

## 📈 Performance

- **Async Architecture**: Full async/await implementation
- **Connection Pooling**: Efficient HTTP connection management
- **Redis Caching**: Multi-layer caching with compression
- **Concurrent Scraping**: Configurable concurrent request limits
- **Request Deduplication**: Automatic duplicate request handling

### Benchmarks

- **Throughput**: 1000+ requests per second
- **Latency**: <500ms average response time
- **Concurrency**: 100+ concurrent requests
- **Cache Hit Rate**: >80% for repeated queries

## 🔄 Background Tasks

Start Celery worker for async processing:

```bash
# Start worker
make worker

# Monitor with Flower
make flower
```

## 🗄️ Database

### Migrations

```bash
# Create migration
make migration

# Apply migrations
make migrate
```

### Schema

The API uses PostgreSQL with the following main tables:

**Core Tables:**
- `api_keys` - Legacy API key management
- `search_requests` - Request logging and analytics
- `search_results` - Individual search results
- `scraping_jobs` - Async scraping job tracking
- `error_logs` - Error logging and debugging

**User Management & Billing:**
- `users` - User accounts and profiles
- `user_api_keys` - User-specific API keys
- `subscriptions` - Active subscriptions and plans
- `plans` - Available subscription plans
- `usage_records` - Monthly usage tracking
- `invoices` - Payment history and invoices
- `webhook_events` - Stripe webhook event processing

## 🛡️ Error Handling

Comprehensive error handling with:

- **Structured Error Responses**: Consistent error format
- **Retry Logic**: Automatic retries for transient failures
- **Circuit Breakers**: Protection against cascade failures
- **Graceful Degradation**: Fallback mechanisms
- **Error Logging**: Detailed error tracking and analytics

## 📚 Documentation

**API Documentation:**
- **Interactive Docs**: http://localhost:8000/docs
- **OpenAPI Schema**: http://localhost:8000/openapi.json
- **ReDoc**: http://localhost:8000/redoc

**Setup & Operations:**
- **[Billing Setup Guide](docs/BILLING_SETUP.md)** - Complete authentication and billing setup
- **[API Examples](docs/API_EXAMPLES.md)** - Comprehensive usage examples
- **[Operations Runbooks](docs/operations/RUNBOOKS.md)** - Operational procedures
- **[Secrets Management](docs/SECRETS_MANAGEMENT.md)** - Security and secrets guide

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run the test suite
6. Submit a pull request

### Development Setup

```bash
# Setup development environment
make dev-setup

# Run pre-commit hooks
make pre-commit

# Format code
make format

# Run linting
make lint

# Type checking
make typecheck
```

## 📄 License

This project is licensed under the AGPL-3.0 License - see the LICENSE file for details.

## 🔗 Links

- **SearXNG**: https://github.com/searxng/searxng
- **FastAPI**: https://fastapi.tiangolo.com/
- **BeautifulSoup4**: https://www.crummy.com/software/BeautifulSoup/
- **Redis**: https://redis.io/
- **PostgreSQL**: https://www.postgresql.org/
- **Celery**: https://docs.celeryproject.org/

## 🆘 Support

- **Issues**: Create an issue on GitHub
- **Documentation**: Check the `/docs` endpoint
- **Monitoring**: Use the `/health` and `/metrics` endpoints

## 🎯 Roadmap

- [x] User authentication and JWT tokens
- [x] Stripe billing integration
- [x] Usage tracking and plan-based limits
- [x] Plan-based rate limiting
- [ ] JavaScript rendering support
- [ ] Advanced content extraction (readability.js)
- [ ] GraphQL API support
- [ ] Kubernetes deployment manifests
- [ ] Advanced analytics dashboard
- [ ] Machine learning-based result ranking
- [ ] WebSocket real-time updates
- [ ] Plugin system for custom scrapers
- [ ] Enterprise SSO integration
- [ ] Usage analytics dashboard

---

**SearchScrape API** - Production-ready web search and scraping made simple.
