"use client"

import { useState } from "react"

import { createCheckout, createPortal } from "~/lib/api"
import { getStoredToken } from "~/lib/auth"

const PLANS = [
  { id: "pro", name: "Pro", price: "$19/mo", quota: "25,000 queries / mo" },
  { id: "growth", name: "Growth", price: "$49/mo", quota: "100,000 queries / mo" },
  { id: "scale", name: "Scale", price: "$149/mo", quota: "500,000 queries / mo" },
] as const

export default function BillingPage() {
  const [loading, setLoading] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function upgrade(plan: "pro" | "growth" | "scale") {
    const token = getStoredToken()
    if (!token) return
    setError(null)
    setLoading(plan)
    try {
      const resp = await createCheckout(token, { plan, interval: "monthly" })
      window.location.href = resp.checkout_url
    } catch (err) {
      setError(err instanceof Error ? err.message : "Checkout failed")
    } finally {
      setLoading(null)
    }
  }

  async function openPortal() {
    const token = getStoredToken()
    if (!token) return
    setError(null)
    setLoading("portal")
    try {
      const resp = await createPortal(token)
      window.location.href = resp.portal_url
    } catch (err) {
      setError(err instanceof Error ? err.message : "Portal unavailable")
    } finally {
      setLoading(null)
    }
  }

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-semibold">Billing</h1>
        <p className="mt-1 text-sm text-[color:var(--color-muted-foreground)]">Upgrade to unlock higher quotas and webhooks.</p>
      </header>

      {error && <p className="text-sm text-[color:var(--color-destructive)]">{error}</p>}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {PLANS.map((p) => (
          <div key={p.id} className="rounded-lg border p-6">
            <h3 className="text-base font-semibold">{p.name}</h3>
            <p className="mt-1 text-2xl font-semibold">{p.price}</p>
            <p className="mt-1 text-sm text-[color:var(--color-muted-foreground)]">{p.quota}</p>
            <button
              onClick={() => upgrade(p.id)}
              disabled={loading === p.id}
              className="mt-6 w-full rounded-md bg-[color:var(--color-primary)] px-3 py-2 text-sm text-[color:var(--color-primary-foreground)] disabled:opacity-50"
            >
              {loading === p.id ? "Redirecting…" : "Upgrade"}
            </button>
          </div>
        ))}
      </div>

      <button
        onClick={openPortal}
        disabled={loading === "portal"}
        className="rounded-md border px-4 py-2 text-sm hover:bg-[color:var(--color-accent)] disabled:opacity-50"
      >
        {loading === "portal" ? "Opening…" : "Manage subscription"}
      </button>
    </div>
  )
}
