"""
Cloudflare KV-backed cache adapter for FastAPI on Cloudflare Containers.

Replaces the Redis-backed `CacheService` in `app/services/core/cache.py`.
KV is eventually consistent (~60s globally) so it's appropriate for hot
read-mostly caches: search results, neural search results, content safety
classifications. For strict-consistency state (sessions, rate-limit
counters, idempotency tokens), the Worker uses Durable Objects instead.

Containers can't bind to KV directly. We talk to KV via REST. The Worker
also writes to the same namespace, so cache entries set by the Container
are visible at the edge and vice-versa.

Bindings exposed as env vars (set by wrangler container deploy):
  CLOUDFLARE_ACCOUNT_ID
  CLOUDFLARE_API_TOKEN
  CLOUDFLARE_KV_CACHE_NAMESPACE_ID
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

KV_API_BASE = "https://api.cloudflare.com/client/v4"


class KVCache:
    """Async KV-backed cache with JSON envelope + TTL."""

    def __init__(
        self,
        account_id: str | None = None,
        api_token: str | None = None,
        namespace_id: str | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        self.account_id = account_id or os.environ["CLOUDFLARE_ACCOUNT_ID"]
        self.api_token = api_token or os.environ["CLOUDFLARE_API_TOKEN"]
        self.namespace_id = namespace_id or os.environ["CLOUDFLARE_KV_CACHE_NAMESPACE_ID"]
        self._http = httpx.AsyncClient(
            timeout=timeout_seconds,
            headers={"Authorization": f"Bearer {self.api_token}"},
            base_url=f"{KV_API_BASE}/accounts/{self.account_id}/storage/kv/namespaces/{self.namespace_id}",
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    async def get(self, key: str) -> Any | None:
        try:
            resp = await self._http.get(f"/values/{_encode(key)}")
        except httpx.HTTPError as exc:
            logger.warning("kv get failed", extra={"key": key, "err": str(exc)})
            return None
        if resp.status_code == 404:
            return None
        if resp.status_code != 200:
            logger.warning("kv get unexpected status", extra={"key": key, "status": resp.status_code})
            return None
        try:
            return resp.json()
        except Exception:
            return resp.text

    async def set(self, key: str, value: Any, *, ttl_seconds: int | None = None) -> bool:
        body = json.dumps(value, default=str) if not isinstance(value, (str, bytes)) else value
        params = {"expiration_ttl": ttl_seconds} if ttl_seconds and ttl_seconds >= 60 else None
        try:
            resp = await self._http.put(
                f"/values/{_encode(key)}",
                content=body,
                headers={"Content-Type": "application/json"},
                params=params,
            )
        except httpx.HTTPError as exc:
            logger.warning("kv set failed", extra={"key": key, "err": str(exc)})
            return False
        return resp.status_code == 200

    async def delete(self, key: str) -> bool:
        try:
            resp = await self._http.delete(f"/values/{_encode(key)}")
        except httpx.HTTPError as exc:
            logger.warning("kv delete failed", extra={"key": key, "err": str(exc)})
            return False
        return resp.status_code in (200, 404)

    async def exists(self, key: str) -> bool:
        return (await self.get(key)) is not None


def _encode(key: str) -> str:
    """KV keys must be URL-safe. Newlines/spaces would break the path."""
    from urllib.parse import quote
    return quote(key, safe="")


# ----- Singleton -----

_cache: KVCache | None = None
_lock = asyncio.Lock()


async def get_kv_cache() -> KVCache:
    global _cache
    async with _lock:
        if _cache is None:
            _cache = KVCache()
    return _cache


async def close_kv_cache() -> None:
    global _cache
    if _cache is not None:
        await _cache.aclose()
        _cache = None
