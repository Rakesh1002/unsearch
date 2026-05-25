import { Hono } from "hono"
import { HTTPException } from "hono/http-exception"
import { SignJWT } from "jose"
import { z } from "zod"
import { zValidator } from "@hono/zod-validator"

import type { Env, Variables } from "../env.js"
import { callContainer } from "../lib/container.js"
import { d1First, d1Run, nowIso } from "../lib/d1.js"
import { requireAuth } from "../middleware/auth.js"

export const authRoutes = new Hono<{ Bindings: Env; Variables: Variables }>()

const signupSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8).max(128),
  full_name: z.string().min(1).max(255).optional(),
  company: z.string().max(255).optional(),
})

authRoutes.post("/signup", zValidator("json", signupSchema), async (c) => {
  const body = c.req.valid("json")
  const existing = await d1First(c.env.DB, `SELECT id FROM users WHERE email = ?1`, [body.email])
  if (existing) throw new HTTPException(409, { message: "Email already registered" })

  const salt = crypto.randomUUID().replace(/-/g, "")
  const passwordHash = await hashPassword(body.password, salt, c.env.SECRET_KEY)
  const uuid = crypto.randomUUID()
  const verificationToken = crypto.randomUUID().replace(/-/g, "")

  await d1Run(
    c.env.DB,
    `INSERT INTO users (uuid, email, password_hash, salt, full_name, company, verification_token)
     VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)`,
    [uuid, body.email, passwordHash, salt, body.full_name ?? null, body.company ?? null, verificationToken],
  )

  const user = await d1First<{ id: number }>(
    c.env.DB,
    `SELECT id FROM users WHERE email = ?1`,
    [body.email],
  )
  if (!user) throw new HTTPException(500, { message: "Signup failed" })

  // Default subscription: FREE
  await d1Run(
    c.env.DB,
    `INSERT INTO subscriptions (user_id, plan_type, status, search_limit, scrape_limit, rate_limit)
     VALUES (?1, 'FREE', 'ACTIVE', 5000, 500, '10/minute')`,
    [user.id],
  )

  await sendVerificationEmail(c.env, body.email, verificationToken)

  const token = await issueJwt(c.env, user.id, "FREE")
  return c.json({ user_id: user.id, uuid, email: body.email, token, plan: "FREE" }, 201)
})

const loginSchema = z.object({
  email: z.string().email(),
  password: z.string().min(1),
})

authRoutes.post("/login", zValidator("json", loginSchema), async (c) => {
  const body = c.req.valid("json")
  const user = await d1First<{
    id: number
    password_hash: string
    salt: string
    is_active: number
    is_verified: number
  }>(
    c.env.DB,
    `SELECT id, password_hash, salt, is_active, is_verified FROM users WHERE email = ?1`,
    [body.email],
  )
  if (!user || user.is_active !== 1) throw new HTTPException(401, { message: "Invalid credentials" })

  const expected = await hashPassword(body.password, user.salt, c.env.SECRET_KEY)
  if (expected !== user.password_hash) {
    throw new HTTPException(401, { message: "Invalid credentials" })
  }

  await d1Run(c.env.DB, `UPDATE users SET last_login_at = ?1 WHERE id = ?2`, [nowIso(), user.id])

  const sub = await d1First<{ plan_type: string }>(
    c.env.DB,
    `SELECT plan_type FROM subscriptions WHERE user_id = ?1 AND status IN ('ACTIVE','TRIALING') ORDER BY created_at DESC LIMIT 1`,
    [user.id],
  )
  const token = await issueJwt(c.env, user.id, sub?.plan_type ?? "FREE")
  return c.json({ user_id: user.id, token, plan: sub?.plan_type ?? "FREE", verified: user.is_verified === 1 })
})

authRoutes.get("/me", requireAuth(), async (c) => {
  const auth = c.get("auth")
  const user = await d1First(
    c.env.DB,
    `SELECT id, uuid, email, full_name, company, is_verified, created_at FROM users WHERE id = ?1`,
    [auth.userId],
  )
  return c.json({ user, plan: auth.planType, rate_limit: auth.rateLimit })
})

const verifySchema = z.object({ token: z.string().min(10) })
authRoutes.post("/verify", zValidator("json", verifySchema), async (c) => {
  const { token } = c.req.valid("json")
  const user = await d1First<{ id: number }>(
    c.env.DB,
    `SELECT id FROM users WHERE verification_token = ?1`,
    [token],
  )
  if (!user) throw new HTTPException(400, { message: "Invalid verification token" })
  await d1Run(
    c.env.DB,
    `UPDATE users SET is_verified = 1, email_verified_at = ?1, verification_token = NULL WHERE id = ?2`,
    [nowIso(), user.id],
  )
  return c.json({ verified: true })
})

const apiKeyCreateSchema = z.object({
  name: z.string().min(1).max(255),
  description: z.string().max(1000).optional(),
  scopes: z.array(z.string()).optional(),
  expires_in_days: z.number().int().positive().max(3650).optional(),
})

authRoutes.post("/keys", requireAuth(), zValidator("json", apiKeyCreateSchema), async (c) => {
  const auth = c.get("auth")
  const body = c.req.valid("json")
  const key = `unsk_${randomToken(48)}`
  const expiresAt = body.expires_in_days
    ? new Date(Date.now() + body.expires_in_days * 86400_000).toISOString()
    : null
  await d1Run(
    c.env.DB,
    `INSERT INTO user_api_keys (user_id, key, name, description, scopes, expires_at)
     VALUES (?1, ?2, ?3, ?4, ?5, ?6)`,
    [
      auth.userId,
      key,
      body.name,
      body.description ?? null,
      JSON.stringify(body.scopes ?? ["*"]),
      expiresAt,
    ],
  )
  return c.json({ key, name: body.name, scopes: body.scopes ?? ["*"], expires_at: expiresAt }, 201)
})

authRoutes.get("/keys", requireAuth(), async (c) => {
  const auth = c.get("auth")
  const keys = await c.env.DB.prepare(
    `SELECT id, name, description, scopes, last_used_at, request_count, is_active, expires_at, created_at
     FROM user_api_keys WHERE user_id = ?1 ORDER BY created_at DESC`,
  )
    .bind(auth.userId)
    .all()
  return c.json({ keys: keys.results })
})

authRoutes.delete("/keys/:id", requireAuth(), async (c) => {
  const auth = c.get("auth")
  const id = Number(c.req.param("id"))
  await d1Run(
    c.env.DB,
    `UPDATE user_api_keys SET is_active = 0 WHERE id = ?1 AND user_id = ?2`,
    [id, auth.userId],
  )
  return c.json({ revoked: true })
})

// OAuth scaffolding — actual flow handled by providers
authRoutes.get("/callback/:provider", async (c) => {
  const provider = c.req.param("provider")
  const code = c.req.query("code")
  if (!code) throw new HTTPException(400, { message: "Missing code" })
  // Provider exchange handled in Stage 5 frontend integration; this stub
  // exchanges the code at the Container so we don't duplicate the flow.
  return callContainer(
    c.env,
    `https://container.internal/api/v1/auth/callback/${provider}?code=${encodeURIComponent(code)}`,
  )
})

async function hashPassword(password: string, salt: string, pepper: string): Promise<string> {
  const data = new TextEncoder().encode(`${password}${salt}${pepper}`)
  const hash = await crypto.subtle.digest("SHA-256", data)
  return Array.from(new Uint8Array(hash))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("")
}

async function issueJwt(env: Env, userId: number, plan: string): Promise<string> {
  const secret = new TextEncoder().encode(env.SECRET_KEY)
  return new SignJWT({ plan })
    .setProtectedHeader({ alg: "HS256" })
    .setIssuer("unsearch")
    .setSubject(String(userId))
    .setIssuedAt()
    .setExpirationTime("30d")
    .sign(secret)
}

function randomToken(byteLen: number): string {
  const buf = new Uint8Array(byteLen)
  crypto.getRandomValues(buf)
  return Array.from(buf)
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("")
}

async function sendVerificationEmail(env: Env, email: string, token: string): Promise<void> {
  if (!env.RESEND_API_KEY) return
  const verifyUrl = `${env.FRONTEND_URL}/verify?token=${token}`
  await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${env.RESEND_API_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      from: env.EMAIL_FROM,
      to: [email],
      reply_to: env.EMAIL_REPLY_TO,
      subject: "Verify your UnSearch account",
      html: `<p>Welcome to UnSearch.</p><p><a href="${verifyUrl}">Verify your email</a></p>`,
    }),
  }).catch(() => {})
}
