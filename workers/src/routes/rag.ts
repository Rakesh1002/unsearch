import { Hono } from "hono"
import { streamSSE } from "hono/streaming"
import { z } from "zod"
import { zValidator } from "@hono/zod-validator"

import type { Env, Variables } from "../env.js"
import { proxyToContainer } from "../lib/container.js"
import { searchVectors, upsertVectors } from "../lib/vectorize.js"
import { chat, chatStream, embed } from "../lib/workers-ai.js"
import { requireAuth } from "../middleware/auth.js"
import { rateLimitMiddleware } from "../middleware/rate-limit.js"

export const ragRoutes = new Hono<{ Bindings: Env; Variables: Variables }>()

ragRoutes.use("*", requireAuth(), rateLimitMiddleware())

const querySchema = z.object({
  query: z.string().min(1).max(1000),
  namespace: z.string().optional(),
  top_k: z.number().int().min(1).max(20).default(5),
  stream: z.boolean().default(false),
  model_tier: z.enum(["fast", "balanced", "reasoning"]).default("balanced"),
})

ragRoutes.post("/query", zValidator("json", querySchema), async (c) => {
  const body = c.req.valid("json")
  const auth = c.get("auth")

  const [queryVec] = await embed(c.env.AI, c.env, [body.query])
  const matches = await searchVectors(c.env.VECTORS, queryVec, {
    topK: body.top_k,
    namespace: body.namespace ?? `user:${auth.userId}`,
    returnMetadata: true,
  })

  const context = matches
    .map((m, i) => `[${i + 1}] ${(m.metadata?.title as string) ?? m.id}\n${(m.metadata?.text as string) ?? ""}`)
    .join("\n\n")

  const messages = [
    {
      role: "system" as const,
      content: "Answer the user's question grounded in the provided context. Cite sources with [n] inline. If the context is insufficient, say so.",
    },
    { role: "user" as const, content: `Question: ${body.query}\n\nContext:\n${context}` },
  ]

  if (body.stream) {
    return streamSSE(c, async (stream) => {
      await stream.writeSSE({ event: "sources", data: JSON.stringify({ matches }) })
      const aiStream = await chatStream(c.env.AI, c.env, messages, {
        tier: body.model_tier,
        maxTokens: 1500,
      })
      const reader = aiStream.getReader()
      const decoder = new TextDecoder()
      while (true) {
        const { value, done } = await reader.read()
        if (done) break
        await stream.writeSSE({ event: "token", data: decoder.decode(value, { stream: true }) })
      }
      await stream.writeSSE({ event: "done", data: "{}" })
    })
  }

  const answer = await chat(c.env.AI, c.env, messages, {
    tier: body.model_tier,
    maxTokens: 1500,
  })
  return c.json({
    query: body.query,
    answer: answer.response,
    sources: matches,
  })
})

const ingestSchema = z.object({
  namespace: z.string().optional(),
  documents: z.array(
    z.object({
      id: z.string().min(1).max(255).optional(),
      text: z.string().min(1).max(50_000),
      metadata: z.record(z.unknown()).optional(),
    }),
  ).min(1).max(100),
})

ragRoutes.post("/ingest", zValidator("json", ingestSchema), async (c) => {
  const body = c.req.valid("json")
  const auth = c.get("auth")
  const namespace = body.namespace ?? `user:${auth.userId}`

  const texts = body.documents.map((d) => d.text)
  const vectors = await embed(c.env.AI, c.env, texts)

  const upserts = body.documents.map((d, i) => ({
    id: d.id ?? crypto.randomUUID(),
    values: vectors[i],
    metadata: { ...d.metadata, text: d.text.slice(0, 2000), userId: auth.userId },
    namespace,
  }))
  const result = await upsertVectors(c.env.VECTORS, upserts)
  return c.json({ ingested: result.count, mutation_id: result.mutationId, namespace })
})

ragRoutes.delete("/namespace/:name", async (c) =>
  proxyToContainer(c.env, c.req.raw as unknown as Request),
)
