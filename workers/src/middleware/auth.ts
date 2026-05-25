import type { MiddlewareHandler } from "hono"
import { HTTPException } from "hono/http-exception"
import { jwtVerify } from "jose"

import type { AuthContext, Env, Variables } from "../env.js"
import { d1First } from "../lib/d1.js"

interface ApiKeyRow {
  id: number
  user_id: number
  is_active: number
  expires_at: string | null
  scopes: string | null
}

interface UserPlanRow {
  user_id: number
  plan_type: AuthContext["planType"]
  rate_limit: string
  status: string
}

export function requireAuth(): MiddlewareHandler<{ Bindings: Env; Variables: Variables }> {
  return async (c, next) => {
    const auth = await resolveAuth(c.req.raw, c.env)
    if (!auth) {
      throw new HTTPException(401, { message: "Authentication required" })
    }
    c.set("auth", auth)
    await next()
  }
}

export function optionalAuth(): MiddlewareHandler<{ Bindings: Env; Variables: Variables }> {
  return async (c, next) => {
    const auth = await resolveAuth(c.req.raw, c.env)
    if (auth) c.set("auth", auth)
    await next()
  }
}

async function resolveAuth(req: Request, env: Env): Promise<AuthContext | null> {
  const apiKey = req.headers.get("X-API-Key")
  if (apiKey) return resolveByApiKey(apiKey, env)

  const authz = req.headers.get("Authorization")
  if (authz?.startsWith("Bearer ")) return resolveByJwt(authz.slice(7), env)

  return null
}

async function resolveByApiKey(key: string, env: Env): Promise<AuthContext | null> {
  // Fast path: KV
  const cached = await env.API_KEYS.get<AuthContext>(`key:${key}`, "json")
  if (cached) return cached

  // Cold path: D1 (legacy api_keys + new user_api_keys)
  const row = await d1First<ApiKeyRow>(
    env.DB,
    `SELECT id, user_id, is_active, expires_at, scopes
     FROM user_api_keys WHERE key = ?1
     UNION ALL
     SELECT id, user_id, is_active, NULL as expires_at, NULL as scopes
     FROM api_keys WHERE key = ?1
     LIMIT 1`,
    [key],
  )
  if (!row || row.is_active !== 1) return null
  if (row.expires_at && new Date(row.expires_at) < new Date()) return null

  const plan = await d1First<UserPlanRow>(
    env.DB,
    `SELECT user_id, plan_type, rate_limit, status
     FROM subscriptions
     WHERE user_id = ?1 AND status IN ('ACTIVE','TRIALING')
     ORDER BY created_at DESC LIMIT 1`,
    [row.user_id],
  )

  const auth: AuthContext = {
    userId: row.user_id,
    apiKeyId: row.id,
    planType: plan?.plan_type ?? "FREE",
    rateLimit: plan?.rate_limit ?? "10/minute",
    scopes: row.scopes ? (JSON.parse(row.scopes) as string[]) : ["*"],
  }

  // Update last_used_at + cache (waitUntil not available here, fire-and-forget)
  await env.API_KEYS.put(`key:${key}`, JSON.stringify(auth), { expirationTtl: 300 })
  return auth
}

async function resolveByJwt(token: string, env: Env): Promise<AuthContext | null> {
  try {
    const secret = new TextEncoder().encode(env.SECRET_KEY)
    const { payload } = await jwtVerify<{ sub: string; plan?: string }>(token, secret, {
      issuer: "unsearch",
    })
    const userId = Number(payload.sub)
    if (!Number.isFinite(userId)) return null

    const plan = await d1First<UserPlanRow>(
      env.DB,
      `SELECT user_id, plan_type, rate_limit, status
       FROM subscriptions
       WHERE user_id = ?1 AND status IN ('ACTIVE','TRIALING')
       ORDER BY created_at DESC LIMIT 1`,
      [userId],
    )
    return {
      userId,
      apiKeyId: null,
      planType: plan?.plan_type ?? "FREE",
      rateLimit: plan?.rate_limit ?? "10/minute",
      scopes: ["*"],
    }
  } catch {
    return null
  }
}
