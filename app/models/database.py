"""
SQLAlchemy database models.
"""
from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, JSON, Text, Index, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import uuid

Base = declarative_base()


class APIKey(Base):
    """API key management."""
    __tablename__ = "api_keys"
    
    id = Column(Integer, primary_key=True)
    key = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used_at = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True)
    rate_limit_override = Column(String(50))  # e.g., "5000/hour"
    metadata = Column(JSON, default={})
    
    # Relationships
    requests = relationship("SearchRequest", back_populates="api_key")
    
    __table_args__ = (
        Index("idx_api_keys_active", "is_active"),
    )


class SearchRequest(Base):
    """Search request logging and analytics."""
    __tablename__ = "search_requests"
    
    id = Column(Integer, primary_key=True)
    request_id = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    api_key_id = Column(Integer, ForeignKey("api_keys.id"))
    query = Column(Text, nullable=False)
    engines = Column(JSON, nullable=False)
    max_results = Column(Integer, nullable=False)
    language = Column(String(2))
    safe_search = Column(String(10))
    
    # Performance metrics
    search_time_ms = Column(Integer)
    scraping_time_ms = Column(Integer)
    total_time_ms = Column(Integer)
    results_count = Column(Integer)
    scraped_count = Column(Integer)
    
    # Cache info
    cache_hit = Column(Boolean, default=False)
    cache_key = Column(String(64))
    
    # Request metadata
    client_ip = Column(String(45))  # IPv6 support
    user_agent = Column(Text)
    request_headers = Column(JSON)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    
    # Relationships
    api_key = relationship("APIKey", back_populates="requests")
    results = relationship("SearchResult", back_populates="request", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_search_requests_created", "created_at"),
        Index("idx_search_requests_query", "query"),
        Index("idx_search_requests_cache_key", "cache_key"),
    )


class SearchResult(Base):
    """Individual search result storage."""
    __tablename__ = "search_results"
    
    id = Column(Integer, primary_key=True)
    request_id = Column(Integer, ForeignKey("search_requests.id"), nullable=False)
    rank = Column(Integer, nullable=False)
    title = Column(Text, nullable=False)
    url = Column(Text, nullable=False)
    snippet = Column(Text)
    engine = Column(String(50), nullable=False)
    score = Column(Float)
    
    # Scraping results
    scraped_successfully = Column(Boolean, default=False)
    scraped_content = Column(JSON)  # Compressed JSON of ScrapedContent
    scraping_error = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    request = relationship("SearchRequest", back_populates="results")
    
    __table_args__ = (
        Index("idx_search_results_request", "request_id"),
        Index("idx_search_results_url", "url"),
    )


class ScrapingJob(Base):
    """Async scraping job tracking."""
    __tablename__ = "scraping_jobs"
    
    id = Column(Integer, primary_key=True)
    job_id = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    task_id = Column(String(255))  # Celery task ID
    urls = Column(JSON, nullable=False)
    config = Column(JSON, nullable=False)
    status = Column(String(20), nullable=False, default="pending")  # pending, processing, completed, failed
    
    # Results
    results = Column(JSON)
    error_message = Column(Text)
    
    # Webhook
    webhook_url = Column(Text)
    webhook_attempts = Column(Integer, default=0)
    webhook_last_attempt = Column(DateTime(timezone=True))
    webhook_success = Column(Boolean)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    
    __table_args__ = (
        Index("idx_scraping_jobs_status", "status"),
        Index("idx_scraping_jobs_created", "created_at"),
    )


class CacheEntry(Base):
    """Cache metadata for analytics."""
    __tablename__ = "cache_entries"
    
    id = Column(Integer, primary_key=True)
    cache_key = Column(String(64), unique=True, nullable=False)
    query_hash = Column(String(64), nullable=False)
    size_bytes = Column(Integer)
    hit_count = Column(Integer, default=0)
    ttl_seconds = Column(Integer)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_accessed_at = Column(DateTime(timezone=True))
    expires_at = Column(DateTime(timezone=True))
    
    __table_args__ = (
        Index("idx_cache_entries_key", "cache_key"),
        Index("idx_cache_entries_expires", "expires_at"),
    )


class ErrorLog(Base):
    """Error logging for debugging."""
    __tablename__ = "error_logs"
    
    id = Column(Integer, primary_key=True)
    request_id = Column(String(36))
    error_type = Column(String(100), nullable=False)
    error_message = Column(Text, nullable=False)
    error_details = Column(JSON)
    stack_trace = Column(Text)
    
    # Context
    endpoint = Column(String(255))
    method = Column(String(10))
    status_code = Column(Integer)
    client_ip = Column(String(45))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index("idx_error_logs_created", "created_at"),
        Index("idx_error_logs_type", "error_type"),
        Index("idx_error_logs_request", "request_id"),
    )
