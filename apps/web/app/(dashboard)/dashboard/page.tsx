"use client"

import { useEffect, useState } from "react"

import { getUsage, me } from "~/lib/api"
import { getStoredToken } from "~/lib/auth"

interface UsageState {
  plan: string
  rate_limit: string
  email?: string
  current?: {
    search_count?: number
    scrape_count?: number
    api_calls?: number
    period_end?: string
  } | null
}

export default function DashboardOverview() {
  const [state, setState] = useState<UsageState | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const token = getStoredToken()
    if (!token) return
    Promise.all([me(token), getUsage(token)])
      .then(([identity, usage]) => {
        setState({
          plan: identity.plan,
          rate_limit: identity.rate_limit,
          email: (identity.user as { email?: string })?.email,
          current: (usage.current_period as UsageState["current"]) ?? null,
        })
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load usage"))
  }, [])

  if (error) return <p className="text-[color:var(--color-destructive)]">{error}</p>
  if (!state) return <p className="text-[color:var(--color-muted-foreground)]">Loading…</p>

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-semibold">Overview</h1>
        <p className="mt-1 text-sm text-[color:var(--color-muted-foreground)]">
          Signed in as {state.email}. Plan: {state.plan}. Rate limit: {state.rate_limit}.
        </p>
      </header>

      <section className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <Stat label="Search calls (this period)" value={state.current?.search_count ?? 0} />
        <Stat label="Scrape calls" value={state.current?.scrape_count ?? 0} />
        <Stat label="Total API calls" value={state.current?.api_calls ?? 0} />
      </section>

      <section className="rounded-lg border p-6">
        <h2 className="text-base font-medium">Quick start</h2>
        <pre className="mt-4 overflow-x-auto rounded-md bg-[color:var(--color-muted)] p-4 text-sm">
{`curl https://api.unsearch.dev/api/v1/search \\
  -H "X-API-Key: \${UNSEARCH_API_KEY}" \\
  -H "Content-Type: application/json" \\
  -d '{"query": "Cloudflare Workers in 2026"}'`}
        </pre>
        <p className="mt-3 text-sm text-[color:var(--color-muted-foreground)]">
          Generate an API key on the <a className="underline" href="/api-keys">API keys</a> page.
        </p>
      </section>
    </div>
  )
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border p-4">
      <div className="text-xs uppercase tracking-wider text-[color:var(--color-muted-foreground)]">{label}</div>
      <div className="mt-2 text-2xl font-semibold">{value.toLocaleString()}</div>
    </div>
  )
}
