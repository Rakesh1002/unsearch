"""
Custom exceptions for the UnQuest API.
"""
from typing import Optional, Dict, Any
from fastapi import HTTPException, status


class UnQuestException(Exception):
    """Base exception for UnQuest API."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class SearXNGException(UnQuestException):
    """Exception related to SearXNG operations."""
    pass


class ScrapingException(UnQuestException):
    """Exception related to content scraping."""
    pass


class CacheException(UnQuestException):
    """Exception related to cache operations."""
    pass


class DatabaseException(UnQuestException):
    """Exception related to database operations."""
    pass


class RateLimitException(UnQuestException):
    """Exception for rate limiting violations."""
    pass


class AuthenticationException(UnQuestException):
    """Exception for authentication failures."""
    pass


class ValidationException(UnQuestException):
    """Exception for request validation failures."""
    pass


# HTTP Exception classes with proper status codes
class UnQuestHTTPException(HTTPException):
    """Base HTTP exception with structured error response."""
    
    def __init__(
        self,
        status_code: int,
        error_code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ):
        self.error_code = error_code
        self.details = details or {}
        
        detail = {
            "error": error_code,
            "message": message,
            "details": self.details
        }
        
        super().__init__(status_code=status_code, detail=detail, headers=headers)


class BadRequestException(UnQuestHTTPException):
    """400 Bad Request."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="BadRequest",
            message=message,
            details=details
        )


class UnauthorizedException(UnQuestHTTPException):
    """401 Unauthorized."""
    
    def __init__(self, message: str = "Authentication required", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="Unauthorized",
            message=message,
            details=details,
            headers={"WWW-Authenticate": "Bearer"}
        )


class ForbiddenException(UnQuestHTTPException):
    """403 Forbidden."""
    
    def __init__(self, message: str = "Access forbidden", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="Forbidden",
            message=message,
            details=details
        )


class NotFoundException(UnQuestHTTPException):
    """404 Not Found."""
    
    def __init__(self, message: str = "Resource not found", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="NotFound",
            message=message,
            details=details
        )


class TooManyRequestsException(UnQuestHTTPException):
    """429 Too Many Requests."""
    
    def __init__(
        self, 
        message: str = "Rate limit exceeded", 
        details: Optional[Dict[str, Any]] = None,
        retry_after: Optional[int] = None
    ):
        headers = {}
        if retry_after:
            headers["Retry-After"] = str(retry_after)
            
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="TooManyRequests",
            message=message,
            details=details,
            headers=headers
        )


class InternalServerErrorException(UnQuestHTTPException):
    """500 Internal Server Error."""
    
    def __init__(self, message: str = "Internal server error", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="InternalServerError",
            message=message,
            details=details
        )


class ServiceUnavailableException(UnQuestHTTPException):
    """503 Service Unavailable."""
    
    def __init__(
        self, 
        message: str = "Service temporarily unavailable", 
        details: Optional[Dict[str, Any]] = None,
        retry_after: Optional[int] = None
    ):
        headers = {}
        if retry_after:
            headers["Retry-After"] = str(retry_after)
            
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="ServiceUnavailable",
            message=message,
            details=details,
            headers=headers
        )


class GatewayTimeoutException(UnQuestHTTPException):
    """504 Gateway Timeout."""
    
    def __init__(self, message: str = "Request timeout", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            error_code="GatewayTimeout",
            message=message,
            details=details
        )
