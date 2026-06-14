"""
Redis caching service for search results and content.
"""
import json
import gzip
import hashlib
from typing import Optional, Any, Dict, List
from datetime import datetime, timedelta
import redis.asyncio as redis
from redis.asyncio.connection import ConnectionPool
import orjson

from app.config import get_settings
from app.models.responses import UnSearchResponse
from app.models.requests import UnSearchRequest
import structlog

logger = structlog.get_logger(__name__)
settings = get_settings()


class CacheService:
    """Redis-based caching service with compression and multi-layer caching."""
    
    def __init__(self):
        self.redis_url = settings.redis_url
        self.default_ttl = settings.cache_default_ttl
        self.compression_enabled = settings.cache_compression
        self._pool: Optional[ConnectionPool] = None
        self._client: Optional[redis.Redis] = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
        
    async def initialize(self):
        """Initialize Redis connection pool."""
        if not self._client:
            self._pool = ConnectionPool.from_url(
                self.redis_url,
                max_connections=settings.redis_max_connections,
                decode_responses=False  # We'll handle encoding/decoding
            )
            self._client = redis.Redis(connection_pool=self._pool)
            
            # Test connection
            try:
                await self._client.ping()
                logger.info("redis_connection_established")
            except Exception as e:
                logger.error("redis_connection_failed", error=str(e))
                raise
                
    async def close(self):
        """Close Redis connections."""
        if self._client:
            await self._client.close()
            self._client = None
        if self._pool:
            await self._pool.disconnect()
            self._pool = None
            
    async def get_search_results(self, cache_key: str) -> Optional[UnSearchResponse]:
        """
        Retrieve search results from cache.
        
        Args:
            cache_key: Cache key for the search results
            
        Returns:
            Cached UnSearchResponse or None if not found
        """
        if not self._client:
            await self.initialize()
            
        try:
            # Get from cache
            cached_data = await self._client.get(cache_key)
            
            if not cached_data:
                logger.debug("cache_miss", key=cache_key)
                return None
                
            # Decompress if needed
            if self.compression_enabled:
                try:
                    cached_data = gzip.decompress(cached_data)
                except:
                    # Data might not be compressed
                    pass
                    
            # Deserialize
            data = orjson.loads(cached_data)
            
            # Update hit count
            await self._increment_hit_count(cache_key)
            
            # Convert back to response model
            response = UnSearchResponse(**data)
            response.cached = True
            response.cache_key = cache_key
            
            logger.info("cache_hit", key=cache_key)
            return response
            
        except Exception as e:
            logger.error("cache_get_error", key=cache_key, error=str(e))
            return None
            
    async def set_search_results(
        self, 
        cache_key: str, 
        data: UnSearchResponse, 
        ttl: Optional[int] = None
    ):
        """
        Cache search results with optional compression.
        
        Args:
            cache_key: Cache key for the search results
            data: UnSearchResponse to cache
            ttl: Time to live in seconds (uses default if not specified)
        """
        if not self._client:
            await self.initialize()
            
        try:
            # Use provided TTL or default
            ttl = ttl or self.default_ttl
            
            # Serialize data
            serialized = orjson.dumps(data.model_dump(mode="json"))
            
            # Compress if enabled
            if self.compression_enabled:
                original_size = len(serialized)
                serialized = gzip.compress(serialized, compresslevel=6)
                compressed_size = len(serialized)
                compression_ratio = (1 - compressed_size / original_size) * 100
                logger.debug(
                    "cache_compression",
                    original_size=original_size,
                    compressed_size=compressed_size,
                    compression_ratio=f"{compression_ratio:.1f}%"
                )
                
            # Set in Redis with TTL
            await self._client.setex(cache_key, ttl, serialized)
            
            # Store metadata
            await self._store_cache_metadata(cache_key, data, ttl)
            
            logger.info("cache_set", key=cache_key, ttl=ttl)
            
        except Exception as e:
            logger.error("cache_set_error", key=cache_key, error=str(e))
            
    async def invalidate_pattern(self, pattern: str):
        """
        Invalidate cache entries matching a pattern.
        
        Args:
            pattern: Redis pattern (e.g., "search:query:python*")
        """
        if not self._client:
            await self.initialize()
            
        try:
            # Find matching keys
            cursor = 0
            invalidated_count = 0
            
            while True:
                cursor, keys = await self._client.scan(
                    cursor, 
                    match=pattern, 
                    count=100
                )
                
                if keys:
                    # Delete in batch
                    await self._client.delete(*keys)
                    invalidated_count += len(keys)
                    
                if cursor == 0:
                    break
                    
            logger.info(
                "cache_invalidated_pattern",
                pattern=pattern,
                invalidated_count=invalidated_count
            )
            
        except Exception as e:
            logger.error("cache_invalidate_error", pattern=pattern, error=str(e))
            
    def generate_cache_key(self, request: UnSearchRequest) -> str:
        """
        Generate deterministic cache key from request parameters.
        
        Args:
            request: UnSearchRequest object
            
        Returns:
            Cache key string
        """
        # Extract relevant fields for cache key
        key_data = {
            "query": request.query.lower().strip(),
            "engines": sorted(request.engines),
            "max_results": request.max_results,
            "language": request.language,
            "safe_search": request.safe_search,
            "scrape_content": request.scrape_content,
            "include_images": request.include_images,
            "include_links": request.include_links
        }
        
        # Add custom selectors if present
        if request.scrape_selectors:
            key_data["selectors"] = sorted(request.scrape_selectors.items())
            
        # Create deterministic string
        key_string = orjson.dumps(key_data, option=orjson.OPT_SORT_KEYS).decode()
        
        # Generate hash
        hash_digest = hashlib.sha256(key_string.encode()).hexdigest()[:16]
        
        # Create readable key
        query_slug = request.query[:20].replace(' ', '_').lower()
        cache_key = f"search:{query_slug}:{hash_digest}"
        
        return cache_key
        
    async def get_cached_url_content(self, url: str) -> Optional[str]:
        """
        Get cached content for a specific URL.
        
        Args:
            url: URL to check
            
        Returns:
            Cached content or None
        """
        if not self._client:
            await self.initialize()
            
        url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
        cache_key = f"url_content:{url_hash}"
        
        try:
            content = await self._client.get(cache_key)
            if content:
                return content.decode('utf-8')
        except:
            pass
            
        return None
        
    async def set_cached_url_content(
        self, 
        url: str, 
        content: str, 
        ttl: int = 86400  # 24 hours default
    ):
        """
        Cache content for a specific URL.
        
        Args:
            url: URL of the content
            content: Content to cache
            ttl: Time to live in seconds
        """
        if not self._client:
            await self.initialize()
            
        url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
        cache_key = f"url_content:{url_hash}"
        
        try:
            await self._client.setex(cache_key, ttl, content.encode('utf-8'))
        except Exception as e:
            logger.error("url_cache_set_error", url=url, error=str(e))
            
    async def _increment_hit_count(self, cache_key: str):
        """Increment cache hit count for analytics."""
        try:
            hit_key = f"{cache_key}:hits"
            await self._client.incr(hit_key)
        except:
            pass  # Non-critical operation
            
    async def _store_cache_metadata(
        self, 
        cache_key: str, 
        data: UnSearchResponse, 
        ttl: int
    ):
        """Store cache metadata for monitoring and analytics."""
        try:
            metadata = {
                "query": data.search_metadata.query,
                "engines": data.search_metadata.engines_used,
                "results_count": len(data.results),
                "created_at": datetime.utcnow().isoformat(),
                "expires_at": (datetime.utcnow() + timedelta(seconds=ttl)).isoformat(),
                "ttl": ttl
            }
            
            metadata_key = f"{cache_key}:metadata"
            await self._client.setex(
                metadata_key, 
                ttl, 
                orjson.dumps(metadata)
            )
        except:
            pass  # Non-critical operation
            
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring."""
        if not self._client:
            await self.initialize()
            
        try:
            info = await self._client.info()
            
            stats = {
                "connected": True,
                "used_memory": info.get("used_memory_human", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "hit_rate": 0.0
            }
            
            # Calculate hit rate
            total_ops = stats["keyspace_hits"] + stats["keyspace_misses"]
            if total_ops > 0:
                stats["hit_rate"] = (stats["keyspace_hits"] / total_ops) * 100
                
            return stats
            
        except Exception as e:
            logger.error("cache_stats_error", error=str(e))
            return {
                "connected": False,
                "error": str(e)
            }
            
    async def warmup_cache(self, popular_queries: List[str]):
        """
        Warmup cache with popular queries.
        
        Args:
            popular_queries: List of queries to pre-cache
        """
        logger.info("cache_warmup_started", queries_count=len(popular_queries))
        
        # This would typically trigger actual searches
        # Implementation depends on your search service
        
        logger.info("cache_warmup_completed")


# Singleton instance
_cache_service: Optional[CacheService] = None


async def get_cache_service() -> CacheService:
    """Get or create cache service instance."""
    global _cache_service
    
    if _cache_service is None:
        _cache_service = CacheService()
        await _cache_service.initialize()
        
    return _cache_service