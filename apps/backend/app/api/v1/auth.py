"""
Authentication and user management endpoints.
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, status, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import structlog

from app.models.auth_models import (
    UserRegisterRequest,
    UserLoginRequest,
    RefreshTokenRequest,
    CreateAPIKeyRequest,
    ResetPasswordRequest,
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
from app.services.database import get_database_service, DatabaseService
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
        
        # TODO: Send verification email
        # background_tasks.add_task(send_verification_email, user)
        
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
        scopes=request.scopes
    )
    
    return APIKeyResponse(
        id=api_key.id,
        key=api_key.key,  # Only shown once
        name=api_key.name,
        description=api_key.description,
        scopes=api_key.scopes,
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
    """Request password reset."""
    reset_token = await auth_service.reset_password_request(request.email)
    
    # TODO: Send reset email
    # background_tasks.add_task(send_reset_email, request.email, reset_token)
    
    return {"message": "If the email exists, a reset link has been sent"}


@router.post("/reset-password/confirm")
async def reset_password(
    token: str,
    new_password: str,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Reset password using token."""
    try:
        success = await auth_service.reset_password(token, new_password)
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
    if not user:
        # Create a random password for OAuth users (not used for login)
        # Reuse AuthService to create user properly
        user = await auth_service.register_user(
            email=request.email,
            password=jwt.encode({"rand": request.oauth_id}, settings.secret_key, algorithm=settings.jwt_algorithm),
            full_name=request.full_name
        )
        user.is_verified = True
        await db_service.update_user(user)

    # Issue tokens
    access_token = auth_service.create_access_token(user)
    refresh_token = auth_service.create_refresh_token(user)
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
            "plan": user.current_plan.value if user.current_plan else "free",
        },
    )
