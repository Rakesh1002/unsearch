# Billing and Authentication Setup Guide

This guide walks you through setting up the complete billing and authentication system for the UnSearch API.

## Table of Contents

1. [Overview](#overview)
2. [Database Setup](#database-setup)
3. [Stripe Configuration](#stripe-configuration)
4. [Environment Variables](#environment-variables)
5. [Testing the System](#testing-the-system)
6. [API Usage](#api-usage)

## Overview

The UnSearch API now includes a complete billing system with:

- **User Authentication**: JWT-based authentication with registration/login
- **Subscription Plans**:
  - **Free Plan**: 1,000 searches, 10,000 scrapes per month
  - **Pro Plan ($20/month)**: Unlimited searches and scrapes
- **Usage Tracking**: Per-user monthly usage limits
- **Rate Limiting**: Plan-based rate limits
- **Stripe Integration**: Payment processing and subscription management

## Database Setup

1. **Run the database migration**:

```bash
# Make sure PostgreSQL is running
docker-compose up -d postgres

# Run migrations
alembic upgrade head
```

2. **Verify tables were created**:

```bash
psql -h localhost -U UnSearch -d UnSearch -c "\dt"
```

You should see these new tables:

- `users`
- `user_api_keys`
- `subscriptions`
- `plans`
- `usage_records`
- `invoices`
- `webhook_events`

## Stripe Configuration

### 1. Install Stripe CLI

```bash
# macOS
brew install stripe/stripe-cli/stripe

# Linux
# Download from https://github.com/stripe/stripe-cli/releases
```

### 2. Run the Setup Script

```bash
# For test mode (recommended for development)
./scripts/setup-stripe.sh

# For live mode (production)
./scripts/setup-stripe.sh live
```

This script will:

- Create the Pro plan product and price in Stripe
- Set up webhook endpoints
- Configure the customer portal
- Generate configuration values

### 3. Get Your API Keys

1. Go to [Stripe Dashboard](https://dashboard.stripe.com/test/apikeys)
2. Copy your test keys:
   - **Publishable key**: `pk_test_...`
   - **Secret key**: `sk_test_...`

### 4. Test Webhooks Locally

```bash
# Forward webhooks to your local server
stripe listen --forward-to localhost:8000/api/v1/billing/webhook/stripe

# Copy the webhook signing secret that appears
```

## Environment Variables

Add these to your `.env` file:

```bash
# JWT Settings
SECRET_KEY="your-secret-key-here"  # Generate: openssl rand -hex 32
JWT_ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES="1440"

# Stripe Settings (from setup script output)
STRIPE_SECRET_KEY="sk_test_..."
STRIPE_PUBLISHABLE_KEY="pk_test_..."
STRIPE_WEBHOOK_SECRET="whsec_..."
STRIPE_PRICE_ID_PRO="price_..."
```

## Testing the System

### 1. Start the Services

```bash
# Start all services
docker-compose up -d

# Start the API
make dev
```

### 2. Register a User

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPass123!",
    "full_name": "Test User"
  }'
```

### 3. Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPass123!"
  }'
```

Save the `access_token` from the response.

### 4. Create API Key

```bash
curl -X POST http://localhost:8000/api/v1/auth/api-keys \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production API Key",
    "description": "For production use"
  }'
```

### 5. Check Usage

```bash
curl http://localhost:8000/api/v1/auth/usage \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 6. Subscribe to Pro Plan

```bash
# Create checkout session
curl -X POST http://localhost:8000/api/v1/billing/checkout-session \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "price_id": "YOUR_PRO_PRICE_ID",
    "success_url": "http://localhost:3000/success",
    "cancel_url": "http://localhost:3000/cancel"
  }'
```

Visit the `checkout_url` returned to complete payment.

### 7. Test with API Key

```bash
# Use the API key for searches
curl -X POST http://localhost:8000/api/v1/search \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "test search",
    "engines": ["google"],
    "max_results": 5
  }'
```

## API Usage

### Authentication Endpoints

| Endpoint                | Method   | Description               |
| ----------------------- | -------- | ------------------------- |
| `/api/v1/auth/register` | POST     | Register new user         |
| `/api/v1/auth/login`    | POST     | Login with email/password |
| `/api/v1/auth/refresh`  | POST     | Refresh access token      |
| `/api/v1/auth/me`       | GET      | Get current user info     |
| `/api/v1/auth/api-keys` | GET/POST | Manage API keys           |
| `/api/v1/auth/usage`    | GET      | Get usage statistics      |

### Billing Endpoints

| Endpoint                           | Method              | Description            |
| ---------------------------------- | ------------------- | ---------------------- |
| `/api/v1/billing/plans`            | GET                 | List available plans   |
| `/api/v1/billing/subscription`     | GET/POST/PUT/DELETE | Manage subscription    |
| `/api/v1/billing/checkout-session` | POST                | Create Stripe checkout |
| `/api/v1/billing/billing-portal`   | POST                | Access customer portal |
| `/api/v1/billing/invoices`         | GET                 | List invoices          |
| `/api/v1/billing/payment-methods`  | GET/POST/DELETE     | Manage payment methods |

### Rate Limits

| Plan | Rate Limit | Monthly Searches | Monthly Scrapes |
| ---- | ---------- | ---------------- | --------------- |
| Free | 100/hour   | 1,000            | 10,000          |
| Pro  | 1,000/hour | Unlimited        | Unlimited       |

### Usage Tracking

The system automatically tracks:

- Monthly search count
- Monthly scrape count
- Usage by search engine
- Daily usage patterns

When limits are exceeded, the API returns:

```json
{
  "error": "UsageLimitExceeded",
  "message": "Monthly search limit (1000) exceeded",
  "details": {
    "limit": 1000,
    "used": 1001,
    "plan": "free"
  }
}
```

## Testing with Stripe Test Cards

Use these test card numbers:

| Card      | Number              | Behavior                |
| --------- | ------------------- | ----------------------- |
| Success   | 4242 4242 4242 4242 | Payment succeeds        |
| Decline   | 4000 0000 0000 0002 | Payment declined        |
| 3D Secure | 4000 0025 0000 3155 | Requires authentication |

Use any future date for expiry and any 3-digit CVC.

## Monitoring

### Check Subscription Status

```bash
# Via API
curl http://localhost:8000/api/v1/billing/subscription \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Via Stripe CLI
stripe subscriptions list --customer cus_...
```

### View Webhook Events

```bash
# In Stripe Dashboard
https://dashboard.stripe.com/test/webhooks

# Via CLI
stripe events list --limit 10
```

### Database Queries

```sql
-- Check user subscriptions
SELECT u.email, s.plan_type, s.status, s.current_period_end
FROM users u
JOIN subscriptions s ON u.id = s.user_id;

-- Check usage
SELECT u.email, ur.search_count, ur.scrape_count, ur.period_start
FROM users u
JOIN usage_records ur ON u.id = ur.user_id
WHERE ur.period_start = date_trunc('month', CURRENT_DATE);

-- Check rate limits
SELECT u.email, s.rate_limit
FROM users u
LEFT JOIN subscriptions s ON u.id = s.user_id
WHERE s.status = 'ACTIVE';
```

## Troubleshooting

### Common Issues

1. **"Rate limit exceeded"**

   - Check user's plan and current usage
   - Verify rate limit configuration

2. **"Invalid API key"**

   - Ensure API key is active
   - Check if user account is active

3. **Webhook failures**

   - Verify webhook secret is correct
   - Check webhook logs in Stripe Dashboard

4. **Subscription not activating**
   - Ensure webhook handler is processing events
   - Check `webhook_events` table for errors

### Debug Mode

Enable debug logging:

```bash
export DEBUG=true
export LOG_LEVEL=DEBUG
```

## Production Deployment

1. **Use production Stripe keys**
2. **Set strong SECRET_KEY**
3. **Enable HTTPS for webhook endpoint**
4. **Set up monitoring for failed payments**
5. **Configure backup payment methods**
6. **Set up customer support workflows**

## Support

For issues or questions:

- Check logs: `docker-compose logs -f api`
- View metrics: http://localhost:8000/metrics
- Stripe support: https://support.stripe.com
