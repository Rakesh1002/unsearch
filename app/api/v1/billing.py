"""
Billing and subscription management endpoints.
"""
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Request, status, Header
from fastapi.responses import RedirectResponse
import structlog
import stripe

from app.models.requests import (
    CreateCheckoutSessionRequest, CreateSubscriptionRequest,
    UpdateSubscriptionRequest
)
from app.models.responses import (
    SubscriptionResponse, PlanResponse, InvoiceResponse,
    CheckoutSessionResponse, BillingPortalResponse
)
from app.services.auth_service import get_auth_service, AuthService
from app.services.stripe_service import get_stripe_service, StripeService
from app.services.database import get_database_service, DatabaseService
from app.models.users import User, Subscription, Plan, Invoice
from app.api.v1.auth import get_current_user
from app.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/plans", response_model=List[PlanResponse])
async def list_plans(
    db_service: DatabaseService = Depends(get_database_service)
):
    """List all available subscription plans."""
    plans = await db_service.get_active_plans()
    
    return [
        PlanResponse(
            id=plan.id,
            name=plan.name,
            display_name=plan.display_name,
            description=plan.description,
            price=plan.price,
            currency=plan.currency,
            interval=plan.interval,
            search_limit=plan.search_limit,
            scrape_limit=plan.scrape_limit,
            rate_limit=plan.rate_limit,
            features=plan.features
        )
        for plan in plans
    ]


@router.get("/subscription", response_model=Optional[SubscriptionResponse])
async def get_subscription(
    user: User = Depends(get_current_user),
    db_service: DatabaseService = Depends(get_database_service)
):
    """Get current user subscription."""
    subscription = user.current_subscription
    
    if not subscription:
        return None
    
    return SubscriptionResponse(
        id=subscription.id,
        plan_type=subscription.plan_type.value,
        status=subscription.status.value,
        amount=subscription.amount,
        currency=subscription.currency,
        interval=subscription.interval,
        search_limit=subscription.search_limit,
        scrape_limit=subscription.scrape_limit,
        rate_limit=subscription.rate_limit,
        features=subscription.features,
        current_period_start=subscription.current_period_start,
        current_period_end=subscription.current_period_end,
        trial_end=subscription.trial_end,
        cancelled_at=subscription.cancelled_at,
        is_active=subscription.is_active,
        days_remaining=subscription.days_remaining
    )


@router.post("/subscription", response_model=SubscriptionResponse)
async def create_subscription(
    request: CreateSubscriptionRequest,
    user: User = Depends(get_current_user),
    stripe_service: StripeService = Depends(get_stripe_service)
):
    """Create a new subscription."""
    # Check if user already has an active subscription
    if user.current_subscription and user.current_subscription.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has an active subscription"
        )
    
    try:
        subscription = await stripe_service.create_subscription(
            user=user,
            price_id=request.price_id,
            trial_days=request.trial_days or 0
        )
        
        return SubscriptionResponse(
            id=subscription.id,
            plan_type=subscription.plan_type.value,
            status=subscription.status.value,
            amount=subscription.amount,
            currency=subscription.currency,
            interval=subscription.interval,
            search_limit=subscription.search_limit,
            scrape_limit=subscription.scrape_limit,
            rate_limit=subscription.rate_limit,
            features=subscription.features,
            current_period_start=subscription.current_period_start,
            current_period_end=subscription.current_period_end,
            trial_end=subscription.trial_end,
            is_active=subscription.is_active
        )
        
    except stripe.error.StripeError as e:
        logger.error("subscription_creation_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Subscription creation failed: {str(e)}"
        )


@router.put("/subscription", response_model=SubscriptionResponse)
async def update_subscription(
    request: UpdateSubscriptionRequest,
    user: User = Depends(get_current_user),
    stripe_service: StripeService = Depends(get_stripe_service)
):
    """Update existing subscription to a different plan."""
    subscription = user.current_subscription
    
    if not subscription or not subscription.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )
    
    try:
        subscription = await stripe_service.update_subscription(
            subscription=subscription,
            new_price_id=request.price_id
        )
        
        return SubscriptionResponse(
            id=subscription.id,
            plan_type=subscription.plan_type.value,
            status=subscription.status.value,
            amount=subscription.amount,
            currency=subscription.currency,
            interval=subscription.interval,
            search_limit=subscription.search_limit,
            scrape_limit=subscription.scrape_limit,
            rate_limit=subscription.rate_limit,
            features=subscription.features,
            current_period_start=subscription.current_period_start,
            current_period_end=subscription.current_period_end,
            is_active=subscription.is_active
        )
        
    except stripe.error.StripeError as e:
        logger.error("subscription_update_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Subscription update failed: {str(e)}"
        )


@router.delete("/subscription")
async def cancel_subscription(
    immediately: bool = False,
    user: User = Depends(get_current_user),
    stripe_service: StripeService = Depends(get_stripe_service)
):
    """Cancel current subscription."""
    subscription = user.current_subscription
    
    if not subscription or not subscription.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )
    
    try:
        await stripe_service.cancel_subscription(
            subscription=subscription,
            immediately=immediately
        )
        
        return {
            "message": f"Subscription {'cancelled immediately' if immediately else 'will be cancelled at period end'}"
        }
        
    except stripe.error.StripeError as e:
        logger.error("subscription_cancellation_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Subscription cancellation failed: {str(e)}"
        )


@router.post("/checkout-session", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    request: CreateCheckoutSessionRequest,
    user: User = Depends(get_current_user),
    stripe_service: StripeService = Depends(get_stripe_service)
):
    """Create a Stripe Checkout session for subscription."""
    try:
        checkout_url = await stripe_service.create_checkout_session(
            user=user,
            price_id=request.price_id,
            success_url=request.success_url,
            cancel_url=request.cancel_url,
            trial_days=request.trial_days or 0
        )
        
        return CheckoutSessionResponse(
            checkout_url=checkout_url
        )
        
    except stripe.error.StripeError as e:
        logger.error("checkout_session_creation_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Checkout session creation failed: {str(e)}"
        )


@router.post("/billing-portal", response_model=BillingPortalResponse)
async def create_billing_portal_session(
    return_url: str,
    user: User = Depends(get_current_user),
    stripe_service: StripeService = Depends(get_stripe_service)
):
    """Create a Stripe Billing Portal session for subscription management."""
    try:
        portal_url = await stripe_service.create_billing_portal_session(
            user=user,
            return_url=return_url
        )
        
        return BillingPortalResponse(
            portal_url=portal_url
        )
        
    except Exception as e:
        logger.error("billing_portal_session_creation_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Billing portal session creation failed: {str(e)}"
        )


@router.get("/invoices", response_model=List[InvoiceResponse])
async def list_invoices(
    limit: int = 10,
    user: User = Depends(get_current_user),
    db_service: DatabaseService = Depends(get_database_service)
):
    """List user invoices."""
    invoices = await db_service.get_user_invoices(user.id, limit)
    
    return [
        InvoiceResponse(
            id=invoice.id,
            invoice_number=invoice.invoice_number,
            status=invoice.status,
            amount_due=invoice.amount_due / 100,  # Convert from cents
            amount_paid=invoice.amount_paid / 100 if invoice.amount_paid else 0,
            currency=invoice.currency,
            period_start=invoice.period_start,
            period_end=invoice.period_end,
            paid_at=invoice.paid_at,
            invoice_pdf=invoice.invoice_pdf,
            hosted_invoice_url=invoice.hosted_invoice_url,
            created_at=invoice.created_at
        )
        for invoice in invoices
    ]


@router.post("/webhook/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="Stripe-Signature"),
    stripe_service: StripeService = Depends(get_stripe_service)
):
    """Handle Stripe webhook events."""
    # Get the raw body
    body = await request.body()
    
    # Handle the webhook
    success = await stripe_service.handle_webhook(
        payload=body.decode('utf-8'),
        signature=stripe_signature
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook processing failed"
        )
    
    return {"received": True}


@router.get("/payment-methods")
async def list_payment_methods(
    user: User = Depends(get_current_user)
):
    """List user payment methods."""
    if not user.stripe_customer_id:
        return []
    
    try:
        payment_methods = stripe.PaymentMethod.list(
            customer=user.stripe_customer_id,
            type="card"
        )
        
        return [
            {
                "id": pm.id,
                "brand": pm.card.brand,
                "last4": pm.card.last4,
                "exp_month": pm.card.exp_month,
                "exp_year": pm.card.exp_year,
                "is_default": pm.id == user.stripe_payment_method_id
            }
            for pm in payment_methods.data
        ]
        
    except stripe.error.StripeError as e:
        logger.error("payment_methods_fetch_failed", error=str(e))
        return []


@router.post("/payment-methods")
async def add_payment_method(
    payment_method_id: str,
    set_as_default: bool = True,
    user: User = Depends(get_current_user),
    db_service: DatabaseService = Depends(get_database_service)
):
    """Add a payment method to user account."""
    if not user.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User has no Stripe customer account"
        )
    
    try:
        # Attach payment method to customer
        payment_method = stripe.PaymentMethod.attach(
            payment_method_id,
            customer=user.stripe_customer_id
        )
        
        # Set as default if requested
        if set_as_default:
            stripe.Customer.modify(
                user.stripe_customer_id,
                invoice_settings={"default_payment_method": payment_method_id}
            )
            user.stripe_payment_method_id = payment_method_id
            await db_service.update_user(user)
        
        return {
            "message": "Payment method added successfully",
            "payment_method": {
                "id": payment_method.id,
                "brand": payment_method.card.brand,
                "last4": payment_method.card.last4
            }
        }
        
    except stripe.error.StripeError as e:
        logger.error("payment_method_add_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to add payment method: {str(e)}"
        )


@router.delete("/payment-methods/{payment_method_id}")
async def remove_payment_method(
    payment_method_id: str,
    user: User = Depends(get_current_user)
):
    """Remove a payment method."""
    try:
        stripe.PaymentMethod.detach(payment_method_id)
        
        return {"message": "Payment method removed successfully"}
        
    except stripe.error.StripeError as e:
        logger.error("payment_method_removal_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to remove payment method: {str(e)}"
        )
