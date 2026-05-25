import { DurableObject } from "cloudflare:workers"

import type { Env } from "../env.js"

interface SessionState {
  userId: number
  createdAt: number
  lastSeenAt: number
  cursor?: string
  context: Record<string, unknown>
}

export class SessionManager extends DurableObject<Env> {
  override async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url)
    const path = url.pathname

    if (request.method === "POST" && path === "/init") {
      const body = (await request.json()) as { userId: number }
      const state: SessionState = {
        userId: body.userId,
        createdAt: Date.now(),
        lastSeenAt: Date.now(),
        context: {},
      }
      await this.ctx.storage.put("state", state)
      return Response.json(state)
    }

    if (request.method === "GET" && path === "/state") {
      const state = await this.ctx.storage.get<SessionState>("state")
      return state ? Response.json(state) : new Response("not_found", { status: 404 })
    }

    if (request.method === "PATCH" && path === "/state") {
      const patch = (await request.json()) as Partial<SessionState>
      const current = (await this.ctx.storage.get<SessionState>("state")) ?? null
      if (!current) return new Response("not_found", { status: 404 })
      const next: SessionState = { ...current, ...patch, lastSeenAt: Date.now() }
      await this.ctx.storage.put("state", next)
      return Response.json(next)
    }

    if (request.method === "DELETE" && path === "/") {
      await this.ctx.storage.deleteAll()
      return new Response(null, { status: 204 })
    }

    return new Response("not_found", { status: 404 })
  }
}
