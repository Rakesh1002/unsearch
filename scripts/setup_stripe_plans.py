#!/usr/bin/env python3
"""
Setup Stripe products and prices for UnSearch pricing tiers.

Usage:
    python scripts/setup_stripe_plans.py

Requires:
    - STRIPE_SECRET_KEY environment variable set
    - stripe package installed (pip install stripe)

This script creates:
    - Pro plan: $19/mo, $190/yr (17% off)
    - Growth plan: $49/mo, $490/yr (17% off)  
    - Scale plan: $149/mo, $1490/yr (17% off)

After running, update your .env with the generated price IDs.
"""

import os
import sys

try:
    import stripe
except ImportError:
    print("Error: stripe package not installed. Run: pip install stripe")
    sys.exit(1)

# Get API key from environment
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")

if not stripe.api_key:
    print("Error: STRIPE_SECRET_KEY environment variable not set")
    print("Set it with: export STRIPE_SECRET_KEY=sk_test_...")
    sys.exit(1)

# Pricing tiers configuration
PLANS = [
    {
        "name": "pro",
        "display_name": "UnSearch Pro",
        "description": "For serious AI applications - 25,000 queries/month",
        "monthly_price": 1900,  # $19 in cents
        "yearly_price": 19000,  # $190 in cents (10 months = 17% off)
        "metadata": {
            "queries": "25000",
            "scrapes": "5000",
            "rate_limit": "60/minute"
        }
    },
    {
        "name": "growth",
        "display_name": "UnSearch Growth",
        "description": "For scaling teams - 100,000 queries/month",
        "monthly_price": 4900,  # $49 in cents
        "yearly_price": 49000,  # $490 in cents
        "metadata": {
            "queries": "100000",
            "scrapes": "25000",
            "rate_limit": "200/minute"
        }
    },
    {
        "name": "scale",
        "display_name": "UnSearch Scale",
        "description": "For high-volume AI apps - 500,000 queries/month",
        "monthly_price": 14900,  # $149 in cents
        "yearly_price": 149000,  # $1490 in cents
        "metadata": {
            "queries": "500000",
            "scrapes": "100000",
            "rate_limit": "1000/minute"
        }
    }
]


def create_products_and_prices():
    """Create Stripe products and prices for all plans."""
    results = {}
    
    print("=" * 60)
    print("Creating Stripe Products and Prices for UnSearch")
    print("=" * 60)
    print()
    
    for plan in PLANS:
        print(f"Creating {plan['display_name']}...")
        
        # Create product
        product = stripe.Product.create(
            name=plan["display_name"],
            description=plan["description"],
            metadata={
                "plan_name": plan["name"],
                **plan["metadata"]
            }
        )
        print(f"  Product ID: {product.id}")
        
        # Create monthly price
        monthly_price = stripe.Price.create(
            product=product.id,
            unit_amount=plan["monthly_price"],
            currency="usd",
            recurring={"interval": "month"},
            metadata={"billing_period": "monthly"}
        )
        print(f"  Monthly Price ID: {monthly_price.id} (${plan['monthly_price']/100}/mo)")
        
        # Create yearly price
        yearly_price = stripe.Price.create(
            product=product.id,
            unit_amount=plan["yearly_price"],
            currency="usd",
            recurring={"interval": "year"},
            metadata={"billing_period": "yearly"}
        )
        print(f"  Yearly Price ID: {yearly_price.id} (${plan['yearly_price']/100}/yr)")
        
        results[plan["name"]] = {
            "product_id": product.id,
            "monthly_price_id": monthly_price.id,
            "yearly_price_id": yearly_price.id
        }
        print()
    
    return results


def print_env_config(results):
    """Print environment variable configuration."""
    print("=" * 60)
    print("Add these to your .env file:")
    print("=" * 60)
    print()
    print("# Stripe Price IDs (generated)")
    for plan_name, ids in results.items():
        print(f"# {plan_name.upper()} Plan")
        print(f"STRIPE_{plan_name.upper()}_PRODUCT_ID={ids['product_id']}")
        print(f"STRIPE_{plan_name.upper()}_MONTHLY_PRICE_ID={ids['monthly_price_id']}")
        print(f"STRIPE_{plan_name.upper()}_YEARLY_PRICE_ID={ids['yearly_price_id']}")
        print()


def print_sql_update(results):
    """Print SQL to update plans table with Stripe IDs."""
    print("=" * 60)
    print("SQL to update plans table (run after migration):")
    print("=" * 60)
    print()
    for plan_name, ids in results.items():
        print(f"""UPDATE plans SET 
    stripe_product_id = '{ids['product_id']}',
    stripe_price_id = '{ids['monthly_price_id']}',
    stripe_price_id_yearly = '{ids['yearly_price_id']}'
WHERE name = '{plan_name}';
""")


def main():
    try:
        # Verify connection
        print("Verifying Stripe API connection...")
        account = stripe.Account.retrieve()
        print(f"Connected to Stripe account: {account.get('business_profile', {}).get('name', account.id)}")
        print(f"Mode: {'TEST' if 'test' in stripe.api_key else 'LIVE'}")
        print()
        
        # Check for existing products
        existing = stripe.Product.list(limit=100)
        unsearch_products = [p for p in existing.data if p.name.startswith("UnSearch")]
        
        if unsearch_products:
            print("Warning: Found existing UnSearch products:")
            for p in unsearch_products:
                print(f"  - {p.name} ({p.id})")
            print()
            response = input("Continue and create new products? (y/N): ")
            if response.lower() != 'y':
                print("Aborted.")
                return
        
        # Create products and prices
        results = create_products_and_prices()
        
        # Print configuration
        print_env_config(results)
        print_sql_update(results)
        
        print("=" * 60)
        print("Setup complete!")
        print("=" * 60)
        
    except stripe.error.AuthenticationError:
        print("Error: Invalid Stripe API key")
        sys.exit(1)
    except stripe.error.StripeError as e:
        print(f"Stripe Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
