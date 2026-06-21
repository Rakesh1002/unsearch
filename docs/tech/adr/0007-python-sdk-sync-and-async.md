# ADR-0007: Python SDK ships sync + async clients

- Status: Accepted
- Date: 2026-05-28
- Deciders: @Rakesh1002

## Context

The Python SDK was the next P0 roadmap item (see [`docs/roadmap.md`](../roadmap.md)). Python's HTTP-client ecosystem is split:

- The Python community is roughly half sync (notebooks, scripts, classic Flask apps) and half async (FastAPI services, Trio/asyncio apps, agent frameworks like LangChain's async path)
- Competitor SDKs:
  - `tavily-python` — sync only
  - `exa-py` — sync only with an `async` wrapper that uses threadpools (not real asyncio)
  - `openai-python` — both, in a single package, sharing the same surface
- Python 3.12+ has improved async ergonomics enough that "sync-only" is increasingly read as "legacy"

Forcing a choice creates friction:

- **Sync-only:** Forces async users to wrap every call in `asyncio.to_thread(...)`, breaks idiomatic FastAPI/LangChain async code, and signals "we didn't think about your stack."
- **Async-only:** Hostile to notebook users and scripts. Breaks the "5-minute pip install demo" because every example has to start with `asyncio.run(...)`.

## Decision

The `unsearch` Python package exports **both `UnSearch` and `AsyncUnSearch`** with **identical method surfaces**.

- Both clients share `httpx` as the underlying HTTP layer (sync + async modes of the same library — no two networking stacks).
- Both use **TypedDict request/response types** and a `py.typed` marker so downstream projects get full mypy / pyright coverage.
- Method names match the TypeScript SDK in snake_case form (`neural_search`, `tavily_search`, `start_research`).
- Streaming endpoints (`stream_search`, `stream_rag`) return `Iterator[StreamEvent]` (sync) or `AsyncIterator[StreamEvent]` (async).
- Polling helpers (`poll_research`) sleep with the matching primitive (`time.sleep` / `asyncio.sleep`).

The package supports Python 3.9–3.13, tested in CI across all five versions.

## Consequences

- **Pro:** Drop-in for both audiences. The pip-install demo and the FastAPI/LangChain reference snippets both work without wrapping.
- **Pro:** Type signatures, method names, and request shapes match the TypeScript SDK 1:1 — onboarding from one to the other is mechanical.
- **Pro:** `httpx` is the single networking dependency. No `requests` + `aiohttp` split, no `requests` legacy quirks.
- **Pro:** Methods exposed as instance methods (not class methods) so each client can be a context manager (`with UnSearch(...) as client:`), which matters because we set a timeout per-client and don't want lingering connections.
- **Con:** ~2× the surface area to maintain. We mitigate by sharing internals (`_request`, `_headers`, `_parse_sse_chunk`) and a single test fixture set that runs against both clients.
- **Con:** Users have to choose which to import. We address this with a top-of-README example that shows both side by side.
- **Con:** Async clients require Python 3.7+ asyncio, which is fine for 3.9+ but rules out hypothetical Python 2 support. Trivially acceptable.

## Alternatives considered

- **Sync-only with a `client.async_session()` helper.** Considered — modeled after `requests-async`. Rejected — the helper would need to wrap every method, doubling the surface anyway.
- **Async-only and tell users to wrap in `asyncio.run`.** Rejected — breaks the notebook experience and is what `exa-py`'s "async wrapper" does badly.
- **Two separate packages (`unsearch` for sync, `unsearch-async` for async).** Rejected — splits documentation, splits issues, doubles release work.
- **Use the `anyio` portable async layer to expose a single surface that works both ways.** Considered. Rejected — anyio is a great library but the runtime branching makes stack traces harder to read, and our use case doesn't need Trio support.
