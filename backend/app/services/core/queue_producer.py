"""
CF Queues producer for FastAPI Container.

Replaces Celery task dispatch. The Container publishes a JSON task
message to the CF Queue via the same REST API; the Worker's queue
consumer (workers/src/queue-consumer.ts) processes it.

Task message shape mirrors `TaskMessage` in workers/src/env.ts.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

QUEUES_API_BASE = "https://api.cloudflare.com/client/v4"


class QueueProducer:
    """Async client that publishes messages to a CF Queue."""

    def __init__(
        self,
        account_id: str | None = None,
        api_token: str | None = None,
        queue_id: str | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        self.account_id = account_id or os.environ["CLOUDFLARE_ACCOUNT_ID"]
        self.api_token = api_token or os.environ["CLOUDFLARE_API_TOKEN"]
        self.queue_id = queue_id or os.environ["CLOUDFLARE_QUEUE_ID"]
        self._http = httpx.AsyncClient(
            timeout=timeout_seconds,
            headers={
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
            },
            base_url=f"{QUEUES_API_BASE}/accounts/{self.account_id}/queues/{self.queue_id}/messages",
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    async def send(self, body: dict[str, Any], *, delay_seconds: int | None = None) -> bool:
        payload: dict[str, Any] = {"body": body, "content_type": "json"}
        if delay_seconds is not None:
            payload["delay_seconds"] = delay_seconds
        try:
            resp = await self._http.post("", json=payload)
        except httpx.HTTPError as exc:
            logger.warning("queue send failed", extra={"err": str(exc)})
            return False
        if resp.status_code not in (200, 202):
            logger.warning("queue send returned status %d: %s", resp.status_code, resp.text[:200])
            return False
        return True

    async def send_batch(self, bodies: list[dict[str, Any]]) -> bool:
        payload = {"messages": [{"body": b, "content_type": "json"} for b in bodies]}
        try:
            resp = await self._http.post("/batch", json=payload)
        except httpx.HTTPError as exc:
            logger.warning("queue send_batch failed", extra={"err": str(exc)})
            return False
        return resp.status_code in (200, 202)

    # ----- Typed helpers (mirror Worker's TaskMessage union) -----

    async def dispatch_scrape(
        self, job_id: str, urls: list[str], config: dict[str, Any] | None = None
    ) -> bool:
        return await self.send({"type": "scrape", "jobId": job_id, "urls": urls, "config": config or {}})

    async def dispatch_research(self, session_id: str, query: str, depth: int = 3) -> bool:
        return await self.send(
            {"type": "research", "sessionId": session_id, "query": query, "depth": depth}
        )

    async def dispatch_embed(self, documents: list[dict[str, Any]]) -> bool:
        return await self.send({"type": "embed", "documents": documents})

    async def dispatch_monitor_check(self, monitor_id: str) -> bool:
        return await self.send({"type": "monitor.check", "monitorId": monitor_id})

    async def dispatch_webhook(
        self, url: str, payload: Any, *, attempt: int = 1, delay_seconds: int | None = None
    ) -> bool:
        return await self.send(
            {"type": "webhook.deliver", "url": url, "payload": payload, "attempt": attempt},
            delay_seconds=delay_seconds,
        )


# ----- Singleton -----

_producer: QueueProducer | None = None
_lock = asyncio.Lock()


async def get_queue_producer() -> QueueProducer:
    global _producer
    async with _lock:
        if _producer is None:
            _producer = QueueProducer()
    return _producer


async def close_queue_producer() -> None:
    global _producer
    if _producer is not None:
        await _producer.aclose()
        _producer = None
