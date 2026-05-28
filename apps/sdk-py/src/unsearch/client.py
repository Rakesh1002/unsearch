from __future__ import annotations

import json
import time
from typing import Any, AsyncIterator, Iterator, Mapping, Optional
from urllib.parse import quote

import httpx

from ._version import __version__
from .errors import UnSearchError
from .types import (
    HighlightsRequest,
    HighlightsResponse,
    IngestRequest,
    IngestResponse,
    MonitorRequest,
    NeuralSearchRequest,
    NeuralSearchResponse,
    RagQueryRequest,
    RagQueryResponse,
    ResearchSession,
    SearchRequest,
    SearchResponse,
    SimilarRequest,
    SimilarResponse,
    StreamEvent,
)

_DEFAULT_BASE_URL = "https://api.unsearch.dev"
_DEFAULT_TIMEOUT = 60.0
_USER_AGENT = f"unsearch-python/{__version__}"


def _headers(api_key: str) -> dict[str, str]:
    return {
        "X-API-Key": api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": _USER_AGENT,
    }


def _error_from_response(resp: httpx.Response) -> UnSearchError:
    body: Any = None
    try:
        body = resp.json()
    except (ValueError, json.JSONDecodeError):
        body = resp.text or None
    return UnSearchError(
        f"UnSearch {resp.status_code}: {resp.reason_phrase or 'request failed'}",
        resp.status_code,
        body,
    )


def _parse_sse_chunk(buffer: str) -> tuple[list[StreamEvent], str]:
    events: list[StreamEvent] = []
    while "\n\n" in buffer:
        block, buffer = buffer.split("\n\n", 1)
        event_name = "message"
        data = ""
        for line in block.splitlines():
            if line.startswith("event:"):
                event_name = line[6:].strip()
            elif line.startswith("data:"):
                data += line[5:].lstrip()
        if data:
            events.append({"event": event_name, "data": data})
    return events, buffer


class UnSearch:
    """Synchronous client for the UnSearch API."""

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: float = _DEFAULT_TIMEOUT,
        transport: Optional[httpx.BaseTransport] = None,
    ) -> None:
        if not api_key:
            raise ValueError("UnSearch: api_key is required")
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=timeout,
            headers=_headers(api_key),
            transport=transport,
        )

    def __enter__(self) -> "UnSearch":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    # ----- Search -----

    def search(self, request: SearchRequest) -> SearchResponse:
        return self._request("POST", "/api/v1/search", json=request)

    def stream_search(self, request: SearchRequest) -> Iterator[StreamEvent]:
        with self._client.stream(
            "POST", "/api/v1/search/stream", json=request
        ) as resp:
            if resp.status_code >= 400:
                raise _error_from_response(resp)
            buffer = ""
            for chunk in resp.iter_text():
                buffer += chunk
                events, buffer = _parse_sse_chunk(buffer)
                yield from events

    # ----- Neural -----

    def neural_search(self, request: NeuralSearchRequest) -> NeuralSearchResponse:
        return self._request("POST", "/api/v1/neural/search", json=request)

    def similar(self, request: SimilarRequest) -> SimilarResponse:
        return self._request("POST", "/api/v1/neural/similar", json=request)

    def highlights(self, request: HighlightsRequest) -> HighlightsResponse:
        return self._request("POST", "/api/v1/neural/highlights", json=request)

    # ----- RAG -----

    def rag_query(self, request: RagQueryRequest) -> RagQueryResponse:
        return self._request("POST", "/api/v1/rag/query", json=request)

    def stream_rag(self, request: RagQueryRequest) -> Iterator[StreamEvent]:
        body = {**request, "stream": True}
        with self._client.stream("POST", "/api/v1/rag/query", json=body) as resp:
            if resp.status_code >= 400:
                raise _error_from_response(resp)
            buffer = ""
            for chunk in resp.iter_text():
                buffer += chunk
                events, buffer = _parse_sse_chunk(buffer)
                yield from events

    def ingest(self, request: IngestRequest) -> IngestResponse:
        return self._request("POST", "/api/v1/rag/ingest", json=request)

    # ----- Research agent -----

    def start_research(self, query: str, *, depth: Optional[int] = None) -> Mapping[str, Any]:
        body: dict[str, Any] = {"query": query}
        if depth is not None:
            body["depth"] = depth
        return self._request("POST", "/api/v1/agent/research", json=body)

    def get_research(self, session_id: str) -> ResearchSession:
        return self._request(
            "GET", f"/api/v1/agent/research/{quote(session_id, safe='')}"
        )

    def poll_research(
        self,
        session_id: str,
        *,
        interval: float = 1.5,
        timeout: float = 120.0,
    ) -> ResearchSession:
        start = time.monotonic()
        while True:
            session = self.get_research(session_id)
            if session.get("status") != "running":
                return session
            if time.monotonic() - start > timeout:
                raise UnSearchError("Research polling timed out", 408)
            time.sleep(interval)

    # ----- Verify -----

    def verify_claim(self, claim: str) -> Mapping[str, Any]:
        return self._request("POST", "/api/v1/verify/claim", json={"claim": claim})

    def verify_source(self, url: str) -> Mapping[str, Any]:
        return self._request("POST", "/api/v1/verify/source", json={"url": url})

    # ----- Topic monitoring -----

    def create_monitor(self, request: MonitorRequest) -> Mapping[str, Any]:
        return self._request("POST", "/api/v1/monitor/topics", json=request)

    # ----- Tavily-compatible drop-in -----

    def tavily_search(self, request: SearchRequest) -> Mapping[str, Any]:
        return self._request("POST", "/api/v1/agent/search", json=request)

    # ----- Internals -----

    def _request(self, method: str, path: str, *, json: Any = None) -> Any:
        resp = self._client.request(method, path, json=json)
        if resp.status_code >= 400:
            raise _error_from_response(resp)
        if resp.status_code == 204 or not resp.content:
            return None
        return resp.json()


class AsyncUnSearch:
    """Asynchronous client for the UnSearch API."""

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: float = _DEFAULT_TIMEOUT,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ) -> None:
        if not api_key:
            raise ValueError("UnSearch: api_key is required")
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=timeout,
            headers=_headers(api_key),
            transport=transport,
        )

    async def __aenter__(self) -> "AsyncUnSearch":
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    # ----- Search -----

    async def search(self, request: SearchRequest) -> SearchResponse:
        return await self._request("POST", "/api/v1/search", json=request)

    async def stream_search(self, request: SearchRequest) -> AsyncIterator[StreamEvent]:
        async with self._client.stream(
            "POST", "/api/v1/search/stream", json=request
        ) as resp:
            if resp.status_code >= 400:
                raise _error_from_response(resp)
            buffer = ""
            async for chunk in resp.aiter_text():
                buffer += chunk
                events, buffer = _parse_sse_chunk(buffer)
                for ev in events:
                    yield ev

    # ----- Neural -----

    async def neural_search(self, request: NeuralSearchRequest) -> NeuralSearchResponse:
        return await self._request("POST", "/api/v1/neural/search", json=request)

    async def similar(self, request: SimilarRequest) -> SimilarResponse:
        return await self._request("POST", "/api/v1/neural/similar", json=request)

    async def highlights(self, request: HighlightsRequest) -> HighlightsResponse:
        return await self._request("POST", "/api/v1/neural/highlights", json=request)

    # ----- RAG -----

    async def rag_query(self, request: RagQueryRequest) -> RagQueryResponse:
        return await self._request("POST", "/api/v1/rag/query", json=request)

    async def stream_rag(self, request: RagQueryRequest) -> AsyncIterator[StreamEvent]:
        body = {**request, "stream": True}
        async with self._client.stream("POST", "/api/v1/rag/query", json=body) as resp:
            if resp.status_code >= 400:
                raise _error_from_response(resp)
            buffer = ""
            async for chunk in resp.aiter_text():
                buffer += chunk
                events, buffer = _parse_sse_chunk(buffer)
                for ev in events:
                    yield ev

    async def ingest(self, request: IngestRequest) -> IngestResponse:
        return await self._request("POST", "/api/v1/rag/ingest", json=request)

    # ----- Research agent -----

    async def start_research(
        self, query: str, *, depth: Optional[int] = None
    ) -> Mapping[str, Any]:
        body: dict[str, Any] = {"query": query}
        if depth is not None:
            body["depth"] = depth
        return await self._request("POST", "/api/v1/agent/research", json=body)

    async def get_research(self, session_id: str) -> ResearchSession:
        return await self._request(
            "GET", f"/api/v1/agent/research/{quote(session_id, safe='')}"
        )

    async def poll_research(
        self,
        session_id: str,
        *,
        interval: float = 1.5,
        timeout: float = 120.0,
    ) -> ResearchSession:
        import asyncio

        start = time.monotonic()
        while True:
            session = await self.get_research(session_id)
            if session.get("status") != "running":
                return session
            if time.monotonic() - start > timeout:
                raise UnSearchError("Research polling timed out", 408)
            await asyncio.sleep(interval)

    # ----- Verify -----

    async def verify_claim(self, claim: str) -> Mapping[str, Any]:
        return await self._request("POST", "/api/v1/verify/claim", json={"claim": claim})

    async def verify_source(self, url: str) -> Mapping[str, Any]:
        return await self._request("POST", "/api/v1/verify/source", json={"url": url})

    # ----- Topic monitoring -----

    async def create_monitor(self, request: MonitorRequest) -> Mapping[str, Any]:
        return await self._request("POST", "/api/v1/monitor/topics", json=request)

    # ----- Tavily-compatible drop-in -----

    async def tavily_search(self, request: SearchRequest) -> Mapping[str, Any]:
        return await self._request("POST", "/api/v1/agent/search", json=request)

    # ----- Internals -----

    async def _request(self, method: str, path: str, *, json: Any = None) -> Any:
        resp = await self._client.request(method, path, json=json)
        if resp.status_code >= 400:
            raise _error_from_response(resp)
        if resp.status_code == 204 or not resp.content:
            return None
        return resp.json()
