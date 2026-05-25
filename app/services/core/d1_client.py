"""
D1 REST client for FastAPI (running on Cloudflare Containers).

Cloudflare Containers cannot bind to D1 directly. Instead, the container
calls D1's HTTP API. Credentials come from CLOUDFLARE_ACCOUNT_ID +
CLOUDFLARE_API_TOKEN secrets (set via `wrangler secret put` and surfaced
to the container as env vars).

This client is a low-level primitive. Service classes (auth, billing,
search) sit on top of it and expose typed methods.

Reference: https://developers.cloudflare.com/api/operations/cloudflare-d1-query-database
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Iterable, Mapping, Sequence

import httpx

logger = logging.getLogger(__name__)

D1_API_BASE = "https://api.cloudflare.com/client/v4"


class D1Error(RuntimeError):
    """Raised when the D1 REST API returns an error."""

    def __init__(self, message: str, *, status: int | None = None, errors: list[Any] | None = None):
        super().__init__(message)
        self.status = status
        self.errors = errors or []


class D1Client:
    """
    Async D1 REST client.

    Single connection-pooled httpx.AsyncClient, reused across requests.
    Call `await client.aclose()` on shutdown.
    """

    def __init__(
        self,
        account_id: str | None = None,
        api_token: str | None = None,
        database_id: str | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        self.account_id = account_id or os.environ["CLOUDFLARE_ACCOUNT_ID"]
        self.api_token = api_token or os.environ["CLOUDFLARE_API_TOKEN"]
        self.database_id = database_id or os.environ["CLOUDFLARE_D1_DATABASE_ID"]
        self._http = httpx.AsyncClient(
            timeout=timeout_seconds,
            headers={
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
            },
            base_url=f"{D1_API_BASE}/accounts/{self.account_id}/d1/database/{self.database_id}",
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    # ----- Core query methods -----

    async def query(self, sql: str, params: Sequence[Any] | None = None) -> list[dict[str, Any]]:
        """Run a query and return all rows. Use for SELECT statements."""
        result = await self._raw(sql, params)
        return result.get("results", []) or []

    async def first(self, sql: str, params: Sequence[Any] | None = None) -> dict[str, Any] | None:
        """Return the first row or None."""
        rows = await self.query(sql, params)
        return rows[0] if rows else None

    async def execute(self, sql: str, params: Sequence[Any] | None = None) -> dict[str, Any]:
        """
        Run a write statement and return the meta (rows_written, last_row_id, ...).
        Use for INSERT/UPDATE/DELETE.
        """
        result = await self._raw(sql, params)
        return result.get("meta") or {}

    async def batch(
        self, statements: Iterable[Mapping[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Atomic multi-statement execution. Each statement: {"sql": "...", "params": [...]}.
        D1 batches commit as one transaction.
        """
        body = [
            {"sql": s["sql"], "params": list(s.get("params") or [])}
            for s in statements
        ]
        # Cloudflare D1's REST API supports a single multi-statement endpoint
        resp = await self._http.post("/query", json=body)
        return self._unwrap_list(resp)

    # ----- Internals -----

    async def _raw(self, sql: str, params: Sequence[Any] | None) -> dict[str, Any]:
        body: dict[str, Any] = {"sql": sql, "params": list(params or [])}
        resp = await self._http.post("/query", json=body)
        return self._unwrap_single(resp)

    def _unwrap_single(self, resp: httpx.Response) -> dict[str, Any]:
        payload = self._safe_json(resp)
        if not payload.get("success"):
            raise D1Error(
                self._format_errors(payload.get("errors")),
                status=resp.status_code,
                errors=payload.get("errors"),
            )
        result = payload.get("result")
        if isinstance(result, list):
            return result[0] if result else {}
        return result or {}

    def _unwrap_list(self, resp: httpx.Response) -> list[dict[str, Any]]:
        payload = self._safe_json(resp)
        if not payload.get("success"):
            raise D1Error(
                self._format_errors(payload.get("errors")),
                status=resp.status_code,
                errors=payload.get("errors"),
            )
        result = payload.get("result")
        if isinstance(result, list):
            return result
        return [result] if result else []

    @staticmethod
    def _safe_json(resp: httpx.Response) -> dict[str, Any]:
        try:
            return resp.json()
        except Exception as exc:
            raise D1Error(
                f"D1 returned non-JSON response (status={resp.status_code}): {resp.text[:200]}",
                status=resp.status_code,
            ) from exc

    @staticmethod
    def _format_errors(errors: Any) -> str:
        if not errors:
            return "Unknown D1 error"
        if isinstance(errors, list):
            return "; ".join(str(e.get("message", e)) for e in errors)
        return str(errors)


# ----- Singleton helpers -----

_client: D1Client | None = None
_client_lock = asyncio.Lock()


async def get_d1() -> D1Client:
    """
    Get the process-wide D1 client. Lazy-initialized.
    Call `close_d1()` from your FastAPI shutdown handler.
    """
    global _client
    async with _client_lock:
        if _client is None:
            _client = D1Client()
    return _client


async def close_d1() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
