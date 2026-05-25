"""
Authentication and user management service.
"""
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import jwt
import secrets
import hashlib
import structlog
import bcrypt

from app.config import get_settings
from app.models.users import User, UserAPIKey, UsageRecord
from app.services.core.database import DatabaseService, get_database_service
from fastapi import Depends
from app.utils.exceptions import AuthenticationException, UnauthorizedException

logger = structlog.get_logger(__name__)
settings = get_settings()


def hash_password(password: str) -> str:
    """Hash a password using bcrypt with automatic truncation to 72 bytes."""
    # bcrypt has a 72-byte limit, truncate if necessary
    password_bytes = password.encode('utf-8')[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against a bcrypt hash."""
    password_bytes = password.encode('utf-8')[:72]
    hashed_bytes = hashed.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)


class AuthService:
    """Service for authentication and user management."""
    
    def __init__(self, db_service: DatabaseService):
        self.db = db_service
        self.secret_key = settings.secret_key
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 60 * 24  # 24 hours
        self.refresh_token_expire_days = 30
    
    async def register_user(
        self,
        email: str,
        password: str,
        full_name: Optional[str] = None,
        company: Optional[str] = None
    ) -> User:
        """Register a new user."""
        # Check if user exists
        existing = await self.db.get_user_by_email(email)
        if existing:
            raise AuthenticationException("User with this email already exists")
        
        # Hash password using bcrypt (handles salt internally, truncates to 72 bytes)
        password_hash = hash_password(password)
        
        # Create user
        user = User(
            email=email,
            password_hash=password_hash,
            salt="",  # bcrypt handles salt internally, kept for schema compatibility
            full_name=full_name,
            company=company,
            verification_token=secrets.token_urlsafe(32)
        )
        
        user = await self.db.create_user(user)
        
        # Create initial API key
        await self.create_api_key(user, "Default API Key")
        
        # Initialize usage record for current month
        await self._initialize_usage_record(user)
        
        logger.info("user_registered", user_id=user.id, email=email)
        
        return user
    
    async def login(self, email: str, password: str) -> Dict[str, Any]:
        """Authenticate user and return tokens."""
        # Get user
        user = await self.db.get_user_by_email(email)
        if not user:
            raise UnauthorizedException("Invalid email or password")
        
        # For backward compatibility: if user has a salt, use old password format
        if user.salt:
            password_to_verify = password + user.salt
        else:
            password_to_verify = password
        
        # Verify password
        if not verify_password(password_to_verify, user.password_hash):
            raise UnauthorizedException("Invalid email or password")
        
        # Check if user is active
        if not user.is_active:
            raise UnauthorizedException("Account is disabled")
        
        # Capture plan before any operations that might detach the session
        try:
            plan = user.current_plan.value if user.current_plan else "free"
        except Exception:
            plan = "free"
        
        # Update last login
        user.last_login_at = datetime.utcnow()
        await self.db.update_user(user)
        
        # Generate tokens
        access_token = self.create_access_token(user)
        refresh_token = self.create_refresh_token(user)
        
        logger.info("user_login", user_id=user.id)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": self.access_token_expire_minutes * 60,
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "is_verified": user.is_verified,
                "plan": plan
            }
        }
    
    def create_access_token(self, user: User) -> str:
        """Create JWT access token."""
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        payload = {
            "sub": str(user.id),
            "email": user.email,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def create_refresh_token(self, user: User) -> str:
        """Create JWT refresh token."""
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        payload = {
            "sub": str(user.id),
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh"
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    async def verify_token(self, token: str) -> Optional[User]:
        """Verify JWT token and return user."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            user_id = payload.get("sub")
            
            if not user_id:
                return None
            
            user = await self.db.get_user(int(user_id))
            if not user or not user.is_active:
                return None
            
            return user
            
        except jwt.ExpiredSignatureError:
            logger.warning("token_expired")
            return None
        except jwt.PyJWTError:
            logger.warning("invalid_token")
            return None
    
    async def refresh_tokens(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token using refresh token."""
        try:
            payload = jwt.decode(refresh_token, self.secret_key, algorithms=[self.algorithm])
            
            if payload.get("type") != "refresh":
                raise UnauthorizedException("Invalid refresh token")
            
            user_id = payload.get("sub")
            if not user_id:
                raise UnauthorizedException("Invalid refresh token")
            
            user = await self.db.get_user(int(user_id))
            if not user or not user.is_active:
                raise UnauthorizedException("User not found or inactive")
            
            # Generate new tokens
            new_access_token = self.create_access_token(user)
            new_refresh_token = self.create_refresh_token(user)
            
            return {
                "access_token": new_access_token,
                "refresh_token": new_refresh_token,
                "token_type": "bearer",
                "expires_in": self.access_token_expire_minutes * 60
            }
            
        except jwt.ExpiredSignatureError:
            raise UnauthorizedException("Refresh token expired")
        except jwt.PyJWTError:
            raise UnauthorizedException("Invalid refresh token")
    
    async def create_api_key(
        self,
        user: User,
        name: str,
        description: Optional[str] = None,
        scopes: Optional[List[str]] = None,
        expires_in_days: Optional[int] = None
    ) -> UserAPIKey:
        """Create an API key for a user."""
        # Generate secure API key
        key_prefix = "sk_"
        if settings.environment == "production":
            key_prefix = "sk_live_"
        elif settings.environment == "development":
            key_prefix = "sk_test_"
        
        key = key_prefix + secrets.token_urlsafe(32)
        
        # Calculate expiration date if specified
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        # Create API key record
        api_key = UserAPIKey(
            user_id=user.id,
            key=key,
            name=name,
            description=description,
            scopes=scopes or ["read", "write"],
            expires_at=expires_at
        )
        
        api_key = await self.db.create_user_api_key(api_key)
        
        logger.info("api_key_created", user_id=user.id, key_id=api_key.id, expires_at=expires_at)
        
        return api_key
    
    async def verify_api_key(self, key: str) -> Optional[User]:
        """Verify API key and return associated user."""
        api_key = await self.db.get_api_key_by_value(key)
        
        if not api_key or not api_key.is_active:
            return None
        
        # Check expiration
        if api_key.expires_at and api_key.expires_at < datetime.utcnow():
            return None
        
        # Update last used
        api_key.last_used_at = datetime.utcnow()
        api_key.request_count += 1
        await self.db.update_api_key(api_key)
        
        # Get user
        user = await self.db.get_user(api_key.user_id)
        if not user or not user.is_active:
            return None
        
        return user
    
    async def reset_password_request(self, email: str) -> Optional[str]:
        """
        Request password reset. Returns reset token if user exists, None otherwise.
        Caller should send email only when token is not None; always respond with same message.
        """
        user = await self.db.get_user_by_email(email)
        if not user:
            return None

        reset_token = secrets.token_urlsafe(32)
        user.reset_token = reset_token
        user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
        await self.db.update_user(user)
        logger.info("password_reset_requested", user_id=user.id)
        return reset_token
    
    async def reset_password(self, token: str, new_password: str) -> bool:
        """Reset password using token."""
        user = await self.db.get_user_by_reset_token(token)
        
        if not user:
            raise AuthenticationException("Invalid reset token")
        
        if user.reset_token_expires < datetime.utcnow():
            raise AuthenticationException("Reset token expired")
        
        # Hash password using bcrypt (handles salt internally, truncates to 72 bytes)
        password_hash = hash_password(new_password)
        
        # Update user
        user.password_hash = password_hash
        user.salt = ""  # bcrypt handles salt internally, clear legacy salt
        user.reset_token = None
        user.reset_token_expires = None
        await self.db.update_user(user)
        
        logger.info("password_reset_completed", user_id=user.id)
        
        return True
    
    async def verify_email(self, token: str) -> bool:
        """Verify email using token."""
        user = await self.db.get_user_by_verification_token(token)
        
        if not user:
            raise AuthenticationException("Invalid verification token")
        
        user.is_verified = True
        user.email_verified_at = datetime.utcnow()
        user.verification_token = None
        await self.db.update_user(user)
        
        logger.info("email_verified", user_id=user.id)
        
        return True
    
    async def get_user_usage(self, user: User) -> Dict[str, Any]:
        """Get current usage statistics for a user."""
        # Get current period
        now = datetime.utcnow()
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Get or create usage record
        usage = await self.db.get_user_usage(user.id, period_start)
        
        if not usage:
            usage = await self._initialize_usage_record(user)
        
        # Get subscription limits (defaults match frontend pricing: 5000 searches, 500 scrapes)
        subscription = user.current_subscription
        search_limit = subscription.search_limit if subscription else 5000
        scrape_limit = subscription.scrape_limit if subscription else 500
        
        # Calculate today's usage from usage_by_day
        today = now.date().isoformat()
        queries_today = usage.usage_by_day.get(today, 0) if usage.usage_by_day else 0
        scrapes_today = 0  # We don't track scrapes by day separately yet
        
        # Convert usage_by_day to daily_usage array for frontend
        daily_usage = [
            {"date": date, "queries": count, "scrapes": 0}
            for date, count in (usage.usage_by_day or {}).items()
        ]
        daily_usage.sort(key=lambda x: x["date"])
        
        return {
            # Frontend expected fields
            "total_queries": usage.search_count,
            "total_scrapes": usage.scrape_count,
            "queries_today": queries_today,
            "scrapes_today": scrapes_today,
            "queries_this_month": usage.search_count,
            "scrapes_this_month": usage.scrape_count,
            "daily_usage": daily_usage,
            
            # Detailed breakdown
            "period": {
                "start": period_start.isoformat(),
                "end": (period_start + timedelta(days=30)).isoformat()
            },
            "searches": {
                "used": usage.search_count,
                "limit": search_limit,
                "remaining": (search_limit - usage.search_count) if search_limit else None,
                "unlimited": search_limit is None
            },
            "scrapes": {
                "used": usage.scrape_count,
                "limit": scrape_limit,
                "remaining": (scrape_limit - usage.scrape_count) if scrape_limit else None,
                "unlimited": scrape_limit is None
            },
            "api_calls": usage.api_calls,
            "usage_by_engine": usage.usage_by_engine or {},
            "usage_by_day": usage.usage_by_day or {}
        }
    
    async def check_usage_limits(self, user: User, search: bool = False, scrape: bool = False) -> bool:
        """Check if user has exceeded usage limits."""
        # Get current usage
        usage_data = await self.get_user_usage(user)
        
        if search:
            if not usage_data["searches"]["unlimited"]:
                if usage_data["searches"]["remaining"] <= 0:
                    return False
        
        if scrape:
            if not usage_data["scrapes"]["unlimited"]:
                if usage_data["scrapes"]["remaining"] <= 0:
                    return False
        
        return True
    
    async def increment_usage(
        self,
        user: User,
        search_count: int = 0,
        scrape_count: int = 0,
        engine: Optional[str] = None
    ):
        """Increment usage counters for a user."""
        now = datetime.utcnow()
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        usage = await self.db.get_user_usage(user.id, period_start)
        if not usage:
            usage = await self._initialize_usage_record(user)
        
        # Update counts
        usage.search_count += search_count
        usage.scrape_count += scrape_count
        usage.api_calls += 1
        
        # Update usage by engine
        if engine and search_count > 0:
            if engine not in usage.usage_by_engine:
                usage.usage_by_engine[engine] = 0
            usage.usage_by_engine[engine] += search_count
        
        # Update usage by day
        today = now.date().isoformat()
        if today not in usage.usage_by_day:
            usage.usage_by_day[today] = 0
        usage.usage_by_day[today] += search_count + scrape_count
        
        # Check for overages
        subscription = user.current_subscription
        if subscription:
            if subscription.search_limit and usage.search_count > subscription.search_limit:
                usage.search_overage = usage.search_count - subscription.search_limit
            if subscription.scrape_limit and usage.scrape_count > subscription.scrape_limit:
                usage.scrape_overage = usage.scrape_count - subscription.scrape_limit
        
        await self.db.update_usage_record(usage)
    
    async def _initialize_usage_record(self, user: User) -> UsageRecord:
        """Initialize usage record for current period."""
        now = datetime.utcnow()
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        period_end = (period_start + timedelta(days=30)).replace(hour=23, minute=59, second=59)
        
        usage = UsageRecord(
            user_id=user.id,
            period_start=period_start,
            period_end=period_end,
            search_count=0,
            scrape_count=0,
            api_calls=0,
            usage_by_engine={},
            usage_by_day={}
        )
        
        return await self.db.create_usage_record(usage)


# Singleton instance
_auth_service: Optional[AuthService] = None


async def get_auth_service(db_service: DatabaseService = Depends(get_database_service)) -> AuthService:
    """Get or create auth service instance."""
    global _auth_service
    
    if _auth_service is None:
        _auth_service = AuthService(db_service)
    
    return _auth_service


async def track_usage(
    user_id: int,
    search_count: int = 0,
    scrape_count: int = 0,
    engine: Optional[str] = None
):
    """
    Track usage for a user. Call this from API endpoints after successful operations.
    
    Args:
        user_id: The user's ID
        search_count: Number of searches to add (default 1 per search request)
        scrape_count: Number of scrapes to add
        engine: Optional engine name for breakdown tracking
    """
    try:
        db_service = await get_database_service()
        
        now = datetime.utcnow()
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        usage = await db_service.get_user_usage(user_id, period_start)
        
        if not usage:
            # Create new usage record for this period
            period_end = (period_start + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
            usage = UsageRecord(
                user_id=user_id,
                period_start=period_start,
                period_end=period_end,
                search_count=0,
                scrape_count=0,
                api_calls=0,
                usage_by_engine={},
                usage_by_day={}
            )
            usage = await db_service.create_usage_record(usage)
        
        # Update counts
        usage.search_count += search_count
        usage.scrape_count += scrape_count
        usage.api_calls += 1
        
        # Update usage by engine
        if engine and search_count > 0:
            if not usage.usage_by_engine:
                usage.usage_by_engine = {}
            if engine not in usage.usage_by_engine:
                usage.usage_by_engine[engine] = 0
            usage.usage_by_engine[engine] += search_count
        
        # Update usage by day
        today = now.date().isoformat()
        if not usage.usage_by_day:
            usage.usage_by_day = {}
        if today not in usage.usage_by_day:
            usage.usage_by_day[today] = 0
        usage.usage_by_day[today] += search_count + scrape_count
        
        await db_service.update_usage_record(usage)
        
        logger.debug(
            "usage_tracked",
            user_id=user_id,
            search_count=search_count,
            scrape_count=scrape_count,
            total_searches=usage.search_count,
            total_scrapes=usage.scrape_count
        )
        
    except Exception as e:
        # Don't fail the request if usage tracking fails
        logger.error("usage_tracking_failed", user_id=user_id, error=str(e))
