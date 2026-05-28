import type { Env } from "../env.js"

const STRIPE_API = "https://api.stripe.com/v1"

export interface StripeCheckoutSession {
  id: string
  url: string
  status: string
}

export async function stripeRequest<T>(
  env: Env,
  path: string,
  init: { method?: string; body?: Record<string, string | number> } = {},
): Promise<T> {
  const body =
    init.body && Object.keys(init.body).length > 0
      ? new URLSearchParams(
          Object.fromEntries(Object.entries(init.body).map(([k, v]) => [k, String(v)])),
        ).toString()
      : undefined

  const resp = await fetch(`${STRIPE_API}${path}`, {
    method: init.method ?? "POST",
    headers: {
      Authorization: `Bearer ${env.STRIPE_SECRET_KEY}`,
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body,
  })

  if (!resp.ok) {
    const text = await resp.text()
    throw new Error(`Stripe ${resp.status}: ${text}`)
  }
  return (await resp.json()) as T
}

export async function createCheckoutSession(
  env: Env,
  args: {
    customerId?: string
    email?: string
    priceId: string
    successUrl: string
    cancelUrl: string
    clientReferenceId?: string
  },
): Promise<StripeCheckoutSession> {
  const body: Record<string, string | number> = {
    mode: "subscription",
    "line_items[0][price]": args.priceId,
    "line_items[0][quantity]": 1,
    success_url: args.successUrl,
    cancel_url: args.cancelUrl,
    allow_promotion_codes: "true",
  }
  if (args.customerId) body.customer = args.customerId
  if (args.email) body.customer_email = args.email
  if (args.clientReferenceId) body.client_reference_id = args.clientReferenceId

  return stripeRequest<StripeCheckoutSession>(env, "/checkout/sessions", { body })
}

export async function createBillingPortalSession(
  env: Env,
  args: { customerId: string; returnUrl: string },
): Promise<{ url: string }> {
  return stripeRequest<{ url: string }>(env, "/billing_portal/sessions", {
    body: { customer: args.customerId, return_url: args.returnUrl },
  })
}

/**
 * Verify Stripe webhook signature.
 *
 * Stripe uses a custom HMAC-SHA256 scheme over `{timestamp}.{rawBody}`.
 * Reference: https://stripe.com/docs/webhooks/signatures
 */
export async function verifyWebhookSignature(
  rawBody: string,
  signatureHeader: string | null,
  secret: string,
  toleranceSeconds = 300,
): Promise<boolean> {
  if (!signatureHeader) return false

  const parts = Object.fromEntries(
    signatureHeader.split(",").map((kv) => kv.split("=") as [string, string]),
  )
  const timestamp = parts.t
  const signature = parts.v1
  if (!timestamp || !signature) return false

  const ageSec = Math.floor(Date.now() / 1000) - Number(timestamp)
  if (Math.abs(ageSec) > toleranceSeconds) return false

  const payload = `${timestamp}.${rawBody}`
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  )
  const mac = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(payload))
  const expected = Array.from(new Uint8Array(mac))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("")
  return timingSafeEq(expected, signature)
}

function timingSafeEq(a: string, b: string): boolean {
  if (a.length !== b.length) return false
  let mismatch = 0
  for (let i = 0; i < a.length; i++) mismatch |= a.charCodeAt(i) ^ b.charCodeAt(i)
  return mismatch === 0
}
