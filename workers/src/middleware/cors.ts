import { cors } from "hono/cors"
import type { MiddlewareHandler } from "hono"

import type { Env, Variables } from "../env.js"

export function corsMiddleware(): MiddlewareHandler<{ Bindings: Env; Variables: Variables }> {
  return cors({
    origin: (origin, c) => {
      if (!origin) return undefined
      const env = c.env.ENVIRONMENT
      if (env !== "production") return origin
      const allowed = [
        "https://unsearch.dev",
        "https://www.unsearch.dev",
        "https://docs.unsearch.dev",
        c.env.FRONTEND_URL,
      ]
      return allowed.includes(origin) ? origin : undefined
    },
    allowMethods: ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allowHeaders: ["Content-Type", "Authorization", "X-API-Key", "X-Request-Id"],
    exposeHeaders: ["X-Request-Id", "X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
    credentials: true,
    maxAge: 86400,
  })
}
