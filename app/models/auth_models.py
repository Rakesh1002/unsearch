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


class ResetPasswordRequest(BaseModel):
    """Password reset request."""
    email: EmailStr


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
    """Create Stripe checkout session request."""
    price_id: str
    success_url: str
    cancel_url: str
    trial_days: Optional[int] = 0


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
    last_used_at: Optional[datetime]
    created_at: datetime


class UsageResponse(BaseModel):
    """Usage statistics response."""
    period: Dict[str, str]
    searches: Dict[str, Any]
    scrapes: Dict[str, Any]
    api_calls: int
    usage_by_engine: Dict[str, int]
    usage_by_day: Dict[str, int]


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


class BillingPortalResponse(BaseModel):
    """Billing portal response."""
    portal_url: str
