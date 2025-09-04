"""
Stripe payment and subscription service.
"""
import stripe
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import structlog

from app.config import get_settings
from app.models.users import (
    User, Subscription, Plan, Invoice, WebhookEvent,
    PlanType, SubscriptionStatus
)
from app.services.database import DatabaseService

logger = structlog.get_logger(__name__)
settings = get_settings()

# Configure Stripe
stripe.api_key = settings.stripe_secret_key


class StripeService:
    """Service for managing Stripe payments and subscriptions."""
    
    def __init__(self, db_service: DatabaseService):
        self.db = db_service
        self.webhook_secret = settings.stripe_webhook_secret
        
    async def create_customer(self, user: User) -> str:
        """Create a Stripe customer for a user."""
        try:
            customer = stripe.Customer.create(
                email=user.email,
                name=user.full_name,
                metadata={
                    "user_id": str(user.id),
                    "username": user.username or ""
                }
            )
            
            # Update user with Stripe customer ID
            user.stripe_customer_id = customer.id
            await self.db.update_user(user)
            
            logger.info("stripe_customer_created", 
                       user_id=user.id, 
                       customer_id=customer.id)
            
            return customer.id
            
        except stripe.error.StripeError as e:
            logger.error("stripe_customer_creation_failed", 
                        user_id=user.id, 
                        error=str(e))
            raise
    
    async def create_subscription(
        self, 
        user: User, 
        price_id: str,
        trial_days: int = 0
    ) -> Subscription:
        """Create a subscription for a user."""
        # Ensure customer exists
        if not user.stripe_customer_id:
            await self.create_customer(user)
        
        try:
            # Create Stripe subscription
            stripe_sub = stripe.Subscription.create(
                customer=user.stripe_customer_id,
                items=[{"price": price_id}],
                trial_period_days=trial_days,
                payment_behavior="default_incomplete",
                expand=["latest_invoice.payment_intent"],
                metadata={
                    "user_id": str(user.id)
                }
            )
            
            # Get plan details
            plan = await self.db.get_plan_by_price_id(price_id)
            
            # Create local subscription record
            subscription = Subscription(
                user_id=user.id,
                stripe_subscription_id=stripe_sub.id,
                stripe_price_id=price_id,
                stripe_product_id=stripe_sub.items.data[0].price.product,
                plan_type=self._get_plan_type(plan),
                status=self._map_subscription_status(stripe_sub.status),
                amount=stripe_sub.items.data[0].price.unit_amount / 100,
                currency=stripe_sub.currency,
                interval=stripe_sub.items.data[0].price.recurring.interval,
                search_limit=plan.search_limit if plan else 1000,
                scrape_limit=plan.scrape_limit if plan else 10000,
                rate_limit=plan.rate_limit if plan else "100/hour",
                features=plan.features if plan else {},
                trial_start=datetime.fromtimestamp(stripe_sub.trial_start) if stripe_sub.trial_start else None,
                trial_end=datetime.fromtimestamp(stripe_sub.trial_end) if stripe_sub.trial_end else None,
                current_period_start=datetime.fromtimestamp(stripe_sub.current_period_start),
                current_period_end=datetime.fromtimestamp(stripe_sub.current_period_end)
            )
            
            await self.db.create_subscription(subscription)
            
            logger.info("subscription_created",
                       user_id=user.id,
                       subscription_id=stripe_sub.id,
                       plan=plan.name if plan else "unknown")
            
            return subscription
            
        except stripe.error.StripeError as e:
            logger.error("subscription_creation_failed",
                        user_id=user.id,
                        error=str(e))
            raise
    
    async def cancel_subscription(self, subscription: Subscription, immediately: bool = False) -> Subscription:
        """Cancel a subscription."""
        try:
            if immediately:
                # Cancel immediately
                stripe_sub = stripe.Subscription.delete(subscription.stripe_subscription_id)
            else:
                # Cancel at period end
                stripe_sub = stripe.Subscription.modify(
                    subscription.stripe_subscription_id,
                    cancel_at_period_end=True
                )
            
            # Update local subscription
            subscription.status = SubscriptionStatus.CANCELLED
            subscription.cancelled_at = datetime.utcnow()
            if immediately:
                subscription.ended_at = datetime.utcnow()
            
            await self.db.update_subscription(subscription)
            
            logger.info("subscription_cancelled",
                       subscription_id=subscription.id,
                       immediately=immediately)
            
            return subscription
            
        except stripe.error.StripeError as e:
            logger.error("subscription_cancellation_failed",
                        subscription_id=subscription.id,
                        error=str(e))
            raise
    
    async def update_subscription(self, subscription: Subscription, new_price_id: str) -> Subscription:
        """Update subscription to a different plan."""
        try:
            # Get the subscription item ID
            stripe_sub = stripe.Subscription.retrieve(subscription.stripe_subscription_id)
            item_id = stripe_sub.items.data[0].id
            
            # Update the subscription
            stripe_sub = stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                items=[{
                    "id": item_id,
                    "price": new_price_id
                }],
                proration_behavior="create_prorations"
            )
            
            # Get new plan details
            plan = await self.db.get_plan_by_price_id(new_price_id)
            
            # Update local subscription
            subscription.stripe_price_id = new_price_id
            subscription.plan_type = self._get_plan_type(plan)
            subscription.amount = stripe_sub.items.data[0].price.unit_amount / 100
            subscription.search_limit = plan.search_limit if plan else None
            subscription.scrape_limit = plan.scrape_limit if plan else None
            subscription.rate_limit = plan.rate_limit if plan else "1000/hour"
            subscription.features = plan.features if plan else {}
            
            await self.db.update_subscription(subscription)
            
            logger.info("subscription_updated",
                       subscription_id=subscription.id,
                       new_plan=plan.name if plan else "unknown")
            
            return subscription
            
        except stripe.error.StripeError as e:
            logger.error("subscription_update_failed",
                        subscription_id=subscription.id,
                        error=str(e))
            raise
    
    async def create_payment_intent(
        self,
        user: User,
        amount: int,
        currency: str = "usd",
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a payment intent for one-time payment."""
        if not user.stripe_customer_id:
            await self.create_customer(user)
        
        try:
            intent = stripe.PaymentIntent.create(
                amount=amount,  # Amount in cents
                currency=currency,
                customer=user.stripe_customer_id,
                description=description,
                metadata={
                    "user_id": str(user.id)
                }
            )
            
            return {
                "client_secret": intent.client_secret,
                "payment_intent_id": intent.id
            }
            
        except stripe.error.StripeError as e:
            logger.error("payment_intent_creation_failed",
                        user_id=user.id,
                        error=str(e))
            raise
    
    async def create_checkout_session(
        self,
        user: User,
        price_id: str,
        success_url: str,
        cancel_url: str,
        trial_days: int = 0
    ) -> str:
        """Create a Stripe Checkout session."""
        if not user.stripe_customer_id:
            await self.create_customer(user)
        
        try:
            session = stripe.checkout.Session.create(
                customer=user.stripe_customer_id,
                payment_method_types=["card"],
                line_items=[{
                    "price": price_id,
                    "quantity": 1
                }],
                mode="subscription",
                success_url=success_url,
                cancel_url=cancel_url,
                subscription_data={
                    "trial_period_days": trial_days,
                    "metadata": {
                        "user_id": str(user.id)
                    }
                }
            )
            
            logger.info("checkout_session_created",
                       user_id=user.id,
                       session_id=session.id)
            
            return session.url
            
        except stripe.error.StripeError as e:
            logger.error("checkout_session_creation_failed",
                        user_id=user.id,
                        error=str(e))
            raise
    
    async def create_billing_portal_session(self, user: User, return_url: str) -> str:
        """Create a billing portal session for subscription management."""
        if not user.stripe_customer_id:
            raise ValueError("User has no Stripe customer ID")
        
        try:
            session = stripe.billing_portal.Session.create(
                customer=user.stripe_customer_id,
                return_url=return_url
            )
            
            return session.url
            
        except stripe.error.StripeError as e:
            logger.error("billing_portal_session_creation_failed",
                        user_id=user.id,
                        error=str(e))
            raise
    
    async def handle_webhook(self, payload: str, signature: str) -> bool:
        """Handle Stripe webhook events."""
        try:
            # Verify webhook signature
            event = stripe.Webhook.construct_event(
                payload, signature, self.webhook_secret
            )
            
            # Check if we've already processed this event
            existing = await self.db.get_webhook_event(event.id)
            if existing and existing.processed:
                logger.info("webhook_already_processed", event_id=event.id)
                return True
            
            # Store webhook event
            webhook_event = await self.db.create_webhook_event(
                stripe_event_id=event.id,
                event_type=event.type,
                data=event.data.object
            )
            
            # Process event based on type
            if event.type == "customer.subscription.created":
                await self._handle_subscription_created(event.data.object)
            elif event.type == "customer.subscription.updated":
                await self._handle_subscription_updated(event.data.object)
            elif event.type == "customer.subscription.deleted":
                await self._handle_subscription_deleted(event.data.object)
            elif event.type == "invoice.paid":
                await self._handle_invoice_paid(event.data.object)
            elif event.type == "invoice.payment_failed":
                await self._handle_invoice_payment_failed(event.data.object)
            elif event.type == "payment_intent.succeeded":
                await self._handle_payment_succeeded(event.data.object)
            
            # Mark webhook as processed
            webhook_event.processed = True
            webhook_event.processed_at = datetime.utcnow()
            await self.db.update_webhook_event(webhook_event)
            
            logger.info("webhook_processed",
                       event_id=event.id,
                       event_type=event.type)
            
            return True
            
        except stripe.error.SignatureVerificationError:
            logger.error("webhook_signature_verification_failed")
            return False
        except Exception as e:
            logger.error("webhook_processing_failed", error=str(e))
            return False
    
    async def _handle_subscription_created(self, stripe_sub):
        """Handle subscription created event."""
        user = await self.db.get_user_by_stripe_customer(stripe_sub.customer)
        if not user:
            logger.error("user_not_found_for_subscription", customer_id=stripe_sub.customer)
            return
        
        # Check if subscription already exists
        subscription = await self.db.get_subscription_by_stripe_id(stripe_sub.id)
        if subscription:
            return
        
        # Get plan details
        price_id = stripe_sub.items.data[0].price.id
        plan = await self.db.get_plan_by_price_id(price_id)
        
        # Create subscription record
        subscription = Subscription(
            user_id=user.id,
            stripe_subscription_id=stripe_sub.id,
            stripe_price_id=price_id,
            stripe_product_id=stripe_sub.items.data[0].price.product,
            plan_type=self._get_plan_type(plan),
            status=self._map_subscription_status(stripe_sub.status),
            amount=stripe_sub.items.data[0].price.unit_amount / 100,
            currency=stripe_sub.currency,
            interval=stripe_sub.items.data[0].price.recurring.interval,
            search_limit=plan.search_limit if plan else 1000,
            scrape_limit=plan.scrape_limit if plan else 10000,
            rate_limit=plan.rate_limit if plan else "100/hour",
            features=plan.features if plan else {},
            trial_start=datetime.fromtimestamp(stripe_sub.trial_start) if stripe_sub.trial_start else None,
            trial_end=datetime.fromtimestamp(stripe_sub.trial_end) if stripe_sub.trial_end else None,
            current_period_start=datetime.fromtimestamp(stripe_sub.current_period_start),
            current_period_end=datetime.fromtimestamp(stripe_sub.current_period_end)
        )
        
        await self.db.create_subscription(subscription)
        
    async def _handle_subscription_updated(self, stripe_sub):
        """Handle subscription updated event."""
        subscription = await self.db.get_subscription_by_stripe_id(stripe_sub.id)
        if not subscription:
            logger.error("subscription_not_found", stripe_id=stripe_sub.id)
            return
        
        # Update subscription details
        subscription.status = self._map_subscription_status(stripe_sub.status)
        subscription.current_period_start = datetime.fromtimestamp(stripe_sub.current_period_start)
        subscription.current_period_end = datetime.fromtimestamp(stripe_sub.current_period_end)
        
        if stripe_sub.cancel_at_period_end:
            subscription.status = SubscriptionStatus.CANCELLED
        
        await self.db.update_subscription(subscription)
    
    async def _handle_subscription_deleted(self, stripe_sub):
        """Handle subscription deleted event."""
        subscription = await self.db.get_subscription_by_stripe_id(stripe_sub.id)
        if not subscription:
            return
        
        subscription.status = SubscriptionStatus.CANCELLED
        subscription.ended_at = datetime.utcnow()
        await self.db.update_subscription(subscription)
    
    async def _handle_invoice_paid(self, invoice):
        """Handle invoice paid event."""
        user = await self.db.get_user_by_stripe_customer(invoice.customer)
        if not user:
            return
        
        # Create or update invoice record
        inv = await self.db.get_invoice_by_stripe_id(invoice.id)
        if not inv:
            inv = Invoice(
                user_id=user.id,
                stripe_invoice_id=invoice.id,
                stripe_charge_id=invoice.charge,
                invoice_number=invoice.number,
                status="paid",
                amount_due=invoice.amount_due,
                amount_paid=invoice.amount_paid,
                amount_remaining=invoice.amount_remaining,
                subtotal=invoice.subtotal,
                tax=invoice.tax,
                total=invoice.total,
                currency=invoice.currency,
                period_start=datetime.fromtimestamp(invoice.period_start) if invoice.period_start else None,
                period_end=datetime.fromtimestamp(invoice.period_end) if invoice.period_end else None,
                paid_at=datetime.fromtimestamp(invoice.status_transitions.paid_at) if invoice.status_transitions.paid_at else None,
                invoice_pdf=invoice.invoice_pdf,
                hosted_invoice_url=invoice.hosted_invoice_url
            )
            await self.db.create_invoice(inv)
        else:
            inv.status = "paid"
            inv.paid_at = datetime.fromtimestamp(invoice.status_transitions.paid_at) if invoice.status_transitions.paid_at else None
            await self.db.update_invoice(inv)
        
        # Reset usage for new billing period
        await self.db.reset_user_usage(user.id)
    
    async def _handle_invoice_payment_failed(self, invoice):
        """Handle invoice payment failed event."""
        subscription = await self.db.get_subscription_by_stripe_customer(invoice.customer)
        if subscription:
            subscription.status = SubscriptionStatus.PAST_DUE
            await self.db.update_subscription(subscription)
    
    async def _handle_payment_succeeded(self, payment_intent):
        """Handle payment intent succeeded event."""
        logger.info("payment_succeeded",
                   payment_intent_id=payment_intent.id,
                   amount=payment_intent.amount)
    
    def _map_subscription_status(self, stripe_status: str) -> SubscriptionStatus:
        """Map Stripe subscription status to our enum."""
        mapping = {
            "active": SubscriptionStatus.ACTIVE,
            "trialing": SubscriptionStatus.TRIALING,
            "canceled": SubscriptionStatus.CANCELLED,
            "past_due": SubscriptionStatus.PAST_DUE,
            "unpaid": SubscriptionStatus.UNPAID,
            "incomplete": SubscriptionStatus.INCOMPLETE
        }
        return mapping.get(stripe_status, SubscriptionStatus.CANCELLED)
    
    def _get_plan_type(self, plan: Optional[Plan]) -> PlanType:
        """Get plan type from plan object."""
        if not plan:
            return PlanType.FREE
        
        if "pro" in plan.name.lower():
            return PlanType.PRO
        elif "enterprise" in plan.name.lower():
            return PlanType.ENTERPRISE
        else:
            return PlanType.FREE
    
    async def setup_default_plans(self):
        """Set up default pricing plans in Stripe and database."""
        plans_config = [
            {
                "name": "free",
                "display_name": "Free Plan",
                "description": "Perfect for getting started",
                "price": 0,
                "search_limit": 1000,
                "scrape_limit": 10000,
                "rate_limit": "100/hour",
                "features": {
                    "api_access": True,
                    "webhook_support": False,
                    "priority_support": False
                }
            },
            {
                "name": "pro",
                "display_name": "Pro Plan",
                "description": "Unlimited searches and scrapes",
                "price": 20.00,
                "search_limit": None,  # Unlimited
                "scrape_limit": None,  # Unlimited
                "rate_limit": "1000/hour",
                "features": {
                    "api_access": True,
                    "webhook_support": True,
                    "priority_support": True,
                    "custom_engines": True
                }
            }
        ]
        
        for plan_config in plans_config:
            # Check if plan exists
            existing = await self.db.get_plan_by_name(plan_config["name"])
            if existing:
                continue
            
            # Create Stripe product and price if not free
            if plan_config["price"] > 0:
                product = stripe.Product.create(
                    name=plan_config["display_name"],
                    description=plan_config["description"],
                    metadata={
                        "plan_name": plan_config["name"]
                    }
                )
                
                price = stripe.Price.create(
                    product=product.id,
                    unit_amount=int(plan_config["price"] * 100),  # Convert to cents
                    currency="usd",
                    recurring={"interval": "month"}
                )
                
                stripe_product_id = product.id
                stripe_price_id = price.id
            else:
                stripe_product_id = None
                stripe_price_id = None
            
            # Create plan in database
            plan = Plan(
                name=plan_config["name"],
                display_name=plan_config["display_name"],
                description=plan_config["description"],
                stripe_product_id=stripe_product_id,
                stripe_price_id=stripe_price_id,
                price=plan_config["price"],
                currency="usd",
                interval="month",
                search_limit=plan_config["search_limit"],
                scrape_limit=plan_config["scrape_limit"],
                rate_limit=plan_config["rate_limit"],
                features=plan_config["features"],
                is_active=True,
                is_visible=True
            )
            
            await self.db.create_plan(plan)
            
            logger.info("plan_created",
                       name=plan_config["name"],
                       price=plan_config["price"])


# Singleton instance
_stripe_service: Optional[StripeService] = None


async def get_stripe_service(db_service: DatabaseService) -> StripeService:
    """Get or create Stripe service instance."""
    global _stripe_service
    
    if _stripe_service is None:
        _stripe_service = StripeService(db_service)
        # Set up default plans if needed
        await _stripe_service.setup_default_plans()
    
    return _stripe_service
