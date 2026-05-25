import { Hono } from "hono"
import { HTTPException } from "hono/http-exception"
import { z } from "zod"
import { zValidator } from "@hono/zod-validator"

import type { Env, Variables } from "../env.js"
import { callContainer } from "../lib/container.js"
import { d1First, d1Run } from "../lib/d1.js"
import {
  createBillingPortalSession,
  createCheckoutSession,
  verifyWebhookSignature,
} from "../lib/stripe.js"
import { requireAuth } from "../middleware/auth.js"

export const billingRoutes = new Hono<{ Bindings: Env; Variables: Variables }>()

const checkoutSchema = z.object({
  plan: z.enum(["pro", "growth", "scale"]),
  interval: z.enum(["monthly", "yearly"]).default("monthly"),
})

billingRoutes.post("/checkout", requireAuth(), zValidator("json", checkoutSchema), async (c) => {
  const auth = c.get("auth")
  const { plan, interval } = c.req.valid("json")

  const priceIdMap: Record<string, Record<string, string | undefined>> = {
    pro: { monthly: c.env.STRIPE_PRO_MONTHLY_PRICE_ID, yearly: c.env.STRIPE_PRO_YEARLY_PRICE_ID },
    growth: { monthly: c.env.STRIPE_GROWTH_MONTHLY_PRICE_ID, yearly: c.env.STRIPE_GROWTH_YEARLY_PRICE_ID },
    scale: { monthly: c.env.STRIPE_SCALE_MONTHLY_PRICE_ID, yearly: c.env.STRIPE_SCALE_YEARLY_PRICE_ID },
  }
  const priceId = priceIdMap[plan]?.[interval]
  if (!priceId) throw new HTTPException(400, { message: `No price ID configured for ${plan} ${interval}` })

  const user = await d1First<{ email: string; stripe_customer_id: string | null }>(
    c.env.DB,
    `SELECT email, stripe_customer_id FROM users WHERE id = ?1`,
    [auth.userId],
  )
  if (!user) throw new HTTPException(404, { message: "User not found" })

  const session = await createCheckoutSession(c.env, {
    customerId: user.stripe_customer_id ?? undefined,
    email: user.stripe_customer_id ? undefined : user.email,
    priceId,
    successUrl: `${c.env.FRONTEND_URL}/billing/success?session_id={CHECKOUT_SESSION_ID}`,
    cancelUrl: `${c.env.FRONTEND_URL}/billing`,
    clientReferenceId: String(auth.userId),
  })

  return c.json({ checkout_url: session.url, session_id: session.id })
})

billingRoutes.post("/portal", requireAuth(), async (c) => {
  const auth = c.get("auth")
  const user = await d1First<{ stripe_customer_id: string | null }>(
    c.env.DB,
    `SELECT stripe_customer_id FROM users WHERE id = ?1`,
    [auth.userId],
  )
  if (!user?.stripe_customer_id) {
    throw new HTTPException(400, { message: "No Stripe customer for this user yet" })
  }
  const portal = await createBillingPortalSession(c.env, {
    customerId: user.stripe_customer_id,
    returnUrl: `${c.env.FRONTEND_URL}/billing`,
  })
  return c.json({ portal_url: portal.url })
})

billingRoutes.get("/usage", requireAuth(), async (c) => {
  const auth = c.get("auth")
  const usage = await d1First(
    c.env.DB,
    `SELECT period_start, period_end, search_count, scrape_count, api_calls, search_overage, scrape_overage
     FROM usage_records
     WHERE user_id = ?1
     ORDER BY period_end DESC LIMIT 1`,
    [auth.userId],
  )
  return c.json({ plan: auth.planType, current_period: usage })
})

billingRoutes.post("/webhook", async (c) => {
  const sig = c.req.header("stripe-signature")
  const raw = await c.req.text()
  const ok = await verifyWebhookSignature(raw, sig ?? null, c.env.STRIPE_WEBHOOK_SECRET)
  if (!ok) throw new HTTPException(400, { message: "Invalid signature" })

  const event = JSON.parse(raw) as { id: string; type: string; data: { object: Record<string, unknown> } }

  // Idempotency: ignore if we've seen this event ID
  const seen = await d1First(
    c.env.DB,
    `SELECT id FROM webhook_events WHERE stripe_event_id = ?1`,
    [event.id],
  )
  if (seen) return c.json({ received: true, duplicate: true })

  await d1Run(
    c.env.DB,
    `INSERT INTO webhook_events (stripe_event_id, event_type, data) VALUES (?1, ?2, ?3)`,
    [event.id, event.type, raw],
  )

  // Forward complex business logic to the Container so we don't duplicate state machines
  await callContainer(c.env, "https://container.internal/internal/stripe-webhook", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: raw,
  }).catch((err) => console.error("forward stripe webhook to container failed", err))

  await d1Run(
    c.env.DB,
    `UPDATE webhook_events SET processed = 1, processed_at = ?1 WHERE stripe_event_id = ?2`,
    [new Date().toISOString(), event.id],
  )

  return c.json({ received: true })
})
