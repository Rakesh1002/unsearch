"use client"

import { ExternalLink, Play, TerminalSquare } from "lucide-react"
import { useState } from "react"

import { search, type SearchResult } from "~/lib/api"
import { PageHeader } from "~/app/_components/page-header"

export default function PlaygroundPage() {
  const [apiKey, setApiKey] = useState("")
  const [query, setQuery] = useState("Cloudflare Workers in 2026")
  const [results, setResults] = useState<SearchResult[] | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [latency, setLatency] = useState<number | null>(null)

  async function onRun(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setResults(null)
    try {
      const resp = await search(apiKey, { query, max_results: 10 })
      setResults(resp.results)
      setLatency(resp.response_time_ms)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-8">
      <PageHeader title="Playground" description="Try the Search API live. Use a key from the API keys page." />

      <form onSubmit={onRun} className="space-y-4 rounded-xl border border-border bg-card p-5">
        <div>
          <label htmlFor="api-key" className="text-sm font-medium">
            API key
          </label>
          <input
            id="api-key"
            required
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder="unsk_…"
            className="mt-1.5 block h-10 w-full rounded-md border border-input bg-background px-3 font-mono text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>
        <div>
          <label htmlFor="query" className="text-sm font-medium">
            Query
          </label>
          <textarea
            id="query"
            required
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            rows={3}
            className="mt-1.5 block w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>
        <div className="flex items-center justify-between">
          <p className="text-xs text-muted-foreground">
            {latency !== null && <span>Last run: {latency} ms</span>}
          </p>
          <button
            type="submit"
            disabled={loading}
            className="inline-flex h-10 items-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground shadow-sm transition-colors hover:bg-primary/90 disabled:opacity-50"
          >
            <Play className="mr-1.5 size-3.5" strokeWidth={2.5} />
            {loading ? "Searching…" : "Run search"}
          </button>
        </div>
      </form>

      {error && (
        <div className="rounded-md border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {results === null && !loading && !error && (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border bg-card px-6 py-14 text-center">
          <div className="inline-flex size-12 items-center justify-center rounded-full bg-muted text-muted-foreground">
            <TerminalSquare className="size-5" />
          </div>
          <p className="mt-3 text-sm text-muted-foreground">Run a query to see live results.</p>
        </div>
      )}

      {results && results.length > 0 && (
        <ol className="space-y-3">
          {results.map((r) => (
            <li
              key={r.url}
              className="group rounded-xl border border-border bg-card p-5 transition-all hover:border-foreground/20 hover:shadow-sm"
            >
              <div className="flex items-start justify-between gap-3">
                <a
                  href={r.url}
                  target="_blank"
                  rel="noopener"
                  className="font-medium text-foreground transition-colors group-hover:text-primary"
                >
                  {r.title}
                </a>
                <a
                  href={r.url}
                  target="_blank"
                  rel="noopener"
                  aria-label="Open link"
                  className="shrink-0 text-muted-foreground transition-colors hover:text-foreground"
                >
                  <ExternalLink className="size-3.5" />
                </a>
              </div>
              <p className="mt-1 truncate font-mono text-xs text-muted-foreground">{r.url}</p>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{r.snippet}</p>
              <div className="mt-3 flex items-center gap-3 text-xs text-muted-foreground">
                <span className="inline-flex items-center rounded-full bg-muted px-2 py-0.5 font-medium">
                  {r.engine}
                </span>
                {r.score !== null && <span>score · {r.score.toFixed(2)}</span>}
              </div>
            </li>
          ))}
        </ol>
      )}

      {results && results.length === 0 && (
        <div className="rounded-xl border border-dashed border-border bg-card px-6 py-10 text-center text-sm text-muted-foreground">
          No results.
        </div>
      )}
    </div>
  )
}
