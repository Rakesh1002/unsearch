import type { MiddlewareHandler } from "hono"

import type { Env, Variables } from "../env.js"

export function requestIdMiddleware(): MiddlewareHandler<{ Bindings: Env; Variables: Variables }> {
  return async (c, next) => {
    const incoming = c.req.header("X-Request-Id")
    const requestId = incoming ?? crypto.randomUUID()
    c.set("requestId", requestId)
    c.header("X-Request-Id", requestId)

    const start = Date.now()
    await next()
    const durationMs = Date.now() - start

    try {
      c.env.ANALYTICS.writeDataPoint({
        blobs: [
          c.req.method,
          new URL(c.req.url).pathname,
          c.req.header("cf-ipcountry") ?? "",
          c.get("auth")?.planType ?? "ANON",
          requestId,
        ],
        doubles: [durationMs, c.res.status],
        indexes: [String(c.get("auth")?.userId ?? "0")],
      })
    } catch {
      // Analytics writes are best-effort
    }
  }
}
