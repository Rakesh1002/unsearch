"""
Advanced database management system with connection pooling, migrations, and caching.

This module provides comprehensive database management:
- Async connection pooling with SQLite and PostgreSQL support
- Migration system with version management
- Content hashing and deduplication
- Structured logging and error handling
- Performance optimization with batch operations
"""

import os
import asyncio
import time
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import aiosqlite
import structlog

from app.models.requests import UnSearchRequest, ScrapingConfig

logger = structlog.get_logger(__name__)


@dataclass
class CrawlRecord:
    """Record for crawled content storage."""
    url: str
    content_hash: str
    content: str
    metadata: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    success: bool = True
    error: Optional[str] = None
    response_code: Optional[int] = None
    content_type: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            'url': self.url,
            'content_hash': self.content_hash,
            'content': self.content,
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat(),
            'success': self.success,
            'error': self.error,
            'response_code': self.response_code,
            'content_type': self.content_type
        }


@dataclass
class DatabaseStats:
    """Database performance and usage statistics."""
    total_records: int = 0
    successful_crawls: int = 0
    failed_crawls: int = 0
    unique_domains: int = 0
    avg_content_size: float = 0.0
    last_cleanup: Optional[datetime] = None
    cache_hit_rate: float = 0.0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_records == 0:
            return 0.0
        return (self.successful_crawls / self.total_records) * 100


class DatabaseManager:
    """
    Advanced database manager with connection pooling and performance optimization.
    
    Features:
    - Async connection pooling
    - Content deduplication with hashing
    - Migration system
    - Performance metrics
    - Configurable retention policies
    """
    
    def __init__(self, 
                 db_path: Optional[str] = None,
                 pool_size: int = 10,
                 max_retries: int = 3,
                 retention_days: int = 30):
        """
        Initialize database manager.
        
        Args:
            db_path: Database file path (defaults to ~/.unsearch/crawl_data.db)
            pool_size: Maximum number of connections in pool
            max_retries: Maximum retry attempts for failed operations
            retention_days: Days to retain crawl data
        """
        # Database configuration
        if db_path:
            self.db_path = Path(db_path)
        else:
            base_dir = Path.home() / '.unsearch'
            base_dir.mkdir(exist_ok=True)
            self.db_path = base_dir / 'crawl_data.db'
        
        self.pool_size = pool_size
        self.max_retries = max_retries
        self.retention_days = retention_days
        
        # Connection management
        self.connection_pool: List[aiosqlite.Connection] = []
        self.pool_lock = asyncio.Lock()
        self.init_lock = asyncio.Lock()
        self.connection_semaphore = asyncio.Semaphore(pool_size)
        self._initialized = False
        
        # Performance tracking
        self._stats = DatabaseStats()
        self._cache_hits = 0
        self._cache_misses = 0
        
        # Schema version for migrations
        self.schema_version = 1
    
    async def initialize(self):
        """Initialize database and connection pool."""
        async with self.init_lock:
            if self._initialized:
                return
            
            logger.info(f"Initializing database at {self.db_path}")
            
            # Ensure database directory exists
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create schema
            await self._create_schema()
            
            # Run migrations if needed
            await self._run_migrations()
            
            # Initialize connection pool
            await self._initialize_pool()
            
            # Update stats
            await self._update_stats()
            
            self._initialized = True
            logger.success("Database initialization completed")
    
    async def _create_schema(self):
        """Create database schema."""
        schema_sql = """
        CREATE TABLE IF NOT EXISTS crawl_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            content_hash TEXT NOT NULL UNIQUE,
            content TEXT NOT NULL,
            metadata TEXT DEFAULT '{}',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            success BOOLEAN DEFAULT TRUE,
            error TEXT NULL,
            response_code INTEGER NULL,
            content_type TEXT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_url ON crawl_data(url);
        CREATE INDEX IF NOT EXISTS idx_content_hash ON crawl_data(content_hash);
        CREATE INDEX IF NOT EXISTS idx_timestamp ON crawl_data(timestamp);
        CREATE INDEX IF NOT EXISTS idx_success ON crawl_data(success);
        
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS crawl_stats (
            id INTEGER PRIMARY KEY,
            key TEXT UNIQUE NOT NULL,
            value TEXT NOT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.executescript(schema_sql)
            await conn.commit()
    
    async def _run_migrations(self):
        """Run database migrations."""
        async with aiosqlite.connect(self.db_path) as conn:
            # Check current version
            cursor = await conn.execute("SELECT MAX(version) FROM schema_version")
            result = await cursor.fetchone()
            current_version = result[0] if result[0] else 0
            
            # Apply migrations if needed
            if current_version < self.schema_version:
                logger.info(f"Applying migrations from version {current_version} to {self.schema_version}")
                
                # Example migration (add new columns, indexes, etc.)
                if current_version < 1:
                    await conn.execute("""
                        ALTER TABLE crawl_data 
                        ADD COLUMN content_length INTEGER DEFAULT 0
                    """)
                
                # Update schema version
                await conn.execute(
                    "INSERT OR REPLACE INTO schema_version (version) VALUES (?)",
                    (self.schema_version,)
                )
                await conn.commit()
                
                logger.success(f"Migration to version {self.schema_version} completed")
    
    async def _initialize_pool(self):
        """Initialize connection pool."""
        async with self.pool_lock:
            for _ in range(self.pool_size):
                conn = await aiosqlite.connect(self.db_path)
                # Enable WAL mode for better concurrent access
                await conn.execute("PRAGMA journal_mode=WAL")
                await conn.execute("PRAGMA synchronous=NORMAL")
                await conn.execute("PRAGMA cache_size=10000")
                await conn.execute("PRAGMA temp_store=memory")
                self.connection_pool.append(conn)
    
    @asynccontextmanager
    async def get_connection(self):
        """Get connection from pool."""
        if not self._initialized:
            await self.initialize()
        
        async with self.connection_semaphore:
            async with self.pool_lock:
                if self.connection_pool:
                    conn = self.connection_pool.pop()
                else:
                    # Create new connection if pool is empty
                    conn = await aiosqlite.connect(self.db_path)
            
            try:
                yield conn
            finally:
                async with self.pool_lock:
                    if len(self.connection_pool) < self.pool_size:
                        self.connection_pool.append(conn)
                    else:
                        await conn.close()
    
    def _generate_content_hash(self, content: str, url: str) -> str:
        """Generate content hash for deduplication."""
        # Combine URL and content for hash
        combined = f"{url}:{content}"
        return hashlib.sha256(combined.encode()).hexdigest()[:16]
    
    async def store_crawl_result(self, 
                                url: str, 
                                content: str,
                                metadata: Dict[str, Any] = None,
                                success: bool = True,
                                error: Optional[str] = None,
                                response_code: Optional[int] = None,
                                content_type: Optional[str] = None) -> str:
        """
        Store crawl result in database.
        
        Args:
            url: The crawled URL
            content: The extracted content
            metadata: Additional metadata
            success: Whether the crawl was successful
            error: Error message if failed
            response_code: HTTP response code
            content_type: Content type header
            
        Returns:
            Content hash of the stored record
        """
        if not self._initialized:
            await self.initialize()
        
        content_hash = self._generate_content_hash(content, url)
        metadata = metadata or {}
        
        record = CrawlRecord(
            url=url,
            content_hash=content_hash,
            content=content,
            metadata=metadata,
            success=success,
            error=error,
            response_code=response_code,
            content_type=content_type
        )
        
        for attempt in range(self.max_retries):
            try:
                async with self.get_connection() as conn:
                    await conn.execute("""
                        INSERT OR REPLACE INTO crawl_data 
                        (url, content_hash, content, metadata, success, error, response_code, content_type)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        record.url,
                        record.content_hash,
                        record.content,
                        str(record.metadata),
                        record.success,
                        record.error,
                        record.response_code,
                        record.content_type
                    ))
                    await conn.commit()
                
                logger.debug(f"Stored crawl result for {url} with hash {content_hash}")
                return content_hash
                
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed to store crawl result: {str(e)}")
                if attempt == self.max_retries - 1:
                    logger.error(f"Failed to store crawl result after {self.max_retries} attempts: {str(e)}")
                    raise
                await asyncio.sleep(0.1 * (attempt + 1))
    
    async def get_crawl_result(self, 
                              url: str = None, 
                              content_hash: str = None) -> Optional[CrawlRecord]:
        """
        Retrieve crawl result by URL or content hash.
        
        Args:
            url: URL to search for
            content_hash: Content hash to search for
            
        Returns:
            CrawlRecord if found, None otherwise
        """
        if not self._initialized:
            await self.initialize()
        
        if not url and not content_hash:
            raise ValueError("Either url or content_hash must be provided")
        
        try:
            async with self.get_connection() as conn:
                if content_hash:
                    cursor = await conn.execute(
                        "SELECT * FROM crawl_data WHERE content_hash = ? ORDER BY timestamp DESC LIMIT 1",
                        (content_hash,)
                    )
                    self._cache_hits += 1
                else:
                    cursor = await conn.execute(
                        "SELECT * FROM crawl_data WHERE url = ? ORDER BY timestamp DESC LIMIT 1",
                        (url,)
                    )
                    self._cache_misses += 1
                
                row = await cursor.fetchone()
                if row:
                    return CrawlRecord(
                        url=row[1],
                        content_hash=row[2],
                        content=row[3],
                        metadata=eval(row[4]) if row[4] else {},
                        timestamp=datetime.fromisoformat(row[5]),
                        success=bool(row[6]),
                        error=row[7],
                        response_code=row[8],
                        content_type=row[9]
                    )
                
                return None
                
        except Exception as e:
            logger.error(f"Failed to retrieve crawl result: {str(e)}")
            return None
    
    async def search_crawl_results(self, 
                                  query: str,
                                  limit: int = 100,
                                  offset: int = 0) -> List[CrawlRecord]:
        """
        Search crawl results by content or URL.
        
        Args:
            query: Search query
            limit: Maximum results to return
            offset: Offset for pagination
            
        Returns:
            List of matching CrawlRecord objects
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            async with self.get_connection() as conn:
                cursor = await conn.execute("""
                    SELECT * FROM crawl_data 
                    WHERE url LIKE ? OR content LIKE ?
                    ORDER BY timestamp DESC
                    LIMIT ? OFFSET ?
                """, (f"%{query}%", f"%{query}%", limit, offset))
                
                rows = await cursor.fetchall()
                results = []
                
                for row in rows:
                    results.append(CrawlRecord(
                        url=row[1],
                        content_hash=row[2],
                        content=row[3],
                        metadata=eval(row[4]) if row[4] else {},
                        timestamp=datetime.fromisoformat(row[5]),
                        success=bool(row[6]),
                        error=row[7],
                        response_code=row[8],
                        content_type=row[9]
                    ))
                
                return results
                
        except Exception as e:
            logger.error(f"Failed to search crawl results: {str(e)}")
            return []
    
    async def cleanup_old_records(self, days: Optional[int] = None) -> int:
        """
        Clean up old crawl records.
        
        Args:
            days: Number of days to retain (defaults to self.retention_days)
            
        Returns:
            Number of records deleted
        """
        if not self._initialized:
            await self.initialize()
        
        days = days or self.retention_days
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        try:
            async with self.get_connection() as conn:
                cursor = await conn.execute(
                    "DELETE FROM crawl_data WHERE timestamp < ?",
                    (cutoff_date.isoformat(),)
                )
                await conn.commit()
                
                deleted_count = cursor.rowcount
                logger.info(f"Cleaned up {deleted_count} records older than {days} days")
                
                # Update stats
                await self._update_stats()
                
                return deleted_count
                
        except Exception as e:
            logger.error(f"Failed to cleanup old records: {str(e)}")
            return 0
    
    async def _update_stats(self):
        """Update database statistics."""
        try:
            async with self.get_connection() as conn:
                # Total records
                cursor = await conn.execute("SELECT COUNT(*) FROM crawl_data")
                self._stats.total_records = (await cursor.fetchone())[0]
                
                # Successful crawls
                cursor = await conn.execute("SELECT COUNT(*) FROM crawl_data WHERE success = 1")
                self._stats.successful_crawls = (await cursor.fetchone())[0]
                
                # Failed crawls
                self._stats.failed_crawls = self._stats.total_records - self._stats.successful_crawls
                
                # Unique domains
                cursor = await conn.execute("""
                    SELECT COUNT(DISTINCT 
                        CASE 
                            WHEN url LIKE 'http%' THEN 
                                substr(url, instr(url, '://') + 3, instr(substr(url, instr(url, '://') + 3), '/') - 1)
                            ELSE url 
                        END
                    ) FROM crawl_data
                """)
                self._stats.unique_domains = (await cursor.fetchone())[0]
                
                # Average content size
                cursor = await conn.execute("SELECT AVG(LENGTH(content)) FROM crawl_data")
                result = await cursor.fetchone()
                self._stats.avg_content_size = result[0] if result[0] else 0.0
                
                # Cache hit rate
                total_requests = self._cache_hits + self._cache_misses
                if total_requests > 0:
                    self._stats.cache_hit_rate = (self._cache_hits / total_requests) * 100
                
                self._stats.last_cleanup = datetime.utcnow()
                
        except Exception as e:
            logger.error(f"Failed to update stats: {str(e)}")
    
    async def get_stats(self) -> DatabaseStats:
        """Get current database statistics."""
        if not self._initialized:
            await self.initialize()
        
        await self._update_stats()
        return self._stats
    
    async def get_domain_stats(self, limit: int = 10) -> List[Tuple[str, int]]:
        """
        Get statistics by domain.
        
        Args:
            limit: Number of top domains to return
            
        Returns:
            List of (domain, count) tuples
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            async with self.get_connection() as conn:
                cursor = await conn.execute("""
                    SELECT 
                        CASE 
                            WHEN url LIKE 'http%' THEN 
                                substr(url, instr(url, '://') + 3, instr(substr(url, instr(url, '://') + 3), '/') - 1)
                            ELSE url 
                        END as domain,
                        COUNT(*) as count
                    FROM crawl_data 
                    GROUP BY domain 
                    ORDER BY count DESC 
                    LIMIT ?
                """, (limit,))
                
                return await cursor.fetchall()
                
        except Exception as e:
            logger.error(f"Failed to get domain stats: {str(e)}")
            return []
    
    async def export_data(self, output_path: str, format: str = 'json') -> bool:
        """
        Export crawl data to file.
        
        Args:
            output_path: Output file path
            format: Export format ('json', 'csv')
            
        Returns:
            True if export successful
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            async with self.get_connection() as conn:
                cursor = await conn.execute("SELECT * FROM crawl_data ORDER BY timestamp DESC")
                rows = await cursor.fetchall()
                
                if format.lower() == 'json':
                    import json
                    data = []
                    for row in rows:
                        record = {
                            'id': row[0],
                            'url': row[1],
                            'content_hash': row[2],
                            'content': row[3],
                            'metadata': row[4],
                            'timestamp': row[5],
                            'success': bool(row[6]),
                            'error': row[7],
                            'response_code': row[8],
                            'content_type': row[9]
                        }
                        data.append(record)
                    
                    with open(output_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                
                elif format.lower() == 'csv':
                    import csv
                    with open(output_path, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        writer.writerow(['id', 'url', 'content_hash', 'content', 'metadata', 
                                       'timestamp', 'success', 'error', 'response_code', 'content_type'])
                        writer.writerows(rows)
                
                logger.success(f"Exported {len(rows)} records to {output_path}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to export data: {str(e)}")
            return False
    
    async def close(self):
        """Close all connections and cleanup."""
        async with self.pool_lock:
            for conn in self.connection_pool:
                await conn.close()
            self.connection_pool.clear()
        
        logger.info("Database manager closed")


# Singleton instance
_db_manager: Optional[DatabaseManager] = None


def get_database_manager(**kwargs) -> DatabaseManager:
    """Get singleton database manager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager(**kwargs)
    return _db_manager


# Convenience functions
async def store_crawl_data(url: str, content: str, **kwargs) -> str:
    """Store crawl data using global database manager."""
    db_manager = get_database_manager()
    return await db_manager.store_crawl_result(url, content, **kwargs)


async def get_cached_content(url: str) -> Optional[str]:
    """Get cached content by URL."""
    db_manager = get_database_manager()
    record = await db_manager.get_crawl_result(url=url)
    return record.content if record and record.success else None


async def search_content(query: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Search crawled content."""
    db_manager = get_database_manager()
    records = await db_manager.search_crawl_results(query, limit)
    return [record.to_dict() for record in records]
