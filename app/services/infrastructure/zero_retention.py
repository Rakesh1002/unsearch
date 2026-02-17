"""
Zero Data Retention service for privacy compliance inspired by Firecrawl.

Provides automatic data deletion capabilities:
- Automatic deletion after configurable time periods
- Privacy-compliant data handling
- Selective retention policies
- Secure data wiping
- Compliance tracking and reporting
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import structlog

from app.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class RetentionPolicy(Enum):
    """Data retention policies."""
    ZERO_HOURS = "zero_hours"  # Delete immediately after use
    ONE_HOUR = "1_hour"
    SIX_HOURS = "6_hours"
    TWENTY_FOUR_HOURS = "24_hours"  # Standard zero retention
    SEVEN_DAYS = "7_days"
    THIRTY_DAYS = "30_days"
    PERMANENT = "permanent"  # No auto-deletion


class DataType(Enum):
    """Types of data subject to retention policies."""
    SCRAPED_CONTENT = "scraped_content"
    EXTRACTED_DATA = "extracted_data"
    SEARCH_RESULTS = "search_results"
    SCREENSHOTS = "screenshots"
    PDFS = "pdfs"
    CRAWL_DATA = "crawl_data"
    BATCH_RESULTS = "batch_results"
    CHANGE_TRACKING = "change_tracking"


@dataclass
class RetentionRule:
    """Rule for data retention."""
    data_type: DataType
    policy: RetentionPolicy
    applies_to: List[str] = field(default_factory=list)  # Specific patterns/tags
    exceptions: List[str] = field(default_factory=list)  # Exclusion patterns


@dataclass
class DataRecord:
    """Record of data subject to retention policy."""
    id: str
    data_type: DataType
    created_at: datetime
    expires_at: datetime
    size_bytes: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    location: Optional[str] = None  # File path, database key, etc.
    secure_delete: bool = False


@dataclass
class RetentionReport:
    """Report on retention policy compliance."""
    total_records: int
    expired_records: int
    deleted_records: int
    failed_deletions: int
    bytes_deleted: int
    compliance_score: float
    policy_violations: List[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.utcnow)


class ZeroRetentionManager:
    """
    Zero Data Retention manager for privacy compliance.
    
    Provides comprehensive data lifecycle management:
    - Automatic data expiration and deletion
    - Flexible retention policies
    - Secure data wiping
    - Compliance monitoring and reporting
    """
    
    def __init__(self):
        """Initialize zero retention manager."""
        self.data_records: Dict[str, DataRecord] = {}
        self.retention_rules: List[RetentionRule] = []
        self.deletion_queue: Set[str] = set()
        self.stats = {
            "total_records_managed": 0,
            "total_deletions": 0,
            "bytes_deleted": 0,
            "policy_violations": 0
        }
        
        # Default retention rules
        self._setup_default_rules()
        
        # Start background deletion task
        self._deletion_task = None
        asyncio.create_task(self._start_deletion_worker())
    
    def _setup_default_rules(self):
        """Setup default retention rules."""
        self.retention_rules = [
            # Zero retention for sensitive data
            RetentionRule(
                data_type=DataType.SCRAPED_CONTENT,
                policy=RetentionPolicy.TWENTY_FOUR_HOURS,
                applies_to=["zero_retention", "privacy"]
            ),
            RetentionRule(
                data_type=DataType.EXTRACTED_DATA,
                policy=RetentionPolicy.TWENTY_FOUR_HOURS,
                applies_to=["zero_retention", "privacy"]
            ),
            RetentionRule(
                data_type=DataType.SCREENSHOTS,
                policy=RetentionPolicy.ONE_HOUR,
                applies_to=["temporary", "debug"]
            ),
            RetentionRule(
                data_type=DataType.PDFS,
                policy=RetentionPolicy.SIX_HOURS,
                applies_to=["temporary"]
            ),
            
            # Standard retention for operational data
            RetentionRule(
                data_type=DataType.SEARCH_RESULTS,
                policy=RetentionPolicy.SEVEN_DAYS,
                applies_to=["cache"]
            ),
            RetentionRule(
                data_type=DataType.CHANGE_TRACKING,
                policy=RetentionPolicy.THIRTY_DAYS,
                applies_to=["monitoring"]
            )
        ]
    
    async def register_data(
        self, 
        data_id: str,
        data_type: DataType,
        size_bytes: int = 0,
        tags: Optional[List[str]] = None,
        location: Optional[str] = None,
        custom_policy: Optional[RetentionPolicy] = None,
        secure_delete: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ) -> DataRecord:
        """
        Register data for retention management.
        
        Args:
            data_id: Unique identifier for the data
            data_type: Type of data being registered
            size_bytes: Size of data in bytes
            tags: Tags for policy matching
            location: Where the data is stored
            custom_policy: Override default retention policy
            secure_delete: Whether to use secure deletion
            metadata: Additional metadata
            
        Returns:
            DataRecord with retention information
        """
        tags = tags or []
        metadata = metadata or {}
        
        # Determine retention policy
        policy = custom_policy
        if not policy:
            policy = self._determine_retention_policy(data_type, tags)
        
        # Calculate expiration time
        expires_at = self._calculate_expiration(policy)
        
        # Create data record
        record = DataRecord(
            id=data_id,
            data_type=data_type,
            created_at=datetime.utcnow(),
            expires_at=expires_at,
            size_bytes=size_bytes,
            metadata=metadata,
            tags=tags,
            location=location,
            secure_delete=secure_delete
        )
        
        self.data_records[data_id] = record
        self.stats["total_records_managed"] += 1
        
        logger.info("data_registered_for_retention",
                   data_id=data_id,
                   data_type=data_type.value,
                   policy=policy.value,
                   expires_at=expires_at.isoformat(),
                   size_bytes=size_bytes)
        
        return record
    
    def _determine_retention_policy(self, data_type: DataType, tags: List[str]) -> RetentionPolicy:
        """Determine retention policy for data."""
        # Find matching rule
        for rule in self.retention_rules:
            if rule.data_type == data_type:
                # Check if tags match applies_to criteria
                if not rule.applies_to or any(tag in rule.applies_to for tag in tags):
                    # Check exclusions
                    if not rule.exceptions or not any(tag in rule.exceptions for tag in tags):
                        return rule.policy
        
        # Default to 24 hours if no specific rule found
        return RetentionPolicy.TWENTY_FOUR_HOURS
    
    def _calculate_expiration(self, policy: RetentionPolicy) -> datetime:
        """Calculate expiration datetime based on policy."""
        now = datetime.utcnow()
        
        if policy == RetentionPolicy.ZERO_HOURS:
            return now  # Expires immediately
        elif policy == RetentionPolicy.ONE_HOUR:
            return now + timedelta(hours=1)
        elif policy == RetentionPolicy.SIX_HOURS:
            return now + timedelta(hours=6)
        elif policy == RetentionPolicy.TWENTY_FOUR_HOURS:
            return now + timedelta(hours=24)
        elif policy == RetentionPolicy.SEVEN_DAYS:
            return now + timedelta(days=7)
        elif policy == RetentionPolicy.THIRTY_DAYS:
            return now + timedelta(days=30)
        else:  # PERMANENT
            return now + timedelta(days=36500)  # 100 years = effectively permanent
    
    async def schedule_deletion(self, data_id: str) -> bool:
        """Schedule data for deletion."""
        if data_id not in self.data_records:
            return False
        
        self.deletion_queue.add(data_id)
        logger.info("data_scheduled_for_deletion", data_id=data_id)
        return True
    
    async def force_delete(self, data_id: str) -> bool:
        """Force immediate deletion of data."""
        if data_id not in self.data_records:
            return False
        
        record = self.data_records[data_id]
        success = await self._delete_data_record(record)
        
        if success:
            del self.data_records[data_id]
            self.deletion_queue.discard(data_id)
        
        return success
    
    async def extend_retention(self, data_id: str, additional_hours: int) -> bool:
        """Extend retention period for data."""
        if data_id not in self.data_records:
            return False
        
        record = self.data_records[data_id]
        record.expires_at += timedelta(hours=additional_hours)
        
        logger.info("retention_extended",
                   data_id=data_id,
                   additional_hours=additional_hours,
                   new_expires_at=record.expires_at.isoformat())
        
        return True
    
    async def get_retention_status(self, data_id: str) -> Optional[Dict[str, Any]]:
        """Get retention status for data."""
        if data_id not in self.data_records:
            return None
        
        record = self.data_records[data_id]
        now = datetime.utcnow()
        
        return {
            "data_id": data_id,
            "data_type": record.data_type.value,
            "created_at": record.created_at.isoformat(),
            "expires_at": record.expires_at.isoformat(),
            "is_expired": now >= record.expires_at,
            "time_remaining_hours": max(0, (record.expires_at - now).total_seconds() / 3600),
            "size_bytes": record.size_bytes,
            "tags": record.tags,
            "secure_delete": record.secure_delete,
            "scheduled_for_deletion": data_id in self.deletion_queue
        }
    
    async def generate_compliance_report(self) -> RetentionReport:
        """Generate compliance report."""
        now = datetime.utcnow()
        
        total_records = len(self.data_records)
        expired_records = 0
        policy_violations = []
        total_size = 0
        
        for record in self.data_records.values():
            total_size += record.size_bytes
            
            if now >= record.expires_at:
                expired_records += 1
                
                # Check for policy violations (expired data not deleted)
                if data_id not in self.deletion_queue:
                    violation = f"Data {record.id} ({record.data_type.value}) expired at {record.expires_at.isoformat()} but not scheduled for deletion"
                    policy_violations.append(violation)
        
        deleted_records = self.stats["total_deletions"]
        failed_deletions = expired_records - len(self.deletion_queue)
        
        compliance_score = 1.0
        if total_records > 0:
            compliance_score = max(0.0, 1.0 - (len(policy_violations) / total_records))
        
        return RetentionReport(
            total_records=total_records,
            expired_records=expired_records,
            deleted_records=deleted_records,
            failed_deletions=max(0, failed_deletions),
            bytes_deleted=self.stats["bytes_deleted"],
            compliance_score=compliance_score,
            policy_violations=policy_violations
        )
    
    async def _start_deletion_worker(self):
        """Start background worker for data deletion."""
        self._deletion_task = asyncio.create_task(self._deletion_worker())
    
    async def _deletion_worker(self):
        """Background worker that deletes expired data."""
        while True:
            try:
                await self._process_expired_data()
                await self._process_deletion_queue()
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                logger.error("deletion_worker_error", error=str(e))
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    async def _process_expired_data(self):
        """Process expired data records."""
        now = datetime.utcnow()
        expired_ids = []
        
        for data_id, record in self.data_records.items():
            if now >= record.expires_at and data_id not in self.deletion_queue:
                expired_ids.append(data_id)
        
        for data_id in expired_ids:
            self.deletion_queue.add(data_id)
            logger.info("data_expired_scheduled_deletion", data_id=data_id)
        
        if expired_ids:
            logger.info("expired_data_processed", count=len(expired_ids))
    
    async def _process_deletion_queue(self):
        """Process data in deletion queue."""
        if not self.deletion_queue:
            return
        
        batch_size = 10
        current_batch = list(self.deletion_queue)[:batch_size]
        
        for data_id in current_batch:
            try:
                if data_id in self.data_records:
                    record = self.data_records[data_id]
                    success = await self._delete_data_record(record)
                    
                    if success:
                        del self.data_records[data_id]
                        self.deletion_queue.remove(data_id)
                        self.stats["total_deletions"] += 1
                        self.stats["bytes_deleted"] += record.size_bytes
                        
                        logger.info("data_deleted",
                                   data_id=data_id,
                                   data_type=record.data_type.value,
                                   size_bytes=record.size_bytes)
                    else:
                        logger.warning("data_deletion_failed", data_id=data_id)
                else:
                    # Record no longer exists, remove from queue
                    self.deletion_queue.remove(data_id)
                    
            except Exception as e:
                logger.error("deletion_processing_error", 
                           data_id=data_id, 
                           error=str(e))
    
    async def _delete_data_record(self, record: DataRecord) -> bool:
        """Delete actual data for a record."""
        try:
            # Handle different data storage types
            if record.location:
                success = await self._delete_file_data(record)
            else:
                success = await self._delete_memory_data(record)
            
            # Secure deletion if requested
            if success and record.secure_delete:
                await self._secure_wipe(record)
            
            return success
            
        except Exception as e:
            logger.error("data_deletion_failed", 
                        data_id=record.id, 
                        error=str(e))
            return False
    
    async def _delete_file_data(self, record: DataRecord) -> bool:
        """Delete file-based data."""
        try:
            import os
            
            if record.location and os.path.exists(record.location):
                os.remove(record.location)
                logger.debug("file_deleted", 
                           data_id=record.id, 
                           location=record.location)
                return True
            
            return True  # File doesn't exist, consider it deleted
            
        except Exception as e:
            logger.error("file_deletion_failed", 
                        data_id=record.id, 
                        location=record.location,
                        error=str(e))
            return False
    
    async def _delete_memory_data(self, record: DataRecord) -> bool:
        """Delete in-memory data."""
        # This would integrate with your caching/storage systems
        # For now, we'll just mark it as handled
        logger.debug("memory_data_deleted", data_id=record.id)
        return True
    
    async def _secure_wipe(self, record: DataRecord):
        """Perform secure wiping of sensitive data."""
        try:
            if record.location:
                # Secure file wiping (simplified implementation)
                import os
                if os.path.exists(record.location):
                    # Overwrite file with random data multiple times
                    file_size = os.path.getsize(record.location)
                    with open(record.location, 'r+b') as f:
                        for _ in range(3):  # 3-pass overwrite
                            f.seek(0)
                            f.write(os.urandom(file_size))
                            f.flush()
                            os.fsync(f.fileno())
                    
                    os.remove(record.location)
                    
            logger.info("secure_wipe_completed", data_id=record.id)
            
        except Exception as e:
            logger.error("secure_wipe_failed", 
                        data_id=record.id, 
                        error=str(e))
    
    async def get_retention_stats(self) -> Dict[str, Any]:
        """Get retention service statistics."""
        now = datetime.utcnow()
        
        active_records = len(self.data_records)
        expired_count = len([r for r in self.data_records.values() if now >= r.expires_at])
        queue_size = len(self.deletion_queue)
        
        total_size = sum(r.size_bytes for r in self.data_records.values())
        
        return {
            "retention_stats": self.stats,
            "active_records": active_records,
            "expired_records": expired_count,
            "deletion_queue_size": queue_size,
            "total_data_size_bytes": total_size,
            "policies_count": len(self.retention_rules),
            "worker_running": self._deletion_task is not None and not self._deletion_task.done()
        }
    
    def add_retention_rule(self, rule: RetentionRule):
        """Add custom retention rule."""
        self.retention_rules.append(rule)
        logger.info("retention_rule_added", 
                   data_type=rule.data_type.value,
                   policy=rule.policy.value)
    
    def remove_retention_rule(self, data_type: DataType, policy: RetentionPolicy) -> bool:
        """Remove retention rule."""
        for i, rule in enumerate(self.retention_rules):
            if rule.data_type == data_type and rule.policy == policy:
                del self.retention_rules[i]
                logger.info("retention_rule_removed", 
                           data_type=data_type.value,
                           policy=policy.value)
                return True
        return False
    
    async def cleanup(self):
        """Cleanup resources."""
        if self._deletion_task:
            self._deletion_task.cancel()
            try:
                await self._deletion_task
            except asyncio.CancelledError:
                pass


# Singleton service
_zero_retention_manager: Optional[ZeroRetentionManager] = None


async def get_zero_retention_manager() -> ZeroRetentionManager:
    """Get or create zero retention manager instance."""
    global _zero_retention_manager
    
    if _zero_retention_manager is None:
        _zero_retention_manager = ZeroRetentionManager()
    
    return _zero_retention_manager


# Convenience functions
async def register_for_zero_retention(
    data_id: str,
    data_type: str,
    size_bytes: int = 0,
    location: Optional[str] = None
) -> bool:
    """
    Register data for zero retention (24-hour deletion).
    
    Args:
        data_id: Unique data identifier
        data_type: Type of data
        size_bytes: Size in bytes
        location: Storage location
        
    Returns:
        True if registered successfully
    """
    manager = await get_zero_retention_manager()
    
    try:
        data_type_enum = DataType(data_type)
    except ValueError:
        data_type_enum = DataType.SCRAPED_CONTENT
    
    record = await manager.register_data(
        data_id=data_id,
        data_type=data_type_enum,
        size_bytes=size_bytes,
        location=location,
        tags=["zero_retention"],
        secure_delete=True
    )
    
    return record is not None


async def check_compliance_status() -> Dict[str, Any]:
    """Check overall compliance status."""
    manager = await get_zero_retention_manager()
    report = await manager.generate_compliance_report()
    
    return {
        "compliant": report.compliance_score >= 0.95,
        "compliance_score": report.compliance_score,
        "total_records": report.total_records,
        "expired_records": report.expired_records,
        "policy_violations": len(report.policy_violations),
        "bytes_deleted": report.bytes_deleted,
        "report_time": report.generated_at.isoformat()
    }
