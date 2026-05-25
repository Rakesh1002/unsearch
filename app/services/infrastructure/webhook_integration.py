"""
Webhook Integration service inspired by Firecrawl.

Provides comprehensive webhook notifications:
- Job status change notifications
- Real-time progress updates
- Error and failure notifications
- Customizable webhook payloads
- Retry logic and failure handling
- Webhook security and validation
"""

import asyncio
import time
import json
import hmac
import hashlib
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import structlog
import httpx

from app.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class WebhookEvent(Enum):
    """Types of webhook events."""
    # Job lifecycle events
    JOB_STARTED = "job.started"
    JOB_COMPLETED = "job.completed"
    JOB_FAILED = "job.failed"
    JOB_CANCELLED = "job.cancelled"
    JOB_PAUSED = "job.paused"
    JOB_RESUMED = "job.resumed"
    
    # Progress events
    PROGRESS_UPDATE = "progress.update"
    MILESTONE_REACHED = "milestone.reached"
    
    # Error events
    ERROR_OCCURRED = "error.occurred"
    RETRY_ATTEMPTED = "retry.attempted"
    CRITICAL_ERROR = "error.critical"
    
    # Data events
    DATA_EXTRACTED = "data.extracted"
    CHANGE_DETECTED = "change.detected"
    BATCH_COMPLETED = "batch.completed"
    
    # System events
    SYSTEM_ALERT = "system.alert"
    QUOTA_WARNING = "quota.warning"
    RATE_LIMIT = "rate_limit.exceeded"


class WebhookStatus(Enum):
    """Status of webhook delivery."""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    RETRYING = "retrying"
    ABANDONED = "abandoned"


@dataclass
class WebhookConfig:
    """Configuration for webhook endpoints."""
    url: str
    events: List[WebhookEvent] = field(default_factory=list)
    secret: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    retry_backoff: float = 2.0
    verify_ssl: bool = True
    enabled: bool = True
    
    # Filtering options
    job_types: List[str] = field(default_factory=list)  # Filter by job types
    tags: List[str] = field(default_factory=list)  # Filter by tags
    
    # Custom payload options
    include_data: bool = False
    include_errors: bool = True
    include_progress: bool = True
    max_payload_size: int = 1024 * 1024  # 1MB


@dataclass
class WebhookPayload:
    """Webhook payload structure."""
    event: WebhookEvent
    timestamp: datetime
    data: Dict[str, Any]
    source: str = "unsearch_backend"
    version: str = "1.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event": self.event.value,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "version": self.version,
            "data": self.data
        }


@dataclass
class WebhookAttempt:
    """Record of webhook delivery attempt."""
    id: str
    webhook_config: WebhookConfig
    payload: WebhookPayload
    status: WebhookStatus = WebhookStatus.PENDING
    attempts: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_attempt_at: Optional[datetime] = None
    next_attempt_at: Optional[datetime] = None
    response_status: Optional[int] = None
    response_body: Optional[str] = None
    error: Optional[str] = None


class WebhookManager:
    """
    Comprehensive webhook management service.
    
    Provides webhook notifications for various system events:
    - Job lifecycle management
    - Real-time progress updates
    - Error and failure notifications
    - Custom event handling
    """
    
    def __init__(self):
        """Initialize webhook manager."""
        self.webhook_configs: Dict[str, WebhookConfig] = {}
        self.pending_attempts: Dict[str, WebhookAttempt] = {}
        self.event_handlers: Dict[WebhookEvent, List[Callable]] = {}
        
        self.stats = {
            "total_webhooks": 0,
            "successful_deliveries": 0,
            "failed_deliveries": 0,
            "active_configs": 0,
            "events_processed": 0
        }
        
        # Start background worker
        self._worker_task = None
        asyncio.create_task(self._start_webhook_worker())
    
    def add_webhook_config(
        self, 
        config_id: str, 
        config: WebhookConfig
    ) -> bool:
        """Add webhook configuration."""
        self.webhook_configs[config_id] = config
        self.stats["active_configs"] = len(self.webhook_configs)
        
        logger.info("webhook_config_added",
                   config_id=config_id,
                   url=config.url,
                   events=len(config.events))
        
        return True
    
    def remove_webhook_config(self, config_id: str) -> bool:
        """Remove webhook configuration."""
        if config_id not in self.webhook_configs:
            return False
        
        del self.webhook_configs[config_id]
        self.stats["active_configs"] = len(self.webhook_configs)
        
        logger.info("webhook_config_removed", config_id=config_id)
        return True
    
    def get_webhook_config(self, config_id: str) -> Optional[WebhookConfig]:
        """Get webhook configuration."""
        return self.webhook_configs.get(config_id)
    
    def list_webhook_configs(self) -> Dict[str, WebhookConfig]:
        """List all webhook configurations."""
        return self.webhook_configs.copy()
    
    async def send_webhook(
        self,
        event: WebhookEvent,
        data: Dict[str, Any],
        config_id: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[str]:
        """
        Send webhook notification for event.
        
        Args:
            event: Webhook event type
            data: Event data payload
            config_id: Specific config to use (if None, uses all matching)
            tags: Event tags for filtering
            
        Returns:
            List of attempt IDs
        """
        tags = tags or []
        attempt_ids = []
        
        # Determine which configs to use
        configs_to_use = {}
        
        if config_id:
            if config_id in self.webhook_configs:
                configs_to_use[config_id] = self.webhook_configs[config_id]
        else:
            configs_to_use = self.webhook_configs.copy()
        
        # Filter configs based on event and tags
        filtered_configs = {}
        for cid, config in configs_to_use.items():
            if not config.enabled:
                continue
            
            # Check if event is subscribed
            if config.events and event not in config.events:
                continue
            
            # Check tag filtering
            if config.tags and not any(tag in config.tags for tag in tags):
                continue
            
            filtered_configs[cid] = config
        
        # Create webhook attempts
        for cid, config in filtered_configs.items():
            attempt_id = await self._create_webhook_attempt(config, event, data)
            attempt_ids.append(attempt_id)
        
        self.stats["events_processed"] += 1
        self.stats["total_webhooks"] += len(attempt_ids)
        
        logger.info("webhook_event_sent",
                   event=event.value,
                   configs_matched=len(filtered_configs),
                   attempts_created=len(attempt_ids))
        
        return attempt_ids
    
    async def _create_webhook_attempt(
        self,
        config: WebhookConfig,
        event: WebhookEvent,
        data: Dict[str, Any]
    ) -> str:
        """Create a webhook delivery attempt."""
        # Create payload
        payload = WebhookPayload(
            event=event,
            timestamp=datetime.utcnow(),
            data=self._prepare_payload_data(data, config)
        )
        
        # Create attempt record
        attempt_id = f"webhook_{int(time.time() * 1000)}_{id(config)}"
        attempt = WebhookAttempt(
            id=attempt_id,
            webhook_config=config,
            payload=payload,
            next_attempt_at=datetime.utcnow()
        )
        
        self.pending_attempts[attempt_id] = attempt
        
        return attempt_id
    
    def _prepare_payload_data(self, data: Dict[str, Any], config: WebhookConfig) -> Dict[str, Any]:
        """Prepare payload data according to config."""
        filtered_data = data.copy()
        
        # Remove sensitive data if not requested
        if not config.include_data:
            # Remove large data fields
            for key in ["results", "scraped_content", "extracted_data"]:
                if key in filtered_data:
                    if isinstance(filtered_data[key], list):
                        filtered_data[key] = {"count": len(filtered_data[key])}
                    else:
                        filtered_data[key] = {"size": len(str(filtered_data[key]))}
        
        if not config.include_errors:
            filtered_data.pop("errors", None)
            filtered_data.pop("error", None)
        
        if not config.include_progress:
            filtered_data.pop("progress", None)
        
        # Check payload size
        payload_str = json.dumps(filtered_data)
        if len(payload_str) > config.max_payload_size:
            # Truncate large fields
            filtered_data = self._truncate_payload(filtered_data, config.max_payload_size)
        
        return filtered_data
    
    def _truncate_payload(self, data: Dict[str, Any], max_size: int) -> Dict[str, Any]:
        """Truncate payload to fit size limit."""
        truncated = data.copy()
        
        # Truncate large text fields
        for key, value in data.items():
            if isinstance(value, str) and len(value) > 1000:
                truncated[key] = value[:1000] + "... [truncated]"
            elif isinstance(value, list) and len(value) > 10:
                truncated[key] = value[:10] + [{"truncated": f"{len(value) - 10} more items"}]
        
        return truncated
    
    async def _start_webhook_worker(self):
        """Start background worker for webhook delivery."""
        self._worker_task = asyncio.create_task(self._webhook_worker())
    
    async def _webhook_worker(self):
        """Background worker that delivers webhooks."""
        while True:
            try:
                await self._process_pending_webhooks()
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error("webhook_worker_error", error=str(e))
                await asyncio.sleep(30)  # Wait 30 seconds before retrying
    
    async def _process_pending_webhooks(self):
        """Process pending webhook deliveries."""
        now = datetime.utcnow()
        ready_attempts = []
        
        # Find attempts ready for delivery
        for attempt_id, attempt in self.pending_attempts.items():
            if attempt.status == WebhookStatus.PENDING or (
                attempt.status == WebhookStatus.RETRYING and 
                attempt.next_attempt_at and 
                now >= attempt.next_attempt_at
            ):
                ready_attempts.append(attempt)
        
        # Process attempts concurrently
        if ready_attempts:
            await asyncio.gather(
                *[self._deliver_webhook(attempt) for attempt in ready_attempts],
                return_exceptions=True
            )
    
    async def _deliver_webhook(self, attempt: WebhookAttempt):
        """Deliver a single webhook."""
        config = attempt.webhook_config
        
        try:
            attempt.attempts += 1
            attempt.last_attempt_at = datetime.utcnow()
            attempt.status = WebhookStatus.SENT if attempt.attempts == 1 else WebhookStatus.RETRYING
            
            # Prepare request
            payload_dict = attempt.payload.to_dict()
            headers = config.headers.copy()
            headers["Content-Type"] = "application/json"
            headers["User-Agent"] = "UnSearch-Webhook/1.0"
            
            # Add signature if secret is provided
            if config.secret:
                signature = self._generate_signature(json.dumps(payload_dict), config.secret)
                headers["X-Webhook-Signature"] = signature
            
            # Make HTTP request
            async with httpx.AsyncClient(verify=config.verify_ssl) as client:
                response = await client.post(
                    config.url,
                    json=payload_dict,
                    headers=headers,
                    timeout=config.timeout
                )
                
                attempt.response_status = response.status_code
                attempt.response_body = response.text[:1000]  # Limit response body
                
                if 200 <= response.status_code < 300:
                    # Success
                    attempt.status = WebhookStatus.SENT
                    self.stats["successful_deliveries"] += 1
                    
                    # Remove from pending
                    if attempt.id in self.pending_attempts:
                        del self.pending_attempts[attempt.id]
                    
                    logger.info("webhook_delivered_successfully",
                               attempt_id=attempt.id,
                               url=config.url,
                               status_code=response.status_code,
                               attempts=attempt.attempts)
                else:
                    # HTTP error
                    raise httpx.HTTPStatusError(
                        message=f"HTTP {response.status_code}",
                        request=response.request,
                        response=response
                    )
        
        except Exception as e:
            await self._handle_webhook_failure(attempt, str(e))
    
    async def _handle_webhook_failure(self, attempt: WebhookAttempt, error: str):
        """Handle webhook delivery failure."""
        config = attempt.webhook_config
        attempt.error = error
        
        if attempt.attempts >= config.max_retries:
            # Max retries reached, abandon
            attempt.status = WebhookStatus.ABANDONED
            self.stats["failed_deliveries"] += 1
            
            # Remove from pending
            if attempt.id in self.pending_attempts:
                del self.pending_attempts[attempt.id]
            
            logger.warning("webhook_delivery_abandoned",
                          attempt_id=attempt.id,
                          url=config.url,
                          attempts=attempt.attempts,
                          error=error)
        else:
            # Schedule retry
            attempt.status = WebhookStatus.FAILED
            retry_delay = config.retry_delay * (config.retry_backoff ** (attempt.attempts - 1))
            attempt.next_attempt_at = datetime.utcnow() + timedelta(seconds=retry_delay)
            
            logger.info("webhook_delivery_failed_will_retry",
                       attempt_id=attempt.id,
                       url=config.url,
                       attempts=attempt.attempts,
                       retry_in_seconds=retry_delay,
                       error=error)
    
    def _generate_signature(self, payload: str, secret: str) -> str:
        """Generate HMAC signature for webhook payload."""
        signature = hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return f"sha256={signature}"
    
    def register_event_handler(
        self,
        event: WebhookEvent,
        handler: Callable[[Dict[str, Any]], Any]
    ):
        """Register custom event handler."""
        if event not in self.event_handlers:
            self.event_handlers[event] = []
        
        self.event_handlers[event].append(handler)
        logger.info("event_handler_registered", event=event.value)
    
    async def emit_event(
        self,
        event: WebhookEvent,
        data: Dict[str, Any],
        tags: Optional[List[str]] = None
    ) -> List[str]:
        """
        Emit event to both webhooks and custom handlers.
        
        Args:
            event: Event type
            data: Event data
            tags: Event tags
            
        Returns:
            List of webhook attempt IDs
        """
        # Call custom handlers
        if event in self.event_handlers:
            for handler in self.event_handlers[event]:
                try:
                    handler(data)
                except Exception as e:
                    logger.error("event_handler_failed",
                               event=event.value,
                               error=str(e))
        
        # Send webhooks
        return await self.send_webhook(event, data, tags=tags)
    
    async def get_webhook_stats(self) -> Dict[str, Any]:
        """Get webhook service statistics."""
        pending_count = len(self.pending_attempts)
        failed_count = len([a for a in self.pending_attempts.values() if a.status == WebhookStatus.FAILED])
        
        return {
            "webhook_stats": self.stats,
            "active_configs": len(self.webhook_configs),
            "pending_attempts": pending_count,
            "failed_attempts": failed_count,
            "success_rate": (
                self.stats["successful_deliveries"] / 
                max(1, self.stats["total_webhooks"])
            ) if self.stats["total_webhooks"] > 0 else 0,
            "worker_running": self._worker_task is not None and not self._worker_task.done()
        }
    
    async def get_webhook_attempt_status(self, attempt_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a webhook attempt."""
        if attempt_id not in self.pending_attempts:
            return None
        
        attempt = self.pending_attempts[attempt_id]
        
        return {
            "id": attempt.id,
            "status": attempt.status.value,
            "attempts": attempt.attempts,
            "created_at": attempt.created_at.isoformat(),
            "last_attempt_at": attempt.last_attempt_at.isoformat() if attempt.last_attempt_at else None,
            "next_attempt_at": attempt.next_attempt_at.isoformat() if attempt.next_attempt_at else None,
            "response_status": attempt.response_status,
            "error": attempt.error,
            "webhook_url": attempt.webhook_config.url,
            "event": attempt.payload.event.value
        }
    
    async def cleanup(self):
        """Cleanup resources."""
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass


# Singleton service
_webhook_manager: Optional[WebhookManager] = None


async def get_webhook_manager() -> WebhookManager:
    """Get or create webhook manager service instance."""
    global _webhook_manager
    
    if _webhook_manager is None:
        _webhook_manager = WebhookManager()
    
    return _webhook_manager


# Convenience functions
async def send_job_webhook(
    job_id: str,
    event: str,
    status: str,
    data: Optional[Dict[str, Any]] = None,
    webhook_url: Optional[str] = None
) -> List[str]:
    """
    Send job-related webhook notification.
    
    Args:
        job_id: Job identifier
        event: Event type (started, completed, failed, etc.)
        status: Current job status
        data: Additional job data
        webhook_url: Specific webhook URL to use
        
    Returns:
        List of webhook attempt IDs
    """
    manager = await get_webhook_manager()
    
    # Map event string to enum
    event_mapping = {
        "started": WebhookEvent.JOB_STARTED,
        "completed": WebhookEvent.JOB_COMPLETED,
        "failed": WebhookEvent.JOB_FAILED,
        "cancelled": WebhookEvent.JOB_CANCELLED,
        "paused": WebhookEvent.JOB_PAUSED,
        "resumed": WebhookEvent.JOB_RESUMED
    }
    
    webhook_event = event_mapping.get(event, WebhookEvent.JOB_STARTED)
    
    payload_data = {
        "job_id": job_id,
        "status": status,
        **(data or {})
    }
    
    # If specific webhook URL provided, create temporary config
    if webhook_url:
        temp_config_id = f"temp_{job_id}_{int(time.time())}"
        temp_config = WebhookConfig(
            url=webhook_url,
            events=[webhook_event],
            timeout=30,
            max_retries=3
        )
        
        manager.add_webhook_config(temp_config_id, temp_config)
        
        try:
            return await manager.send_webhook(webhook_event, payload_data, temp_config_id)
        finally:
            manager.remove_webhook_config(temp_config_id)
    else:
        return await manager.send_webhook(webhook_event, payload_data)


async def send_progress_webhook(
    job_id: str,
    progress_data: Dict[str, Any],
    tags: Optional[List[str]] = None
) -> List[str]:
    """Send progress update webhook."""
    manager = await get_webhook_manager()
    
    payload_data = {
        "job_id": job_id,
        "progress": progress_data
    }
    
    return await manager.send_webhook(WebhookEvent.PROGRESS_UPDATE, payload_data, tags=tags)


async def send_error_webhook(
    error_type: str,
    error_message: str,
    context: Optional[Dict[str, Any]] = None,
    critical: bool = False
) -> List[str]:
    """Send error notification webhook."""
    manager = await get_webhook_manager()
    
    event = WebhookEvent.CRITICAL_ERROR if critical else WebhookEvent.ERROR_OCCURRED
    
    payload_data = {
        "error_type": error_type,
        "error_message": error_message,
        "critical": critical,
        "context": context or {}
    }
    
    return await manager.send_webhook(event, payload_data)

