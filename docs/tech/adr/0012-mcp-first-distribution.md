# ADR-0012: MCP-first distribution

- Status: Accepted
- Date: 2026-05-28
- Deciders: @Rakesh1002

## Context

UnSearch was originally planned with SDK-first distribution: `pip install unsearch`, `pnpm add @unsearch/sdk`, `@unsearch/llamaindex` — each SDK as a separate channel, each with its own onboarding (signup → API key → SDK install → first request).

That motion competed against Tavily / Exa / Brave / Linkup / Firecrawl all running the same playbook. The differentiator was price + Tavily compatibility, both of which lost defensibility when Anthropic shipped native `web_search` and Codex CLI shipped first-party search default-on. Native LLM search costs $0 for many users; UnSearch's SDK funnel started with a signup form between intent and proof.

Three 2026 developments reshape the distribution landscape:

1. **MCP registry exploded.** As of April 2026, the official `modelcontextprotocol.io` registry crossed 800 servers, and the broader ecosystem catalog exceeds 13,000. Notion, Stripe, Cloudflare, Slack, Vercel all shipped official MCP servers in 2026.
2. **Tool Search in Claude Code 4.x.** Lazy-loaded tools mean a Claude Code user can register 10+ MCP servers without flooding context. Installing UnSearch alongside other MCPs is no longer a context-cost tradeoff.
3. **Codex CLI's first-party search ships as a native tool**, not as an MCP — but Codex CLI also supports external MCPs. UnSearch can register as an external MCP for Codex users who want verifiable retrieval instead of OpenAI's cache.

The evaluation experience for an MCP is fundamentally different from an SDK:

- **SDK path:** read README → signup form → email verify → API key → SDK install → first call → maybe activate. Typical drop-off: 70–80% before first activated call.
- **MCP path:** `claude mcp add unsearch` → tool appears in next agent call → first verified result returned in one user turn. Free tier built into the MCP server itself, no signup required to evaluate. Effective drop-off: ~20%.

The MCP path is also where ICP-1 (engineering leads at regulated-AI startups) already lives. They're shipping agents on Claude Code, Cursor, Continue.dev, Zed — all MCP-compatible. A single `claude mcp add unsearch` wires all of them simultaneously.

## Decision

UnSearch's headline distribution surface is **MCP-first**. The MCP server is the lead onboarding path, not the SDK. SDKs and the dashboard remain shipped and supported, but they sit below the MCP in messaging hierarchy.

Practical implementation:

- A hosted MCP server at `api.unsearch.dev/mcp` using Streamable HTTP transport.
- A standalone `npx @unsearch/mcp-server` package (`apps/mcp-server/`) that proxies to the hosted endpoint, so `claude mcp add unsearch` works with a single command and no signup.
- Four MCP tools exposed: `search`, `extract`, `research`, `verify_claim`. The last is the wedge differentiator and is exposed at the same hierarchy level as `search`, not buried under "advanced."
- Free tier (5,000 verified searches / month) is built into the MCP server — no signup required to evaluate.
- Auth via `X-API-Key` header for users who want quota beyond Free; D1 lookup applies plan-aware rate limits.
- The MCP server is listed in (a) the official MCP registry at `modelcontextprotocol.io/registry`, (b) `awesome-mcp-servers`, (c) `awesome-llm-tools`, (d) the Anthropic MCP marketplace, (e) the Cursor MCP gallery.

The SDK funnel (`pip install unsearch`, `pnpm add @unsearch/sdk`) is the secondary surface, mostly for customers who graduated from MCP-evaluation to production-SDK integration and want native types / async / batch operations.

## Consequences

We commit to:

- The MCP server is a P0 SLO concern alongside the hosted API. Tool definitions, descriptions, and example invocations are first-class product surfaces — they ship in the launch and are iterated based on telemetry.
- `verify_claim` is exposed as a tool, not as an SDK-only feature. Hiding it in the SDK would defeat the wedge.
- Tool descriptions in the MCP server are written for Claude / Codex / Cursor's planning models, not for human marketers. We optimize for the LLM's tool selection accuracy.
- MCP telemetry (anonymized) flows into PostHog so we can instrument the install-to-activation funnel.
- A community-maintained relationship with the MCP registry maintainers — submit fixes upstream, respond to schema-evolution PRs.

What we knowingly give up:

- The full breadth of the API surface visible in the lead onboarding path. The MCP exposes 4 tools; the underlying REST API has 93 endpoints. Customers who need the long tail upgrade to SDK or REST.
- Some signup-funnel control. No-signup MCP evaluation means the first usage signal is the install, not a form submission. We trade attribution clarity for activation rate.
- Some Tavily-migration story leverage. The Tavily-compatible REST endpoint is still there, but customers coming via MCP do not see "this is a Tavily replacement" as the first message — they see "this is verifiable retrieval."

## Alternatives considered

**1. SDK-first (the prior plan).** Rejected: signup-form friction kills evaluation; every search vendor ships SDKs; UnSearch wins on no axis they don't already cover.

**2. Dashboard-first (signup → playground → API key).** Rejected: dashboard activation rates are dominated by signup form drop-off; doesn't match how ICP-1 actually evaluates retrieval primitives in 2026.

**3. SDK and MCP at equal hierarchy.** Rejected: "equal" means neither is the headline, which forces the marketing site to explain both and dilutes the evaluation path. MCP wins because it has lower friction *and* is where regulated-AI eng leads (ICP-1) already work.

**4. Multi-protocol leadership (MCP + A2A + ACP).** Rejected for v1: A2A and ACP are early; the agent-tooling community is on MCP. Re-evaluate when ACP / AP2 ship at meaningful scale.

**5. Build a custom MCP-superset protocol with verification primitives baked in.** Rejected: zero distribution surface. MCP is the standard the agent ecosystem coalesced around; we ride that distribution rather than fragment it.

## Cross-references

- [ADR-0009](./0009-verifiable-retrieval-as-product-surface.md) — product surface that MCP-first distribution surfaces
- [`docs/strategy/gtm.md`](../strategy/gtm.md) — Phase 1 motion built around MCP launch
- [`docs/strategy/user-journey.md`](../strategy/user-journey.md) — MCP install path vs dashboard path
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [`awesome-mcp-servers`](https://github.com/punkpeye/awesome-mcp-servers)
