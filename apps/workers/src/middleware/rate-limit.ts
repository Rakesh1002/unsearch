import type { MiddlewareHandler } from "hono"
import { HTTPException } from "hono/http-exception"

import type { Env, Variables } from "../env.js"

interface RateLimitResult {
  allowed: boolean
  limit: number
  remaining: number
  resetAt: number
}

export function rateLimitMiddleware(): MiddlewareHandler<{ Bindings: Env; Variables: Variables }> {
  return async (c, next) => {
    const auth = c.get("auth")
    const key = auth ? `user:${auth.userId}` : `ip:${c.req.header("cf-connecting-ip") ?? "unknown"}`
    const limit = parseRate(auth?.rateLimit ?? "10/minute")

    const id = c.env.RATE_LIMITER.idFromName(key)
    const stub = c.env.RATE_LIMITER.get(id)
    const url = new URL(c.req.url)
    url.pathname = "/check"
    url.searchParams.set("limit", String(limit.count))
    url.searchParams.set("windowMs", String(limit.windowMs))

    const resp = await stub.fetch(url.toString(), { method: "POST" })
    const result = (await resp.json()) as RateLimitResult

    c.header("X-RateLimit-Limit", String(result.limit))
    c.header("X-RateLimit-Remaining", String(result.remaining))
    c.header("X-RateLimit-Reset", String(result.resetAt))

    if (!result.allowed) {
      throw new HTTPException(429, {
        message: "Rate limit exceeded",
        res: c.json(
          { error: "rate_limit_exceeded", retry_after_ms: result.resetAt - Date.now() },
          429,
        ),
      })
    }

    await next()
  }
}

function parseRate(spec: string): { count: number; windowMs: number } {
  const [countStr, unit] = spec.split("/")
  const count = Number(countStr) || 10
  const windowMs =
    unit === "second" ? 1_000 : unit === "hour" ? 3_600_000 : unit === "day" ? 86_400_000 : 60_000
  return { count, windowMs }
}
