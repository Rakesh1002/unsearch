"""
Agent self-registration API endpoints.

This module provides endpoints for AI agents to self-register and get API keys:
- POST /agents/register - Register a new agent (sandbox access: 25 queries/day for 7 days)
- GET /agents/me - Get current agent status, limits, and claim URL
- POST /agents/resend-claim - Get claim URL again (for stuck humans)

The sandbox model:
1. Agent registers with just a name (no email needed)
2. Gets API key immediately with 25 queries/day for 7 days
3. Agent shares claim_url with human owner
4. Human claims by signing up with email, verifying it
5. Agent gets upgraded to full free tier (5,000 queries/month)
"""
import secrets
import re
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field, validator
import structlog

from app.config import get_settings
from app.api.dependencies import AuthUserDep, DatabaseDep
from app.models.users import User, UserAPIKey

logger = structlog.get_logger(__name__)
settings = get_settings()

router = APIRouter(prefix="/agents", tags=["Agent Registration"])

# Constants
SANDBOX_DAILY_LIMIT = 25
SANDBOX_DURATION_DAYS = 7


# ============================================================================
# Request/Response Models
# ============================================================================

class AgentRegisterRequest(BaseModel):
    """Request to register a new agent."""
    name: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Unique agent identifier (alphanumeric and hyphens only)"
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="Description of what the agent does"
    )
    
    @validator('name')
    def validate_name(cls, v):
        if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9-]*[a-zA-Z0-9]$|^[a-zA-Z0-9]$', v):
            raise ValueError('Agent name must be alphanumeric with hyphens (no leading/trailing hyphens)')
        if '--' in v:
            raise ValueError('Agent name cannot contain consecutive hyphens')
        return v.lower()  # Normalize to lowercase


class AgentAccessInfo(BaseModel):
    """Access level and limits info."""
    level: str  # "sandbox" or "free" or plan name
    is_claimed: bool
    daily_limit: Optional[int] = None
    daily_used: Optional[int] = None
    daily_remaining: Optional[int] = None
    days_remaining: Optional[int] = None
    expires_at: Optional[datetime] = None
    monthly_limit: Optional[int] = None
    monthly_used: Optional[int] = None
    monthly_remaining: Optional[int] = None
    rate_limit: Optional[str] = None


class AgentRegisterResponse(BaseModel):
    """Response after registering an agent."""
    api_key: str
    claim_url: str
    claim_code: str
    agent_name: str
    access: AgentAccessInfo
    message: str


class AgentStatusResponse(BaseModel):
    """Response for agent status check."""
    agent_name: str
    description: Optional[str] = None
    access: AgentAccessInfo
    claim_url: Optional[str] = None
    action_required: Optional[str] = None
    human_owner: Optional[dict] = None


class ResendClaimResponse(BaseModel):
    """Response for resend claim endpoint."""
    claim_url: str
    claim_code: str
    message: str


# ============================================================================
# Helper Functions
# ============================================================================

def generate_claim_code() -> str:
    """Generate a unique claim code."""
    return secrets.token_urlsafe(32)


def generate_agent_api_key() -> str:
    """Generate an API key for an agent."""
    token = secrets.token_urlsafe(32)
    env_prefix = "live" if settings.environment == "production" else "test"
    return f"sk_{env_prefix}_{token}"


def get_claim_url(claim_code: str) -> str:
    """Get the full claim URL for a claim code."""
    base_url = settings.frontend_url or "https://unsearch.dev"
    return f"{base_url}/claim/{claim_code}"


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/register", response_model=AgentRegisterResponse, status_code=status.HTTP_201_CREATED)
async def register_agent(
    request_data: AgentRegisterRequest,
    request: Request,
    db: DatabaseDep
):
    """
    Register a new AI agent and get an API key.
    
    **Sandbox Access:**
    - 25 queries per day (shared across all agents from same IP)
    - Valid for 7 days
    - No email required
    
    **To unlock full access (5,000 queries/month):**
    Share the `claim_url` with your human owner. They sign up with email
    and verify it, and your agent is upgraded automatically.
    
    **Anti-abuse:**
    - Only one unclaimed agent per IP at a time
    - If you already have an unclaimed agent, this returns its credentials
    - Daily sandbox quota is shared per IP (can't bypass by registering new names)
    """
    client_ip = request.client.host if request.client else "unknown"
    now = datetime.utcnow()
    
    # =========================================================================
    # ANTI-ABUSE: Check if this IP already has an unclaimed agent
    # If so, return the existing agent's credentials (idempotent behavior)
    # =========================================================================
    existing_unclaimed = await db.get_unclaimed_agent_by_ip(client_ip)
    if existing_unclaimed:
        # Get the API key for this agent
        api_keys = await db.get_user_api_keys(existing_unclaimed.id)
        if api_keys:
            existing_api_key = api_keys[0].key
            claim_url = get_claim_url(existing_unclaimed.claim_code)
            
            # Get current daily usage (IP-based)
            daily_used = await db.get_ip_daily_sandbox_usage(client_ip)
            daily_remaining = max(0, SANDBOX_DAILY_LIMIT - daily_used)
            
            # Calculate days remaining
            days_remaining = 0
            if existing_unclaimed.sandbox_expires_at and not existing_unclaimed.is_sandbox_expired:
                delta = existing_unclaimed.sandbox_expires_at - now
                days_remaining = max(0, delta.days + 1)
            
            logger.info(
                "agent_registration_returned_existing",
                agent_name=existing_unclaimed.agent_name,
                requested_name=request_data.name,
                user_id=existing_unclaimed.id,
                client_ip=client_ip
            )
            
            return AgentRegisterResponse(
                api_key=existing_api_key,
                claim_url=claim_url,
                claim_code=existing_unclaimed.claim_code,
                agent_name=existing_unclaimed.agent_name,
                access=AgentAccessInfo(
                    level="sandbox",
                    is_claimed=False,
                    daily_limit=SANDBOX_DAILY_LIMIT,
                    daily_used=daily_used,
                    daily_remaining=daily_remaining,
                    days_remaining=days_remaining,
                    expires_at=existing_unclaimed.sandbox_expires_at,
                ),
                message=f"You already have an unclaimed agent '{existing_unclaimed.agent_name}'. "
                        f"Returning existing credentials. Have your human claim it to register another."
            )
    
    # =========================================================================
    # Check if agent name already exists (could be claimed by someone else)
    # =========================================================================
    existing_by_name = await db.get_user_by_agent_name(request_data.name)
    if existing_by_name:
        # If it's unclaimed and from a different IP, name is taken
        # If it's claimed, name is taken
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "agent_name_taken",
                "message": f"Agent name '{request_data.name}' is already registered. Please choose a different name."
            }
        )
    
    # =========================================================================
    # Create new agent
    # =========================================================================
    claim_code = generate_claim_code()
    api_key = generate_agent_api_key()
    
    # Calculate sandbox expiry (7 days from now)
    sandbox_expires_at = now + timedelta(days=SANDBOX_DURATION_DAYS)
    daily_reset_at = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Create placeholder user
    placeholder_email = f"agent_{claim_code[:16]}@placeholder.unsearch.dev"
    
    try:
        user = User(
            email=placeholder_email,
            password_hash="",  # No password for placeholder
            salt="",  # No salt needed
            is_agent_placeholder=True,
            agent_name=request_data.name,
            agent_description=request_data.description,
            claim_code=claim_code,
            daily_searches_used=0,
            daily_reset_at=daily_reset_at,
            sandbox_expires_at=sandbox_expires_at,
            is_sandbox_expired=False,
            is_active=True,
            is_verified=False,
            registration_ip=client_ip,
        )
        user = await db.create_user(user)
        
        # Create API key for the agent
        user_api_key = UserAPIKey(
            user_id=user.id,
            key=api_key,
            name=f"Agent: {request_data.name}",
            description=f"Auto-generated key for agent '{request_data.name}'",
            scopes=["read", "write"],
            is_active=True,
        )
        await db.create_user_api_key(user_api_key)
        
        logger.info(
            "agent_registered",
            agent_name=request_data.name,
            user_id=user.id,
            client_ip=client_ip
        )
        
        claim_url = get_claim_url(claim_code)
        
        return AgentRegisterResponse(
            api_key=api_key,
            claim_url=claim_url,
            claim_code=claim_code,
            agent_name=request_data.name,
            access=AgentAccessInfo(
                level="sandbox",
                is_claimed=False,
                daily_limit=SANDBOX_DAILY_LIMIT,
                daily_used=0,
                daily_remaining=SANDBOX_DAILY_LIMIT,
                days_remaining=SANDBOX_DURATION_DAYS,
                expires_at=sandbox_expires_at,
            ),
            message=f"Agent registered! Share the claim_url with your human within {SANDBOX_DURATION_DAYS} days to unlock 5,000 queries/month."
        )
        
    except Exception as e:
        logger.error("agent_registration_failed", error=str(e), agent_name=request_data.name)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register agent. Please try again."
        )


@router.get("/me", response_model=AgentStatusResponse)
async def get_agent_status(
    auth_user: AuthUserDep,
    db: DatabaseDep
):
    """
    Get current agent status, limits, and claim information.
    
    Returns different info based on whether the agent is:
    - Unclaimed (sandbox): daily limits, days remaining, claim_url
    - Claimed (free tier): monthly limits, dashboard access
    - Upgraded (paid): plan limits and features
    """
    if not auth_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )
    
    user = await db.get_user(auth_user.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    now = datetime.utcnow()
    
    # Check if this is an agent placeholder (unclaimed)
    if user.is_agent_placeholder:
        # Check sandbox expiry
        is_expired = user.sandbox_expires_at and now >= user.sandbox_expires_at
        if is_expired and not user.is_sandbox_expired:
            await db.mark_agent_sandbox_expired(user.id)
            user.is_sandbox_expired = True
        
        # Get daily usage
        daily_used, daily_reset_at = await db.get_agent_daily_searches(user.id)
        daily_remaining = max(0, SANDBOX_DAILY_LIMIT - daily_used)
        
        # Calculate days remaining
        days_remaining = 0
        if user.sandbox_expires_at and not user.is_sandbox_expired:
            delta = user.sandbox_expires_at - now
            days_remaining = max(0, delta.days + 1)  # +1 to include today
        
        claim_url = get_claim_url(user.claim_code) if user.claim_code else None
        
        # Determine action required
        action_required = None
        if user.is_sandbox_expired:
            action_required = "Sandbox expired. Have your human verify at claim_url to restore access."
        elif days_remaining <= 2:
            action_required = f"Only {days_remaining} days left! Have your human verify at claim_url soon."
        else:
            action_required = "Have your human verify at claim_url to unlock 5,000 queries/month."
        
        return AgentStatusResponse(
            agent_name=user.agent_name,
            description=user.agent_description,
            access=AgentAccessInfo(
                level="sandbox",
                is_claimed=False,
                daily_limit=SANDBOX_DAILY_LIMIT,
                daily_used=daily_used,
                daily_remaining=daily_remaining,
                days_remaining=days_remaining,
                expires_at=user.sandbox_expires_at,
            ),
            claim_url=claim_url,
            action_required=action_required
        )
    
    # Claimed user - return full access info
    monthly_limit = auth_user.search_limit or 5000
    monthly_used = auth_user.search_used or 0
    monthly_remaining = max(0, monthly_limit - monthly_used)
    
    # Determine access level from plan
    level = auth_user.plan_name or "free"
    
    # Get rate limit from plan
    rate_limit = "10/minute"  # Default free tier
    if level == "pro":
        rate_limit = "60/minute"
    elif level == "growth":
        rate_limit = "200/minute"
    elif level == "scale":
        rate_limit = "1000/minute"
    
    return AgentStatusResponse(
        agent_name=user.agent_name or user.email.split("@")[0],
        description=user.agent_description,
        access=AgentAccessInfo(
            level=level,
            is_claimed=True,
            monthly_limit=monthly_limit,
            monthly_used=monthly_used,
            monthly_remaining=monthly_remaining,
            rate_limit=rate_limit,
        ),
        human_owner={
            "email_verified": user.is_verified,
            "can_manage_billing": True,
            "dashboard_url": f"{settings.frontend_url or 'https://unsearch.dev'}/dashboard"
        }
    )


@router.post("/resend-claim", response_model=ResendClaimResponse)
async def resend_claim_link(
    auth_user: AuthUserDep,
    db: DatabaseDep
):
    """
    Get the claim URL again.
    
    Use this if your human lost the claim link or needs it resent.
    Works even after sandbox expiry - claims are always allowed.
    """
    if not auth_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )
    
    user = await db.get_user(auth_user.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if already claimed
    if not user.is_agent_placeholder:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "already_claimed",
                "message": "This agent is already claimed. Your human can manage API keys at the dashboard.",
                "dashboard_url": f"{settings.frontend_url or 'https://unsearch.dev'}/dashboard"
            }
        )
    
    if not user.claim_code:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No claim code found. Please contact support."
        )
    
    claim_url = get_claim_url(user.claim_code)
    
    return ResendClaimResponse(
        claim_url=claim_url,
        claim_code=user.claim_code,
        message="Share this link with your human owner to complete verification."
    )
