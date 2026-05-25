# UnSearch Production Secrets

All secrets are bound via `wrangler secret put <NAME>` per environment. Never commit values.

## Required for production

| Secret | Purpose | How to source |
|---|---|---|
| `SECRET_KEY` | JWT signing key (32-byte hex) | `openssl rand -hex 32` |
| `CLOUDFLARE_ACCOUNT_ID` | D1/Vectorize REST + container deploy | `wrangler whoami` |
| `CLOUDFLARE_API_TOKEN` | Container deploy + REST API | dash.cloudflare.com/profile/api-tokens (perms: Workers, Containers, D1, KV, R2, Vectorize, Queues, Pages — all R/W) |
| `STRIPE_SECRET_KEY` | Subscription mgmt | dashboard.stripe.com/apikeys |
| `STRIPE_PUBLISHABLE_KEY` | Frontend checkout | dashboard.stripe.com/apikeys |
| `STRIPE_WEBHOOK_SECRET` | Webhook signature verify | Stripe → Webhooks → endpoint `api.unsearch.dev/v1/billing/webhook` |
| `STRIPE_PRO_PRODUCT_ID` | Pro product ID | `scripts/setup_stripe_plans.py` |
| `STRIPE_PRO_MONTHLY_PRICE_ID` | Pro monthly price ID | same |
| `STRIPE_PRO_YEARLY_PRICE_ID` | Pro yearly price ID | same |
| `STRIPE_GROWTH_PRODUCT_ID` | Growth product | same |
| `STRIPE_GROWTH_MONTHLY_PRICE_ID` | Growth monthly | same |
| `STRIPE_GROWTH_YEARLY_PRICE_ID` | Growth yearly | same |
| `STRIPE_SCALE_PRODUCT_ID` | Scale product | same |
| `STRIPE_SCALE_MONTHLY_PRICE_ID` | Scale monthly | same |
| `STRIPE_SCALE_YEARLY_PRICE_ID` | Scale yearly | same |
| `RESEND_API_KEY` | Transactional email | resend.com → API keys (verify `unsearch.dev` DNS first) |
| `GOOGLE_CLIENT_ID` | OAuth | console.cloud.google.com → Credentials |
| `GOOGLE_CLIENT_SECRET` | OAuth | same |
| `GITHUB_CLIENT_ID` | OAuth | github.com/settings/developers |
| `GITHUB_CLIENT_SECRET` | OAuth | same |
| `SEARXNG_SECRET_KEY` | SearXNG internal (container only) | `openssl rand -hex 32` |

## Optional

| Secret | Purpose | Source |
|---|---|---|
| `SENTRY_DSN` | Error tracking | sentry.io project DSN |
| `POSTHOG_API_KEY` | Product analytics | posthog.com |
| `POSTHOG_HOST` | PostHog host URL | `https://app.posthog.com` or self-host |
| `SERPER_API_KEY` | Search fallback | serper.dev |
| `SEARCHAPI_KEY` | Search fallback | searchapi.io |
| `GOOGLE_CSE_API_KEY` | Google CSE fallback | console.cloud.google.com |
| `GOOGLE_CSE_CX` | Google CSE ID | same |
| `OPENAI_API_KEY` | Embeddings fallback | platform.openai.com |

## OAuth callback URLs

When creating OAuth apps, configure these callbacks:

- Google: `https://api.unsearch.dev/api/v1/auth/callback/google`
- GitHub: `https://api.unsearch.dev/api/v1/auth/callback/github`

## Stripe webhook endpoint

`https://api.unsearch.dev/api/v1/billing/webhook` — subscribe to:
- `checkout.session.completed`
- `customer.subscription.created`
- `customer.subscription.updated`
- `customer.subscription.deleted`
- `invoice.paid`
- `invoice.payment_failed`

## Set secrets in bulk

```bash
# Interactive (one at a time)
npx wrangler secret put SECRET_KEY --env production

# Bulk from .dev.vars (NEVER commit this file)
npx wrangler secret bulk .dev.vars --env production
```

## Container secrets

Cloudflare Containers receive secrets via environment variables defined in the
container config (see `workers/container.toml`). Same set as above; map them
1:1 from Worker secrets to container env.
