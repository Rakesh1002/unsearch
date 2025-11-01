# UnQuest - Privacy-Respecting Search & Scraping Platform

A full-stack privacy-focused search and content scraping platform built with FastAPI, Next.js, and powered by SearXNG.

## 🏗️ Architecture

This is a **Turborepo monorepo** containing:

- **Backend API** (`apps/backend/`) - FastAPI application with SearXNG integration
- **Frontend Web App** (`apps/web/`) - Next.js dashboard for API management
- **Shared Package** (`packages/shared/`) - TypeScript types and utilities

## 🚀 Quick Start

### Prerequisites

- **Node.js 18+** and **npm**
- **Python 3.11+** and **pip**
- **PostgreSQL 12+**
- **Redis 6.0+**
- **Docker & Docker Compose** (optional)

### 1. Clone and Install

```bash
git clone <repository-url>
cd unquest
npm install
```

### 2. Environment Setup

**Backend Environment** (apps/backend/.env):

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/unquest

# Redis
REDIS_URL=redis://localhost:6379

# API Keys
SECRET_KEY=your-super-secret-key
JWT_SECRET_KEY=your-jwt-secret

# Stripe (for billing)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# SearXNG
SEARXNG_URL=http://localhost:8080
```

**Frontend Environment** (apps/web/.env.local):

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_URL=http://localhost:3000
```

### 3. Start Services

**Option A: Docker (Recommended)**

```bash
# Start infrastructure services
cd apps/backend
docker-compose up -d postgres redis searxng

# Run database migrations
alembic upgrade head
```

**Option B: Local Services**

```bash
# Install and configure PostgreSQL, Redis, and SearXNG locally
```

### 4. Development

```bash
# Start all services in development mode
npm run dev

# Or start individually:
npm run dev --workspace=apps/backend  # Backend on :8000
npm run dev --workspace=apps/web      # Frontend on :3000
```

## 🎯 Features

### Backend API (`apps/backend/`)

- **Multi-Engine Search** via SearXNG integration
- **Intelligent Web Scraping** with BeautifulSoup4
- **User Authentication** with JWT tokens
- **API Key Management** with per-user keys
- **Subscription & Billing** via Stripe integration
- **Usage Tracking** with rate limiting
- **Async Processing** with Celery workers
- **Comprehensive Monitoring** with metrics & health checks

### Frontend Dashboard (`apps/web/`)

- **Modern React/Next.js** interface
- **User Authentication** with secure session management
- **API Key Management** - create, view, and manage API keys
- **Usage Dashboard** - real-time usage statistics
- **Billing Portal** - subscription management via Stripe
- **API Documentation** - integrated docs viewer
- **Responsive Design** - works on all devices

## 📚 API Usage

### Authentication

```bash
# Register new user
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123",
    "full_name": "John Doe"
  }'

# Login
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123"
  }'
```

### Search & Scraping

```bash
# Search with scraping
curl -X POST "http://localhost:8000/api/v1/search" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "artificial intelligence trends 2024",
    "engines": ["google", "bing", "duckduckgo"],
    "scrape_results": true,
    "max_results": 10
  }'

# Batch search
curl -X POST "http://localhost:8000/api/v1/search/batch" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "queries": [
      {"query": "machine learning", "max_results": 5},
      {"query": "web scraping tools", "max_results": 5}
    ]
  }'
```

## 🚀 Deployment

### Production Architecture

```
┌─────────────────────┐    ┌─────────────────────┐
│   Vercel (Frontend) │    │  Railway (Backend)  │
│   ├─ Next.js Web    │◄──►│  ├─ FastAPI API     │
│   ├─ User Dashboard │    │  ├─ PostgreSQL DB   │
│   └─ Static Assets  │    │  ├─ Redis Cache     │
└─────────────────────┘    │  └─ SearXNG Engine  │
                           └─────────────────────┘
```

### Backend Deployment (Railway)

1. **Create Railway Project**

```bash
npm install -g @railway/cli
railway login
railway init
```

2. **Configure Environment Variables** in Railway dashboard:

```bash
DATABASE_URL=<railway-postgres-url>
REDIS_URL=<railway-redis-url>
SECRET_KEY=<production-secret>
STRIPE_SECRET_KEY=<live-stripe-key>
```

3. **Deploy**

```bash
cd apps/backend
railway deploy
```

### Frontend Deployment (Vercel)

1. **Install Vercel CLI**

```bash
npm install -g vercel
vercel login
```

2. **Configure Project**

```bash
cd apps/web
vercel
```

3. **Set Environment Variables** in Vercel dashboard:

```bash
NEXT_PUBLIC_API_URL=https://your-app.railway.app
```

### CI/CD Pipeline

The repository includes GitHub Actions for automated deployment:

**Required Secrets:**

- `RAILWAY_TOKEN` - Railway deployment token
- `VERCEL_TOKEN` - Vercel deployment token
- `VERCEL_ORG_ID` - Vercel organization ID
- `VERCEL_PROJECT_ID` - Vercel project ID

## 🛠️ Development

### Project Structure

```
unquest/
├── apps/
│   ├── backend/          # FastAPI application
│   │   ├── app/          # Application code
│   │   ├── alembic/      # Database migrations
│   │   ├── tests/        # Test suites
│   │   └── scripts/      # Utility scripts
│   └── web/              # Next.js application
│       ├── src/
│       │   ├── app/      # App Router pages
│       │   ├── components/ # UI components
│       │   └── lib/      # Utilities and hooks
│       └── public/       # Static assets
├── packages/
│   └── shared/           # Shared TypeScript types
├── .github/
│   └── workflows/        # CI/CD pipelines
└── docs/                 # Documentation
```

### Available Scripts

**Root Level:**

```bash
npm run dev          # Start all services
npm run build        # Build all applications
npm run test         # Run all tests
npm run lint         # Lint all code
npm run format       # Format code
```

**Backend:**

```bash
npm run dev --workspace=apps/backend    # Start FastAPI server
npm run test --workspace=apps/backend   # Run Python tests
npm run migrate --workspace=apps/backend # Run DB migrations
```

**Frontend:**

```bash
npm run dev --workspace=apps/web       # Start Next.js dev server
npm run build --workspace=apps/web     # Build for production
npm run type-check --workspace=apps/web # TypeScript checking
```

## 📋 Subscription Plans

| Feature          | Free         | Pro ($20/mo) |
| ---------------- | ------------ | ------------ |
| Searches         | 1,000/month  | Unlimited    |
| Scrapes          | 10,000/month | Unlimited    |
| API Keys         | 3            | Unlimited    |
| Rate Limit       | 60/min       | 1000/min     |
| Webhook Support  | ❌           | ✅           |
| Priority Support | ❌           | ✅           |

## 🔒 Security

- **JWT Authentication** with refresh tokens
- **API Key Management** with scoped permissions
- **Rate Limiting** based on subscription tiers
- **Input Validation** with Pydantic models
- **SQL Injection Protection** via SQLAlchemy ORM
- **CORS Configuration** for cross-origin requests

## 📈 Monitoring

- **Health Checks** at `/health` and `/metrics`
- **Prometheus Metrics** integration
- **Grafana Dashboards** for visualization
- **Structured Logging** with request tracking
- **Error Handling** with detailed error responses

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`npm run test`)
5. Commit changes (`git commit -m 'Add amazing feature'`)
6. Push to branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Development Guidelines

- Follow **TypeScript** best practices for frontend
- Use **Python type hints** for backend code
- Write **comprehensive tests** for new features
- Update **documentation** for API changes
- Follow **semantic commit** conventions

## 📄 License

This project is licensed under the AGPL-3.0 License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: [docs.unquest.ai](https://docs.unquest.ai)
- **API Status**: [status.unquest.ai](https://status.unquest.ai)
- **GitHub Issues**: For bug reports and feature requests
- **Email**: support@unquest.ai

---

**Built with ❤️ for developers who value privacy**
