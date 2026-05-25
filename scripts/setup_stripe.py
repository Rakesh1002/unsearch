#!/usr/bin/env python3
"""
Setup Stripe products and prices for UnSearch

This script creates the necessary Stripe products and prices for UnSearch.
Run with: python scripts/setup_stripe.py

Requirements: pip install stripe python-dotenv
"""

import os
import sys
from dotenv import load_dotenv

try:
    import stripe
except ImportError:
    print("Error: stripe package not installed")
    print("Install with: pip install stripe")
    sys.exit(1)

# Load environment variables
load_dotenv()

# Get Stripe API key
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
if not stripe.api_key:
    print("Error: STRIPE_SECRET_KEY not set in environment")
    print("Set it with: export STRIPE_SECRET_KEY=sk_test_...")
    sys.exit(1)

# Product configurations with uns_ prefix in metadata
PRODUCTS = [
    {
        'name': 'UnSearch Pro',
        'description': '10,000 queries per month with RAG capabilities',
        'metadata': {
            'plan_id': 'uns_pro',
            'plan_type': 'pro',
            'queries_limit': '10000',
            'rate_limit': '100',
            'features': 'rag,search,extract,webhooks'
        },
        'price': {
            'unit_amount': 2900,  # $29.00
            'currency': 'usd',
            'recurring': {'interval': 'month'},
            'lookup_key': 'uns_pro_monthly'
        }
    },
    {
        'name': 'UnSearch Growth',
        'description': '100,000 queries per month with advanced features including neural search',
        'metadata': {
            'plan_id': 'uns_growth',
            'plan_type': 'growth',
            'queries_limit': '100000',
            'rate_limit': '1000',
            'features': 'rag,search,extract,webhooks,neural_search,knowledge_graph'
        },
        'price': {
            'unit_amount': 9900,  # $99.00
            'currency': 'usd',
            'recurring': {'interval': 'month'},
            'lookup_key': 'uns_growth_monthly'
        }
    },
    {
        'name': 'UnSearch Scale',
        'description': '1,000,000 queries per month with enterprise features',
        'metadata': {
            'plan_id': 'uns_scale',
            'plan_type': 'scale',
            'queries_limit': '1000000',
            'rate_limit': '10000',
            'features': 'rag,search,extract,webhooks,neural_search,knowledge_graph,monitoring,verification,priority_support'
        },
        'price': {
            'unit_amount': 29900,  # $299.00
            'currency': 'usd',
            'recurring': {'interval': 'month'},
            'lookup_key': 'uns_scale_monthly'
        }
    }
]

def create_products_and_prices():
    """Create Stripe products and prices"""
    created = []

    print("Creating Stripe products and prices for UnSearch...")
    print(f"Using Stripe API key: {stripe.api_key[:12]}...")
    print()

    for product_config in PRODUCTS:
        try:
            # Create product
            print(f"Creating product: {product_config['name']}")
            product = stripe.Product.create(
                name=product_config['name'],
                description=product_config['description'],
                metadata=product_config['metadata']
            )
            print(f"  ✓ Product created: {product.id}")

            # Create price
            price_config = product_config['price']
            price = stripe.Price.create(
                product=product.id,
                **price_config
            )
            print(f"  ✓ Price created: {price.id}")
            print(f"  ✓ Lookup key: {price_config['lookup_key']}")
            print()

            created.append({
                'product_name': product_config['name'],
                'product_id': product.id,
                'price_id': price.id,
                'lookup_key': price_config['lookup_key'],
                'plan_id': product_config['metadata']['plan_id']
            })

        except stripe.error.StripeError as e:
            print(f"  ✗ Error creating {product_config['name']}: {e}")
            continue

    return created

def print_env_variables(created):
    """Print environment variables to add"""
    print("\n" + "="*60)
    print("SUCCESS! Add these to your .env file:")
    print("="*60)
    print()

    for item in created:
        env_var_name = f"STRIPE_{item['plan_id'].upper()}_PRICE_ID"
        print(f"{env_var_name}={item['price_id']}")

    print()
    print("Or use lookup keys in your code:")
    for item in created:
        print(f"  {item['lookup_key']} -> {item['price_id']}")

    print()
    print("="*60)
    print("Next steps:")
    print("="*60)
    print("1. Add the price IDs to your .env file")
    print("2. Set up webhook endpoint:")
    print("   URL: https://api.unsearch.dev/api/v1/billing/webhook/stripe")
    print("   Events: customer.subscription.*, invoice.*, payment_intent.*")
    print("3. Get webhook secret and add to .env as STRIPE_WEBHOOK_SECRET")
    print("4. Test the integration with: stripe trigger customer.subscription.created")
    print()

def main():
    """Main function"""
    print("UnSearch Stripe Setup")
    print("=" * 60)

    # Confirm before creating
    response = input("This will create products in Stripe. Continue? (y/n): ")
    if response.lower() != 'y':
        print("Aborted.")
        return

    # Create products and prices
    created = create_products_and_prices()

    if created:
        print_env_variables(created)
    else:
        print("No products were created.")
        sys.exit(1)

if __name__ == '__main__':
    main()
