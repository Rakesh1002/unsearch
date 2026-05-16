import { Hono } from "hono"
import { z } from "zod"
import { zValidator } from "@hono/zod-validator"

import type { Env, Variables } from "../env.js"
import { requireAuth } from "../middleware/auth.js"
import { rateLimitMiddleware } from "../middleware/rate-limit.js"

export const agentRoutes = new Hono<{ Bindings: Env; Variables: Variables }>()

agentRoutes.use("*", requireAuth(), rateLimitMiddleware())

// Tavily-compatible search endpoint
const tavilySearchSchema = z.object({
  query: z.string().min(1).max(400),
  search_depth: z.enum(["basic", "advanced"]).default("basic"),
  include_answer: z.boolean().default(true),
  include_raw_content: z.boolean().default(false),
  include_images: z.boolean().default(false),
  max_results: z.number().int().min(1).max(20).default(5),
  include_domains: z.array(z.string()).optional(),
  exclude_domains: z.array(z.string()).optional(),
})

agentRoutes.post("/search", zValidator("json", tavilySearchSchema), async (c) => {
  // Forward to container — search aggregation logic stays in Python for v1
  return c.env.CONTAINER.fetch(c.req.raw)
})

// Tavily-compatible extract endpoint
const extractSchema = z.object({
  urls: z.union([z.string().url(), z.array(z.string().url()).min(1).max(20)]),
  include_images: z.boolean().default(false),
  extract_depth: z.enum(["basic", "advanced"]).default("basic"),
})

agentRoutes.post("/extract", zValidator("json", extractSchema), async (c) => {
  return c.env.CONTAINER.fetch(c.req.raw)
})

// Deep research agent — handled via Durable Object
const researchSchema = z.object({
  query: z.string().min(1).max(1000),
  depth: z.number().int().min(1).max(5).default(3),
  stream: z.boolean().default(false),
})

agentRoutes.post("/research", zValidator("json", researchSchema), async (c) => {
  const body = c.req.valid("json")
  const auth = c.get("auth")
  const sessionId = crypto.randomUUID()

  const id = c.env.RESEARCH_AGENT.idFromName(sessionId)
  const stub = c.env.RESEARCH_AGENT.get(id)

  await stub.fetch("https://do.internal/start", {
    method: "POST",
    body: JSON.stringify({ sessionId, userId: auth.userId, query: body.query, depth: body.depth }),
  })

  return c.json({
    session_id: sessionId,
    status: "running",
    poll_url: `/api/v1/agent/research/${sessionId}`,
  }, 202)
})

agentRoutes.get("/research/:sessionId", async (c) => {
  const sessionId = c.req.param("sessionId")
  const id = c.env.RESEARCH_AGENT.idFromName(sessionId)
  const stub = c.env.RESEARCH_AGENT.get(id)
  const resp = await stub.fetch("https://do.internal/state")
  if (!resp.ok) return c.json({ error: "session_not_found" }, 404)
  return c.json(await resp.json())
})

agentRoutes.get("/models", (c) =>
  c.json({
    models: [
      { id: "@cf/openai/gpt-oss-120b", name: "GPT OSS 120B", tier: "reasoning" },
      { id: c.env.CLOUDFLARE_REASONING_MODEL, name: "QwQ 32B", tier: "reasoning" },
      { id: c.env.CLOUDFLARE_LLM_MODEL, name: "Llama 3.3 70B", tier: "balanced" },
      { id: "@cf/meta/llama-3.1-8b-instruct", name: "Llama 3.1 8B", tier: "fast" },
      { id: c.env.CLOUDFLARE_EMBEDDING_MODEL, name: "BGE M3 Embeddings", tier: "embedding" },
    ],
  }),
)

agentRoutes.get("/health", (c) =>
  c.json({ status: "ok", environment: c.env.ENVIRONMENT, timestamp: new Date().toISOString() }),
)
