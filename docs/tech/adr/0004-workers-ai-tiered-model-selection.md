# ADR-0004: Workers AI with tiered model selection

- Status: Accepted
- Date: 2026-04-15
- Deciders: @Rakesh1002

## Context

The AI layer needs to do three things — answer generation, embeddings, and reranking — across a workload that ranges from "give me a 50-token summary" to "synthesize 12 sources into a 2-page research brief." Pricing AI inference is the single biggest cost lever for an LLM-flavored search product.

Constraints that ruled out the obvious choices:

- **Single-LLM strategy (OpenAI-only).** Adds vendor lock that contradicts our positioning. Forces a price-passthrough that destroys margin at the Growth tier.
- **Self-hosted LLM (vLLM on GPUs).** Capex is incompatible with a solo-founder budget. Cold-start latency on autoscaling GPUs is fatal for our p95 target.
- **Bring-your-own-key.** Considered for Enterprise — but bad as a default because the playground onboarding flow then asks the user for an API key before they've seen any value.

## Decision

Use **Cloudflare Workers AI as the default inference provider, with explicit model tiers** exposed via the API.

The tiers are picked per-request via the `model_tier` parameter (RAG) or `model` parameter (search):

| Tier | Model | Use case |
|------|-------|----------|
| `fast` | `@cf/meta/llama-3.1-8b-instruct-fast` | Cheap, low-latency answers; default for free tier |
| `balanced` | `@cf/meta/llama-3.3-70b-instruct-fp8-fast` | Default for Growth tier |
| `reasoning` | `@cf/qwen/qwq-32b` | Multi-step reasoning, research agent |
| `production` | `@cf/openai/gpt-oss-120b` | Highest quality, Enterprise |

Embeddings: `@cf/baai/bge-m3` (1024 dims) → Cloudflare Vectorize. Reranking: `@cf/baai/bge-reranker-base` over the candidate set returned from SearXNG.

Tier selection is **explicit, not hidden behind "auto-mode"** — callers know what they're getting and we can publish per-tier latency / quality / cost benchmarks honestly.

## Consequences

- **Pro:** Single vendor for inference simplifies the cost model and unblocks the Cloudflare-native architecture in [ADR-0001](./0001-cloudflare-native-edge-architecture.md). Workers AI bindings work directly from the edge worker — no separate inference endpoint to manage.
- **Pro:** Tier selection becomes a product differentiator. Tavily and Exa hide the model behind their API; we expose it.
- **Pro:** We can change the underlying model in a tier without breaking callers, because the tier name is the contract, not the model ID.
- **Con:** Workers AI's model catalog is more limited than OpenAI's / Anthropic's. We don't have a "Claude Sonnet" or "GPT-4o" tier today, and some workloads (long-context summarization >32k tokens) currently degrade.
- **Con:** Latency-per-token on Workers AI is higher than on the frontier provider APIs for the same parameter count. For interactive playground use this is acceptable; for batch workloads our research agent has to lean on parallelism, not raw throughput.
- **Con:** We're betting on Cloudflare expanding Workers AI's model catalog over time. If that bet doesn't pay off, the escape hatch is per-tier provider routing (e.g., `production` tier → Anthropic Bedrock) without breaking the tier contract.

## Alternatives considered

- **OpenAI-only with `gpt-4o` / `gpt-4o-mini`.** Rejected — vendor lock, opaque cost passthrough, no edge bindings.
- **Anthropic-only with Claude Sonnet / Haiku.** Same problem, same rejection. (We'd still consider Bedrock as a routing target for the `production` tier if Workers AI quality lags.)
- **Per-request "auto" model selection.** Considered. Rejected because it hides cost from callers and makes our pricing harder to predict. We may revisit when we have multi-tier benchmark data.
- **Self-hosted Ollama / vLLM behind a Cloudflare Tunnel.** Rejected — capex, ops burden, cold-start latency, GPU spot-instance instability.
