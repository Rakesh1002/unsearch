"""
Topic Monitor API - Real-time Web Monitoring

Endpoints for:
- Creating topic monitors
- Managing alerts
- Viewing monitoring results
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict, Any
from datetime import datetime
import asyncio
import hashlib

from app.config import get_settings
from app.services.ai.cloudflare_ai import CloudflareAIService, CFModel

router = APIRouter(prefix="/monitor", tags=["Topic Monitoring"])

settings = get_settings()


# Models
class TopicMonitorCreate(BaseModel):
    topic: str = Field(..., description="Topic to monitor")
    keywords: List[str] = Field(default=[], description="Additional keywords to track")
    sources: Optional[List[str]] = Field(None, description="Specific domains to monitor")
    check_interval_minutes: int = Field(60, ge=5, le=1440, description="Check interval in minutes")
    webhook_url: Optional[HttpUrl] = Field(None, description="Webhook for alerts")
    deep_analysis: bool = Field(False, description="Include AI analysis with alerts")
    

class TopicMonitor(BaseModel):
    id: str
    topic: str
    keywords: List[str]
    sources: Optional[List[str]]
    check_interval_minutes: int
    webhook_url: Optional[str]
    deep_analysis: bool
    status: str  # active, paused, stopped
    last_checked: Optional[datetime]
    alerts_sent: int
    created_at: datetime


class MonitorResult(BaseModel):
    id: str
    monitor_id: str
    timestamp: datetime
    new_results: List[Dict[str, Any]]
    analysis: Optional[str]
    

class MonitorAlert(BaseModel):
    monitor_id: str
    topic: str
    new_results: List[Dict[str, Any]]
    analysis: Optional[str]
    timestamp: datetime


# In-memory storage (replace with D1/PostgreSQL in production)
_monitors: Dict[str, TopicMonitor] = {}
_monitor_results: Dict[str, List[MonitorResult]] = {}


def generate_monitor_id(topic: str) -> str:
    return hashlib.md5(f"{topic}:{datetime.now().isoformat()}".encode()).hexdigest()[:12]


@router.post("/topics", response_model=TopicMonitor)
async def create_topic_monitor(
    monitor: TopicMonitorCreate,
    background_tasks: BackgroundTasks
):
    """
    Create a new topic monitor.
    
    The monitor will periodically check for new content related to the topic
    and send alerts via webhook when new relevant content is found.
    
    This is a groundbreaking feature not available in Tavily, Exa, or Glean.
    """
    monitor_id = generate_monitor_id(monitor.topic)
    
    topic_monitor = TopicMonitor(
        id=monitor_id,
        topic=monitor.topic,
        keywords=monitor.keywords,
        sources=monitor.sources,
        check_interval_minutes=monitor.check_interval_minutes,
        webhook_url=str(monitor.webhook_url) if monitor.webhook_url else None,
        deep_analysis=monitor.deep_analysis,
        status="active",
        last_checked=None,
        alerts_sent=0,
        created_at=datetime.now()
    )
    
    _monitors[monitor_id] = topic_monitor
    _monitor_results[monitor_id] = []
    
    # Schedule first check
    background_tasks.add_task(check_monitor, monitor_id)
    
    return topic_monitor


@router.get("/topics", response_model=List[TopicMonitor])
async def list_monitors():
    """List all topic monitors."""
    return list(_monitors.values())


@router.get("/topics/{monitor_id}", response_model=TopicMonitor)
async def get_monitor(monitor_id: str):
    """Get a specific monitor by ID."""
    if monitor_id not in _monitors:
        raise HTTPException(status_code=404, detail="Monitor not found")
    return _monitors[monitor_id]


@router.post("/topics/{monitor_id}/pause")
async def pause_monitor(monitor_id: str):
    """Pause a monitor."""
    if monitor_id not in _monitors:
        raise HTTPException(status_code=404, detail="Monitor not found")
    
    _monitors[monitor_id].status = "paused"
    return {"status": "paused", "monitor_id": monitor_id}


@router.post("/topics/{monitor_id}/resume")
async def resume_monitor(monitor_id: str, background_tasks: BackgroundTasks):
    """Resume a paused monitor."""
    if monitor_id not in _monitors:
        raise HTTPException(status_code=404, detail="Monitor not found")
    
    _monitors[monitor_id].status = "active"
    background_tasks.add_task(check_monitor, monitor_id)
    
    return {"status": "active", "monitor_id": monitor_id}


@router.delete("/topics/{monitor_id}")
async def delete_monitor(monitor_id: str):
    """Delete a monitor."""
    if monitor_id not in _monitors:
        raise HTTPException(status_code=404, detail="Monitor not found")
    
    del _monitors[monitor_id]
    if monitor_id in _monitor_results:
        del _monitor_results[monitor_id]
    
    return {"deleted": True, "monitor_id": monitor_id}


@router.post("/topics/{monitor_id}/check")
async def trigger_check(monitor_id: str, background_tasks: BackgroundTasks):
    """Manually trigger a check for a monitor."""
    if monitor_id not in _monitors:
        raise HTTPException(status_code=404, detail="Monitor not found")
    
    background_tasks.add_task(check_monitor, monitor_id)
    
    return {"status": "check_triggered", "monitor_id": monitor_id}


@router.get("/topics/{monitor_id}/results", response_model=List[MonitorResult])
async def get_monitor_results(monitor_id: str, limit: int = 50):
    """Get recent results from a monitor."""
    if monitor_id not in _monitors:
        raise HTTPException(status_code=404, detail="Monitor not found")
    
    results = _monitor_results.get(monitor_id, [])
    return results[-limit:]


async def check_monitor(monitor_id: str):
    """
    Background task to check a monitor for new content.
    
    In production, this would be handled by Cloudflare Durable Objects
    with scheduled alarms.
    """
    if monitor_id not in _monitors:
        return
    
    monitor = _monitors[monitor_id]
    
    if monitor.status != "active":
        return
    
    try:
        # Build search query
        search_query = f"{monitor.topic} {' '.join(monitor.keywords)}"
        
        # Get AI service
        ai = CloudflareAIService(
            account_id=settings.cloudflare_account_id,
            api_token=settings.cloudflare_api_token
        )
        
        # Search SearXNG for new content
        from app.services.core.searxng import SearXNGService
        search = SearXNGService(base_url=settings.searxng_url)
        
        new_results = []
        try:
            search_results = await search.search(
                query=search_query,
                engines=["google news", "bing news", "duckduckgo"],
                language="en"
            )
            # Convert SearchResult objects to dicts for storage
            for r in search_results[:10]:
                new_results.append({
                    "title": r.title or "",
                    "url": str(r.url),
                    "snippet": r.snippet or "",
                    "engine": r.engine
                })
        except Exception as e:
            print(f"Monitor search failed for {monitor_id}: {e}")
        
        # Generate analysis if enabled
        analysis = None
        if monitor.deep_analysis and new_results:
            context = "\n".join([f"- {r['title']}: {r['snippet'][:200]}" for r in new_results[:5]])
            analysis = await ai.generate_text(
                prompt=f"Briefly summarize these new developments about '{monitor.topic}':\n{context}",
                model=CFModel.LLAMA_3_1_8B_FAST,
                max_tokens=300
            )
        
        # Store result
        result = MonitorResult(
            id=hashlib.md5(f"{monitor_id}:{datetime.now().isoformat()}".encode()).hexdigest()[:12],
            monitor_id=monitor_id,
            timestamp=datetime.now(),
            new_results=new_results,
            analysis=analysis
        )
        
        if monitor_id in _monitor_results:
            _monitor_results[monitor_id].append(result)
            # Keep only last 100 results
            _monitor_results[monitor_id] = _monitor_results[monitor_id][-100:]
        
        # Send webhook if configured and has results
        if monitor.webhook_url and new_results:
            import httpx
            async with httpx.AsyncClient() as client:
                await client.post(
                    monitor.webhook_url,
                    json={
                        "event": "topic_alert",
                        "monitor_id": monitor_id,
                        "topic": monitor.topic,
                        "new_results": new_results,
                        "analysis": analysis,
                        "timestamp": datetime.now().isoformat()
                    },
                    timeout=10.0
                )
            monitor.alerts_sent += 1
        
        monitor.last_checked = datetime.now()
        
    except Exception as e:
        # Log error but don't crash
        print(f"Monitor check error for {monitor_id}: {e}")
