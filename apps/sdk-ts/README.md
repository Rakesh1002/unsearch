# @unsearch/sdk

Official TypeScript SDK for [UnSearch](https://unsearch.dev) — open-source search API for AI agents.

## Install

```bash
pnpm add @unsearch/sdk
# or npm / yarn / bun
```

## Use

```ts
import { UnSearch } from "@unsearch/sdk"

const client = new UnSearch({ apiKey: process.env.UNSEARCH_API_KEY! })

// Web search
const search = await client.search({ query: "Cloudflare Workers in 2026", max_results: 10 })

// Neural / semantic search over your indexed corpus
const neural = await client.neuralSearch({ query: "vector databases for AI agents", top_k: 5 })

// RAG: retrieval-augmented generation grounded in your corpus
const rag = await client.ragQuery({ query: "How does D1 differ from Postgres?", model_tier: "reasoning" })

// Stream tokens
for await (const chunk of client.streamRag({ query: "Explain Durable Objects" })) {
  if (chunk.event === "token") process.stdout.write(chunk.data)
}

// Multi-step research agent
const session = await client.startResearch({ query: "AI agent landscape 2026", depth: 4 })
const final = await client.pollResearch(session.session_id)
console.log(final.finalAnswer)

// Tavily-compatible drop-in
const tavilyShape = await client.tavilySearch({ query: "...", include_answer: true })
```

## Compatibility

Works in any modern JS runtime: Node ≥18, Bun, Deno, browsers, Cloudflare Workers, Vercel Edge.

## License

Apache-2.0
