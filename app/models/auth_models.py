"""
Pydantic models for authentication and billing requests/responses.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, validator


# ==================== Request Models ====================

class UserRegisterRequest(BaseModel):
    """User registration request."""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    full_name: Optional[str] = Field(None, max_length=255)
    company: Optional[str] = Field(None, max_length=255)
    
    @validator('password')
    def validate_password(cls, v):
        """Ensure password meets complexity requirements."""
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one digit')
        if not any(char.isupper() for char in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(char.islower() for char in v):
            raise ValueError('Password must contain at least one lowercase letter')
        return v


class UserLoginRequest(BaseModel):
    """User login request."""
    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""
    refresh_token: str


class CreateAPIKeyRequest(BaseModel):
    """Create API key request."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    scopes: Optional[List[str]] = ["read", "write"]
    expires_in_days: Optional[int] = Field(None, ge=1, le=365, description="Days until key expires (1-365)")


class ResetPasswordRequest(BaseModel):
    """Password reset request."""
    email: EmailStr


class ResetPasswordConfirmRequest(BaseModel):
    """Password reset confirmation (token + new password)."""
    token: str
    password: str = Field(..., min_length=8, max_length=100)


class ChangePasswordRequest(BaseModel):
    """Change password request."""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)


class CreateSubscriptionRequest(BaseModel):
    """Create subscription request."""
    price_id: str
    trial_days: Optional[int] = 0


class UpdateSubscriptionRequest(BaseModel):
    """Update subscription request."""
    price_id: str


class CreateCheckoutSessionRequest(BaseModel):
    """Create Stripe checkout session request.
    
    Accepts either:
    - price_id directly (Stripe price ID)
    - OR plan_id + billing_period (resolved to price_id via plans table)
    """
    price_id: Optional[str] = None
    plan_id: Optional[str] = None
    billing_period: Optional[str] = None  # "monthly" or "yearly"
    success_url: str
    cancel_url: str
    trial_days: Optional[int] = 0
    
    @validator('billing_period')
    def validate_billing_period(cls, v):
        if v and v not in ("monthly", "yearly"):
            raise ValueError('billing_period must be "monthly" or "yearly"')
        return v


# ==================== Response Models ====================

class UserResponse(BaseModel):
    """User response model."""
    id: int
    email: str
    full_name: Optional[str]
    company: Optional[str]
    is_verified: bool
    plan: str
    created_at: datetime


class LoginResponse(BaseModel):
    """Login response model."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: Optional[Dict[str, Any]] = None


class APIKeyResponse(BaseModel):
    """API key response model."""
    id: int
    key: str
    name: str
    description: Optional[str]
    scopes: List[str]
    last_used_at: Optional[datetime] = None
    created_at: datetime


class UsageDetailResponse(BaseModel):
    """Detailed usage breakdown."""
    used: int
    limit: Optional[int]
    remaining: Optional[int]
    unlimited: bool


class UsageResponse(BaseModel):
    """Usage statistics response - matches frontend UsageStats interface."""
    # Legacy fields for existing frontend
    total_queries: int = 0
    total_scrapes: int = 0
    queries_today: int = 0
    scrapes_today: int = 0
    queries_this_month: int = 0
    scrapes_this_month: int = 0
    daily_usage: List[Dict[str, Any]] = []
    
    # Detailed breakdown
    period: Optional[Dict[str, str]] = None
    searches: Optional[UsageDetailResponse] = None
    scrapes: Optional[UsageDetailResponse] = None
    api_calls: int = 0
    usage_by_engine: Dict[str, int] = {}
    usage_by_day: Dict[str, int] = {}


class SubscriptionResponse(BaseModel):
    """Subscription response model."""
    id: int
    plan_type: str
    status: str
    amount: float
    currency: str
    interval: str
    search_limit: Optional[int]
    scrape_limit: Optional[int]
    rate_limit: str
    features: Dict[str, bool]
    current_period_start: datetime
    current_period_end: datetime
    trial_end: Optional[datetime]
    cancelled_at: Optional[datetime]
    is_active: bool
    days_remaining: Optional[int] = None


class PlanResponse(BaseModel):
    """Subscription plan response."""
    id: int
    name: str
    display_name: str
    description: Optional[str]
    price: float
    currency: str
    interval: str
    search_limit: Optional[int]
    scrape_limit: Optional[int]
    rate_limit: str
    features: Dict[str, bool]


class InvoiceResponse(BaseModel):
    """Invoice response model."""
    id: int
    invoice_number: Optional[str]
    status: str
    amount_due: float
    amount_paid: float
    currency: str
    period_start: Optional[datetime]
    period_end: Optional[datetime]
    paid_at: Optional[datetime]
    invoice_pdf: Optional[str]
    hosted_invoice_url: Optional[str]
    created_at: datetime


class CheckoutSessionResponse(BaseModel):
    """Checkout session response."""
    checkout_url: str
    url: Optional[str] = None  # alias for frontend; set same as checkout_url in endpoint


class BillingPortalRequest(BaseModel):
    """Billing portal session request (POST body)."""
    return_url: Optional[str] = None


class BillingPortalResponse(BaseModel):
    """Billing portal response."""
    portal_url: str
    url: Optional[str] = None  # alias for frontend; set same as portal_url in endpoint


class OAuthSyncRequest(BaseModel):
    """OAuth sync request for third-party providers (e.g., GitHub)."""
    provider: str
    oauth_id: str
    email: EmailStr
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
