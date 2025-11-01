"""
Authentication and user management service.
"""
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import jwt
import secrets
import hashlib
import structlog
from passlib.context import CryptContext

from app.config import get_settings
from app.models.users import User, UserAPIKey, UsageRecord
from app.services.database import DatabaseService
from app.utils.exceptions import AuthenticationException, UnauthorizedException

logger = structlog.get_logger(__name__)
settings = get_settings()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


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
        
        # Generate salt and hash password
        salt = secrets.token_hex(16)
        password_hash = pwd_context.hash(password + salt)
        
        # Create user
        user = User(
            email=email,
            password_hash=password_hash,
            salt=salt,
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
        
        # Verify password
        if not pwd_context.verify(password + user.salt, user.password_hash):
            raise UnauthorizedException("Invalid email or password")
        
        # Check if user is active
        if not user.is_active:
            raise UnauthorizedException("Account is disabled")
        
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
                "plan": user.current_plan.value if user.current_plan else "free"
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
        except jwt.JWTError:
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
        except jwt.JWTError:
            raise UnauthorizedException("Invalid refresh token")
    
    async def create_api_key(
        self,
        user: User,
        name: str,
        description: Optional[str] = None,
        scopes: Optional[List[str]] = None
    ) -> UserAPIKey:
        """Create an API key for a user."""
        # Generate secure API key
        key_prefix = "sk_"
        if settings.environment == "production":
            key_prefix = "sk_live_"
        elif settings.environment == "development":
            key_prefix = "sk_test_"
        
        key = key_prefix + secrets.token_urlsafe(32)
        
        # Create API key record
        api_key = UserAPIKey(
            user_id=user.id,
            key=key,
            name=name,
            description=description,
            scopes=scopes or ["read", "write"]
        )
        
        api_key = await self.db.create_api_key(api_key)
        
        logger.info("api_key_created", user_id=user.id, key_id=api_key.id)
        
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
    
    async def reset_password_request(self, email: str) -> str:
        """Request password reset."""
        user = await self.db.get_user_by_email(email)
        if not user:
            # Don't reveal if user exists
            return "If the email exists, a reset link has been sent"
        
        # Generate reset token
        reset_token = secrets.token_urlsafe(32)
        user.reset_token = reset_token
        user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
        await self.db.update_user(user)
        
        # TODO: Send email with reset link
        logger.info("password_reset_requested", user_id=user.id)
        
        return reset_token
    
    async def reset_password(self, token: str, new_password: str) -> bool:
        """Reset password using token."""
        user = await self.db.get_user_by_reset_token(token)
        
        if not user:
            raise AuthenticationException("Invalid reset token")
        
        if user.reset_token_expires < datetime.utcnow():
            raise AuthenticationException("Reset token expired")
        
        # Generate new salt and hash password
        salt = secrets.token_hex(16)
        password_hash = pwd_context.hash(new_password + salt)
        
        # Update user
        user.password_hash = password_hash
        user.salt = salt
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
        
        # Get subscription limits
        subscription = user.current_subscription
        search_limit = subscription.search_limit if subscription else 1000
        scrape_limit = subscription.scrape_limit if subscription else 10000
        
        return {
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
            "usage_by_engine": usage.usage_by_engine,
            "usage_by_day": usage.usage_by_day
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


async def get_auth_service(db_service: DatabaseService) -> AuthService:
    """Get or create auth service instance."""
    global _auth_service
    
    if _auth_service is None:
        _auth_service = AuthService(db_service)
    
    return _auth_service
