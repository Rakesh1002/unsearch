"use client"

import { useState } from "react"

import { search, type SearchResult } from "~/lib/api"

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
      <header>
        <h1 className="text-2xl font-semibold">Playground</h1>
        <p className="mt-1 text-sm text-[color:var(--color-muted-foreground)]">
          Try the Search API live. Use a key from the API keys page.
        </p>
      </header>

      <form onSubmit={onRun} className="space-y-3">
        <input
          required
          type="password"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          placeholder="X-API-Key (unsk_…)"
          className="w-full rounded-md border bg-[color:var(--color-background)] px-3 py-2 text-sm"
        />
        <textarea
          required
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          rows={3}
          className="w-full rounded-md border bg-[color:var(--color-background)] px-3 py-2 text-sm"
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded-md bg-[color:var(--color-primary)] px-4 py-2 text-sm font-medium text-[color:var(--color-primary-foreground)] disabled:opacity-50"
        >
          {loading ? "Searching…" : "Run search"}
        </button>
      </form>

      {error && <p className="text-sm text-[color:var(--color-destructive)]">{error}</p>}
      {latency !== null && (
        <p className="text-xs text-[color:var(--color-muted-foreground)]">Round-trip: {latency} ms</p>
      )}
      {results && (
        <ol className="space-y-3">
          {results.map((r) => (
            <li key={r.url} className="rounded-md border p-4">
              <a href={r.url} target="_blank" rel="noopener" className="font-medium underline">{r.title}</a>
              <p className="mt-1 text-sm text-[color:var(--color-muted-foreground)]">{r.snippet}</p>
              <p className="mt-1 text-xs text-[color:var(--color-muted-foreground)]">{r.engine}{r.score !== null ? ` · score ${r.score.toFixed(2)}` : ""}</p>
            </li>
          ))}
        </ol>
      )}
    </div>
  )
}
