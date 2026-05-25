import * as Sentry from "@sentry/cloudflare"
import type { MiddlewareHandler } from "hono"

import type { Env, Variables } from "../env.js"

/**
 * Sentry middleware for the Worker. Optional — if SENTRY_DSN is unset,
 * this middleware is a no-op so the Worker still boots.
 *
 * Usage in src/index.ts:
 *   import { sentryMiddleware, wrapSentry } from "./middleware/sentry.js"
 *   app.use("*", sentryMiddleware())
 *   export default wrapSentry({ fetch: app.fetch, ... })
 */
export function sentryMiddleware(): MiddlewareHandler<{ Bindings: Env; Variables: Variables }> {
  return async (c, next) => {
    if (!c.env.SENTRY_DSN) return next()
    try {
      await next()
    } catch (err) {
      Sentry.captureException(err, {
        tags: {
          environment: c.env.ENVIRONMENT,
          path: new URL(c.req.url).pathname,
          method: c.req.method,
        },
        extra: { request_id: c.get("requestId") },
      })
      throw err
    }
  }
}

export function wrapSentry<T>(handler: T): T {
  return Sentry.withSentry(
    (env: Env) => ({
      dsn: env.SENTRY_DSN || "",
      tracesSampleRate: env.ENVIRONMENT === "production" ? 0.1 : 1.0,
      environment: env.ENVIRONMENT,
      release: "unsearch-workers@0.1.0",
    }),
    handler as never,
  ) as T
}
