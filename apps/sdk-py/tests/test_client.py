from __future__ import annotations

import httpx
import pytest
import respx

from unsearch import AsyncUnSearch, UnSearch, UnSearchError, __version__

BASE = "https://api.test.local"


def _client() -> UnSearch:
    return UnSearch(api_key="uns_test_key", base_url=BASE)


def test_init_requires_api_key():
    with pytest.raises(ValueError):
        UnSearch(api_key="")


def test_default_base_url_uses_dev_tld():
    client = UnSearch(api_key="x")
    try:
        assert str(client._client.base_url).rstrip("/") == "https://api.unsearch.dev"
    finally:
        client.close()


@respx.mock
def test_search_posts_payload_and_sends_headers():
    route = respx.post(f"{BASE}/api/v1/search").mock(
        return_value=httpx.Response(
            200,
            json={
                "query": "ai agents",
                "results": [
                    {
                        "rank": 1,
                        "title": "Anthropic",
                        "url": "https://www.anthropic.com",
                        "snippet": "Claude",
                        "engine": "google",
                        "score": 0.9,
                    }
                ],
                "response_time_ms": 42,
                "cache_hit": False,
            },
        )
    )
    with _client() as client:
        resp = client.search({"query": "ai agents", "max_results": 1})
    assert resp["query"] == "ai agents"
    assert resp["results"][0]["title"] == "Anthropic"
    req = route.calls[0].request
    assert req.headers["X-API-Key"] == "uns_test_key"
    assert req.headers["User-Agent"] == f"unsearch-python/{__version__}"
    assert req.headers["Content-Type"] == "application/json"


@respx.mock
def test_non_2xx_raises_unsearch_error_with_body():
    respx.post(f"{BASE}/api/v1/search").mock(
        return_value=httpx.Response(401, json={"detail": "invalid api key"})
    )
    with _client() as client:
        with pytest.raises(UnSearchError) as ei:
            client.search({"query": ""})
    assert ei.value.status == 401
    assert ei.value.body == {"detail": "invalid api key"}


@respx.mock
def test_tavily_search_hits_agent_search_path():
    respx.post(f"{BASE}/api/v1/agent/search").mock(
        return_value=httpx.Response(200, json={"answer": "ok", "results": []})
    )
    with _client() as client:
        out = client.tavily_search({"query": "tav", "include_answer": True})
    assert out["answer"] == "ok"


@respx.mock
def test_neural_search_endpoint():
    respx.post(f"{BASE}/api/v1/neural/search").mock(
        return_value=httpx.Response(
            200, json={"query": "q", "matches": [{"id": "doc-1", "score": 0.42}]}
        )
    )
    with _client() as client:
        out = client.neural_search({"query": "q", "top_k": 5})
    assert out["matches"][0]["id"] == "doc-1"


@respx.mock
def test_get_research_url_encodes_session_id():
    route = respx.get(
        f"{BASE}/api/v1/agent/research/sess%2F123%20a"
    ).mock(return_value=httpx.Response(200, json={"session_id": "sess/123 a", "status": "completed", "steps": []}))
    with _client() as client:
        out = client.get_research("sess/123 a")
    assert route.called
    assert out["status"] == "completed"


@respx.mock
def test_204_response_returns_none():
    respx.post(f"{BASE}/api/v1/monitor/topics").mock(
        return_value=httpx.Response(204)
    )
    with _client() as client:
        assert client.create_monitor({"topic": "ai", "query": "ai"}) is None


@respx.mock
def test_stream_rag_parses_sse_events():
    sse_body = (
        "event: token\n"
        "data: hello\n"
        "\n"
        "event: token\n"
        "data:  world\n"
        "\n"
        "event: done\n"
        "data: [DONE]\n"
        "\n"
    )
    respx.post(f"{BASE}/api/v1/rag/query").mock(
        return_value=httpx.Response(
            200, text=sse_body, headers={"Content-Type": "text/event-stream"}
        )
    )
    with _client() as client:
        events = list(client.stream_rag({"query": "x"}))
    assert [e["event"] for e in events] == ["token", "token", "done"]
    assert [e["data"] for e in events] == ["hello", "world", "[DONE]"]


@pytest.mark.asyncio
@respx.mock
async def test_async_search_returns_payload():
    respx.post(f"{BASE}/api/v1/search").mock(
        return_value=httpx.Response(200, json={"query": "async", "results": [], "response_time_ms": 1, "cache_hit": False})
    )
    async with AsyncUnSearch(api_key="uns_async", base_url=BASE) as client:
        out = await client.search({"query": "async"})
    assert out["query"] == "async"


@pytest.mark.asyncio
@respx.mock
async def test_async_error_propagates():
    respx.post(f"{BASE}/api/v1/rag/query").mock(
        return_value=httpx.Response(500, json={"detail": "boom"})
    )
    async with AsyncUnSearch(api_key="x", base_url=BASE) as client:
        with pytest.raises(UnSearchError) as ei:
            await client.rag_query({"query": "x"})
    assert ei.value.status == 500
