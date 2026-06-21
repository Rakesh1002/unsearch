# ADR-0003: Tavily-compatible drop-in API surface

- Status: Accepted
- Date: 2026-04-15
- Deciders: @Rakesh1002

## Context

The Persona A ICP (indie devs shipping AI agents) is overwhelmingly already on Tavily. The friction of switching search providers is not the API call itself — it's the rewrite, the integration tests, the agent prompts written against a specific response shape. Even at 10× cheaper, "rewrite your integration to save money" is a non-starter for someone who already has a paying product on the line.

Empirically, the most successful low-cost-vendor migrations (Resend ← SendGrid, Supabase ← Firebase, Bun ← Node) all leaned into wire-level compatibility, not "you'll like ours better."

## Decision

Expose **Tavily-compatible drop-in endpoints** alongside our native API.

- `POST /api/v1/agent/search` mirrors Tavily's `search()` request and response shape one-for-one
- `POST /api/v1/agent/extract` mirrors Tavily's `extract()`
- `POST /api/v1/agent/research` is the UnSearch-specific deep-research extension (no Tavily equivalent yet — we don't pretend)
- Both Python and TypeScript SDKs expose `tavily_search` / `tavilySearch` methods that hit `/api/v1/agent/search` — explicit naming so the migration intent is obvious in the diff

The native UnSearch surface (`/api/v1/search`, `/api/v1/neural/*`, `/api/v1/rag/*`) exists in parallel and offers strictly richer parameters (engine selection, scraping toggles, model tier selection). New users who don't have Tavily integrations should use the native surface.

## Consequences

- **Pro:** The migration story is "change one base URL + one API key." Lower friction than any other vendor swap on the table.
- **Pro:** Side-by-side dual-write becomes trivial. A caller can call both Tavily and UnSearch with the same request body and diff the response — we use this internally to validate parity.
- **Pro:** Tavily's docs become *de facto* discovery docs for our product. Anyone learning Tavily learns our API.
- **Con:** We're locked into matching Tavily's response shape even when their schema is awkward. Their `include_answer` flag, for example, conflates "give me an answer" with "rank results by relevance to the question," which is two features.
- **Con:** Whenever Tavily breaks their schema, we have to make a call: track them, fork the schema, or version (`/api/v2/agent/search`). The honest answer is "track them for now; fork at the first instance of a clearly-bad change."
- **Con:** Marketing risk — "Tavily-compatible" frames us as the alternative, not the new category leader. We accept this trade for Persona A acquisition; the Persona B / C story leans on the native surface and the Cloudflare-native architecture.

## Alternatives considered

- **Native API only.** Rejected — the migration ask is too high for the ICP.
- **Match every closed-source competitor's surface.** Considered — neural endpoints (Exa-compat) are also matched, but going beyond two means we spend more time chasing schemas than building. Tavily + Exa neural is the cap.
- **Translation layer (proxy that rewrites Tavily-shape requests to UnSearch-shape).** Rejected — adds a hop, leaks abstraction (the proxy needs to know about both schemas, our SDK has to know which mode it's in), and doesn't actually reduce migration friction below the wire-level approach.
