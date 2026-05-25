/**
 * @unsearch/sdk — TypeScript client for the UnSearch API.
 *
 * Works in any modern JS runtime: Node ≥18, Bun, Deno, browsers,
 * Cloudflare Workers, Vercel Edge.
 *
 * @example
 * ```ts
 * import { UnSearch } from "@unsearch/sdk"
 * const client = new UnSearch({ apiKey: process.env.UNSEARCH_API_KEY! })
 * const results = await client.search({ query: "AI agents in 2026" })
 * ```
 */

export interface UnSearchClientOptions {
  apiKey: string
  baseUrl?: string
  timeoutMs?: number
  fetch?: typeof fetch
}

export interface SearchRequest {
  query: string
  engines?: string[]
  max_results?: number
  language?: string
  safe_search?: "off" | "moderate" | "strict"
  scrape_content?: boolean
  use_cache?: boolean
}

export interface SearchResult {
  rank: number
  title: string
  url: string
  snippet: string
  engine: string
  score: number | null
  scraped_content?: { text: string; html?: string } | null
}

export interface SearchResponse {
  query: string
  results: SearchResult[]
  response_time_ms: number
  cache_hit: boolean
  request_id?: string
}

export interface NeuralSearchRequest {
  query: string
  top_k?: number
  use_autoprompt?: boolean
  category?: string
  namespace?: string
}

export interface VectorMatch {
  id: string
  score: number
  metadata?: Record<string, unknown>
}

export interface NeuralSearchResponse {
  query: string
  expanded_from?: string
  matches: VectorMatch[]
}

export interface RagQueryRequest {
  query: string
  namespace?: string
  top_k?: number
  model_tier?: "fast" | "balanced" | "reasoning"
}

export interface RagQueryResponse {
  query: string
  answer: string
  sources: VectorMatch[]
}

export interface ResearchSession {
  session_id: string
  status: "running" | "completed" | "failed"
  steps: Array<{ step: number; query: string; reasoning: string; results: SearchResult[]; finishedAt: number }>
  finalAnswer?: string
}

export class UnSearchError extends Error {
  constructor(message: string, public status: number, public body?: unknown) {
    super(message)
    this.name = "UnSearchError"
  }
}

export class UnSearch {
  private apiKey: string
  private baseUrl: string
  private timeoutMs: number
  private fetcher: typeof fetch

  constructor(opts: UnSearchClientOptions) {
    if (!opts.apiKey) throw new Error("UnSearch: apiKey is required")
    this.apiKey = opts.apiKey
    this.baseUrl = (opts.baseUrl ?? "https://api.unsearch.dev").replace(/\/$/, "")
    this.timeoutMs = opts.timeoutMs ?? 60_000
    this.fetcher = opts.fetch ?? fetch
  }

  // ----- Search -----

  search(req: SearchRequest): Promise<SearchResponse> {
    return this.request<SearchResponse>("POST", "/api/v1/search", req)
  }

  async *streamSearch(req: SearchRequest): AsyncIterable<{ event: string; data: string }> {
    const resp = await this.fetcher(`${this.baseUrl}/api/v1/search/stream`, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify(req),
    })
    if (!resp.ok || !resp.body) throw await this.toError(resp)
    yield* parseSSE(resp.body)
  }

  // ----- Neural -----

  neuralSearch(req: NeuralSearchRequest): Promise<NeuralSearchResponse> {
    return this.request("POST", "/api/v1/neural/search", req)
  }

  similar(req: { url?: string; text?: string; top_k?: number }) {
    return this.request<{ matches: VectorMatch[] }>("POST", "/api/v1/neural/similar", req)
  }

  highlights(req: { query: string; document: string; num_highlights?: number }) {
    return this.request<{ highlights: Array<{ text: string; relevance: number }> }>(
      "POST",
      "/api/v1/neural/highlights",
      req,
    )
  }

  // ----- RAG -----

  ragQuery(req: RagQueryRequest): Promise<RagQueryResponse> {
    return this.request("POST", "/api/v1/rag/query", req)
  }

  async *streamRag(req: RagQueryRequest): AsyncIterable<{ event: string; data: string }> {
    const resp = await this.fetcher(`${this.baseUrl}/api/v1/rag/query`, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify({ ...req, stream: true }),
    })
    if (!resp.ok || !resp.body) throw await this.toError(resp)
    yield* parseSSE(resp.body)
  }

  ingest(req: {
    namespace?: string
    documents: Array<{ id?: string; text: string; metadata?: Record<string, unknown> }>
  }) {
    return this.request<{ ingested: number; mutation_id: string; namespace: string }>(
      "POST",
      "/api/v1/rag/ingest",
      req,
    )
  }

  // ----- Research agent -----

  startResearch(req: { query: string; depth?: number }): Promise<{ session_id: string; status: string }> {
    return this.request("POST", "/api/v1/agent/research", req)
  }

  getResearch(sessionId: string): Promise<ResearchSession> {
    return this.request("GET", `/api/v1/agent/research/${encodeURIComponent(sessionId)}`)
  }

  async pollResearch(
    sessionId: string,
    opts: { intervalMs?: number; timeoutMs?: number } = {},
  ): Promise<ResearchSession> {
    const interval = opts.intervalMs ?? 1500
    const timeout = opts.timeoutMs ?? 120_000
    const start = Date.now()
    while (true) {
      const session = await this.getResearch(sessionId)
      if (session.status !== "running") return session
      if (Date.now() - start > timeout) throw new UnSearchError("Research polling timed out", 408)
      await new Promise((r) => setTimeout(r, interval))
    }
  }

  // ----- Verify -----

  verifyClaim(claim: string) {
    return this.request<Record<string, unknown>>("POST", "/api/v1/verify/claim", { claim })
  }

  verifySource(url: string) {
    return this.request<Record<string, unknown>>("POST", "/api/v1/verify/source", { url })
  }

  // ----- Topic monitoring -----

  createMonitor(req: {
    topic: string
    query: string
    interval_minutes?: number
    webhook_url?: string
  }) {
    return this.request<{ monitor_id: string }>("POST", "/api/v1/monitor/topics", req)
  }

  // ----- Tavily-compatible drop-in -----

  tavilySearch(req: SearchRequest & { include_answer?: boolean }) {
    return this.request("POST", "/api/v1/agent/search", req)
  }

  // ----- Internals -----

  private headers(): Record<string, string> {
    return {
      "X-API-Key": this.apiKey,
      "Content-Type": "application/json",
      "User-Agent": "@unsearch/sdk-ts/0.1.0",
    }
  }

  private async request<T>(method: string, path: string, body?: unknown): Promise<T> {
    const ctrl = new AbortController()
    const timer = setTimeout(() => ctrl.abort(), this.timeoutMs)
    try {
      const resp = await this.fetcher(`${this.baseUrl}${path}`, {
        method,
        headers: this.headers(),
        body: body !== undefined ? JSON.stringify(body) : undefined,
        signal: ctrl.signal,
      })
      if (!resp.ok) throw await this.toError(resp)
      if (resp.status === 204) return undefined as T
      return (await resp.json()) as T
    } finally {
      clearTimeout(timer)
    }
  }

  private async toError(resp: Response): Promise<UnSearchError> {
    let body: unknown = undefined
    try { body = await resp.json() } catch { /* ignore */ }
    return new UnSearchError(`UnSearch ${resp.status}: ${resp.statusText}`, resp.status, body)
  }
}

async function* parseSSE(body: ReadableStream<Uint8Array>): AsyncIterable<{ event: string; data: string }> {
  const reader = body.getReader()
  const decoder = new TextDecoder()
  let buffer = ""
  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const events = buffer.split("\n\n")
    buffer = events.pop() ?? ""
    for (const block of events) {
      const lines = block.split("\n")
      let event = "message"
      let data = ""
      for (const line of lines) {
        if (line.startsWith("event:")) event = line.slice(6).trim()
        else if (line.startsWith("data:")) data += line.slice(5).trimStart()
      }
      if (data) yield { event, data }
    }
  }
}
