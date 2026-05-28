"""
Simple client for an external Puppeteer render service.

Expected service API:
POST /render { url, waitUntil, timeout, screenshot, pdf, userAgent, headers?, cookies?, proxy? }
Response JSON: { html: string, finalUrl?: string, screenshot?: string(base64), pdf?: string(base64) }
"""
from typing import Any, Dict, Optional
import httpx
from app.config import get_settings
import structlog

logger = structlog.get_logger(__name__)
settings = get_settings()


class PuppeteerClient:
    def __init__(self, base_url: Optional[str] = None, timeout_seconds: Optional[int] = None):
        self.base_url = (base_url or str(settings.puppeteer_service_url)).rstrip("/")
        self.timeout = timeout_seconds or settings.puppeteer_timeout

    async def render(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}/render"
        async with httpx.AsyncClient(timeout=httpx.Timeout(self.timeout)) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            # Basic validation
            if not isinstance(data, dict) or "html" not in data:
                raise ValueError("Invalid response from Puppeteer service: missing 'html'")
            return data


