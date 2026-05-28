import { DurableObject } from "cloudflare:workers"

import type { Env } from "../env.js"

interface CheckResult {
  allowed: boolean
  limit: number
  remaining: number
  resetAt: number
}

export class RateLimiter extends DurableObject<Env> {
  override async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url)
    const limit = Number(url.searchParams.get("limit")) || 10
    const windowMs = Number(url.searchParams.get("windowMs")) || 60_000

    const now = Date.now()
    const since = now - windowMs

    // Persist sliding window in DO storage
    const stored = (await this.ctx.storage.get<number[]>("hits")) ?? []
    const fresh = stored.filter((t) => t > since)
    const allowed = fresh.length < limit

    if (allowed) fresh.push(now)
    await this.ctx.storage.put("hits", fresh)

    const earliest = fresh[0] ?? now
    const result: CheckResult = {
      allowed,
      limit,
      remaining: Math.max(0, limit - fresh.length),
      resetAt: earliest + windowMs,
    }

    return Response.json(result)
  }
}
