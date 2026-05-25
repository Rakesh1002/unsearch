"use client"

import { Check, ExternalLink } from "lucide-react"
import { useState } from "react"

import { createCheckout, createPortal } from "~/lib/api"
import { getStoredToken } from "~/lib/auth"
import { PageHeader } from "~/app/_components/page-header"

const PLANS = [
  {
    id: "pro",
    name: "Pro",
    price: "$19",
    quota: "25,000 queries / mo",
    features: ["All search engines", "Email support", "Standard rate limits"],
  },
  {
    id: "growth",
    name: "Growth",
    price: "$49",
    quota: "100,000 queries / mo",
    features: ["Everything in Pro", "Priority queue", "Webhooks", "Higher rate limits"],
    highlight: true,
  },
  {
    id: "scale",
    name: "Scale",
    price: "$149",
    quota: "500,000 queries / mo",
    features: ["Everything in Growth", "Dedicated support", "SLA", "Custom regions"],
  },
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
      <PageHeader title="Billing" description="Upgrade to unlock higher quotas, webhooks, and priority routing.">
        <button
          onClick={openPortal}
          disabled={loading === "portal"}
          className="inline-flex h-9 items-center rounded-md border border-border bg-background px-3.5 text-sm font-medium transition-colors hover:bg-accent disabled:opacity-50"
        >
          {loading === "portal" ? "Opening…" : "Manage subscription"}
          <ExternalLink className="ml-1.5 size-3.5" />
        </button>
      </PageHeader>

      {error && (
        <div className="rounded-md border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {PLANS.map((p) => {
          const highlight = "highlight" in p && p.highlight
          return (
            <div
              key={p.id}
              className={`relative flex flex-col rounded-xl border bg-card p-6 transition-all ${
                highlight
                  ? "border-foreground/30 shadow-md ring-1 ring-foreground/10"
                  : "border-border hover:border-foreground/20"
              }`}
            >
              {highlight && (
                <span className="absolute -top-2.5 right-4 inline-flex items-center rounded-full bg-foreground px-2.5 py-0.5 text-[10px] font-medium tracking-wide text-background uppercase">
                  Most popular
                </span>
              )}
              <h3 className="text-sm font-semibold">{p.name}</h3>
              <div className="mt-3 text-4xl font-semibold tracking-tighter">
                {p.price}
                <span className="text-sm font-normal text-muted-foreground">/mo</span>
              </div>
              <p className="mt-1 text-xs text-muted-foreground">{p.quota}</p>
              <ul className="mt-5 space-y-2 text-sm">
                {p.features.map((f) => (
                  <li key={f} className="flex items-start gap-2 text-muted-foreground">
                    <Check className="mt-0.5 size-3.5 shrink-0 text-foreground" strokeWidth={2.5} />
                    <span>{f}</span>
                  </li>
                ))}
              </ul>
              <button
                onClick={() => upgrade(p.id)}
                disabled={loading === p.id}
                className={`mt-6 inline-flex h-10 items-center justify-center rounded-md px-3 text-sm font-medium transition-colors ${
                  highlight
                    ? "bg-primary text-primary-foreground shadow-sm hover:bg-primary/90"
                    : "border border-border bg-background hover:bg-accent"
                } disabled:opacity-50`}
              >
                {loading === p.id ? "Redirecting…" : `Upgrade to ${p.name}`}
              </button>
            </div>
          )
        })}
      </div>
    </div>
  )
}
