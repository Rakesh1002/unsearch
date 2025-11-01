"""
Application configuration management using Pydantic Settings.
"""
from typing import List, Literal, Optional
from pydantic import HttpUrl, PostgresDsn, field_validator, ValidationInfo
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict
import os


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application
    app_name: str = "UnSearch API"
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
    
    # Upstash Redis (cloud Redis service)
    upstash_redis_rest_url: Optional[str] = None
    upstash_redis_rest_token: Optional[str] = None
    
    # Database
    database_url: PostgresDsn = "postgresql://user:pass@localhost:5432/database"
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
    scraping_user_agent: str = "UnSearch-API/1.0 (+https://github.com/UnSearch)"
    scraping_respect_robots_txt: bool = True
    scraping_min_delay_seconds: float = 0.5
    scraping_max_retries: int = 3
    scraping_javascript_enabled: bool = False
    # Puppeteer JS rendering service
    puppeteer_enabled: bool = True
    puppeteer_service_url: Optional[HttpUrl] = "http://localhost:9223"
    puppeteer_timeout: int = 30
    puppeteer_default_wait_until: str = "networkidle0"
    
    # Advanced Features Configuration
    # Fire Engine service for advanced scraping
    fire_engine_url: Optional[str] = None
    fire_engine_timeout: int = 60
    
    # Multi-provider search API keys
    serper_api_key: Optional[str] = None
    searchapi_key: Optional[str] = None
    
    # LLM Configuration
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4"
    openai_max_tokens: int = 4096
    
    # Batch Operations
    batch_max_concurrent_jobs: int = 5
    batch_max_workers: int = 10
    batch_job_timeout: int = 3600  # 1 hour
    
    # Playwright service for advanced rendering  
    playwright_service_url: Optional[str] = None
    playwright_timeout: int = 60
    
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
    
    @field_validator("api_keys", mode="before")
    def parse_api_keys(cls, v):
        """Parse API keys from comma-separated string."""
        if isinstance(v, str):
            return [key.strip() for key in v.split(",") if key.strip()]
        return v or []
    
    @field_validator("searxng_enabled_engines", "allowed_origins", "cors_methods", "cors_headers", mode="before")
    def parse_list_fields(cls, v):
        """Parse list fields from comma-separated strings."""
        if isinstance(v, str):
            if not v.strip():  # Handle empty strings
                return []
            return [item.strip() for item in v.split(",") if item.strip()]
        return v or []
    
    @field_validator("celery_broker_url", mode="before")
    def set_celery_broker(cls, v, info: ValidationInfo):
        """Use Redis URL for Celery broker if not specified."""
        if v:
            return v
        # Get redis_url from the data being validated
        data = info.data if info.data else {}
        return data.get("redis_url", "redis://localhost:6379")
    
    @field_validator("celery_result_backend", mode="before")
    def set_celery_backend(cls, v, info: ValidationInfo):
        """Use Redis URL for Celery backend if not specified."""
        if v:
            return v
        # Get redis_url from the data being validated
        data = info.data if info.data else {}
        return data.get("redis_url", "redis://localhost:6379")
    
    @field_validator("rate_limit_storage_url", mode="before")
    def set_rate_limit_storage(cls, v, info: ValidationInfo):
        """Use Redis URL for rate limit storage if not specified."""
        if v:
            return v
        # Get redis_url from the data being validated
        data = info.data if info.data else {}
        return data.get("redis_url", "redis://localhost:6379")
    
    @field_validator("database_url", mode="before")
    def validate_database_url(cls, v):
        """Ensure database URL is properly formatted."""
        if isinstance(v, str) and not v.startswith(("postgresql://", "postgres://")):
            raise ValueError("Database URL must be a valid PostgreSQL connection string")
        return v
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_parse_none_str="None"  # Handle None values properly
    )


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings."""
    return settings
