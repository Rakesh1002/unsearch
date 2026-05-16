import { DurableObject } from "cloudflare:workers"

import type { Env } from "../env.js"

interface MonitorConfig {
  monitorId: string
  userId: number
  topic: string
  query: string
  intervalMinutes: number
  webhookUrl?: string
  isActive: boolean
  createdAt: number
  lastCheckAt?: number
  seenUrls: string[]
}

interface MonitorResult {
  url: string
  title: string
  snippet: string
  detectedAt: number
}

export class TopicMonitor extends DurableObject<Env> {
  override async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url)

    if (request.method === "POST" && url.pathname === "/configure") {
      const body = (await request.json()) as Omit<MonitorConfig, "createdAt" | "seenUrls" | "isActive"> & {
        isActive?: boolean
      }
      const config: MonitorConfig = {
        ...body,
        isActive: body.isActive ?? true,
        createdAt: Date.now(),
        seenUrls: [],
      }
      await this.ctx.storage.put("config", config)
      const intervalMs = Math.max(60_000, body.intervalMinutes * 60_000)
      await this.ctx.storage.setAlarm(Date.now() + intervalMs)
      return Response.json(config)
    }

    if (request.method === "POST" && url.pathname === "/check") {
      await this.runCheck()
      const config = await this.ctx.storage.get<MonitorConfig>("config")
      return config ? Response.json(config) : new Response("not_found", { status: 404 })
    }

    if (request.method === "GET" && url.pathname === "/results") {
      const results = (await this.ctx.storage.get<MonitorResult[]>("results")) ?? []
      return Response.json({ results })
    }

    if (request.method === "DELETE" && url.pathname === "/") {
      await this.ctx.storage.deleteAlarm()
      await this.ctx.storage.deleteAll()
      return new Response(null, { status: 204 })
    }

    return new Response("not_found", { status: 404 })
  }

  override async alarm(): Promise<void> {
    await this.runCheck()
    const config = await this.ctx.storage.get<MonitorConfig>("config")
    if (config?.isActive) {
      const intervalMs = Math.max(60_000, config.intervalMinutes * 60_000)
      await this.ctx.storage.setAlarm(Date.now() + intervalMs)
    }
  }

  private async runCheck(): Promise<void> {
    const config = await this.ctx.storage.get<MonitorConfig>("config")
    if (!config?.isActive) return

    const resp = await this.env.CONTAINER.fetch(
      new Request("https://container.internal/api/v1/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: config.query, max_results: 20 }),
      }),
    )
    const data = (await resp.json()) as {
      results?: Array<{ url: string; title: string; snippet: string }>
    }

    const seen = new Set(config.seenUrls)
    const fresh = (data.results ?? []).filter((r) => !seen.has(r.url))
    if (fresh.length === 0) {
      config.lastCheckAt = Date.now()
      await this.ctx.storage.put("config", config)
      return
    }

    const detected: MonitorResult[] = fresh.map((r) => ({
      url: r.url,
      title: r.title,
      snippet: r.snippet,
      detectedAt: Date.now(),
    }))

    const existing = (await this.ctx.storage.get<MonitorResult[]>("results")) ?? []
    await this.ctx.storage.put("results", [...detected, ...existing].slice(0, 200))

    fresh.forEach((r) => config.seenUrls.push(r.url))
    config.seenUrls = config.seenUrls.slice(-1000)
    config.lastCheckAt = Date.now()
    await this.ctx.storage.put("config", config)

    if (config.webhookUrl) {
      // Hand off to queue for retried delivery
      await this.env.TASK_QUEUE.send({
        type: "webhook.deliver",
        url: config.webhookUrl,
        payload: { monitorId: config.monitorId, topic: config.topic, results: detected },
        attempt: 1,
      })
    }
  }
}
