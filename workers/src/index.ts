import { Hono } from "hono"
import { logger } from "hono/logger"
import { secureHeaders } from "hono/secure-headers"
import { trimTrailingSlash } from "hono/trailing-slash"

import type { Env, TaskMessage, Variables } from "./env.js"
import { corsMiddleware } from "./middleware/cors.js"
import { requestIdMiddleware } from "./middleware/logging.js"
import { agentRoutes } from "./routes/agent.js"
import { authRoutes } from "./routes/auth.js"
import { billingRoutes } from "./routes/billing.js"
import { knowledgeRoutes } from "./routes/knowledge.js"
import { monitorRoutes } from "./routes/monitor.js"
import { neuralRoutes } from "./routes/neural.js"
import { proxyRoutes } from "./routes/proxy.js"
import { ragRoutes } from "./routes/rag.js"
import { searchRoutes } from "./routes/search.js"
import { verifyRoutes } from "./routes/verify.js"
import { handleQueueBatch } from "./queue-consumer.js"
import { handleScheduled } from "./scheduled.js"

export { RateLimiter } from "./durable-objects/rate-limiter.js"
export { ResearchAgent } from "./durable-objects/research-agent.js"
export { SessionManager } from "./durable-objects/session-manager.js"
export { TopicMonitor } from "./durable-objects/topic-monitor.js"

const app = new Hono<{ Bindings: Env; Variables: Variables }>()

app.use("*", trimTrailingSlash())
app.use("*", requestIdMiddleware())
app.use("*", logger())
app.use("*", secureHeaders())
app.use("*", corsMiddleware())

app.get("/", (c) =>
  c.json({
    name: c.env.APP_NAME,
    version: c.env.API_VERSION,
    environment: c.env.ENVIRONMENT,
    docs: "https://docs.unsearch.dev",
    status: "ok",
  }),
)

app.get("/health", (c) =>
  c.json({
    status: "ok",
    environment: c.env.ENVIRONMENT,
    timestamp: new Date().toISOString(),
  }),
)

const v1 = new Hono<{ Bindings: Env; Variables: Variables }>()
v1.route("/auth", authRoutes)
v1.route("/search", searchRoutes)
v1.route("/neural", neuralRoutes)
v1.route("/knowledge", knowledgeRoutes)
v1.route("/rag", ragRoutes)
v1.route("/monitor", monitorRoutes)
v1.route("/verify", verifyRoutes)
v1.route("/agent", agentRoutes)
v1.route("/billing", billingRoutes)
v1.route("/", proxyRoutes)

app.route("/api/v1", v1)

app.notFound((c) =>
  c.json(
    { error: "not_found", message: `No route for ${c.req.method} ${c.req.path}` },
    404,
  ),
)

app.onError((err, c) => {
  console.error("unhandled error", err)
  return c.json(
    {
      error: "internal_error",
      message: c.env.ENVIRONMENT === "production" ? "Internal server error" : err.message,
      request_id: c.get("requestId"),
    },
    500,
  )
})

export default {
  fetch: app.fetch,
  async queue(batch: MessageBatch<TaskMessage>, env: Env): Promise<void> {
    await handleQueueBatch(batch, env)
  },
  async scheduled(controller: ScheduledController, env: Env, ctx: ExecutionContext): Promise<void> {
    ctx.waitUntil(handleScheduled(controller, env))
  },
} satisfies ExportedHandler<Env, TaskMessage>
