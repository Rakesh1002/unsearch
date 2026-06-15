"""
Cloudflare Vectorize REST client.

Used by the RAG pipeline to persist embeddings in a Vectorize index when
running on the hosted Cloudflare stack. Falls back to in-memory storage when
Vectorize credentials are not configured.

See: https://developers.cloudflare.com/api/operations/vectorize-search-vectors
"""
import os
from typing import Any, Dict, List, Optional, Tuple
import httpx
import structlog

from app.config import get_settings

logger = structlog.get_logger(__name__)


class VectorizeClient:
    """Async REST client for Cloudflare Vectorize."""

    def __init__(
        self,
        account_id: Optional[str] = None,
        api_token: Optional[str] = None,
        index_name: Optional[str] = None,
    ):
        settings = get_settings()
        self.account_id = account_id or os.environ.get("VECTORIZE_ACCOUNT_ID") or settings.cloudflare_account_id
        self.api_token = api_token or os.environ.get("VECTORIZE_API_TOKEN") or settings.cloudflare_api_token
        self.index_name = index_name or os.environ.get("VECTORIZE_INDEX_NAME") or "unsearch-vectors"
        self.base_url = f"https://api.cloudflare.com/client/v4/accounts/{self.account_id}/vectorize/v2/indexes/{self.index_name}"
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def is_configured(self) -> bool:
        return bool(self.account_id and self.api_token and self.index_name)

    def _client_instance(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(60.0),
                headers={
                    "Authorization": f"Bearer {self.api_token}",
                    "Content-Type": "application/json",
                },
            )
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    async def insert(
        self,
        vectors: List[Dict[str, Any]],
        namespace: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Insert vectors into Vectorize.

        vectors: list of {"id": str, "values": List[float], "metadata": dict}
        """
        payload: Dict[str, Any] = {"vectors": vectors}
        if namespace:
            payload["namespace"] = namespace
        resp = await self._client_instance().post(f"{self.base_url}/insert", json=payload)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("success"):
            errors = data.get("errors", [])
            raise RuntimeError(f"Vectorize insert failed: {errors}")
        return data.get("result", {})

    async def query(
        self,
        vector: List[float],
        top_k: int = 10,
        namespace: Optional[str] = None,
        return_metadata: bool = True,
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """Query Vectorize and return (id, score, metadata) tuples."""
        payload: Dict[str, Any] = {
            "vector": vector,
            "top_k": top_k,
            "return_metadata": return_metadata,
            "return_values": False,
        }
        if namespace:
            payload["namespace"] = namespace
        resp = await self._client_instance().post(f"{self.base_url}/query", json=payload)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("success"):
            errors = data.get("errors", [])
            raise RuntimeError(f"Vectorize query failed: {errors}")

        results = []
        for match in data.get("result", {}).get("matches", []):
            vec_id = match.get("id")
            score = match.get("score", 0.0)
            metadata = match.get("metadata") or {}
            if vec_id is not None:
                results.append((vec_id, score, metadata))
        return results

    async def delete(self, ids: List[str], namespace: Optional[str] = None) -> Dict[str, Any]:
        """Delete vectors by ID."""
        payload: Dict[str, Any] = {"ids": ids}
        if namespace:
            payload["namespace"] = namespace
        resp = await self._client_instance().post(f"{self.base_url}/delete", json=payload)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("success"):
            errors = data.get("errors", [])
            raise RuntimeError(f"Vectorize delete failed: {errors}")
        return data.get("result", {})


_vectorize_client: Optional[VectorizeClient] = None


async def get_vectorize_client() -> VectorizeClient:
    global _vectorize_client
    if _vectorize_client is None:
        _vectorize_client = VectorizeClient()
    return _vectorize_client
