#!/bin/bash

# Setup Stripe for the UnSearch API
# This script creates products, prices, and configures webhooks

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_prompt() {
    echo -e "${BLUE}[PROMPT]${NC} $1"
}

# Check if Stripe CLI is installed
if ! command -v stripe &> /dev/null; then
    log_error "Stripe CLI is not installed"
    log_info "Install it from: https://stripe.com/docs/stripe-cli"
    exit 1
fi

# Load environment variables
if [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Check if we're in test mode or live mode
if [ "$1" = "live" ]; then
    MODE="live"
    log_warn "Setting up LIVE Stripe products - this will charge real money!"
    log_prompt "Are you sure you want to continue? (yes/no): "
    read -r response
    if [ "$response" != "yes" ]; then
        log_info "Cancelled"
        exit 0
    fi
else
    MODE="test"
    log_info "Setting up TEST Stripe products"
fi

# Login to Stripe
log_info "Logging into Stripe..."
stripe login

# Set the API key
if [ "$MODE" = "live" ]; then
    stripe config --set live_mode_api_key
else
    stripe config --set test_mode_api_key
fi

# Function to create a product and price
create_product() {
    local name=$1
    local description=$2
    local price=$3
    local interval=$4
    local metadata=$5
    
    log_info "Creating product: $name"
    
    # Create product
    PRODUCT_ID=$(stripe products create \
        --name="$name" \
        --description="$description" \
        --metadata="$metadata" \
        --json | jq -r '.id')
    
    log_info "Product created: $PRODUCT_ID"
    
    if [ "$price" != "0" ]; then
        # Create price
        log_info "Creating price for $name: \$$price/$interval"
        
        PRICE_ID=$(stripe prices create \
            --product="$PRODUCT_ID" \
            --unit-amount="$((price * 100))" \
            --currency="usd" \
            --recurring[interval]="$interval" \
            --json | jq -r '.id')
        
        log_info "Price created: $PRICE_ID"
    else
        PRICE_ID="free"
    fi
    
    echo "$PRODUCT_ID:$PRICE_ID"
}

# Create products and prices
log_info "========================================="
log_info "Creating Stripe Products and Prices"
log_info "========================================="

# Free Plan (no Stripe product needed)
log_info "Free plan doesn't require Stripe setup"

# Pro Plan - $20/month
PRO_RESULT=$(create_product \
    "UnSearch Pro" \
    "Unlimited searches and scrapes with priority support" \
    20 \
    "month" \
    "plan=pro,search_limit=unlimited,scrape_limit=unlimited")

PRO_PRODUCT_ID=$(echo $PRO_RESULT | cut -d':' -f1)
PRO_PRICE_ID=$(echo $PRO_RESULT | cut -d':' -f2)

# Enterprise Plan - $100/month (optional)
ENTERPRISE_RESULT=$(create_product \
    "UnSearch Enterprise" \
    "Custom limits, dedicated support, and SLA" \
    100 \
    "month" \
    "plan=enterprise,custom=true")

ENTERPRISE_PRODUCT_ID=$(echo $ENTERPRISE_RESULT | cut -d':' -f1)
ENTERPRISE_PRICE_ID=$(echo $ENTERPRISE_RESULT | cut -d':' -f2)

# Setup webhook endpoint
log_info "========================================="
log_info "Setting up Webhook Endpoint"
log_info "========================================="

log_prompt "Enter your webhook URL (e.g., https://api.yourdomain.com/api/v1/billing/webhook/stripe): "
read -r WEBHOOK_URL

if [ ! -z "$WEBHOOK_URL" ]; then
    WEBHOOK_ENDPOINT=$(stripe webhook_endpoints create \
        --url="$WEBHOOK_URL" \
        --enabled-events="customer.subscription.created,customer.subscription.updated,customer.subscription.deleted,invoice.paid,invoice.payment_failed,payment_intent.succeeded,payment_method.attached,checkout.session.completed" \
        --json | jq -r '.id')
    
    WEBHOOK_SECRET=$(stripe webhook_endpoints retrieve "$WEBHOOK_ENDPOINT" --json | jq -r '.secret')
    
    log_info "Webhook endpoint created: $WEBHOOK_ENDPOINT"
    log_info "Webhook secret: $WEBHOOK_SECRET"
else
    log_info "Skipping webhook setup"
    WEBHOOK_SECRET="whsec_test_secret"
fi

# Setup billing portal
log_info "========================================="
log_info "Configuring Customer Portal"
log_info "========================================="

stripe billing_portal configurations create \
    --business-profile[headline]="Manage your UnSearch subscription" \
    --business-profile[privacy-policy-url]="https://yourdomain.com/privacy" \
    --business-profile[terms-of-service-url]="https://yourdomain.com/terms" \
    --features[customer-update][enabled]=true \
    --features[customer-update][allowed-updates]="email,tax_id" \
    --features[invoice-history][enabled]=true \
    --features[payment-method-update][enabled]=true \
    --features[subscription-cancel][enabled]=true \
    --features[subscription-cancel][mode]="at_period_end" \
    --features[subscription-pause][enabled]=false \
    --features[subscription-update][enabled]=true \
    --features[subscription-update][products]="$PRO_PRODUCT_ID,$ENTERPRISE_PRODUCT_ID" \
    --default-return-url="https://yourdomain.com/account"

log_info "Customer portal configured"

# Create test customer (optional)
if [ "$MODE" = "test" ]; then
    log_info "========================================="
    log_info "Creating Test Customer"
    log_info "========================================="
    
    TEST_CUSTOMER=$(stripe customers create \
        --email="test@example.com" \
        --name="Test User" \
        --json | jq -r '.id')
    
    log_info "Test customer created: $TEST_CUSTOMER"
    
    # Attach test payment method
    TEST_PM=$(stripe payment_methods attach "pm_card_visa" \
        --customer="$TEST_CUSTOMER" \
        --json | jq -r '.id')
    
    log_info "Test payment method attached"
    
    # Create test subscription
    TEST_SUB=$(stripe subscriptions create \
        --customer="$TEST_CUSTOMER" \
        --items[0][price]="$PRO_PRICE_ID" \
        --payment-behavior="default_incomplete" \
        --trial-period-days=7 \
        --json | jq -r '.id')
    
    log_info "Test subscription created: $TEST_SUB"
fi

# Generate .env configuration
log_info "========================================="
log_info "Generating Configuration"
log_info "========================================="

cat > .env.stripe << EOF
# Stripe Configuration
# Generated on $(date)

# Mode: $MODE

# API Keys (get from https://dashboard.stripe.com/apikeys)
STRIPE_SECRET_KEY=sk_${MODE}_...
STRIPE_PUBLISHABLE_KEY=pk_${MODE}_...

# Webhook Secret
STRIPE_WEBHOOK_SECRET=$WEBHOOK_SECRET

# Product IDs
STRIPE_PRODUCT_ID_PRO=$PRO_PRODUCT_ID
STRIPE_PRODUCT_ID_ENTERPRISE=$ENTERPRISE_PRODUCT_ID

# Price IDs
STRIPE_PRICE_ID_PRO=$PRO_PRICE_ID
STRIPE_PRICE_ID_ENTERPRISE=$ENTERPRISE_PRICE_ID

# Test Customer (if created)
STRIPE_TEST_CUSTOMER_ID=${TEST_CUSTOMER:-}
EOF

log_info "Configuration saved to .env.stripe"

# Instructions
log_info "========================================="
log_info "Setup Complete!"
log_info "========================================="
echo
log_info "Next steps:"
echo "1. Copy the Stripe keys from your dashboard: https://dashboard.stripe.com/apikeys"
echo "2. Add the following to your .env file:"
echo
cat .env.stripe
echo
echo "3. Test the webhook locally using:"
echo "   stripe listen --forward-to localhost:8000/api/v1/billing/webhook/stripe"
echo
echo "4. Create a test subscription:"
echo "   curl -X POST http://localhost:8000/api/v1/billing/subscription \\"
echo "     -H 'Authorization: Bearer YOUR_JWT_TOKEN' \\"
echo "     -d '{\"price_id\": \"$PRO_PRICE_ID\"}'"
echo
log_info "Documentation: https://stripe.com/docs"
