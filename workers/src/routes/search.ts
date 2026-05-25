import { Hono } from "hono"
import { streamSSE } from "hono/streaming"
import { z } from "zod"
import { zValidator } from "@hono/zod-validator"

import type { Env, Variables } from "../env.js"
import { callContainer } from "../lib/container.js"
import { d1Run, nowIso } from "../lib/d1.js"
import { hashKey, kvGet, kvSet } from "../lib/kv-cache.js"
import { requireAuth } from "../middleware/auth.js"
import { rateLimitMiddleware } from "../middleware/rate-limit.js"

export const searchRoutes = new Hono<{ Bindings: Env; Variables: Variables }>()

searchRoutes.use("*", requireAuth(), rateLimitMiddleware())

const searchSchema = z.object({
  query: z.string().min(1).max(500),
  engines: z.array(z.string()).optional(),
  max_results: z.number().int().min(1).max(50).default(10),
  language: z.string().length(2).optional(),
  safe_search: z.enum(["off", "moderate", "strict"]).optional(),
  scrape_content: z.boolean().default(false),
  use_cache: z.boolean().default(true),
})

searchRoutes.post("/", zValidator("json", searchSchema), async (c) => {
  const body = c.req.valid("json")
  const auth = c.get("auth")
  const requestId = c.get("requestId")
  const cacheKey = `search:${await hashKey(JSON.stringify(body))}`

  if (body.use_cache) {
    const cached = await kvGet<unknown>(c.env.CACHE, cacheKey)
    if (cached) return c.json({ ...(cached as object), cache_hit: true })
  }

  const upstream = await callContainer(c.env, "https://container.internal/api/v1/search", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-User-Id": String(auth.userId),
      "X-Request-Id": requestId,
    },
    body: JSON.stringify(body),
  })
  if (upstream.status === 503) return upstream
  const data = await upstream.json()

  if (body.use_cache) {
    await kvSet(c.env.CACHE, cacheKey, data, { ttlSeconds: 600 })
  }

  // Best-effort analytics row
  await d1Run(
    c.env.DB,
    `INSERT INTO search_requests (request_id, api_key_id, query, engines, max_results, cache_hit, created_at, completed_at)
     VALUES (?1, ?2, ?3, ?4, ?5, 0, ?6, ?6)`,
    [
      requestId,
      auth.apiKeyId,
      body.query,
      JSON.stringify(body.engines ?? []),
      body.max_results,
      nowIso(),
    ],
  ).catch(() => {})

  return c.json({ ...(data as object), cache_hit: false })
})

const streamSchema = searchSchema.extend({ stream: z.literal(true).default(true) })
searchRoutes.post("/stream", zValidator("json", streamSchema), async (c) => {
  const body = c.req.valid("json")
  const requestId = c.get("requestId")

  return streamSSE(c, async (stream) => {
    await stream.writeSSE({ event: "start", data: JSON.stringify({ request_id: requestId, query: body.query }) })

    const upstream = await callContainer(c.env, "https://container.internal/api/v1/search/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Request-Id": requestId },
      body: JSON.stringify(body),
    })
    if (upstream.status === 503) {
      await stream.writeSSE({ event: "error", data: "container_not_configured" })
      return
    }
    if (!upstream.body) {
      await stream.writeSSE({ event: "error", data: "no_upstream_body" })
      return
    }

    const reader = upstream.body.getReader()
    const decoder = new TextDecoder()
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      const chunk = decoder.decode(value, { stream: true })
      await stream.writeSSE({ event: "chunk", data: chunk })
    }
    await stream.writeSSE({ event: "done", data: JSON.stringify({ request_id: requestId }) })
  })
})

searchRoutes.get("/engines", async (c) => {
  // Static metadata; the Container exposes the live list under /engines
  return c.json({
    engines: [
      { id: "google", category: "general", enabled: true },
      { id: "bing", category: "general", enabled: true },
      { id: "duckduckgo", category: "general", enabled: true },
      { id: "brave", category: "general", enabled: true },
      { id: "wikipedia", category: "knowledge", enabled: true },
      { id: "github", category: "code", enabled: true },
      { id: "stackoverflow", category: "code", enabled: true },
      { id: "arxiv", category: "research", enabled: true },
      { id: "pubmed", category: "research", enabled: true },
      { id: "youtube", category: "video", enabled: true },
    ],
    note: "Full live list at /api/v1/search/engines/live (proxied to container).",
  })
})
