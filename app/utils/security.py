"""
Security utilities for the SearchScrape API.
"""
import hashlib
import hmac
import secrets
import time
from typing import Optional, Dict, Any
import re
from urllib.parse import urlparse, urljoin
import ipaddress
from fastapi import Request


def generate_api_key(length: int = 32) -> str:
    """
    Generate a secure API key.
    
    Args:
        length: Length of the API key
        
    Returns:
        Generated API key
    """
    return secrets.token_urlsafe(length)


def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    """
    Hash a password with salt.
    
    Args:
        password: Password to hash
        salt: Optional salt (generated if not provided)
        
    Returns:
        Tuple of (hashed_password, salt)
    """
    if salt is None:
        salt = secrets.token_hex(16)
    
    # Use PBKDF2 with SHA-256
    hashed = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return hashed.hex(), salt


def verify_password(password: str, hashed_password: str, salt: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        password: Password to verify
        hashed_password: Hashed password
        salt: Salt used for hashing
        
    Returns:
        True if password is correct
    """
    computed_hash, _ = hash_password(password, salt)
    return hmac.compare_digest(computed_hash, hashed_password)


def sanitize_input(text: str, max_length: int = 1000) -> str:
    """
    Sanitize user input to prevent XSS and injection attacks.
    
    Args:
        text: Input text to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized text
    """
    if not text:
        return ""
    
    # Truncate to max length
    text = text[:max_length]
    
    # Remove potentially dangerous characters
    text = re.sub(r'[<>"\']', '', text)
    
    # Remove SQL injection patterns
    sql_patterns = [
        r'(\bUNION\b)', r'(\bSELECT\b)', r'(\bINSERT\b)', r'(\bUPDATE\b)',
        r'(\bDELETE\b)', r'(\bDROP\b)', r'(\bCREATE\b)', r'(\bALTER\b)',
        r'(\bEXEC\b)', r'(\bEXECUTE\b)', r'(--)', r'(/\*)', r'(\*/)', 
        r'(\bSCRIPT\b)', r'(\bJAVASCRIPT\b)', r'(\bVBSCRIPT\b)'
    ]
    
    for pattern in sql_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    
    return text.strip()


def is_safe_url(url: str, allowed_hosts: Optional[list] = None) -> bool:
    """
    Check if a URL is safe for redirection or webhooks.
    
    Args:
        url: URL to validate
        allowed_hosts: Optional list of allowed hostnames
        
    Returns:
        True if URL is safe
    """
    try:
        parsed = urlparse(url)
        
        # Must have scheme and netloc
        if not parsed.scheme or not parsed.netloc:
            return False
        
        # Only allow HTTP/HTTPS
        if parsed.scheme not in ['http', 'https']:
            return False
        
        # Check for localhost/private IPs
        hostname = parsed.hostname
        if hostname:
            try:
                ip = ipaddress.ip_address(hostname)
                if ip.is_private or ip.is_loopback or ip.is_reserved:
                    return False
            except ValueError:
                # Not an IP address, check hostname
                if hostname.lower() in ['localhost', '127.0.0.1', '::1']:
                    return False
        
        # Check allowed hosts if specified
        if allowed_hosts and hostname not in allowed_hosts:
            return False
            
        return True
        
    except Exception:
        return False


def generate_csrf_token() -> str:
    """Generate a CSRF token."""
    return secrets.token_urlsafe(32)


def verify_csrf_token(token: str, expected_token: str) -> bool:
    """Verify a CSRF token."""
    return hmac.compare_digest(token, expected_token)


def rate_limit_key(request: Request, identifier: Optional[str] = None) -> str:
    """
    Generate a rate limiting key for a request.
    
    Args:
        request: FastAPI request object
        identifier: Optional identifier (API key, user ID, etc.)
        
    Returns:
        Rate limiting key
    """
    if identifier:
        return f"rate_limit:{identifier}"
    
    # Use client IP as fallback
    client_ip = request.client.host if request.client else "unknown"
    return f"rate_limit:ip:{client_ip}"


def mask_sensitive_data(data: Dict[str, Any], sensitive_keys: Optional[list] = None) -> Dict[str, Any]:
    """
    Mask sensitive data in a dictionary for logging.
    
    Args:
        data: Dictionary to mask
        sensitive_keys: List of keys to mask
        
    Returns:
        Dictionary with masked sensitive data
    """
    if sensitive_keys is None:
        sensitive_keys = [
            'password', 'api_key', 'token', 'secret', 'auth', 'authorization',
            'x-api-key', 'cookie', 'session', 'private', 'credential'
        ]
    
    masked_data = {}
    
    for key, value in data.items():
        key_lower = key.lower()
        
        if any(sensitive in key_lower for sensitive in sensitive_keys):
            if isinstance(value, str) and len(value) > 8:
                masked_data[key] = value[:4] + "****" + value[-4:]
            else:
                masked_data[key] = "****"
        elif isinstance(value, dict):
            masked_data[key] = mask_sensitive_data(value, sensitive_keys)
        else:
            masked_data[key] = value
    
    return masked_data


def generate_request_id() -> str:
    """Generate a unique request ID."""
    timestamp = str(int(time.time() * 1000))
    random_part = secrets.token_hex(8)
    return f"req_{timestamp}_{random_part}"


def validate_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """
    Validate webhook signature using HMAC-SHA256.
    
    Args:
        payload: Raw webhook payload
        signature: Signature to verify
        secret: Secret key
        
    Returns:
        True if signature is valid
    """
    expected_signature = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(f"sha256={expected_signature}", signature)


def extract_client_info(request: Request) -> Dict[str, Any]:
    """
    Extract client information from request for security logging.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Dictionary with client information
    """
    headers = dict(request.headers)
    
    return {
        "ip": request.client.host if request.client else None,
        "user_agent": headers.get("user-agent"),
        "referer": headers.get("referer"),
        "origin": headers.get("origin"),
        "x_forwarded_for": headers.get("x-forwarded-for"),
        "x_real_ip": headers.get("x-real-ip"),
        "cf_connecting_ip": headers.get("cf-connecting-ip"),  # Cloudflare
        "x_forwarded_proto": headers.get("x-forwarded-proto"),
        "accept_language": headers.get("accept-language"),
        "accept_encoding": headers.get("accept-encoding"),
    }


def is_suspicious_request(request: Request) -> bool:
    """
    Check if a request looks suspicious.
    
    Args:
        request: FastAPI request object
        
    Returns:
        True if request is suspicious
    """
    user_agent = request.headers.get("user-agent", "").lower()
    
    # Common bot/scanner signatures
    suspicious_agents = [
        'sqlmap', 'nikto', 'nmap', 'masscan', 'zap', 'burp',
        'acunetix', 'nessus', 'openvas', 'w3af', 'dirb',
        'gobuster', 'dirbuster', 'wfuzz', 'ffuf'
    ]
    
    if any(agent in user_agent for agent in suspicious_agents):
        return True
    
    # Check for suspicious paths
    path = request.url.path.lower()
    suspicious_paths = [
        'admin', 'phpmyadmin', 'wp-admin', 'config', 'backup',
        'shell', 'cmd', 'eval', 'exec', 'system', 'passwd'
    ]
    
    if any(path in suspicious_paths for path in suspicious_paths):
        return True
    
    return False


class SecurityHeaders:
    """Security headers for HTTP responses."""
    
    @staticmethod
    def get_headers() -> Dict[str, str]:
        """Get security headers."""
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
            "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'",
        }
