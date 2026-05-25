"""
Advanced cache context management system for intelligent caching decisions.

This module provides sophisticated cache management:
- Multiple cache modes (ENABLED, DISABLED, READ_ONLY, WRITE_ONLY, BYPASS)
- URL type detection and caching rules
- Context-aware caching decisions
- Performance optimization and cache statistics
"""

from enum import Enum
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from urllib.parse import urlparse
import time

import structlog

logger = structlog.get_logger(__name__)


class CacheMode(str, Enum):
    """
    Defines the caching behavior for web crawling operations.
    
    Modes:
    - ENABLED: Normal caching behavior (read and write)
    - DISABLED: No caching at all
    - READ_ONLY: Only read from cache, don't write
    - WRITE_ONLY: Only write to cache, don't read
    - BYPASS: Bypass cache for this operation
    """
    ENABLED = "enabled"
    DISABLED = "disabled"
    READ_ONLY = "read_only"
    WRITE_ONLY = "write_only"
    BYPASS = "bypass"


class URLType(str, Enum):
    """URL type classification for caching decisions."""
    WEB_HTTP = "web_http"
    WEB_HTTPS = "web_https"
    LOCAL_FILE = "local_file"
    RAW_HTML = "raw_html"
    DATA_URI = "data_uri"
    FTP = "ftp"
    UNKNOWN = "unknown"


@dataclass
class CacheRule:
    """Rule for cache behavior based on URL patterns or types."""
    pattern: str
    cache_mode: CacheMode
    ttl: Optional[int] = None  # Time to live in seconds
    priority: int = 0  # Higher priority rules override lower priority
    
    def matches(self, url: str, url_type: URLType) -> bool:
        """Check if this rule matches the given URL."""
        if self.pattern == "*":
            return True
        elif self.pattern.startswith("type:"):
            return url_type.value == self.pattern[5:]
        elif self.pattern.startswith("domain:"):
            try:
                parsed = urlparse(url)
                domain = parsed.netloc.lower()
                pattern_domain = self.pattern[7:].lower()
                return domain == pattern_domain or domain.endswith("." + pattern_domain)
            except Exception:
                return False
        elif self.pattern in url:
            return True
        else:
            return False


@dataclass
class CacheStats:
    """Statistics for cache operations."""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    cache_writes: int = 0
    cache_bypasses: int = 0
    total_time_saved: float = 0.0  # Time saved by cache hits in seconds
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.cache_hits / self.total_requests) * 100
    
    @property
    def miss_rate(self) -> float:
        """Calculate cache miss rate percentage."""
        return 100.0 - self.hit_rate
    
    @property
    def bypass_rate(self) -> float:
        """Calculate cache bypass rate percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.cache_bypasses / self.total_requests) * 100


class CacheContext:
    """
    Encapsulates cache-related decisions and URL handling.
    
    This class centralizes all cache-related logic and URL type checking,
    making the caching behavior more predictable and maintainable.
    """
    
    def __init__(self, 
                 url: str, 
                 cache_mode: CacheMode = CacheMode.ENABLED,
                 always_bypass: bool = False,
                 custom_rules: List[CacheRule] = None,
                 default_ttl: Optional[int] = None):
        """
        Initialize the CacheContext with the provided URL and cache mode.
        
        Args:
            url: The URL being processed
            cache_mode: The cache mode for the current operation
            always_bypass: If True, bypasses caching for this operation
            custom_rules: Additional cache rules to apply
            default_ttl: Default time-to-live for cache entries
        """
        self.url = url
        self.cache_mode = cache_mode
        self.always_bypass = always_bypass
        self.custom_rules = custom_rules or []
        self.default_ttl = default_ttl
        
        # URL analysis
        self.url_type = self._classify_url(url)
        self.is_cacheable = self._determine_cacheability()
        self.parsed_url = self._safe_parse_url(url)
        
        # Display formatting
        self._url_display = self._format_display_url()
        
        # Apply custom rules
        self._effective_cache_mode = self._apply_cache_rules()
        
        # Performance tracking
        self._start_time = time.time()
        self._cache_hit = False
    
    def _classify_url(self, url: str) -> URLType:
        """Classify URL type for caching decisions."""
        if url.startswith("https://"):
            return URLType.WEB_HTTPS
        elif url.startswith("http://"):
            return URLType.WEB_HTTP
        elif url.startswith("file://"):
            return URLType.LOCAL_FILE
        elif url.startswith("raw:"):
            return URLType.RAW_HTML
        elif url.startswith("data:"):
            return URLType.DATA_URI
        elif url.startswith("ftp://"):
            return URLType.FTP
        else:
            return URLType.UNKNOWN
    
    def _determine_cacheability(self) -> bool:
        """Determine if URL is cacheable based on type and content."""
        # Web URLs are generally cacheable
        if self.url_type in [URLType.WEB_HTTP, URLType.WEB_HTTPS]:
            return True
        
        # Local files can be cached
        if self.url_type == URLType.LOCAL_FILE:
            return True
        
        # Raw HTML and data URIs are not typically cached
        if self.url_type in [URLType.RAW_HTML, URLType.DATA_URI]:
            return False
        
        # FTP and unknown types - conservative approach
        return False
    
    def _safe_parse_url(self, url: str):
        """Safely parse URL, handling malformed URLs gracefully."""
        try:
            return urlparse(url)
        except Exception:
            return None
    
    def _format_display_url(self) -> str:
        """Format URL for display purposes."""
        if self.url_type == URLType.RAW_HTML:
            return "Raw HTML Content"
        elif self.url_type == URLType.DATA_URI:
            return "Data URI"
        elif len(self.url) > 100:
            return self.url[:97] + "..."
        else:
            return self.url
    
    def _apply_cache_rules(self) -> CacheMode:
        """Apply custom cache rules to determine effective cache mode."""
        if not self.custom_rules:
            return self.cache_mode
        
        # Find matching rules, sorted by priority
        matching_rules = [
            rule for rule in self.custom_rules 
            if rule.matches(self.url, self.url_type)
        ]
        
        if not matching_rules:
            return self.cache_mode
        
        # Apply highest priority rule
        highest_priority_rule = max(matching_rules, key=lambda r: r.priority)
        return highest_priority_rule.cache_mode
    
    def should_read(self) -> bool:
        """
        Determine if cache should be read based on context.
        
        Returns:
            bool: True if cache should be read, False otherwise
        """
        if self.always_bypass or not self.is_cacheable:
            return False
        
        return self._effective_cache_mode in [CacheMode.ENABLED, CacheMode.READ_ONLY]
    
    def should_write(self) -> bool:
        """
        Determine if cache should be written based on context.
        
        Returns:
            bool: True if cache should be written, False otherwise
        """
        if self.always_bypass or not self.is_cacheable:
            return False
        
        return self._effective_cache_mode in [CacheMode.ENABLED, CacheMode.WRITE_ONLY]
    
    def get_cache_key(self) -> str:
        """Generate cache key for this URL and context."""
        # Include URL and relevant parameters in cache key
        base_key = f"url:{self.url}"
        
        # Add URL type to key for better organization
        base_key += f":type:{self.url_type.value}"
        
        return base_key
    
    def get_ttl(self) -> Optional[int]:
        """Get time-to-live for cache entry."""
        # Check if any custom rules specify TTL
        for rule in self.custom_rules:
            if rule.matches(self.url, self.url_type) and rule.ttl is not None:
                return rule.ttl
        
        # Use default TTL
        return self.default_ttl
    
    def mark_cache_hit(self):
        """Mark this request as a cache hit."""
        self._cache_hit = True
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for this cache operation."""
        elapsed_time = time.time() - self._start_time
        
        return {
            'url': self.url,
            'url_type': self.url_type.value,
            'cache_mode': self._effective_cache_mode.value,
            'cache_hit': self._cache_hit,
            'cacheable': self.is_cacheable,
            'elapsed_time': elapsed_time,
            'should_read': self.should_read(),
            'should_write': self.should_write()
        }
    
    @property
    def display_url(self) -> str:
        """Returns the URL in display format."""
        return self._url_display
    
    @property
    def domain(self) -> Optional[str]:
        """Get domain from URL."""
        if self.parsed_url:
            return self.parsed_url.netloc.lower()
        return None
    
    @property
    def scheme(self) -> Optional[str]:
        """Get URL scheme."""
        if self.parsed_url:
            return self.parsed_url.scheme.lower()
        return None


class CacheContextManager:
    """
    Manager for cache contexts with global rules and statistics.
    
    Provides centralized management of cache rules and performance tracking.
    """
    
    def __init__(self):
        """Initialize cache context manager."""
        self.global_rules: List[CacheRule] = []
        self.stats = CacheStats()
        self.domain_stats: Dict[str, CacheStats] = {}
        
        # Default rules
        self._setup_default_rules()
    
    def _setup_default_rules(self):
        """Setup default cache rules."""
        # Web URLs should be cached
        self.global_rules.append(
            CacheRule("type:web_http", CacheMode.ENABLED, ttl=3600, priority=1)
        )
        self.global_rules.append(
            CacheRule("type:web_https", CacheMode.ENABLED, ttl=3600, priority=1)
        )
        
        # Raw HTML should not be cached
        self.global_rules.append(
            CacheRule("type:raw_html", CacheMode.DISABLED, priority=2)
        )
        
        # Data URIs should not be cached
        self.global_rules.append(
            CacheRule("type:data_uri", CacheMode.DISABLED, priority=2)
        )
        
        # Local files can be cached with shorter TTL
        self.global_rules.append(
            CacheRule("type:local_file", CacheMode.ENABLED, ttl=1800, priority=1)
        )
    
    def add_rule(self, rule: CacheRule):
        """Add a global cache rule."""
        self.global_rules.append(rule)
        # Sort rules by priority
        self.global_rules.sort(key=lambda r: r.priority, reverse=True)
    
    def remove_rule(self, pattern: str):
        """Remove cache rule by pattern."""
        self.global_rules = [r for r in self.global_rules if r.pattern != pattern]
    
    def create_context(self, 
                      url: str, 
                      cache_mode: CacheMode = CacheMode.ENABLED,
                      **kwargs) -> CacheContext:
        """
        Create cache context with global rules applied.
        
        Args:
            url: URL to create context for
            cache_mode: Base cache mode
            **kwargs: Additional context parameters
            
        Returns:
            CacheContext with global rules applied
        """
        # Combine custom rules with global rules
        custom_rules = kwargs.get('custom_rules', [])
        all_rules = self.global_rules + custom_rules
        kwargs['custom_rules'] = all_rules
        
        context = CacheContext(url, cache_mode, **kwargs)
        
        # Update statistics
        self.stats.total_requests += 1
        
        # Track domain-specific stats
        if context.domain:
            if context.domain not in self.domain_stats:
                self.domain_stats[context.domain] = CacheStats()
            self.domain_stats[context.domain].total_requests += 1
        
        return context
    
    def record_cache_hit(self, context: CacheContext, time_saved: float = 0.0):
        """Record a cache hit."""
        context.mark_cache_hit()
        self.stats.cache_hits += 1
        self.stats.total_time_saved += time_saved
        
        if context.domain and context.domain in self.domain_stats:
            self.domain_stats[context.domain].cache_hits += 1
    
    def record_cache_miss(self, context: CacheContext):
        """Record a cache miss."""
        self.stats.cache_misses += 1
        
        if context.domain and context.domain in self.domain_stats:
            self.domain_stats[context.domain].cache_misses += 1
    
    def record_cache_write(self, context: CacheContext):
        """Record a cache write."""
        self.stats.cache_writes += 1
        
        if context.domain and context.domain in self.domain_stats:
            self.domain_stats[context.domain].cache_writes += 1
    
    def record_cache_bypass(self, context: CacheContext):
        """Record a cache bypass."""
        self.stats.cache_bypasses += 1
        
        if context.domain and context.domain in self.domain_stats:
            self.domain_stats[context.domain].cache_bypasses += 1
    
    def get_global_stats(self) -> CacheStats:
        """Get global cache statistics."""
        return self.stats
    
    def get_domain_stats(self, domain: str) -> Optional[CacheStats]:
        """Get cache statistics for specific domain."""
        return self.domain_stats.get(domain)
    
    def get_top_domains(self, limit: int = 10) -> List[tuple]:
        """Get top domains by request count."""
        domain_counts = [
            (domain, stats.total_requests) 
            for domain, stats in self.domain_stats.items()
        ]
        domain_counts.sort(key=lambda x: x[1], reverse=True)
        return domain_counts[:limit]
    
    def reset_stats(self):
        """Reset all statistics."""
        self.stats = CacheStats()
        self.domain_stats.clear()
    
    def export_rules(self) -> List[Dict[str, Any]]:
        """Export cache rules to dictionary format."""
        return [
            {
                'pattern': rule.pattern,
                'cache_mode': rule.cache_mode.value,
                'ttl': rule.ttl,
                'priority': rule.priority
            }
            for rule in self.global_rules
        ]
    
    def import_rules(self, rules_data: List[Dict[str, Any]]):
        """Import cache rules from dictionary format."""
        self.global_rules.clear()
        
        for rule_data in rules_data:
            rule = CacheRule(
                pattern=rule_data['pattern'],
                cache_mode=CacheMode(rule_data['cache_mode']),
                ttl=rule_data.get('ttl'),
                priority=rule_data.get('priority', 0)
            )
            self.global_rules.append(rule)
        
        # Sort by priority
        self.global_rules.sort(key=lambda r: r.priority, reverse=True)


# Singleton instance for global cache management
_cache_manager: Optional[CacheContextManager] = None


def get_cache_manager() -> CacheContextManager:
    """Get singleton cache context manager."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheContextManager()
    return _cache_manager


# Legacy compatibility functions
def _legacy_to_cache_mode(disable_cache: bool = False,
                         bypass_cache: bool = False,
                         no_cache_read: bool = False,
                         no_cache_write: bool = False) -> CacheMode:
    """Convert legacy cache parameters to CacheMode."""
    if disable_cache:
        return CacheMode.DISABLED
    elif bypass_cache:
        return CacheMode.BYPASS
    elif no_cache_read and no_cache_write:
        return CacheMode.DISABLED
    elif no_cache_read:
        return CacheMode.WRITE_ONLY
    elif no_cache_write:
        return CacheMode.READ_ONLY
    else:
        return CacheMode.ENABLED


# Convenience functions
def create_cache_context(url: str, **legacy_params) -> CacheContext:
    """
    Create cache context with legacy parameter support.
    
    Args:
        url: URL to create context for
        **legacy_params: Legacy cache parameters for backward compatibility
        
    Returns:
        CacheContext instance
    """
    # Extract cache mode from legacy parameters
    cache_mode = _legacy_to_cache_mode(
        disable_cache=legacy_params.get('disable_cache', False),
        bypass_cache=legacy_params.get('bypass_cache', False),
        no_cache_read=legacy_params.get('no_cache_read', False),
        no_cache_write=legacy_params.get('no_cache_write', False)
    )
    
    # Use cache manager for consistency
    manager = get_cache_manager()
    return manager.create_context(url, cache_mode)


def should_cache_url(url: str) -> bool:
    """Quick check if URL should be cached."""
    context = create_cache_context(url)
    return context.should_read() or context.should_write()
