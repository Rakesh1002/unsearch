"""
Website change tracking service inspired by Firecrawl.

Provides comprehensive change monitoring capabilities:
- Content comparison and diff generation
- Change detection algorithms
- Historical data storage
- Notification systems
- Advanced diff visualization
"""

import asyncio
import time
import hashlib
import json
import difflib
from typing import Dict, List, Optional, Any, Union, Literal
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import structlog

from app.config import get_settings
from app.models.responses import ScrapedContent, ContentMetadata
from app.services.scraping.enhanced_scraping import get_enhanced_scraping_service
from app.services.core.database import get_database_service

logger = structlog.get_logger(__name__)
settings = get_settings()


class ChangeStatus(Enum):
    """Status of content changes."""
    NEW = "new"
    SAME = "same" 
    CHANGED = "changed"
    REMOVED = "removed"


class VisibilityStatus(Enum):
    """Visibility status of content."""
    VISIBLE = "visible"
    HIDDEN = "hidden"


@dataclass
class ContentChange:
    """Represents a change in content."""
    change_type: str  # "add", "delete", "modify"
    content: str
    line_number: Optional[int] = None
    position: Optional[int] = None
    normal: bool = True


@dataclass
class DiffChunk:
    """A chunk of diff information."""
    content: str
    changes: List[ContentChange]


@dataclass
class DiffFile:
    """File-level diff information."""
    from_version: Optional[str] = None
    to_version: Optional[str] = None
    chunks: List[DiffChunk] = field(default_factory=list)


@dataclass
class ContentDiff:
    """Comprehensive diff result."""
    text_diff: str
    json_diff: Dict[str, Any]


@dataclass
class ChangeTrackingData:
    """Complete change tracking information."""
    previous_scrape_at: Optional[datetime] = None
    change_status: ChangeStatus = ChangeStatus.NEW
    visibility: VisibilityStatus = VisibilityStatus.VISIBLE
    diff: Optional[ContentDiff] = None
    previous_content_hash: Optional[str] = None
    current_content_hash: Optional[str] = None
    change_percentage: float = 0.0
    significant_changes: List[str] = field(default_factory=list)


@dataclass
class ChangeTrackingConfig:
    """Configuration for change tracking."""
    enabled: bool = True
    tag: Optional[str] = None  # Tag for grouping tracked content
    threshold: float = 0.05  # Minimum change percentage to trigger notification
    compare_text: bool = True
    compare_html: bool = True
    compare_metadata: bool = True
    store_history: bool = True
    max_history_entries: int = 100
    notification_webhook: Optional[str] = None
    diff_format: Literal["text", "html", "json"] = "text"


@dataclass
class TrackedContent:
    """Stored content for tracking."""
    url: str
    content_hash: str
    content_data: Dict[str, Any]  # Serialized content
    scraped_at: datetime
    tag: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChangeTrackingResult:
    """Result of change tracking operation."""
    url: str
    tracking_data: ChangeTrackingData
    scraped_content: ScrapedContent
    processing_time_ms: int
    success: bool
    error: Optional[str] = None


class ContentHasher:
    """Handles content hashing for change detection."""
    
    @staticmethod
    def hash_content(content: str) -> str:
        """Generate hash of content."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    @staticmethod
    def hash_scraped_content(scraped_content: ScrapedContent) -> str:
        """Generate hash of scraped content."""
        # Combine relevant fields for hashing
        content_parts = [
            scraped_content.text or "",
            scraped_content.html or "",
            scraped_content.title or "",
            json.dumps(scraped_content.metadata.dict() if scraped_content.metadata else {}, sort_keys=True)
        ]
        
        combined_content = "\n---SEPARATOR---\n".join(content_parts)
        return ContentHasher.hash_content(combined_content)
    
    @staticmethod
    def hash_specific_fields(data: Dict[str, Any], fields: List[str]) -> str:
        """Hash specific fields of data."""
        field_data = {field: data.get(field, "") for field in fields}
        content = json.dumps(field_data, sort_keys=True)
        return ContentHasher.hash_content(content)


class ContentDiffer:
    """Generates diffs between content versions."""
    
    def generate_text_diff(self, old_text: str, new_text: str) -> str:
        """Generate text-based diff."""
        old_lines = old_text.splitlines(keepends=True)
        new_lines = new_text.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            old_lines, 
            new_lines, 
            fromfile='previous', 
            tofile='current',
            lineterm=''
        )
        
        return ''.join(diff)
    
    def generate_html_diff(self, old_text: str, new_text: str) -> str:
        """Generate HTML-based diff."""
        differ = difflib.HtmlDiff()
        return differ.make_file(
            old_text.splitlines(),
            new_text.splitlines(),
            fromdesc='Previous Version',
            todesc='Current Version'
        )
    
    def generate_json_diff(self, old_content: Dict[str, Any], new_content: Dict[str, Any]) -> Dict[str, Any]:
        """Generate JSON-based structural diff."""
        files = []
        
        # Compare text content
        if old_content.get("text") != new_content.get("text"):
            text_changes = self._analyze_text_changes(
                old_content.get("text", ""),
                new_content.get("text", "")
            )
            
            files.append({
                "from": "text",
                "to": "text",
                "chunks": text_changes
            })
        
        # Compare HTML content
        if old_content.get("html") != new_content.get("html"):
            html_changes = self._analyze_text_changes(
                old_content.get("html", ""),
                new_content.get("html", "")
            )
            
            files.append({
                "from": "html", 
                "to": "html",
                "chunks": html_changes
            })
        
        return {"files": files}
    
    def _analyze_text_changes(self, old_text: str, new_text: str) -> List[Dict[str, Any]]:
        """Analyze changes between two text versions."""
        changes = []
        
        # Use difflib to get detailed changes
        old_lines = old_text.splitlines()
        new_lines = new_text.splitlines()
        
        matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                continue
            
            chunk_changes = []
            
            if tag == 'delete':
                for line_num in range(i1, i2):
                    chunk_changes.append({
                        "type": "delete",
                        "ln": line_num + 1,
                        "content": old_lines[line_num] if line_num < len(old_lines) else "",
                        "normal": False
                    })
            
            elif tag == 'insert':
                for line_num in range(j1, j2):
                    chunk_changes.append({
                        "type": "add",
                        "ln": line_num + 1,
                        "content": new_lines[line_num] if line_num < len(new_lines) else "",
                        "normal": False
                    })
            
            elif tag == 'replace':
                # Handle replacements
                for line_num in range(i1, i2):
                    chunk_changes.append({
                        "type": "delete",
                        "ln1": line_num + 1,
                        "content": old_lines[line_num] if line_num < len(old_lines) else "",
                        "normal": False
                    })
                
                for line_num in range(j1, j2):
                    chunk_changes.append({
                        "type": "add",
                        "ln2": line_num + 1,
                        "content": new_lines[line_num] if line_num < len(new_lines) else "",
                        "normal": False
                    })
            
            if chunk_changes:
                changes.append({
                    "content": f"Lines {i1+1}-{i2} / {j1+1}-{j2}",
                    "changes": chunk_changes
                })
        
        return changes
    
    def calculate_change_percentage(self, old_content: str, new_content: str) -> float:
        """Calculate percentage of content that changed."""
        if not old_content and not new_content:
            return 0.0
        
        if not old_content:
            return 100.0
        
        if not new_content:
            return 100.0
        
        # Use difflib to calculate similarity
        similarity = difflib.SequenceMatcher(None, old_content, new_content).ratio()
        return (1 - similarity) * 100


class ChangeTrackingService:
    """
    Website change tracking service.
    
    Provides comprehensive change monitoring including:
    - Content comparison and diff generation
    - Historical data storage
    - Change notifications
    - Advanced analytics
    """
    
    def __init__(self):
        """Initialize change tracking service."""
        self.content_hasher = ContentHasher()
        self.content_differ = ContentDiffer()
        self.tracked_content_cache: Dict[str, TrackedContent] = {}
        self.tracking_stats = {
            "total_tracked": 0,
            "changes_detected": 0,
            "notifications_sent": 0
        }
    
    async def track_content_changes(
        self, 
        url: str, 
        config: Optional[ChangeTrackingConfig] = None
    ) -> ChangeTrackingResult:
        """
        Track changes for a specific URL.
        
        Args:
            url: URL to track
            config: Change tracking configuration
            
        Returns:
            ChangeTrackingResult with change information
        """
        start_time = time.time()
        config = config or ChangeTrackingConfig()
        
        self.tracking_stats["total_tracked"] += 1
        
        logger.info("change_tracking_started", url=url, tag=config.tag)
        
        try:
            # Scrape current content
            scraping_service = await get_enhanced_scraping_service()
            current_results = await scraping_service.scrape_urls_enhanced([url])
            
            if not current_results or not current_results[0].extraction_success:
                raise ValueError("Failed to scrape current content")
            
            current_content = current_results[0]
            
            # Get previous content
            previous_content = await self._get_previous_content(url, config.tag)
            
            # Generate content hash
            current_hash = self.content_hasher.hash_scraped_content(current_content)
            
            # Determine change status
            if previous_content is None:
                change_status = ChangeStatus.NEW
                change_tracking_data = ChangeTrackingData(
                    change_status=change_status,
                    current_content_hash=current_hash
                )
            else:
                change_status = (
                    ChangeStatus.SAME if previous_content.content_hash == current_hash
                    else ChangeStatus.CHANGED
                )
                
                # Generate diff if content changed
                diff = None
                change_percentage = 0.0
                significant_changes = []
                
                if change_status == ChangeStatus.CHANGED:
                    diff = await self._generate_content_diff(
                        previous_content, current_content, config
                    )
                    
                    change_percentage = self.content_differ.calculate_change_percentage(
                        previous_content.content_data.get("text", ""),
                        current_content.text or ""
                    )
                    
                    significant_changes = self._detect_significant_changes(
                        previous_content, current_content
                    )
                    
                    self.tracking_stats["changes_detected"] += 1
                
                change_tracking_data = ChangeTrackingData(
                    previous_scrape_at=previous_content.scraped_at,
                    change_status=change_status,
                    diff=diff,
                    previous_content_hash=previous_content.content_hash,
                    current_content_hash=current_hash,
                    change_percentage=change_percentage,
                    significant_changes=significant_changes
                )
            
            # Store current content for future tracking
            if config.store_history:
                await self._store_content(url, current_content, config)
            
            # Send notifications if needed
            if (change_status == ChangeStatus.CHANGED and 
                config.notification_webhook and 
                change_tracking_data.change_percentage >= config.threshold):
                
                await self._send_change_notification(
                    url, change_tracking_data, config
                )
                self.tracking_stats["notifications_sent"] += 1
            
            # Add change tracking data to scraped content
            current_content_dict = current_content.dict()
            current_content_dict["changeTracking"] = {
                "previousScrapeAt": change_tracking_data.previous_scrape_at.isoformat() if change_tracking_data.previous_scrape_at else None,
                "changeStatus": change_tracking_data.change_status.value,
                "visibility": change_tracking_data.visibility.value,
                "diff": {
                    "text": change_tracking_data.diff.text_diff if change_tracking_data.diff else "",
                    "json": change_tracking_data.diff.json_diff if change_tracking_data.diff else {}
                } if change_tracking_data.diff else None
            }
            
            enhanced_content = ScrapedContent(**current_content_dict)
            
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            result = ChangeTrackingResult(
                url=url,
                tracking_data=change_tracking_data,
                scraped_content=enhanced_content,
                processing_time_ms=processing_time_ms,
                success=True
            )
            
            logger.info("change_tracking_completed",
                       url=url,
                       change_status=change_status.value,
                       change_percentage=change_tracking_data.change_percentage,
                       processing_time_ms=processing_time_ms)
            
            return result
            
        except Exception as e:
            processing_time_ms = int((time.time() - start_time) * 1000)
            error_msg = str(e)
            
            logger.error("change_tracking_failed", 
                        url=url, 
                        error=error_msg,
                        processing_time_ms=processing_time_ms)
            
            return ChangeTrackingResult(
                url=url,
                tracking_data=ChangeTrackingData(),
                scraped_content=ScrapedContent(url=url, extraction_success=False, text=""),
                processing_time_ms=processing_time_ms,
                success=False,
                error=error_msg
            )
    
    async def _get_previous_content(
        self, 
        url: str, 
        tag: Optional[str] = None
    ) -> Optional[TrackedContent]:
        """Retrieve previously stored content for URL."""
        try:
            # Check cache first
            cache_key = f"{url}:{tag or 'default'}"
            if cache_key in self.tracked_content_cache:
                return self.tracked_content_cache[cache_key]
            
            # In a real implementation, this would query the database
            # For now, return None (indicating no previous content)
            return None
            
        except Exception as e:
            logger.error("get_previous_content_failed", url=url, error=str(e))
            return None
    
    async def _store_content(
        self, 
        url: str, 
        content: ScrapedContent, 
        config: ChangeTrackingConfig
    ):
        """Store content for future change tracking."""
        try:
            content_hash = self.content_hasher.hash_scraped_content(content)
            
            tracked_content = TrackedContent(
                url=url,
                content_hash=content_hash,
                content_data={
                    "text": content.text,
                    "html": content.html,
                    "title": content.title,
                    "metadata": content.metadata.dict() if content.metadata else {}
                },
                scraped_at=datetime.utcnow(),
                tag=config.tag,
                metadata={
                    "word_count": content.word_count,
                    "language": content.language_detected,
                    "quality_score": content.content_quality_score
                }
            )
            
            # Store in cache
            cache_key = f"{url}:{config.tag or 'default'}"
            self.tracked_content_cache[cache_key] = tracked_content
            
            # In a real implementation, this would store in database
            logger.debug("content_stored", url=url, tag=config.tag, content_hash=content_hash[:8])
            
        except Exception as e:
            logger.error("store_content_failed", url=url, error=str(e))
    
    async def _generate_content_diff(
        self, 
        previous_content: TrackedContent,
        current_content: ScrapedContent,
        config: ChangeTrackingConfig
    ) -> ContentDiff:
        """Generate comprehensive diff between content versions."""
        try:
            old_data = previous_content.content_data
            new_data = {
                "text": current_content.text or "",
                "html": current_content.html or "", 
                "title": current_content.title or "",
                "metadata": current_content.metadata.dict() if current_content.metadata else {}
            }
            
            # Generate text diff
            text_diff = ""
            if config.compare_text:
                text_diff = self.content_differ.generate_text_diff(
                    old_data.get("text", ""),
                    new_data.get("text", "")
                )
            
            # Generate JSON diff
            json_diff = {}
            if config.diff_format == "json":
                json_diff = self.content_differ.generate_json_diff(old_data, new_data)
            
            return ContentDiff(
                text_diff=text_diff,
                json_diff=json_diff
            )
            
        except Exception as e:
            logger.error("generate_diff_failed", error=str(e))
            return ContentDiff(text_diff="", json_diff={})
    
    def _detect_significant_changes(
        self, 
        previous_content: TrackedContent,
        current_content: ScrapedContent
    ) -> List[str]:
        """Detect significant changes between content versions."""
        changes = []
        
        old_data = previous_content.content_data
        
        # Check title changes
        if old_data.get("title") != current_content.title:
            changes.append("title_changed")
        
        # Check significant text changes (more than 20% change)
        old_text = old_data.get("text", "")
        new_text = current_content.text or ""
        
        if old_text and new_text:
            change_pct = self.content_differ.calculate_change_percentage(old_text, new_text)
            if change_pct > 20:
                changes.append(f"major_text_change_{change_pct:.1f}%")
            elif change_pct > 5:
                changes.append(f"minor_text_change_{change_pct:.1f}%")
        
        # Check word count changes
        old_word_count = len(old_text.split()) if old_text else 0
        new_word_count = current_content.word_count or 0
        
        if abs(old_word_count - new_word_count) > max(10, old_word_count * 0.1):
            changes.append("word_count_change")
        
        return changes
    
    async def _send_change_notification(
        self, 
        url: str, 
        tracking_data: ChangeTrackingData,
        config: ChangeTrackingConfig
    ):
        """Send webhook notification about changes."""
        try:
            if not config.notification_webhook:
                return
            
            notification_data = {
                "url": url,
                "timestamp": datetime.utcnow().isoformat(),
                "change_status": tracking_data.change_status.value,
                "change_percentage": tracking_data.change_percentage,
                "significant_changes": tracking_data.significant_changes,
                "tag": config.tag,
                "previous_scrape": tracking_data.previous_scrape_at.isoformat() if tracking_data.previous_scrape_at else None
            }
            
            # Send webhook (simplified implementation)
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    config.notification_webhook,
                    json=notification_data,
                    timeout=10
                )
                
                if response.status_code == 200:
                    logger.info("change_notification_sent", url=url, webhook=config.notification_webhook)
                else:
                    logger.warning("change_notification_failed", 
                                 url=url, 
                                 status_code=response.status_code)
                
        except Exception as e:
            logger.error("send_notification_failed", url=url, error=str(e))
    
    async def get_change_history(
        self, 
        url: str, 
        tag: Optional[str] = None,
        limit: int = 10
    ) -> List[TrackedContent]:
        """Get change history for a URL."""
        try:
            # In a real implementation, this would query the database
            # For now, return cached content if available
            cache_key = f"{url}:{tag or 'default'}"
            if cache_key in self.tracked_content_cache:
                return [self.tracked_content_cache[cache_key]]
            
            return []
            
        except Exception as e:
            logger.error("get_change_history_failed", url=url, error=str(e))
            return []
    
    async def get_tracking_stats(self) -> Dict[str, Any]:
        """Get change tracking statistics."""
        return {
            "tracking_stats": self.tracking_stats,
            "cached_content": len(self.tracked_content_cache),
            "change_detection_rate": (
                self.tracking_stats["changes_detected"] /
                max(1, self.tracking_stats["total_tracked"])
            ) if self.tracking_stats["total_tracked"] > 0 else 0,
            "notification_rate": (
                self.tracking_stats["notifications_sent"] /
                max(1, self.tracking_stats["changes_detected"])
            ) if self.tracking_stats["changes_detected"] > 0 else 0
        }


# Singleton service
_change_tracking_service: Optional[ChangeTrackingService] = None


async def get_change_tracking_service() -> ChangeTrackingService:
    """Get or create change tracking service instance."""
    global _change_tracking_service
    
    if _change_tracking_service is None:
        _change_tracking_service = ChangeTrackingService()
    
    return _change_tracking_service


# Convenience function
async def track_url_changes(
    url: str,
    tag: Optional[str] = None,
    threshold: float = 0.05,
    webhook_url: Optional[str] = None
) -> ChangeTrackingResult:
    """
    Convenience function for tracking URL changes.
    
    Args:
        url: URL to track
        tag: Optional tag for grouping
        threshold: Minimum change percentage to trigger notification
        webhook_url: Optional webhook for notifications
        
    Returns:
        ChangeTrackingResult with tracking information
    """
    service = await get_change_tracking_service()
    
    config = ChangeTrackingConfig(
        tag=tag,
        threshold=threshold,
        notification_webhook=webhook_url
    )
    
    return await service.track_content_changes(url, config)
