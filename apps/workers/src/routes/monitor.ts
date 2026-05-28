import { Hono } from "hono"
import { z } from "zod"
import { zValidator } from "@hono/zod-validator"

import type { Env, Variables } from "../env.js"
import { requireAuth } from "../middleware/auth.js"
import { rateLimitMiddleware } from "../middleware/rate-limit.js"

export const monitorRoutes = new Hono<{ Bindings: Env; Variables: Variables }>()

monitorRoutes.use("*", requireAuth(), rateLimitMiddleware())

const createMonitorSchema = z.object({
  topic: z.string().min(1).max(100),
  query: z.string().min(1).max(500),
  interval_minutes: z.number().int().min(5).max(1440).default(60),
  webhook_url: z.string().url().optional(),
})

monitorRoutes.post("/topics", zValidator("json", createMonitorSchema), async (c) => {
  const body = c.req.valid("json")
  const auth = c.get("auth")
  const monitorId = crypto.randomUUID()

  const id = c.env.TOPIC_MONITOR.idFromName(monitorId)
  const stub = c.env.TOPIC_MONITOR.get(id)
  await stub.fetch("https://do.internal/configure", {
    method: "POST",
    body: JSON.stringify({
      monitorId,
      userId: auth.userId,
      topic: body.topic,
      query: body.query,
      intervalMinutes: body.interval_minutes,
      webhookUrl: body.webhook_url,
    }),
  })

  return c.json({ monitor_id: monitorId, topic: body.topic, query: body.query, interval_minutes: body.interval_minutes }, 201)
})

monitorRoutes.post("/topics/:id/check", async (c) => {
  const monitorId = c.req.param("id")
  const id = c.env.TOPIC_MONITOR.idFromName(monitorId)
  const stub = c.env.TOPIC_MONITOR.get(id)
  const resp = await stub.fetch("https://do.internal/check", { method: "POST" })
  if (!resp.ok) return c.json({ error: "monitor_not_found" }, 404)
  return c.json(await resp.json())
})

monitorRoutes.get("/topics/:id/results", async (c) => {
  const monitorId = c.req.param("id")
  const id = c.env.TOPIC_MONITOR.idFromName(monitorId)
  const stub = c.env.TOPIC_MONITOR.get(id)
  const resp = await stub.fetch("https://do.internal/results")
  return resp
})

monitorRoutes.delete("/topics/:id", async (c) => {
  const monitorId = c.req.param("id")
  const id = c.env.TOPIC_MONITOR.idFromName(monitorId)
  const stub = c.env.TOPIC_MONITOR.get(id)
  await stub.fetch("https://do.internal/", { method: "DELETE" })
  return new Response(null, { status: 204 })
})
