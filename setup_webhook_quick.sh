#!/bin/bash
# Quick webhook setup for UnSearch API

echo "🪝 Setting up Stripe Webhook for UnSearch API"
echo "============================================="

# Check if Stripe CLI is installed
if ! command -v stripe &> /dev/null; then
    echo "❌ Stripe CLI not found. Please install it first:"
    echo "   brew install stripe/stripe-cli/stripe"
    echo "   Or download: https://github.com/stripe/stripe-cli/releases"
    exit 1
fi

echo "✅ Stripe CLI found"

# Get webhook URL
echo
echo "Enter your webhook URL:"
echo "For local testing: http://localhost:8000/api/v1/billing/webhook/stripe"
echo "For production: https://your-domain.com/api/v1/billing/webhook/stripe"
echo
read -p "Webhook URL: " WEBHOOK_URL

if [ -z "$WEBHOOK_URL" ]; then
    echo "❌ No URL provided. Exiting."
    exit 1
fi

echo
echo "🔄 Creating webhook endpoint..."

# Create webhook with all required events
WEBHOOK_RESULT=$(stripe webhook_endpoints create \
    --url="$WEBHOOK_URL" \
    --enabled-events="customer.subscription.created,customer.subscription.updated,customer.subscription.deleted,invoice.paid,invoice.payment_failed,payment_intent.succeeded,payment_method.attached,checkout.session.completed" \
    --json)

if [ $? -eq 0 ]; then
    WEBHOOK_ID=$(echo $WEBHOOK_RESULT | jq -r '.id')
    WEBHOOK_SECRET=$(echo $WEBHOOK_RESULT | jq -r '.secret')
    
    echo "✅ Webhook created successfully!"
    echo "   ID: $WEBHOOK_ID"
    echo "   Secret: $WEBHOOK_SECRET"
    echo
    echo "📝 Add this to your .env file:"
    echo "   STRIPE_WEBHOOK_SECRET=\"$WEBHOOK_SECRET\""
    echo
    echo "🧪 Test your webhook:"
    echo "   stripe trigger customer.subscription.created"
else
    echo "❌ Failed to create webhook endpoint"
    exit 1
fi
