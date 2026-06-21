# 🪝 Stripe Webhook Setup Guide

## Method 1: Manual Setup (Stripe Dashboard)

### Step 1: Create Webhook Endpoint
1. Go to [Stripe Dashboard > Webhooks](https://dashboard.stripe.com/test/webhooks)
2. Click "+ Add endpoint"
3. Enter your endpoint URL: `https://your-domain.com/api/v1/billing/webhook/stripe`

### Step 2: Select Events
Add these events (copy-paste friendly):
```
customer.subscription.created
customer.subscription.updated  
customer.subscription.deleted
invoice.paid
invoice.payment_failed
payment_intent.succeeded
payment_method.attached
checkout.session.completed
```

### Step 3: Get Webhook Secret
1. Click on your created webhook
2. Click "Reveal" under "Signing secret" 
3. Copy the webhook secret (starts with `whsec_`)
4. Add to your .env file:
   ```bash
   STRIPE_WEBHOOK_SECRET="whsec_your_secret_here"
   ```

## Method 2: Automated Setup (CLI)

### Prerequisites
```bash
# Install Stripe CLI
brew install stripe/stripe-cli/stripe
# OR download from: https://github.com/stripe/stripe-cli/releases
```

### Run Setup Script
```bash
./scripts/setup-stripe.sh
```

## Method 3: Local Development

### For testing locally with ngrok:
```bash
# Install ngrok
brew install ngrok
# OR download from: https://ngrok.com/download

# Expose local server
ngrok http 8000

# Use the ngrok URL in webhook setup:
# https://abc123.ngrok.io/api/v1/billing/webhook/stripe
```

### For testing with Stripe CLI:
```bash
# Forward webhooks to local endpoint
stripe listen --forward-to localhost:8000/api/v1/billing/webhook/stripe

# This will show webhook events in real-time
```

## Testing Your Webhook

### Test Events
```bash
# Test subscription created
stripe trigger customer.subscription.created

# Test payment succeeded  
stripe trigger payment_intent.succeeded

# Test invoice paid
stripe trigger invoice.payment_succeeded
```

### Monitor Webhook Logs
- Dashboard: https://dashboard.stripe.com/test/webhooks
- Or check your application logs for webhook processing
