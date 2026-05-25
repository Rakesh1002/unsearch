# Environment Variables Configuration

## Backend (FastAPI) - `apps/backend/.env`

### Required Variables

```bash
# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/unsearch
# Example: postgresql://postgres:postgres@localhost:5432/unsearch_db

# Redis Configuration
REDIS_URL=redis://localhost:6379
# For production with auth: redis://:password@redis-host:6379/0

# Security Keys
SECRET_KEY=your-super-secret-key-minimum-32-chars
# Generate: openssl rand -hex 32
JWT_SECRET_KEY=your-jwt-secret-key-minimum-32-chars
# Generate: openssl rand -hex 32

# Environment
ENVIRONMENT=development  # Options: development, staging, production
DEBUG=true  # Set to false in production

# API Configuration
APP_NAME=UnSearch API
VERSION=1.0.0
API_PREFIX=/api/v1
```

### Optional Variables

```bash
# Stripe Configuration (Required for billing features)
STRIPE_SECRET_KEY=sk_test_...  # Test key for development
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRO_PRICE_ID=price_...  # Create in Stripe Dashboard

# SearXNG Configuration
SEARXNG_URL=http://localhost:8080  # Default if using Docker
SEARXNG_SECRET=ultrasecretkey  # Must match searxng/settings.yml

# CORS Configuration
ALLOWED_ORIGINS=["http://localhost:3000","https://app.unsearch.ai"]
CORS_CREDENTIALS=true
CORS_METHODS=["GET","POST","PUT","DELETE","OPTIONS"]
CORS_HEADERS=["*"]

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_DEFAULT=100/minute
RATE_LIMIT_STORAGE_URL=redis://localhost:6379/1

# Celery Configuration (For async tasks)
CELERY_BROKER_URL=redis://localhost:6379/2
CELERY_RESULT_BACKEND=redis://localhost:6379/3

# Monitoring
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=9090
SENTRY_DSN=https://...@sentry.io/...  # Optional error tracking

# Email Configuration (For notifications)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=noreply@unsearch.ai

# External Services
OPENAI_API_KEY=sk-...  # If using AI features
SLACK_WEBHOOK_URL=https://hooks.slack.com/...  # For alerts

# Performance Tuning
MAX_CONNECTIONS_COUNT=100
MIN_CONNECTIONS_COUNT=10
CONNECTION_TIMEOUT=30
CACHE_TTL=3600  # 1 hour
MAX_CACHE_SIZE=1000
```

## Frontend (Next.js) - `apps/web/.env.local`

### Required Variables

```bash
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
# Production: https://api.unsearch.ai or your Railway URL

# App Configuration
NEXT_PUBLIC_APP_URL=http://localhost:3000
# Production: https://app.unsearch.ai or your Vercel URL
```

### Optional Variables

```bash
# Analytics (Optional)
NEXT_PUBLIC_GA_ID=G-XXXXXXXXXX  # Google Analytics
NEXT_PUBLIC_MIXPANEL_TOKEN=your-mixpanel-token
NEXT_PUBLIC_POSTHOG_KEY=your-posthog-key

# Feature Flags
NEXT_PUBLIC_ENABLE_BILLING=true
NEXT_PUBLIC_ENABLE_DOCS=true
NEXT_PUBLIC_ENABLE_WEBHOOKS=false

# Stripe (For embedded checkout)
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...

# Sentry (Error tracking)
NEXT_PUBLIC_SENTRY_DSN=https://...@sentry.io/...
SENTRY_AUTH_TOKEN=your-sentry-auth-token
SENTRY_ORG=your-org
SENTRY_PROJECT=your-project

# Support
NEXT_PUBLIC_SUPPORT_EMAIL=support@unsearch.ai
NEXT_PUBLIC_DISCORD_INVITE=https://discord.gg/...
```

## Docker Environment - `docker-compose.yml`

```yaml
services:
  api:
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/unsearch
      - REDIS_URL=redis://redis:6379
      - SEARXNG_URL=http://searxng:8080
      - SECRET_KEY=${SECRET_KEY}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - ENVIRONMENT=production

  postgres:
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=unsearch

  redis:
    # No environment variables needed for basic setup
    # For production, add:
    # command: redis-server --requirepass ${REDIS_PASSWORD}

  searxng:
    environment:
      - SEARXNG_SECRET=ultrasecretkey
      - SEARXNG_SETTINGS_PATH=/etc/searxng/settings.yml
```

## Environment Variables by Service

### PostgreSQL Requirements

- `DATABASE_URL` must include:
  - Username and password
  - Host and port
  - Database name
  - SSL mode for production: `?sslmode=require`

### Redis Requirements

- Basic: `redis://host:port`
- With auth: `redis://:password@host:port/db_number`
- Use different DB numbers for different purposes (cache, celery, rate limiting)

### Stripe Requirements

1. Create account at https://stripe.com
2. Get API keys from Dashboard
3. Create products and prices
4. Set up webhook endpoint
5. Configure webhook secret

### SearXNG Requirements

- Must be accessible from backend
- Settings file must allow API access
- Secret key must match between services

## Generating Secure Keys

```bash
# Generate SECRET_KEY and JWT_SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"

# Or using OpenSSL
openssl rand -hex 32

# Generate strong passwords
openssl rand -base64 32
```

## Validation Script

Create `scripts/validate-env.sh`:

```bash
#!/bin/bash

# Backend validation
echo "Checking backend environment..."
required_backend=(
  "DATABASE_URL"
  "REDIS_URL"
  "SECRET_KEY"
  "JWT_SECRET_KEY"
  "ENVIRONMENT"
)

for var in "${required_backend[@]}"; do
  if [ -z "${!var}" ]; then
    echo "❌ Missing required variable: $var"
    exit 1
  else
    echo "✅ $var is set"
  fi
done

# Frontend validation
echo "Checking frontend environment..."
required_frontend=(
  "NEXT_PUBLIC_API_URL"
  "NEXT_PUBLIC_APP_URL"
)

for var in "${required_frontend[@]}"; do
  if [ -z "${!var}" ]; then
    echo "❌ Missing required variable: $var"
    exit 1
  else
    echo "✅ $var is set"
  fi
done

echo "✅ All required environment variables are set!"
```

## Security Best Practices

1. **Never commit `.env` files** to version control
2. **Use different keys** for different environments
3. **Rotate secrets regularly** (every 90 days)
4. **Use secret management services** in production:
   - AWS Secrets Manager
   - HashiCorp Vault
   - Railway/Vercel environment variables
5. **Encrypt sensitive data** in transit and at rest
6. **Use strong passwords** (minimum 32 characters for keys)
7. **Limit access** to production environment variables

## Environment-Specific Configurations

### Development

```bash
ENVIRONMENT=development
DEBUG=true
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/unsearch_dev
ALLOWED_ORIGINS=["http://localhost:3000"]
```

### Staging

```bash
ENVIRONMENT=staging
DEBUG=false
DATABASE_URL=postgresql://user:pass@staging-db.railway.app:5432/unsearch_staging
ALLOWED_ORIGINS=["https://staging.unsearch.ai"]
```

### Production

```bash
ENVIRONMENT=production
DEBUG=false
DATABASE_URL=postgresql://user:pass@prod-db.railway.app:5432/unsearch_prod?sslmode=require
ALLOWED_ORIGINS=["https://app.unsearch.ai"]
```
