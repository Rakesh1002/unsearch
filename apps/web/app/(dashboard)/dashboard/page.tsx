"use client"

import Link from "next/link"
import { Activity, ExternalLink, Globe2, KeyRound, ScanSearch } from "lucide-react"
import { useEffect, useState } from "react"

import { getUsage, me } from "~/lib/api"
import { getStoredToken } from "~/lib/auth"
import { CopyButton } from "~/app/_components/copy-button"
import { PageHeader } from "~/app/_components/page-header"

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

const SNIPPET = `curl https://api.unsearch.dev/api/v1/search \\
  -H "X-API-Key: $UNSEARCH_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"query": "Cloudflare Workers in 2026"}'`

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

  if (error) {
    return (
      <div className="rounded-md border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
        {error}
      </div>
    )
  }

  return (
    <div className="space-y-10">
      <PageHeader
        title="Overview"
        description={
          state
            ? `Signed in as ${state.email ?? "—"}. ${state.plan} plan · ${state.rate_limit}`
            : "Loading account…"
        }
      >
        <Link
          href="/api-keys"
          className="inline-flex h-9 items-center rounded-md bg-primary px-3.5 text-sm font-medium text-primary-foreground shadow-sm transition-colors hover:bg-primary/90"
        >
          <KeyRound className="mr-1.5 size-3.5" />
          Create API key
        </Link>
      </PageHeader>

      <section className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <Stat icon={ScanSearch} label="Search calls" value={state?.current?.search_count ?? 0} />
        <Stat icon={Globe2} label="Scrape calls" value={state?.current?.scrape_count ?? 0} />
        <Stat icon={Activity} label="Total API calls" value={state?.current?.api_calls ?? 0} />
      </section>

      <section className="overflow-hidden rounded-xl border border-border bg-card">
        <div className="flex items-center justify-between border-b border-border px-5 py-3">
          <div>
            <h2 className="text-sm font-semibold">Quick start</h2>
            <p className="text-xs text-muted-foreground">Try the Search API in your terminal.</p>
          </div>
          <CopyButton value={SNIPPET} />
        </div>
        <pre className="overflow-x-auto bg-card px-5 py-4 font-mono text-[13px] leading-relaxed">
{SNIPPET}
        </pre>
        <div className="flex items-center justify-between border-t border-border bg-muted/30 px-5 py-2.5 text-xs text-muted-foreground">
          <span>Need a key? Generate one on the API keys page.</span>
          <Link
            href="https://docs.unsearch.dev"
            className="inline-flex items-center gap-1 text-foreground hover:underline"
          >
            Read the docs
            <ExternalLink className="size-3" />
          </Link>
        </div>
      </section>
    </div>
  )
}

function Stat({ icon: Icon, label, value }: { icon: typeof Activity; label: string; value: number }) {
  return (
    <div className="rounded-xl border border-border bg-card p-5 transition-colors hover:border-foreground/20">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium tracking-wide text-muted-foreground uppercase">{label}</span>
        <Icon className="size-4 text-muted-foreground" />
      </div>
      <div className="mt-3 font-mono text-3xl font-semibold tracking-tight">{value.toLocaleString()}</div>
    </div>
  )
}

