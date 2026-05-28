import { Hono } from "hono"
import { z } from "zod"
import { zValidator } from "@hono/zod-validator"

import type { Env, Variables } from "../env.js"
import { hashKey, kvGetOrCompute } from "../lib/kv-cache.js"
import { searchVectors } from "../lib/vectorize.js"
import { chat, embed, rerank } from "../lib/workers-ai.js"
import { requireAuth } from "../middleware/auth.js"
import { rateLimitMiddleware } from "../middleware/rate-limit.js"

export const neuralRoutes = new Hono<{ Bindings: Env; Variables: Variables }>()

neuralRoutes.use("*", requireAuth(), rateLimitMiddleware())

const neuralSearchSchema = z.object({
  query: z.string().min(1).max(500),
  top_k: z.number().int().min(1).max(50).default(10),
  use_autoprompt: z.boolean().default(false),
  category: z.string().optional(),
  namespace: z.string().optional(),
})

neuralRoutes.post("/search", zValidator("json", neuralSearchSchema), async (c) => {
  const body = c.req.valid("json")

  let query = body.query
  if (body.use_autoprompt) {
    const expanded = await chat(c.env.AI, c.env, [
      {
        role: "system",
        content: "Rewrite the user's terse search query as a verbose information-seeking sentence that's likely to match relevant documents. Output only the rewritten query.",
      },
      { role: "user", content: body.query },
    ], { tier: "fast", maxTokens: 100 })
    query = expanded.response.trim().slice(0, 500)
  }

  const cacheKey = `neural:${await hashKey(JSON.stringify({ query, top_k: body.top_k, namespace: body.namespace, category: body.category }))}`

  const result = await kvGetOrCompute(
    c.env.CACHE,
    cacheKey,
    async () => {
      const [vector] = await embed(c.env.AI, c.env, [query])
      const matches = await searchVectors(c.env.VECTORS, vector, {
        topK: body.top_k,
        namespace: body.namespace,
        filter: body.category ? { category: body.category } : undefined,
        returnMetadata: true,
      })
      return { query, expanded_from: body.query, matches }
    },
    { ttlSeconds: 300 },
  )

  return c.json(result)
})

const highlightsSchema = z.object({
  query: z.string().min(1),
  document: z.string().min(1).max(50_000),
  num_highlights: z.number().int().min(1).max(10).default(3),
})

neuralRoutes.post("/highlights", zValidator("json", highlightsSchema), async (c) => {
  const body = c.req.valid("json")

  const result = await chat(c.env.AI, c.env, [
    {
      role: "system",
      content: `Extract the ${body.num_highlights} most relevant passages from the document that answer the query. Return JSON: {"highlights":[{"text":"...","relevance":0.0-1.0}]}.`,
    },
    { role: "user", content: `Query: ${body.query}\n\nDocument:\n${body.document}` },
  ], { tier: "balanced", maxTokens: 800 })

  let parsed: { highlights: Array<{ text: string; relevance: number }> }
  try {
    parsed = JSON.parse(result.response.match(/\{[\s\S]*\}/)?.[0] ?? "{}")
  } catch {
    parsed = { highlights: [{ text: result.response.slice(0, 500), relevance: 0.5 }] }
  }
  return c.json(parsed)
})

const similarSchema = z.object({
  url: z.string().url().optional(),
  text: z.string().min(1).max(10_000).optional(),
  top_k: z.number().int().min(1).max(50).default(10),
}).refine((x) => x.url || x.text, { message: "Provide url or text" })

neuralRoutes.post("/similar", zValidator("json", similarSchema), async (c) => {
  const body = c.req.valid("json")
  const text = body.text ?? `URL: ${body.url}`
  const [vector] = await embed(c.env.AI, c.env, [text])
  const matches = await searchVectors(c.env.VECTORS, vector, {
    topK: body.top_k,
    returnMetadata: true,
  })
  return c.json({ matches })
})

const predictiveSchema = z.object({
  partial_query: z.string().min(1).max(200),
  num_suggestions: z.number().int().min(1).max(10).default(5),
})

neuralRoutes.post("/predictive", zValidator("json", predictiveSchema), async (c) => {
  const body = c.req.valid("json")
  const result = await chat(c.env.AI, c.env, [
    {
      role: "system",
      content: `Given a partial search query, predict ${body.num_suggestions} likely completions. Return JSON array of strings.`,
    },
    { role: "user", content: body.partial_query },
  ], { tier: "fast", maxTokens: 200 })
  let suggestions: string[] = []
  try {
    suggestions = JSON.parse(result.response.match(/\[[\s\S]*\]/)?.[0] ?? "[]")
  } catch {
    suggestions = result.response.split("\n").map((s) => s.replace(/^[-*\d.\s]+/, "").trim()).filter(Boolean)
  }
  return c.json({ partial_query: body.partial_query, suggestions: suggestions.slice(0, body.num_suggestions) })
})

const rerankSchema = z.object({
  query: z.string().min(1),
  documents: z.array(z.string().min(1)).min(1).max(50),
})

neuralRoutes.post("/rerank", zValidator("json", rerankSchema), async (c) => {
  const body = c.req.valid("json")
  const ranked = await rerank(c.env.AI, c.env, body.query, body.documents)
  return c.json({ ranked })
})

neuralRoutes.get("/categories", (c) =>
  c.json({
    categories: [
      "general",
      "research",
      "news",
      "company",
      "person",
      "tweet",
      "github",
      "pdf",
      "video",
    ],
  }),
)
