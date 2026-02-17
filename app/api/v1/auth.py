"""
Authentication and user management endpoints.
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, status, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import structlog
import jwt

from app.config import get_settings

settings = get_settings()

from app.models.auth_models import (
    UserRegisterRequest,
    UserLoginRequest,
    RefreshTokenRequest,
    CreateAPIKeyRequest,
    ResetPasswordRequest,
    ResetPasswordConfirmRequest,
    ChangePasswordRequest,
    UserResponse,
    LoginResponse,
    APIKeyResponse,
    UsageResponse,
    SubscriptionResponse,
    OAuthSyncRequest,
)
from app.services.auth_service import get_auth_service, AuthService
from app.services.stripe_service import get_stripe_service, StripeService
from app.services.email_service import (
    send_verification_email,
    send_reset_password_email,
    send_welcome_email,
)
from app.services.core.database import get_database_service, DatabaseService
from app.models.users import User
from app.utils.exceptions import UnauthorizedException, BadRequestException

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service),
    db_service: DatabaseService = Depends(get_database_service)
) -> User:
    """Get current authenticated user from JWT token."""
    token = credentials.credentials
    
    # First try as JWT token
    user = await auth_service.verify_token(token)
    
    # If not JWT, try as API key
    if not user:
        user = await auth_service.verify_api_key(token)
    
    if not user:
        raise UnauthorizedException("Invalid or expired token")
    
    return user


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: UserRegisterRequest,
    background_tasks: BackgroundTasks,
    auth_service: AuthService = Depends(get_auth_service),
    stripe_service: StripeService = Depends(get_stripe_service)
):
    """Register a new user account."""
    try:
        # Create user
        user = await auth_service.register_user(
            email=request.email,
            password=request.password,
            full_name=request.full_name,
            company=request.company
        )
        
        # Create Stripe customer
        background_tasks.add_task(stripe_service.create_customer, user)
        # Resend: verification + welcome (no-op if RESEND_API_KEY not set)
        if user.verification_token:
            background_tasks.add_task(
                send_verification_email, user.email, user.verification_token
            )
        background_tasks.add_task(send_welcome_email, user.email, user.full_name)
        return UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            company=user.company,
            is_verified=user.is_verified,
            plan="free",
            created_at=user.created_at
        )
        
    except Exception as e:
        logger.error("registration_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login", response_model=LoginResponse)
async def login(
    request: UserLoginRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Login with email and password."""
    try:
        result = await auth_service.login(request.email, request.password)
        return LoginResponse(**result)
        
    except UnauthorizedException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except Exception as e:
        logger.error("login_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Login failed"
        )


@router.post("/refresh", response_model=LoginResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Refresh access token using refresh token."""
    try:
        result = await auth_service.refresh_tokens(request.refresh_token)
        return LoginResponse(**result)
        
    except UnauthorizedException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    user: User = Depends(get_current_user)
):
    """Get current user information."""
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        company=user.company,
        is_verified=user.is_verified,
        plan=user.current_plan.value if user.current_plan else "free",
        created_at=user.created_at
    )


@router.put("/me", response_model=UserResponse)
async def update_user(
    full_name: Optional[str] = None,
    company: Optional[str] = None,
    timezone: Optional[str] = None,
    user: User = Depends(get_current_user),
    db_service: DatabaseService = Depends(get_database_service)
):
    """Update current user information."""
    if full_name:
        user.full_name = full_name
    if company:
        user.company = company
    if timezone:
        user.timezone = timezone
    
    await db_service.update_user(user)
    
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        company=user.company,
        is_verified=user.is_verified,
        plan=user.current_plan.value if user.current_plan else "free",
        created_at=user.created_at
    )


@router.post("/api-keys", response_model=APIKeyResponse)
async def create_api_key(
    request: CreateAPIKeyRequest,
    user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Create a new API key."""
    api_key = await auth_service.create_api_key(
        user=user,
        name=request.name,
        description=request.description,
        scopes=request.scopes,
        expires_in_days=request.expires_in_days
    )
    
    return APIKeyResponse(
        id=api_key.id,
        key=api_key.key,  # Only shown once
        name=api_key.name,
        description=api_key.description,
        scopes=api_key.scopes,
        last_used_at=None,  # New keys haven't been used yet
        created_at=api_key.created_at
    )


@router.get("/api-keys", response_model=list[APIKeyResponse])
async def list_api_keys(
    user: User = Depends(get_current_user),
    db_service: DatabaseService = Depends(get_database_service)
):
    """List all API keys for current user."""
    api_keys = await db_service.get_user_api_keys(user.id)
    
    return [
        APIKeyResponse(
            id=key.id,
            key="sk_****" + key.key[-8:],  # Partially hidden
            name=key.name,
            description=key.description,
            scopes=key.scopes,
            last_used_at=key.last_used_at,
            created_at=key.created_at
        )
        for key in api_keys
    ]


@router.delete("/api-keys/{key_id}")
async def delete_api_key(
    key_id: int,
    user: User = Depends(get_current_user),
    db_service: DatabaseService = Depends(get_database_service)
):
    """Delete an API key."""
    success = await db_service.delete_api_key(key_id, user.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    return {"message": "API key deleted"}


@router.get("/usage", response_model=UsageResponse)
async def get_usage(
    user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Get current usage statistics."""
    usage = await auth_service.get_user_usage(user)
    return UsageResponse(**usage)


@router.post("/verify-email")
async def verify_email(
    token: str,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Verify email address."""
    try:
        success = await auth_service.verify_email(token)
        return {"message": "Email verified successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/reset-password")
async def request_password_reset(
    request: ResetPasswordRequest,
    background_tasks: BackgroundTasks,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Request password reset. Sends email via Resend when user exists."""
    reset_token = await auth_service.reset_password_request(request.email)
    if reset_token:
        background_tasks.add_task(
            send_reset_password_email, request.email, reset_token
        )
    return {"message": "If the email exists, a reset link has been sent"}


@router.post("/reset-password/confirm")
async def reset_password_confirm(
    request: ResetPasswordConfirmRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Reset password using token (from email link)."""
    try:
        await auth_service.reset_password(request.token, request.password)
        return {"message": "Password reset successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
    db_service: DatabaseService = Depends(get_database_service)
):
    """Change password for authenticated user."""
    # Verify current password
    try:
        await auth_service.login(user.email, request.current_password)
    except:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect"
        )
    
    # Change password
    await auth_service.reset_password(user.reset_token, request.new_password)
    
    return {"message": "Password changed successfully"}


@router.post("/oauth-sync", response_model=LoginResponse)
async def oauth_sync(
    request: OAuthSyncRequest,
    auth_service: AuthService = Depends(get_auth_service),
    db_service: DatabaseService = Depends(get_database_service)
):
    """Upsert user from OAuth provider and return backend tokens.

    Flow:
    - If user exists by email → return tokens
    - Else create user (verified), set profile fields → return tokens
    """
    # Try to find existing user
    user = await db_service.get_user_by_email(request.email)
    is_new_user = False
    if not user:
        is_new_user = True
        # Create a random password for OAuth users (not used for login)
        # Use a simple random string since OAuth users authenticate via OAuth, not password
        import secrets as oauth_secrets
        random_password = oauth_secrets.token_urlsafe(32)
        user = await auth_service.register_user(
            email=request.email,
            password=random_password,
            full_name=request.full_name
        )
        user.is_verified = True
        await db_service.update_user(user)
        # Re-fetch the user to get all relationships loaded properly
        user = await db_service.get_user_by_email(request.email)

    # Issue tokens
    access_token = auth_service.create_access_token(user)
    refresh_token = auth_service.create_refresh_token(user)
    
    # Safely get plan - new users default to free, existing users check subscription
    try:
        plan = user.current_plan.value if user.current_plan else "free"
    except Exception:
        # Fallback if relationships aren't loaded
        plan = "free"
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=auth_service.access_token_expire_minutes * 60,
        user={
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "is_verified": user.is_verified,
            "plan": plan,
        },
    )


@router.delete("/account")
async def delete_account(
    user: User = Depends(get_current_user),
    db_service: DatabaseService = Depends(get_database_service),
    stripe_service: StripeService = Depends(get_stripe_service)
):
    """Permanently delete user account and all associated data."""
    try:
        # Cancel any active Stripe subscriptions first
        if user.stripe_customer_id:
            try:
                await stripe_service.cancel_all_subscriptions(user.stripe_customer_id)
            except Exception as e:
                logger.warning("stripe_subscription_cancel_failed", user_id=user.id, error=str(e))
        
        # Delete user and all associated data
        success = await db_service.delete_user(user.id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete account"
            )
        
        logger.info("account_deleted", user_id=user.id, email=user.email)
        return {"message": "Account deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("account_deletion_failed", user_id=user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete account"
        )


# ============================================================================
# Agent Claim Endpoints
# ============================================================================

from pydantic import BaseModel, Field, EmailStr


class ClaimInfoResponse(BaseModel):
    """Response for claim info endpoint."""
    agent_name: str
    agent_description: Optional[str] = None
    is_claimed: bool
    is_expired: bool
    can_claim: bool
    message: str


class ClaimAgentRequest(BaseModel):
    """Request to claim an agent."""
    claim_code: str
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=1)


class ClaimAgentResponse(BaseModel):
    """Response after claiming an agent."""
    success: bool
    message: str
    verification_required: bool
    email: str


@router.get("/claim/{claim_code}")
async def get_claim_info(
    claim_code: str,
    db_service: DatabaseService = Depends(get_database_service)
):
    """
    Get information about a claim code.
    
    Returns agent details and whether it can still be claimed.
    Used by the frontend to show the claim form.
    """
    user = await db_service.get_user_by_claim_code(claim_code)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "invalid_claim_code",
                "message": "This claim link is invalid or has expired."
            }
        )
    
    # Check if already claimed
    if not user.is_agent_placeholder:
        return ClaimInfoResponse(
            agent_name=user.agent_name or "Unknown",
            agent_description=user.agent_description,
            is_claimed=True,
            is_expired=False,
            can_claim=False,
            message="Good news! This agent is already verified."
        )
    
    # Check if sandbox expired (but still allow claiming)
    is_expired = user.is_sandbox_expired or False
    
    return ClaimInfoResponse(
        agent_name=user.agent_name or "Unknown",
        agent_description=user.agent_description,
        is_claimed=False,
        is_expired=is_expired,
        can_claim=True,
        message="Verify your email to unlock 5,000 queries/month." if not is_expired else
                "Sandbox expired, but you can still claim to restore access."
    )


@router.post("/claim", response_model=ClaimAgentResponse)
async def claim_agent(
    request: ClaimAgentRequest,
    background_tasks: BackgroundTasks,
    db_service: DatabaseService = Depends(get_database_service),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Claim an agent by providing email and password.
    
    This upgrades a placeholder agent account to a real user account.
    The human owner can then login and manage billing.
    """
    # Get the placeholder user
    placeholder = await db_service.get_user_by_claim_code(request.claim_code)
    
    if not placeholder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "invalid_claim_code",
                "message": "This claim link is invalid or has expired."
            }
        )
    
    # Check if already claimed
    if not placeholder.is_agent_placeholder:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "already_claimed",
                "message": "This agent is already verified. You can login to manage it."
            }
        )
    
    # Check if email is already in use
    existing = await db_service.get_user_by_email(request.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "email_exists",
                "message": "This email is already registered. Please use a different email, "
                          "or login to your existing account to create API keys."
            }
        )
    
    try:
        # Hash the password
        import bcrypt
        import secrets
        
        # Truncate password to 72 bytes for bcrypt
        password_bytes = request.password.encode('utf-8')[:72]
        salt = bcrypt.gensalt()
        password_hash = bcrypt.hashpw(password_bytes, salt).decode('utf-8')
        
        # Generate verification token
        verification_token = secrets.token_urlsafe(32)
        
        # Update the placeholder user
        placeholder.email = request.email
        placeholder.password_hash = password_hash
        placeholder.salt = salt.decode('utf-8')
        placeholder.full_name = request.full_name
        placeholder.is_agent_placeholder = False
        placeholder.is_sandbox_expired = False
        placeholder.claimed_at = datetime.utcnow()
        placeholder.verification_token = verification_token
        placeholder.is_verified = False
        
        await db_service.update_user(placeholder)
        
        # Send verification email
        background_tasks.add_task(
            send_verification_email, request.email, verification_token
        )
        
        # Send welcome email
        background_tasks.add_task(
            send_welcome_email, request.email, request.full_name
        )
        
        logger.info(
            "agent_claimed",
            agent_name=placeholder.agent_name,
            user_id=placeholder.id,
            email=request.email
        )
        
        return ClaimAgentResponse(
            success=True,
            message="Check your email to verify your account. "
                    "Your agent will have 5,000 queries/month once verified.",
            verification_required=True,
            email=request.email
        )
        
    except Exception as e:
        logger.error("claim_agent_failed", error=str(e), claim_code=request.claim_code[:8])
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to claim agent. Please try again."
        )


from datetime import datetime
