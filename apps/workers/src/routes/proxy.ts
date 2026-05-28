import { Hono } from "hono"

import type { Env, Variables } from "../env.js"
import { requireAuth } from "../middleware/auth.js"
import { rateLimitMiddleware } from "../middleware/rate-limit.js"

/**
 * Catch-all proxy for endpoints that require the Python FastAPI backend.
 * Mounted at /api/v1/* AFTER all explicit route groups in index.ts.
 *
 * Heavy ops forwarded as-is: connectors, deep-crawl, complex extraction,
 * enhanced_search v2, and the long tail of legacy endpoints.
 */
export const proxyRoutes = new Hono<{ Bindings: Env; Variables: Variables }>()

proxyRoutes.use("*", requireAuth(), rateLimitMiddleware())

proxyRoutes.all("*", async (c) => {
  const url = new URL(c.req.url)
  // Container has the same path prefix
  const targetUrl = `https://container.internal${url.pathname}${url.search}`

  const headers = new Headers(c.req.raw.headers)
  // Forward auth context as a trusted header so the container can skip its own auth lookup
  const auth = c.get("auth")
  headers.set("X-User-Id", String(auth.userId))
  headers.set("X-User-Plan", auth.planType)
  if (auth.apiKeyId) headers.set("X-Api-Key-Id", String(auth.apiKeyId))
  headers.set("X-Request-Id", c.get("requestId"))

  const proxyReq = new Request(targetUrl, {
    method: c.req.method,
    headers,
    body: ["GET", "HEAD"].includes(c.req.method) ? undefined : c.req.raw.body,
  })
  if (!c.env.CONTAINER) {
    return c.json(
      { error: "container_not_configured", message: "FastAPI container not deployed; this endpoint will return once `wrangler containers deploy` runs." },
      503,
    )
  }
  return c.env.CONTAINER.fetch(proxyReq)
})
