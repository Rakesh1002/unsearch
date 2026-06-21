# Railway Deployment Guide

Deploy UnSearch to Railway for production in under 30 minutes.

## Why Railway?

- ✅ **Fast deployment** - Docker Compose works as-is
- ✅ **Managed services** - PostgreSQL, Redis included
- ✅ **Auto-scaling** - Handles traffic spikes
- ✅ **Simple pricing** - ~$20/mo for MVP
- ✅ **Great DX** - Best developer experience

## Prerequisites

1. Create Railway account: [railway.app](https://railway.app)
2. Install Railway CLI (optional): `npm install -g @railway/cli`
3. Have your domain ready (e.g., `unsearch.dev`)

## Step-by-Step Deployment

### 1. Create New Project

```bash
# Option A: Via CLI
railway login
railway init

# Option B: Via Dashboard
# Go to https://railway.app/new
# Click "Deploy from GitHub repo"
# Connect your GitHub account and select unsearch repo
```

### 2. Add Services

Railway will auto-detect services from `docker-compose.yml`. You need:

#### Service 1: API (FastAPI)
- **Source:** Root directory
- **Build:** Dockerfile
- **Port:** 8000

#### Service 2: Web (Next.js)
- **Source:** apps/web
- **Build:** Dockerfile in apps/web
- **Port:** 3000

#### Service 3: PostgreSQL
- **Type:** Database
- **Use:** Railway-provided PostgreSQL
- **Auto-provisioned**

#### Service 4: Redis
- **Type:** Database
- **Use:** Railway-provided Redis
- **Auto-provisioned**

#### Service 5: SearXNG
- **Source:** Root directory
- **Service:** searxng from docker-compose.yml
- **Port:** 8080

### 3. Configure Environment Variables

Go to your API service → Variables tab and add:

```bash
# Application
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Database (Railway provides these automatically)
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}

# Internal service URLs (Railway provides private networking)
SEARXNG_URL=http://searxng.railway.internal:8080

# Security
SECRET_KEY=<run: openssl rand -hex 32>
ALLOWED_ORIGINS=https://unsearch.dev,https://www.unsearch.dev
CORS_CREDENTIALS=true

# Cloudflare Workers AI
CLOUDFLARE_ACCOUNT_ID=your_account_id
CLOUDFLARE_API_TOKEN=your_api_token
CLOUDFLARE_AI_ENABLED=true

# Stripe (from setup_stripe.py output)
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_UNS_PRO_PRICE_ID=price_...
STRIPE_UNS_GROWTH_PRICE_ID=price_...
STRIPE_UNS_SCALE_PRICE_ID=price_...

# Analytics
POSTHOG_API_KEY=phc_...
POSTHOG_HOST=https://app.posthog.com

# Email
RESEND_API_KEY=re_...
EMAIL_FROM=noreply@unsearch.dev

# Monitoring
SENTRY_DSN=https://...@sentry.io/...
```

For Web service:

```bash
NEXT_PUBLIC_API_URL=https://api.unsearch.dev
NEXTAUTH_URL=https://unsearch.dev
NEXTAUTH_SECRET=<run: openssl rand -base64 32>
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_live_...
```

### 4. Configure Custom Domains

#### API Service (api.unsearch.dev)

1. Go to API service → Settings → Networking
2. Click "Generate Domain" (get: `<random>.up.railway.app`)
3. Click "Custom Domain"
4. Enter: `api.unsearch.dev`
5. Add DNS records to your domain:
   ```
   Type: CNAME
   Name: api
   Value: <random>.up.railway.app
   TTL: 300
   ```

#### Web Service (unsearch.dev)

1. Go to Web service → Settings → Networking
2. Click "Custom Domain"
3. Enter: `unsearch.dev` and `www.unsearch.dev`
4. Add DNS records:
   ```
   Type: CNAME
   Name: @
   Value: <random>.up.railway.app

   Type: CNAME
   Name: www
   Value: <random>.up.railway.app
   ```

Railway automatically provisions SSL certificates via Let's Encrypt.

### 5. Deploy!

Railway will automatically deploy when you push to GitHub (if connected).

Or manually trigger:

```bash
railway up
```

Check deployment status:
```bash
railway logs
```

### 6. Verify Deployment

```bash
# Check API health
curl https://api.unsearch.dev/health

# Check API docs
open https://api.unsearch.dev/docs

# Check web app
open https://unsearch.dev

# Test search endpoint
curl -X POST https://api.unsearch.dev/api/v1/agent/search \
  -H "X-API-Key: your_test_key" \
  -H "Content-Type: application/json" \
  -d '{"query": "test query", "max_results": 3}'
```

### 7. Set Up Stripe Webhook

Now that you have a production URL, configure Stripe webhook:

1. Go to [Stripe Dashboard → Webhooks](https://dashboard.stripe.com/webhooks)
2. Click "Add endpoint"
3. Enter URL: `https://api.unsearch.dev/api/v1/billing/webhook/stripe`
4. Select events:
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.paid`
   - `invoice.payment_failed`
   - `payment_intent.succeeded`
5. Copy webhook secret (starts with `whsec_`)
6. Add to Railway environment variables: `STRIPE_WEBHOOK_SECRET`

### 8. Test Stripe Integration

```bash
# Trigger test webhook (requires Stripe CLI)
stripe trigger customer.subscription.created --override customer.id=cus_test

# Or use Stripe dashboard → Webhooks → Send test webhook
```

## Monitoring & Logs

### View Logs

```bash
# Via CLI
railway logs --service api

# Via Dashboard
Go to service → Deployments → Click on deployment → Logs
```

### Metrics

Railway provides built-in metrics:
- CPU usage
- Memory usage
- Network traffic
- Response times

Access at: Service → Observability

### Alerts

Set up alerts for:
1. High error rate (> 5%)
2. High memory usage (> 80%)
3. Deployment failures

Go to: Project Settings → Notifications

## Scaling

### Horizontal Scaling

```bash
# Scale API to 2 instances
railway service scale --replicas 2 --service api
```

Or in Dashboard: Service → Settings → Scale → Replicas

### Vertical Scaling

Upgrade service resources:
- Hobby: 512MB RAM, 0.5 vCPU ($5/mo)
- Pro: 8GB RAM, 8 vCPU ($20/mo)
- Team: Custom

### Auto-scaling

Enable auto-scaling based on:
- CPU usage
- Memory usage
- Request rate

Go to: Service → Settings → Autoscaling

## Database Management

### Backups

Railway automatically backs up PostgreSQL:
- Hourly snapshots (retained 7 days)
- Daily snapshots (retained 30 days)

Restore from: Database → Backups → Restore

### Migrations

Run Alembic migrations:

```bash
# Via Railway CLI
railway run alembic upgrade head

# Or add to deployment
# In Dockerfile, add:
# RUN alembic upgrade head
```

### Database Access

```bash
# Connect to production DB
railway connect postgres

# Or get connection URL
railway variables --service postgres
```

## Cost Estimation

**Starter Configuration (~$20/mo)**
- API service (512MB): $5
- Web service (512MB): $5
- PostgreSQL (1GB): $5
- Redis (256MB): $5

**Production Configuration (~$100/mo)**
- API service (2GB): $20
- Web service (1GB): $10
- PostgreSQL (8GB): $40
- Redis (1GB): $10
- Multiple environments: $20

## Troubleshooting

### Service Won't Start

1. Check logs: `railway logs --service api`
2. Verify environment variables
3. Check health endpoint: `curl https://api.unsearch.dev/health`

### Database Connection Errors

1. Verify `DATABASE_URL` is set
2. Check PostgreSQL service is running
3. Restart API service

### High Memory Usage

1. Check for memory leaks in logs
2. Increase service memory
3. Enable connection pooling in DB config

### Slow Response Times

1. Check SearXNG service is healthy
2. Enable Redis caching
3. Add CDN (Cloudflare)

## Best Practices

### Security

- [ ] Use environment variables for all secrets
- [ ] Enable Railway's built-in secrets encryption
- [ ] Restrict CORS origins to your domain
- [ ] Use strong `SECRET_KEY` (32+ characters)
- [ ] Enable rate limiting

### Performance

- [ ] Enable Redis caching
- [ ] Use connection pooling
- [ ] Enable GZip compression
- [ ] Add CDN for static assets
- [ ] Monitor slow queries

### Reliability

- [ ] Set up health checks
- [ ] Configure auto-restart on failure
- [ ] Monitor error rates
- [ ] Set up alerting
- [ ] Have rollback plan

## Advanced: CI/CD Pipeline

### GitHub Actions

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Railway

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install Railway CLI
        run: npm install -g @railway/cli

      - name: Deploy to Railway
        run: railway up --service api
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
```

Get `RAILWAY_TOKEN`:
```bash
railway login
railway tokens create
```

Add to GitHub: Settings → Secrets → New repository secret

## Migration from Railway to Cloudflare Workers

After achieving PMF (Month 2+), migrate to Cloudflare Workers for cost savings:

1. See `/docs/deployment-cloudflare.md`
2. Expected cost reduction: $100/mo → $10/mo
3. Performance improvement: Lower latency, edge distribution

## Support

- Railway Docs: https://docs.railway.app
- Railway Discord: https://discord.gg/railway
- UnSearch Support: support@unsearch.dev

---

**Next Steps:**
1. Complete deployment
2. Test all endpoints
3. Set up monitoring
4. Launch to beta users
5. Monitor metrics and iterate
