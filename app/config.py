"""
Application configuration management using Pydantic Settings.
"""
from typing import List, Literal, Optional
from pydantic import BaseSettings, HttpUrl, PostgresDsn, validator
from pydantic_settings import SettingsConfigDict
import os


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application
    app_name: str = "SearchScrape API"
    version: str = "1.0.0"
    debug: bool = False
    environment: Literal["development", "staging", "production"] = "development"
    
    # API Configuration
    api_prefix: str = "/api/v1"
    docs_url: Optional[str] = "/docs"
    openapi_url: Optional[str] = "/openapi.json"
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4
    
    # SearXNG
    searxng_url: HttpUrl = "http://localhost:8080"
    searxng_timeout: int = 10
    searxng_max_retries: int = 3
    searxng_enabled_engines: List[str] = ["google", "bing", "duckduckgo", "startpage", "qwant"]
    
    # Redis
    redis_url: str = "redis://localhost:6379"
    redis_max_connections: int = 20
    cache_default_ttl: int = 3600
    cache_compression: bool = True
    
    # Database
    database_url: PostgresDsn = "postgresql://user:pass@localhost:5432/searchscrape"
    database_pool_size: int = 10
    database_max_overflow: int = 20
    database_pool_timeout: int = 30
    database_echo: bool = False
    
    # Security
    api_key_header: str = "X-API-Key"
    api_keys: List[str] = []  # Load from environment
    allowed_origins: List[str] = ["*"]
    cors_credentials: bool = True
    cors_methods: List[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    cors_headers: List[str] = ["*"]
    
    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_default: str = "1000/hour"
    rate_limit_burst: int = 100
    rate_limit_storage_url: Optional[str] = None  # Uses Redis if None
    
    # Scraping
    scraping_max_concurrent: int = 10
    scraping_timeout: int = 30
    scraping_user_agent: str = "SearchScrape-API/1.0 (+https://github.com/searchscrape)"
    scraping_respect_robots_txt: bool = True
    scraping_min_delay_seconds: float = 0.5
    scraping_max_retries: int = 3
    scraping_javascript_enabled: bool = False
    
    # Content Processing
    content_max_size_mb: int = 10
    content_min_text_length: int = 50
    content_language_detection: bool = True
    content_quality_threshold: float = 0.3
    
    # Monitoring
    enable_metrics: bool = True
    metrics_path: str = "/metrics"
    log_level: str = "INFO"
    log_format: str = "json"
    log_file: Optional[str] = None
    
    # JWT Settings
    secret_key: str = "your-secret-key-change-this-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours
    
    # Stripe Settings
    stripe_secret_key: str = ""
    stripe_publishable_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_id_pro: str = ""  # Will be set after creating products
    
    # Celery
    celery_broker_url: Optional[str] = None  # Uses Redis if None
    celery_result_backend: Optional[str] = None  # Uses Redis if None
    celery_task_time_limit: int = 300
    celery_task_soft_time_limit: int = 240
    celery_worker_concurrency: int = 4
    
    @validator("api_keys", pre=True)
    def parse_api_keys(cls, v):
        """Parse API keys from comma-separated string."""
        if isinstance(v, str):
            return [key.strip() for key in v.split(",") if key.strip()]
        return v or []
    
    @validator("celery_broker_url", pre=True, always=True)
    def set_celery_broker(cls, v, values):
        """Use Redis URL for Celery broker if not specified."""
        return v or values.get("redis_url", "redis://localhost:6379")
    
    @validator("celery_result_backend", pre=True, always=True)
    def set_celery_backend(cls, v, values):
        """Use Redis URL for Celery backend if not specified."""
        return v or values.get("redis_url", "redis://localhost:6379")
    
    @validator("rate_limit_storage_url", pre=True, always=True)
    def set_rate_limit_storage(cls, v, values):
        """Use Redis URL for rate limit storage if not specified."""
        return v or values.get("redis_url", "redis://localhost:6379")
    
    @validator("database_url", pre=True)
    def validate_database_url(cls, v):
        """Ensure database URL is properly formatted."""
        if isinstance(v, str) and not v.startswith(("postgresql://", "postgres://")):
            raise ValueError("Database URL must be a valid PostgreSQL connection string")
        return v
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings."""
    return settings
