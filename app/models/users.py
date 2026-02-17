"""
User, subscription, and billing models for the UnSearch API.
"""
from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, JSON, Text, Index, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timedelta
import enum
import uuid

Base = declarative_base()


class PlanType(enum.Enum):
    """Subscription plan types matching pricing tiers."""
    FREE = "free"
    PRO = "pro"
    GROWTH = "growth"
    SCALE = "scale"
    ENTERPRISE = "enterprise"  # Legacy/custom plans


class SubscriptionStatus(enum.Enum):
    """Subscription status."""
    ACTIVE = "active"
    TRIALING = "trialing"
    CANCELLED = "cancelled"
    PAST_DUE = "past_due"
    UNPAID = "unpaid"
    INCOMPLETE = "incomplete"


class User(Base):
    """User account model."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    uuid = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=True, index=True)
    password_hash = Column(String(255), nullable=False)
    salt = Column(String(32), nullable=False)
    
    # Profile
    full_name = Column(String(255))
    company = Column(String(255))
    phone = Column(String(20))
    timezone = Column(String(50), default="UTC")
    
    # Authentication
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    email_verified_at = Column(DateTime(timezone=True))
    verification_token = Column(String(255))
    reset_token = Column(String(255))
    reset_token_expires = Column(DateTime(timezone=True))
    
    # Stripe
    stripe_customer_id = Column(String(255), unique=True, index=True)
    stripe_payment_method_id = Column(String(255))
    
    # Agent placeholder fields (for AI agent self-registration)
    is_agent_placeholder = Column(Boolean, default=False)  # True until human claims
    agent_name = Column(String(100), unique=True, nullable=True, index=True)  # Agent identifier (reserved even after expiry)
    agent_description = Column(Text, nullable=True)  # Agent description
    claim_code = Column(String(64), unique=True, nullable=True, index=True)  # For human verification
    claimed_at = Column(DateTime(timezone=True))  # When human claimed
    
    # Sandbox limits (only used for unclaimed agents)
    daily_searches_used = Column(Integer, default=0)
    daily_reset_at = Column(DateTime(timezone=True))
    sandbox_expires_at = Column(DateTime(timezone=True))  # 7 days from registration
    is_sandbox_expired = Column(Boolean, default=False)  # True after 7 days without claim
    registration_ip = Column(String(45), nullable=True)  # IP address used for registration (for rate limiting)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login_at = Column(DateTime(timezone=True))
    
    # Relationships
    api_keys = relationship("UserAPIKey", back_populates="user", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")
    usage_records = relationship("UsageRecord", back_populates="user", cascade="all, delete-orphan")
    invoices = relationship("Invoice", back_populates="user", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_users_active", "is_active"),
        Index("idx_users_stripe", "stripe_customer_id"),
        Index("idx_users_agent_placeholder", "is_agent_placeholder"),
        Index("idx_users_claim_code", "claim_code"),
    )
    
    @property
    def current_subscription(self):
        """Get the current active subscription."""
        return next(
            (sub for sub in self.subscriptions if sub.status == SubscriptionStatus.ACTIVE),
            None
        )
    
    @property
    def current_plan(self):
        """Get the current plan type."""
        sub = self.current_subscription
        return sub.plan_type if sub else PlanType.FREE


class UserAPIKey(Base):
    """User-specific API keys."""
    __tablename__ = "user_api_keys"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    key = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Permissions
    scopes = Column(JSON, default=["read", "write"])  # API scopes/permissions
    ip_whitelist = Column(JSON)  # Optional IP restrictions
    
    # Usage
    last_used_at = Column(DateTime(timezone=True))
    request_count = Column(Integer, default=0)
    
    # Status
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="api_keys")
    
    __table_args__ = (
        Index("idx_user_api_keys_active", "is_active"),
        Index("idx_user_api_keys_user", "user_id"),
    )


class Subscription(Base):
    """User subscription model."""
    __tablename__ = "subscriptions"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Stripe
    stripe_subscription_id = Column(String(255), unique=True, index=True)
    stripe_price_id = Column(String(255))
    stripe_product_id = Column(String(255))
    
    # Plan details
    plan_type = Column(Enum(PlanType), nullable=False, default=PlanType.FREE)
    status = Column(Enum(SubscriptionStatus), nullable=False, default=SubscriptionStatus.ACTIVE)
    
    # Billing
    amount = Column(Float, default=0.0)  # Monthly amount in USD
    currency = Column(String(3), default="usd")
    interval = Column(String(20), default="month")  # month, year
    
    # Limits (cached from plan)
    # Consistent with frontend pricing page: 5,000 free queries/month
    search_limit = Column(Integer, default=5000)  # Monthly search limit
    scrape_limit = Column(Integer, default=500)  # Monthly scrape limit (matches frontend)
    rate_limit = Column(String(50), default="10/minute")  # Rate limit (matches frontend: 10 req/min)
    
    # Features
    features = Column(JSON, default={
        "api_access": True,
        "webhook_support": False,
        "priority_support": False,
        "custom_engines": False,
        "dedicated_pool": False,
        "sla": False
    })
    
    # Dates
    trial_start = Column(DateTime(timezone=True))
    trial_end = Column(DateTime(timezone=True))
    current_period_start = Column(DateTime(timezone=True))
    current_period_end = Column(DateTime(timezone=True))
    cancelled_at = Column(DateTime(timezone=True))
    ended_at = Column(DateTime(timezone=True))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="subscriptions")
    
    __table_args__ = (
        Index("idx_subscriptions_user", "user_id"),
        Index("idx_subscriptions_status", "status"),
        Index("idx_subscriptions_stripe", "stripe_subscription_id"),
    )
    
    @property
    def is_active(self):
        """Check if subscription is currently active."""
        return self.status in [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING]
    
    @property
    def plan_name(self):
        """Get the plan name as a string."""
        return self.plan_type.value if self.plan_type else "free"
    
    @property
    def days_remaining(self):
        """Days remaining in current period."""
        if self.current_period_end:
            delta = self.current_period_end - datetime.utcnow()
            return max(0, delta.days)
        return 0


class UsageRecord(Base):
    """Track API usage per user."""
    __tablename__ = "usage_records"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Period
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    
    # Counts
    search_count = Column(Integer, default=0)
    scrape_count = Column(Integer, default=0)
    api_calls = Column(Integer, default=0)
    
    # Detailed usage
    usage_by_engine = Column(JSON, default={})  # {"google": 100, "bing": 50}
    usage_by_day = Column(JSON, default={})  # {"2024-01-01": 50, "2024-01-02": 75}
    
    # Overages
    search_overage = Column(Integer, default=0)
    scrape_overage = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="usage_records")
    
    __table_args__ = (
        Index("idx_usage_records_user", "user_id"),
        Index("idx_usage_records_period", "period_start", "period_end"),
        Index("idx_usage_user_period", "user_id", "period_start", "period_end", unique=True),
    )


class Plan(Base):
    """Subscription plans configuration."""
    __tablename__ = "plans"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    display_name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Stripe
    stripe_product_id = Column(String(255), unique=True)
    stripe_price_id = Column(String(255), unique=True)  # Monthly price ID
    stripe_price_id_yearly = Column(String(255), unique=True)  # Yearly price ID
    
    # Pricing
    price = Column(Float, nullable=False)  # Monthly price in USD
    price_yearly = Column(Float)  # Yearly price in USD (17% discount = 10 months)
    currency = Column(String(3), default="usd")
    interval = Column(String(20), default="month")
    
    # Limits
    search_limit = Column(Integer)  # null = unlimited
    scrape_limit = Column(Integer)  # null = unlimited
    rate_limit = Column(String(50))  # e.g., "10/minute", "60/minute", "1000/minute"
    concurrent_requests = Column(Integer, default=10)
    
    # Features
    features = Column(JSON, default={})
    
    # Status
    is_active = Column(Boolean, default=True)
    is_visible = Column(Boolean, default=True)  # Show in pricing page
    
    # Metadata
    plan_metadata = Column("metadata", JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        Index("idx_plans_active", "is_active"),
        Index("idx_plans_stripe", "stripe_product_id", "stripe_price_id"),
    )


class Invoice(Base):
    """User invoices from Stripe."""
    __tablename__ = "invoices"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Stripe
    stripe_invoice_id = Column(String(255), unique=True, index=True)
    stripe_charge_id = Column(String(255))
    
    # Invoice details
    invoice_number = Column(String(100), unique=True)
    status = Column(String(50))  # draft, open, paid, void, uncollectible
    
    # Amounts (in cents)
    amount_due = Column(Integer)
    amount_paid = Column(Integer)
    amount_remaining = Column(Integer)
    subtotal = Column(Integer)
    tax = Column(Integer)
    total = Column(Integer)
    currency = Column(String(3), default="usd")
    
    # Dates
    period_start = Column(DateTime(timezone=True))
    period_end = Column(DateTime(timezone=True))
    due_date = Column(DateTime(timezone=True))
    paid_at = Column(DateTime(timezone=True))
    
    # URLs
    invoice_pdf = Column(String(500))
    hosted_invoice_url = Column(String(500))
    
    # Metadata
    description = Column(Text)
    invoice_metadata = Column("metadata", JSON, default={})
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="invoices")
    
    __table_args__ = (
        Index("idx_invoices_user", "user_id"),
        Index("idx_invoices_stripe", "stripe_invoice_id"),
        Index("idx_invoices_status", "status"),
    )


class WebhookEvent(Base):
    """Track Stripe webhook events."""
    __tablename__ = "webhook_events"
    
    id = Column(Integer, primary_key=True)
    stripe_event_id = Column(String(255), unique=True, nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    
    # Processing
    processed = Column(Boolean, default=False)
    processed_at = Column(DateTime(timezone=True))
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    
    # Data
    data = Column(JSON, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index("idx_webhook_events_processed", "processed"),
        Index("idx_webhook_events_type", "event_type"),
    )
